"""PFERD adapter. No institution-specific credentials, course aliases or paths."""
from __future__ import annotations

import asyncio
import hashlib
import io
import time
from collections import Counter
from configparser import ConfigParser
from pathlib import Path, PurePath
from urllib.parse import parse_qs, urljoin, urlparse

import aiohttp
import certifi
from bs4 import BeautifulSoup

from .control import CURRENT, checkpoint
from .course_links import course_link, course_link_issues
from .page_index import PageData, PageIndex, decode_element, encode_element
from .security import LoginRequired, get_password
from .storage import Archive, Source, clean_filename, clean_name, data_dir, write_json
from .http_policy import shared_budget


def ref(url):
    import re
    match = re.search(r"/(crs|grp|fold)/(\d+)", url)
    if match:
        return match[1], match[2]
    target = parse_qs(urlparse(url).query).get("target", [""])[0]
    match = re.fullmatch(r"(crs|grp|fold)_(\d+)", target)
    if match:
        return match[1], match[2]
    return None


def memberships(soup, base):
    found = {}
    for link in soup.select("a[href]"):
        url = urljoin(base + "/", link["href"])
        parsed = ref(url)
        name = link.get_text(" ", strip=True)
        if parsed and parsed[0] in {"crs", "grp"} and name and urlparse(url).netloc == urlparse(base).netloc:
            key = "-".join(parsed)
            found.setdefault(key, {"id": key, "name": name, "url": url, "manual": False})
    return list(found.values())


def membership_navigation(soup, base):
    """Read-only membership overview and pager links; never sorting/enrollment actions."""
    urls = []
    for link in soup.select('a[href]'):
        url = urljoin(base + '/', link['href'])
        parts = urlparse(url)
        if parts.netloc != urlparse(base).netloc or parts.scheme != 'https':
            continue
        query = {k.lower(): v[0].lower() for k, v in parse_qs(parts.query).items() if v}
        command = query.get('cmd', '')
        member = query.get('baseclass') == 'ilmembershipoverviewgui' or query.get('cmdclass') == 'ilmembershipblockgui'
        pager = any(x in key for key in query for x in ('offset', 'page', 'trows'))
        if member and command in {'', 'show', 'showmemberships', 'gethtml'} and (pager or query.get('baseclass') == 'ilmembershipoverviewgui'):
            urls.append(url)
    return list(dict.fromkeys(urls))


async def probe(url):
    """Get public login metadata without sending credentials."""
    from .storage import server_url
    import ssl
    base = server_url(url)
    meter = shared_budget().meter()
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30),
                                    connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where())),
                                    **meter.session_options()) as session:
        async with session.get(base + "/login.php") as response:
            response.raise_for_status()
            soup = BeautifulSoup(await response.read(), "html.parser")
            client = parse_qs(response.url.query_string).get("client_id", [""])[0]
            for tag in soup.select("input[name=client_id], a[href], form[action]"):
                candidate = tag.get("value", "") if tag.name == "input" else parse_qs(
                    urlparse(tag.get("href", tag.get("action", ""))).query).get("client_id", [""])[0]
                if candidate and not client:
                    client = candidate
            return {"url": base, "client_id": client,
                    "title": soup.title.get_text(" ", strip=True) if soup.title else urlparse(base).hostname}


def make_crawler(source: Source, emit=lambda event: None, *, discover=False):
    from PFERD.auth import Authenticator
    from PFERD.config import Config
    from PFERD.crawl import CrawlError
    from PFERD.crawl.crawler import anoncritical
    from PFERD.crawl.ilias.async_helper import _iorepeat
    from PFERD.crawl.ilias.ilias_web_crawler import IliasWebCrawler, IliasWebCrawlerSection
    from PFERD.crawl.ilias.kit_ilias_html import IliasElementType as T, IliasPage, IliasSoup
    from PFERD.logging import log
    from PFERD.utils import soupify
    from rich.console import Console

    class StoredAuth(Authenticator):
        async def credentials(self):
            return source.username, get_password(source.id)

        def invalidate_credentials(self):
            raise LoginRequired("ILIAS rejected the sign-in. Update the saved credentials or import a browser session.")

    class NoPrompt(Authenticator):
        async def credentials(self):
            raise LoginRequired("This university requires an interactive sign-in. Import a fresh browser session.")

    class GuardedSession:
        def __init__(self, session):
            self.session = session

        def get(self, *args, **kwargs):
            return self.session.get(*args, **kwargs)

        def post(self, url, **kwargs):
            parsed = urlparse(str(url))
            if parsed.scheme != "https" or parsed.hostname not in {urlparse(source.url).hostname, source.idp_host}:
                raise LoginRequired("SSO attempted to send credentials to an unapproved host. Check the identity provider.")
            # Do not forward credential-bearing POSTs through redirects to another host.
            return self.session.post(url, allow_redirects=False, **kwargs)

    class Crawler(IliasWebCrawler):
        def __init__(self, *args):
            super().__init__(*args)
            self.roots = []
            self.files = {}
            self.skipped = Counter()
            self.current = None
            self.seen = set()
            self.download_issues = {}
            self.course_label = ""
            self.page_labels = {}
            self.empty_meetings = set()
            self.course_folders = {}
            self.active_roots = []
            self.attempted_roots = []
            self.membership_complete = False
            self.failed_checks = {}
            self.http = None
            from .storage import excluded_files
            self.excluded = excluded_files(source.id)
            self.page_index = PageIndex(data_dir() / 'sources' / source.id / 'page-index.json', source,
                                        self._fetch_page)

        async def run(self):
            # Match the pinned PFERD HttpCrawler lifecycle, with public aiohttp
            # middleware/response hooks covering redirects, auth and streams.
            import ssl
            from PFERD import __version__ as pferd_version
            from PFERD.crawl.crawler import Crawler as BaseCrawler
            self._request_count = 0
            self._cookie_jar = aiohttp.CookieJar()
            self._load_cookies()
            self.http = shared_budget().meter()
            success = False
            try:
                async with aiohttp.ClientSession(headers={'User-Agent':f'PFERD/{pferd_version}'},
                        cookie_jar=self._cookie_jar,
                        connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where())),
                        timeout=aiohttp.ClientTimeout(total=15*60, connect=self._http_timeout,
                            sock_connect=self._http_timeout, sock_read=self._http_timeout),
                        requote_redirect_url=False, **self.http.session_options()) as session:
                    self.session = session
                    try:
                        await BaseCrawler.run(self)
                        success = self.error_free
                    finally:
                        del self.session
                self._save_cookies()
            finally:
                await self.page_index.close(success and not discover)

        async def _authenticate(self):
            await checkpoint()
            if source.login == "session":
                raise LoginRequired("Your browser session has expired. Import a new session to continue.")
            if source.login == "shibboleth":
                self._shibboleth_login._tfa_auth = NoPrompt("no-prompt")
                await self._shibboleth_login.login(GuardedSession(self.session))
                return
            async with self.session.get(source.url + "/login.php", params={
                "client_id": source.client_id, "cmd": "force_login"}) as response:
                response.raise_for_status()
                soup = soupify(await response.read())
                page_url = str(response.url)
            form = soup.select_one("form[name=login_form]")
            if not form:
                form = next((f for f in soup.select("form") if f.select_one('input[type=password]')), None)
            if not form:
                raise LoginRequired("No standard ILIAS login form found. Use a browser session for this installation.")
            action = urljoin(page_url, form.get("action", ""))
            if urlparse(action).scheme != "https" or urlparse(action).netloc != urlparse(source.url).netloc:
                raise LoginRequired("The login form points to another server. Choose SSO or a browser session.")
            fields = {i["name"]: i.get("value", "") for i in form.select('input[type=hidden][name]')}
            passwords = form.select('input[type=password][name]')
            users = form.select('input[type=text][name], input[type=email][name], input:not([type])[name]')
            if len(passwords) != 1 or not users:
                raise LoginRequired("This login form is not supported. Import a browser session.")
            user, password = await self._auth.credentials()
            fields[users[0]["name"]] = user
            fields[passwords[0]["name"]] = password
            submit = form.select_one('input[type=submit][name], button[type=submit][name]')
            if submit:
                fields[submit["name"]] = submit.get("value", "")
            async with self.session.post(action, data=fields, allow_redirects=False) as response:
                response.raise_for_status()
                if response.status in (301, 302, 303):
                    location = urljoin(action, response.headers.get("Location", ""))
                    if urlparse(location).netloc != urlparse(source.url).netloc:
                        raise LoginRequired("Sign-in redirected outside this ILIAS. Use SSO or a browser session.")
                    async with self.session.get(location) as final:
                        final.raise_for_status()
                        result = IliasSoup(soupify(await final.read()), str(final.url))
                else:
                    result = IliasSoup(soupify(await response.read()), str(response.url))
            if not IliasPage.is_logged_in(result):
                self._auth.invalidate_credentials()

        async def _fetch_page(self, url):
            await checkpoint()
            auth = await self._current_auth_id()
            expects_export = parse_qs(urlparse(url).query).get('cmd', [''])[0].lower() == 'exporthtml'
            for attempt in range(2):
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    data = PageData(await response.read(), str(response.url))
                    # Link exports have no normal ILIAS chrome; match PFERD's existing resolver contract.
                    query = {k.lower(): v[0].lower() for k, v in parse_qs(urlparse(data.url).query).items()}
                    link_export = 'cmdnode' in query and query.get('cmd') == 'exporthtml'
                    unavailable_link = (query.get('baseclass') == 'illinkresourcehandlergui'
                                        and query.get('cmd') == 'infoscreen')
                    logged_in = data.logged_in()
                    if logged_in is None:
                        logged_in = IliasPage.is_logged_in(IliasSoup(soupify(data.body), data.url))
                    accepted = (link_export or unavailable_link) if expects_export else logged_in
                    if accepted:
                        return data
                    if expects_export and logged_in:
                        raise CrawlError('ILIAS did not return the requested link export.')
                # An unexpected page can lack the usual ILIAS chrome even
                # when the session is fine. Check before attempting sign-in.
                dashboard = source.url + '/ilias.php?baseClass=ilDashboardGUI&cmd=show&view=2'
                if url != dashboard:
                    async with self.session.get(dashboard) as response:
                        response.raise_for_status()
                        if IliasPage.is_logged_in(IliasSoup(soupify(await response.read()), str(response.url))):
                            raise CrawlError('ILIAS returned an unexpected page while the session was active.')
                if not attempt:
                    await self.authenticate(auth)
            raise LoginRequired("Sign-in expired or was rejected by ILIAS.")

        def _parse_page(self, data, root_page_allowed=False):
            soup = IliasSoup(BeautifulSoup(data.body, 'lxml'), data.url)
            # ILIAS show/hide-session controls are navigation, never child folders.
            for link in soup.soup.select('a[href*="crs_next_sess"], a[href*="crs_prev_sess"]'):
                link.decompose()
            return self._verify_page(soup, data.url, root_page_allowed)

        async def _get_page(self, url, root_page_allowed=False):
            await checkpoint()
            self._page_progress(url)
            try:
                page = self._parse_page(await self.page_index.page(url), root_page_allowed)
                self.failed_checks.pop(url, None)
                return page
            except Exception as exc:
                self.record_failed_check(url, exc)
                raise

        def record_failed_check(self, url, exc):
            status = getattr(exc, 'status', None)
            reason = 'server_missing' if status in (404, 410) else 'access_denied' if status in (401, 403) else 'check_failed'
            self.failed_checks[url] = {'path': self.page_labels.get(url, self.current['name'] if self.current else 'Course list'),
                                       'reason': reason, 'exception': type(exc).__name__}

        def check_evidence(self):
            return {'course_scope': [{'id': r['id'], 'name': r['name']} for r in self.attempted_roots],
                    'intended_scope': [{'id': r['id'], 'name': r['name']} for r in self.active_roots],
                    'enumeration_complete': self.membership_complete,
                    'check_issues': list(self.failed_checks.values()),
                    'http': self.http.snapshot() if self.http else {}}

        def _page_progress(self, url):
            if self.current:
                emit({"event": "progress", "message": "Checking " + self.page_labels.get(url, self.course_label)})

        def _parse_plan(self, data, parent):
            page = IliasPage(self._parse_page(data), parent)
            next_stage = page.get_next_stage_element()
            if next_stage:
                return {'stage': encode_element(next_stage)}
            elements = page.get_child_elements()
            if parent is None and (info := page.get_info_tab()):
                elements.append(info)
            description = page.get_description()
            return {'stage': None, 'elements': [encode_element(e) for e in elements],
                    'description': str(description) if description else None,
                    'next': encode_element(page.get_next_page_element())}

        @anoncritical
        async def _crawl_ilias_page(self, url, current_element, cl, expected_course_id=None, crawl_nested_courses=False):
            # Keep the pinned PFERD traversal contract: stage navigation, pagination, description,
            # deterministic deduplication, then bounded child tasks. Only parsing is cached.
            if expected_course_id is not None:
                return await super()._crawl_ilias_page(url, current_element, cl, expected_course_id,
                                                       crawl_nested_courses)

            @_iorepeat(3, 'crawling folder')
            async def gather_elements(initial_url):
                async with cl:
                    next_url, parent = initial_url, current_element
                    stages = set()
                    while next_url:
                        if next_url in stages:
                            raise CrawlError('ILIAS page navigation contains a loop.')
                        stages.add(next_url)
                        await checkpoint()
                        self._page_progress(next_url)
                        try:
                            plan = await self.page_index.plan(next_url, parent, self._parse_plan)
                            self.failed_checks.pop(next_url, None)
                        except Exception as exc:
                            self.record_failed_check(next_url, exc)
                            raise
                        stage = decode_element(plan['stage'])
                        if stage is None:
                            children = [decode_element(e) for e in plan['elements']]
                            data = await self.page_index.page(next_url)
                            candidates = data.empty_meeting_candidates(children)
                            for child in children:
                                if child.url in candidates and self.page_index.verified_empty_meeting(child):
                                    self.empty_meetings.add(child.url)
                            return plan
                        next_url, parent = stage.url, stage

            elements, description, pages = [], None, set()
            while True:
                if url in pages:
                    raise CrawlError('ILIAS pagination contains a loop.')
                pages.add(url)
                plan = await gather_elements(url)
                elements.extend(decode_element(e) for e in plan['elements'])
                description = description or plan['description']
                next_page = decode_element(plan['next'])
                if not next_page:
                    break
                url = next_page.url
            if description:
                await self._download_description(cl.path, BeautifulSoup(description, 'html.parser'))
            tasks = []
            for element in sorted(elements, key=lambda e: e.id()):
                handle = await self._handle_ilias_element(cl.path, element, crawl_nested_courses)
                if handle:
                    tasks.append(asyncio.create_task(handle))
            try:
                await self.gather(tasks)
            finally:
                await asyncio.gather(*tasks, return_exceptions=True)

        async def _resolve_link_target(self, export_url):
            data = await self.page_index.page(export_url)
            query = {k.lower(): v[0].lower() for k, v in parse_qs(urlparse(data.url).query).items()}
            if query.get('baseclass') == 'illinkresourcehandlergui' and query.get('cmd') == 'infoscreen':
                return 'none'
            if 'cmdnode' not in query or query.get('cmd') != 'exporthtml':
                raise CrawlError('ILIAS did not return the requested link export.')
            return BeautifulSoup(data.body, 'lxml')

        async def _run(self):
            # Establish one authenticated session before speculative requests.
            # Expired-session redirects can otherwise rotate cookies while the
            # login POST completes, invalidating the newly accepted sign-in.
            dashboard = await self._get_page(source.url + "/ilias.php?baseClass=ilDashboardGUI&cmd=show&view=2")
            if not discover:
                self.page_index.start_prefetch()
            found = {r['id']: r for r in memberships(dashboard.soup, source.url)}
            pending = membership_navigation(dashboard.soup, source.url)
            visited = set()
            while pending and len(visited) < 40:
                url = pending.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                page = await self._get_page(url)
                found.update({r['id']: r for r in memberships(page.soup, source.url)})
                pending.extend(u for u in membership_navigation(page.soup, source.url) if u not in visited)
            if pending:
                raise CrawlError('Course list exceeded its page limit. Add specific course links.')
            self.roots = list(found.values())
            self.membership_complete = True
            # Also retain explicitly selected folder/course URLs, including institutions with a custom dashboard.
            selected = []
            for url in source.targets:
                absolute, problem = course_link(source.url, url)
                if problem:
                    continue
                identity = ref(absolute)
                key = "-".join(identity) if identity else hashlib.sha256(absolute.encode()).hexdigest()[:12]
                selected.append(found.get(key, {"id": key, "name": "Course " + key,
                                                 "url": absolute, "manual": True}))
            combined = list({r['id']: r for r in [*self.roots, *selected]}.values())
            write_json(data_dir() / 'sources' / source.id / 'courses.json', combined)
            if discover:
                self.roots = combined
                return
            roots = self.roots if source.automatic_courses else list({r['id']: r for r in selected}.values())
            self.active_roots = roots
            from .naming import course_folders
            self.course_folders = course_folders(source, roots, persist=True)
            if not roots and not course_link_issues(source):
                raise CrawlError("No courses found. Add a direct course or folder link in source settings.")
            emit({'event': 'progress', 'message': 'Checking known content pages…'})
            for index, root in enumerate(roots, 1):
                self.attempted_roots.append(root)
                self.current = root
                self.course_label = f"{root['name']} ({index}/{len(roots)})"
                self.page_labels = {}
                self.empty_meetings = set()
                emit({"event": "progress", "message": "Checking " + self.course_label})
                self._visited_urls = {}
                task = await self._handle_ilias_page(root["url"], None, PurePath(root["id"]))
                if task:
                    await task

        async def _handle_ilias_element(self, parent_path, element, crawl_nested_courses=False):
            await checkpoint()
            if element.type == T.MEETING and element.url in self.empty_meetings:
                # Keep discovery/path accounting; the fresh parent summary confirms there are no materials.
                await self.crawl(PurePath(parent_path, element.name))
                return None
            if element.type == T.COURSE:
                return None
            identity = ref(element.url)
            if identity and identity[0] == "grp" and "-".join(identity) not in {r["id"] for r in self.roots}:
                self.skipped["groups without membership"] += 1
                return None
            if element.type in {T.FORUM, T.TEST, T.SURVEY, T.WIKI, T.SCORM_LEARNING_MODULE,
                                T.LEARNING_MODULE_HTML, T.MEDIA_POOL, T.BLOG, T.INDIVIDUAL_ASSESSMENT}:
                self.skipped[element.type.value] += 1
                return None
            self.page_labels[element.url] = " / ".join([self.course_label, *parent_path.parts[1:], element.name])
            return await super()._handle_ilias_element(parent_path, element, crawl_nested_courses)

        async def _handle_file(self, element, element_path, is_video=False):
            identity = element.type.value + ":" + element.id()
            if identity in self.seen:
                return None
            self.seen.add(identity)
            emit({"event": "progress", "message": "Checking " + self.page_labels.get(
                element.url, " / ".join([self.course_label, element.name]))})
            tag = hashlib.sha256(identity.encode()).hexdigest()[:20]
            raw = PurePath("files", tag, clean_name(element.name, 110))
            parts = [self.course_folders[self.current['id']]]
            parts.extend(clean_name(p, 50) for p in element_path.parts[1:-1])
            parts.append(clean_filename(element.name, 100))
            # Cap depth and names for Windows; discarded hierarchy is still in the source link.
            if len(parts) > 5:
                parts = parts[:3] + parts[-2:]
            path = "/".join(parts)
            if path in self.excluded:
                return None
            self.files[identity] = {"raw": raw, "path": path, "url": element.url,
                                    "course_id": self.current['id'], "course_name": self.current['name'],
                                    "logical": '/'.join([self.current['id'], *parts[1:]])}
            return await super()._handle_file(element, raw, is_video)

        async def _stream_from_url(self, element, sink, bar, is_video):
            await checkpoint()
            emit({"event": "progress", "message": "Downloading " + element.name})
            auth = await self._current_auth_id()
            extension = Path(element.name).suffix.casefold()
            for attempt in range(2):
                async with self.session.get(element.url) as response:
                    if response.status in (401, 403) and not attempt:
                        pass
                    else:
                        if response.status >= 400:
                            identity = element.type.value + ':' + element.id()
                            self.download_issues[identity] = ('server_missing' if response.status in (404, 410) else
                                                              'access_denied' if response.status in (401, 403) else 'transfer_failed')
                        response.raise_for_status()
                        html_error = "html" in response.content_type and extension not in {".html", ".htm"}
                        if not html_error:
                            first = await response.content.read(1024)
                            if extension == ".pdf" and not first.lstrip().startswith(b"%PDF-"):
                                self.download_issues[element.type.value + ':' + element.id()] = 'invalid_content'
                                raise CrawlError("Server returned an invalid PDF.")
                            if extension == ".zip" and not first.startswith(b"PK"):
                                self.download_issues[element.type.value + ':' + element.id()] = 'invalid_content'
                                raise CrawlError("Server returned an invalid ZIP.")
                            if response.content_length:
                                bar.set_total(response.content_length)
                            await checkpoint()
                            sink.file.write(first)
                            bar.advance(len(first))
                            async for chunk in response.content.iter_chunked(256 * 1024):
                                await checkpoint()
                                sink.file.write(chunk)
                                bar.advance(len(chunk))
                            sink.done()
                            return
                if not attempt:
                    await self.authenticate(auth)
            raise LoginRequired("A download returned a login page. Sign in again.")

    parser = ConfigParser(interpolation=None)
    state = data_dir() / "sources" / source.id
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    parser["DEFAULT"] = {"working_dir": str(state), "on_conflict": "no-delete", "redownload": "always-smart",
                         "tasks": "8", "task_delay": "0", "windows_paths": "yes"}
    parser["crawl:source"] = {"type": "ilias-web", "base_url": source.url,
                              "client_id": source.client_id or "default", "login_type": "local" if source.login != "shibboleth" else "shibboleth",
                              "target": "desktop", "auth": "auth:source", "output_dir": "cache",
                              "videos": "yes" if source.videos else "no", "forums": "no", "links": "internet-shortcut"}
    log.console = Console(file=io.StringIO(), force_terminal=False)
    log.output_explain = log.output_status = log.output_report = log.output_not_deleted = False
    return Crawler("crawl:source", IliasWebCrawlerSection(parser["crawl:source"]), Config(parser),
                   {"auth:source": StoredAuth("auth:source")})


async def synchronize(source: Source, emit=lambda event: None, *, discover=False):
    source.validate()
    crawler = make_crawler(source, emit, discover=discover)
    start = time.monotonic()
    try:
        if CURRENT.get():
            await crawler.run()
        else:
            await asyncio.wait_for(crawler.run(), timeout=90 if discover else 5400)
        if discover:
            return {"courses": crawler.roots}
        state = data_dir() / "sources" / source.id
        archive = Archive(state, Path(source.destination))
        from .naming import align_folders, named_path
        align_folders(archive, source, crawler.active_roots)
        counts = Counter()
        material_counts = Counter()
        unavailable = []
        paths = set()
        from .storage import excluded_files
        excluded = excluded_files(source.id)
        emit({"event": "progress", "message": "Saving files…"})
        for identity, item in crawler.files.items():
            await checkpoint()
            if item["path"] in excluded:
                continue
            raw = state / "cache" / item["raw"]
            if not raw.is_file() or item["raw"] not in crawler.report.known_files:
                unavailable.append(identity)
                continue
            from .routing import route_file
            destination, relative, route = route_file(source, identity, item['course_id'], item['logical'], item['path'])
            action = archive.publish(identity, raw, relative, destination=destination, route=route,
                                     metadata={'course_id':item['course_id'], 'course_name':item['course_name'],
                                               'logical':item['logical'], 'original_path':item['path'],
                                               'folder_names_applied': dict(source.folder_names)})
            counts[action] += 1
            material_counts[action] += 1
            paths.add(item["raw"])
            emit({"event": "progress", "message": f"{action.capitalize()}: {raw.name}"})
        emit({"event": "progress", "message": "Saving course information…"})
        for path in sorted(crawler.report.known_files):
            await checkpoint()
            if path in paths or path.parts[0] == "files":
                continue
            raw = state / "cache" / path
            if raw.is_file():
                # Preserve HTML resource-relative paths while isolating course information.
                original = path.as_posix().split('/')
                relative = '/'.join([crawler.course_folders.get(original[0], original[0]), *original[1:]])
                relative = named_path(source, path.as_posix(), relative)
                counts[archive.publish("generated:" + str(path), raw, "Course info/" + relative,
                                       metadata={'course_id': original[0],
                                                 'folder_names_applied': dict(source.folder_names)})] += 1
        result = {"counts": dict(counts), "material_counts": dict(material_counts), "files": sum(counts.values()), "unavailable": len(unavailable),
                  "unavailable_items": [crawler.files[identity]['path'] for identity in unavailable],
                  "unavailable_details": [{'path': crawler.files[identity]['path'],
                                           'reason': crawler.download_issues.get(identity, 'not_confirmed')}
                                          for identity in unavailable],
                  'transfer_issues': [{'path': crawler.files[identity]['path'], 'reason': reason}
                                      for identity, reason in crawler.download_issues.items() if identity in crawler.files],
                  "skipped": dict(crawler.skipped), "warnings": len(crawler.report.encountered_warnings),
                  "errors": len(crawler.report.encountered_errors), "seconds": round(time.monotonic() - start, 2),
                  "partial": not crawler.error_free, 'course_link_issues': course_link_issues(source)}
        result['pages'] = {'checked': len(crawler.page_index.used_urls), 'parsed': crawler.page_index.parsed,
                           'reused': crawler.page_index.reused,
                           'empty_meetings': len(crawler.page_index.empty_meetings)}
        result.update(crawler.check_evidence())
        write_json(state / "last-result.json", result)
        return result
    except BaseException as exc:
        exc.sync_evidence = crawler.check_evidence()
        raise
