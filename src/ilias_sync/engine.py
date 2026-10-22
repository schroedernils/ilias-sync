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

from .security import LoginRequired, get_password
from .storage import Archive, Source, clean_name, data_dir, write_json


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
            found.setdefault(key, {"id": key, "name": name, "url": url})
    return list(found.values())


async def probe(url):
    """Get public login metadata without sending credentials."""
    from .storage import server_url
    import ssl
    base = server_url(url)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30),
                                    connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where()))) as session:
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

        async def _authenticate(self):
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

        async def _get_page(self, url, root_page_allowed=False):
            auth = await self._current_auth_id()
            for attempt in range(2):
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    soup = IliasSoup(soupify(await response.read()), str(response.url))
                    if IliasPage.is_logged_in(soup):
                        # ILIAS show/hide-session controls are navigation, never child folders.
                        for link in soup.soup.select('a[href*="crs_next_sess"], a[href*="crs_prev_sess"]'):
                            link.decompose()
                        return self._verify_page(soup, url, root_page_allowed)
                if not attempt:
                    await self.authenticate(auth)
            raise LoginRequired("Sign-in expired or was rejected by ILIAS.")

        async def _run(self):
            dashboard = await self._get_page(source.url + "/ilias.php?baseClass=ilDashboardGUI&cmd=show&view=2")
            self.roots = memberships(dashboard.soup, source.url)
            # Also retain explicitly selected folder/course URLs, including institutions with a custom dashboard.
            selected = []
            for url in source.targets:
                absolute = urljoin(source.url + "/", url)
                if urlparse(absolute).netloc != urlparse(source.url).netloc:
                    raise ValueError("A selected course belongs to a different ILIAS server.")
                identity = ref(absolute)
                key = "-".join(identity) if identity else hashlib.sha256(absolute.encode()).hexdigest()[:12]
                selected.append(next((r for r in self.roots if r["id"] == key),
                                     {"id": key, "name": "Course " + key, "url": absolute}))
            if discover:
                return
            roots = self.roots if source.automatic_courses else selected
            if not roots:
                raise CrawlError("No courses found. Add a direct course or folder link in source settings.")
            for root in roots:
                self.current = root
                emit({"event": "progress", "message": "Checking " + root["name"]})
                self._visited_urls = {}
                task = await self._handle_ilias_page(root["url"], None, PurePath(root["id"]))
                if task:
                    await task

        async def _handle_ilias_element(self, parent_path, element, crawl_nested_courses=False):
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
            return await super()._handle_ilias_element(parent_path, element, crawl_nested_courses)

        async def _handle_file(self, element, element_path, is_video=False):
            identity = element.type.value + ":" + element.id()
            if identity in self.seen:
                return None
            self.seen.add(identity)
            tag = hashlib.sha256(identity.encode()).hexdigest()[:20]
            raw = PurePath("files", tag, clean_name(element.name, 110))
            parts = [clean_name(self.current["name"], 55) + " [" + self.current["id"] + "]"]
            parts.extend(clean_name(p, 50) for p in element_path.parts[1:-1])
            parts.append(clean_name(element.name, 100))
            # Cap depth and names for Windows; discarded hierarchy is still in the source link.
            if len(parts) > 5:
                parts = parts[:3] + parts[-2:]
            self.files[identity] = {"raw": raw, "path": "/".join(parts), "url": element.url}
            return await super()._handle_file(element, raw, is_video)

        async def _stream_from_url(self, element, sink, bar, is_video):
            auth = await self._current_auth_id()
            extension = Path(element.name).suffix.casefold()
            for attempt in range(2):
                async with self.session.get(element.url) as response:
                    if response.status in (401, 403) and not attempt:
                        pass
                    else:
                        response.raise_for_status()
                        html_error = "html" in response.content_type and extension not in {".html", ".htm"}
                        if not html_error:
                            first = await response.content.read(1024)
                            if extension == ".pdf" and not first.lstrip().startswith(b"%PDF-"):
                                raise CrawlError("Server returned an invalid PDF.")
                            if extension == ".zip" and not first.startswith(b"PK"):
                                raise CrawlError("Server returned an invalid ZIP.")
                            if response.content_length:
                                bar.set_total(response.content_length)
                            sink.file.write(first)
                            bar.advance(len(first))
                            async for chunk in response.content.iter_chunked(256 * 1024):
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
                         "tasks": "1", "task_delay": "1", "windows_paths": "yes"}
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
    await asyncio.wait_for(crawler.run(), timeout=90 if discover else 5400)
    if discover:
        return {"courses": crawler.roots}
    state = data_dir() / "sources" / source.id
    archive = Archive(state, Path(source.destination))
    counts = Counter()
    unavailable = []
    paths = set()
    for identity, item in crawler.files.items():
        raw = state / "cache" / item["raw"]
        if not raw.is_file() or item["raw"] not in crawler.report.known_files:
            unavailable.append(identity)
            continue
        action = archive.publish(identity, raw, item["path"])
        counts[action] += 1
        paths.add(item["raw"])
        emit({"event": "progress", "message": f"{action.capitalize()}: {raw.name}"})
    for path in sorted(crawler.report.known_files):
        if path in paths or path.parts[0] == "files":
            continue
        raw = state / "cache" / path
        if raw.is_file():
            # Preserve HTML resource-relative paths while isolating course information.
            counts[archive.publish("generated:" + str(path), raw, "Course info/" + str(path).replace("\\", "/"))] += 1
    result = {"counts": dict(counts), "files": sum(counts.values()), "unavailable": len(unavailable),
              "skipped": dict(crawler.skipped), "warnings": len(crawler.report.encountered_warnings),
              "errors": len(crawler.report.encountered_errors), "seconds": round(time.monotonic() - start, 2),
              "partial": not crawler.error_free}
    write_json(state / "last-result.json", result)
    return result
