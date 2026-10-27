"""Reuse parsing, never freshness: every indexed page is read again on each run."""
from __future__ import annotations

import asyncio
import copy
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re
from urllib.parse import parse_qs, urljoin, urlparse

from lxml import etree, html

from .control import checkpoint
from .storage import read_json, write_json

PAGE_REQUESTS = 64
_UI_ID = re.compile(r'il_ui_fw_[a-zA-Z0-9_]+|il_signal_[a-zA-Z0-9_]+|table_[a-f0-9]{32}')
_READ_COMMANDS = {'', 'show', 'view', 'showsummary', 'infoscreen', 'gethtml', 'submissionscreen',
                  'exporthtml', 'showmemberships', 'listassignments', 'showoverview'}


@dataclass
class PageData:
    body: bytes
    url: str

    def __post_init__(self):
        self.tree = html.fromstring(self.body or b'<html></html>')

    def logged_in(self):
        bars = self.tree.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " il-maincontrols-metabar ")]')
        if not bars:
            return None  # Let PFERD handle legacy dashboards and embedded players.
        return not bars[0].xpath('.//*[@href and contains(@href, "login.php")]') and not self.tree.xpath(
            '//*[@id="button_shib_login"]')

    def empty_meeting_candidates(self, elements):
        """ILIAS's minimal session list emits an assigned-material count only when it is nonzero.

        Require a positive sibling as evidence that this list exposes that property. Unknown layouts
        and newly encountered sessions still use ordinary crawling; the caller also requires a previously
        verified empty session page.
        """
        meetings = {e.url for e in elements if e.type.value == 'meeting'}
        rows = []
        for outer in self.tree.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ilContainerListItemOuter ")]'):
            links = outer.xpath('.//a[contains(concat(" ",normalize-space(@class)," ")," il_ContainerItemTitle ")]')
            urls = {urljoin(self.url, a.get('href', '')) for a in links} & meetings
            if len(urls) != 1:
                continue
            props = outer.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," il_ItemProperty ")]')
            count = None
            for prop in props:
                text = ' '.join(' '.join(prop.itertext()).split())
                match = re.match(r'^(?:Materialien zur Sitzung|Assigned Materials|Assigned materials):\s*(\d+)\b', text)
                if match:
                    count = int(match[1])
            rows.append((urls.pop(), count))
        if not any(count is not None and count > 0 for _, count in rows):
            return set()
        return {url for url, count in rows if count is None or count == 0}

    def fingerprint(self):
        cached = getattr(self, '_fingerprint', None)
        if cached is not None:
            return cached
        # PFERD reads content, tabs, header icons, descriptions and a few script-based players/links.
        # Unknown layouts use the entire document, so a missed selector costs a parse, not freshness.
        containers = self.tree.xpath('//*[@id="ilContentContainer"]')
        if len(containers) == 1:
            scopes = containers + self.tree.xpath(
                '//*[@id="ilTab" or @id="headerimage" or starts-with(@id,"tab_")]'
                '|//script[contains(text(),"paella_config_file") or contains(text(),"il.VideoPlaylist.init")'
                ' or contains(text(),"window.open") or contains(text(),"il.Footer.permalink")]')
            outside_descriptions = self.tree.xpath(
                '//*[contains(@class,"ilc_Paragraph") or contains(@class,"ilCOPageSection")'
                ' or contains(@class,"MediaContainer") or contains(@class,"AccordIHeadCap")]'
                '[not(ancestor::*[@id="ilContentContainer"])]')
            scopes.extend(outside_descriptions)
        else:
            scopes = [self.tree]
        digest = hashlib.sha256(self.url.encode())
        for scope in scopes:
            node = copy.deepcopy(scope)
            for element in list(node.iter()):
                if not isinstance(element.tag, str):
                    continue
                # Hidden form state is not content. Download targets in href/data-action remain significant.
                if element.tag == 'input' and element.get('type', '').lower() == 'hidden':
                    if element.getparent() is not None:
                        element.drop_tree()
                    continue
                for name, value in list(element.attrib.items()):
                    if name == 'nonce':
                        del element.attrib[name]
                    elif name == 'action' and element.tag == 'form':
                        element.attrib[name] = re.sub(r'([?&])rtoken=[^&]*', r'\1rtoken=', value)
                    else:
                        element.attrib[name] = _UI_ID.sub('ui-id', value)
                if element.tag == 'script' and element.text:
                    element.text = _UI_ID.sub('ui-id', element.text)
                # An assignment's countdown changes without a content change. Its fixed dates stay in the hash.
                if element.tag == 'div' and element.get('class') == 'caption' and (element.text or '').strip() in {
                    'Verbleibende Bearbeitungsdauer:', 'Remaining Working Time:', 'Remaining working time:'
                }:
                    for strong in element.findall('strong'):
                        strong.text = ''
            digest.update(etree.tostring(node))
        self._fingerprint = digest.hexdigest()
        return self._fingerprint


def encode_element(element):
    if element is None:
        return None
    value = asdict(element)
    value['type'] = element.type.value
    value['mtime'] = element.mtime.isoformat() if element.mtime else None
    return value


def decode_element(value):
    if value is None:
        return None
    from PFERD.crawl.ilias.kit_ilias_html import IliasElementType, IliasPageElement
    return IliasPageElement(IliasElementType(value['type']), value['url'], value['name'],
                            datetime.fromisoformat(value['mtime']) if value['mtime'] else None, value['description'])


class PageIndex:
    def __init__(self, path, source, fetch):
        self.path = path
        self.origin = urlparse(source.url).netloc
        remote_config = asdict(source)
        remote_config.pop('folder_names', None)
        remote_config.pop('include_course_ids', None)
        self.config = hashlib.sha256(json.dumps(remote_config, sort_keys=True).encode()).hexdigest()
        try:
            old = read_json(path, {})
        except (OSError, ValueError):
            old = {}
        self.old = old if (isinstance(old, dict) and old.get('schema') == 1 and old.get('config') == self.config
                           and isinstance(old.get('urls'), list) and isinstance(old.get('plans'), dict)
                           and isinstance(old.get('routes', {}), dict)) else {}
        self.fetch = fetch
        self.semaphore = asyncio.Semaphore(PAGE_REQUESTS)
        self.pending = {}
        self.used_urls = set()
        self.plans = {}
        self.parsed = self.reused = 0
        self.empty_meetings = set()

    def shortcut(self, original, final):
        """A redirect's stable object route can bypass its routing round trip, not its access check."""
        before, after = urlparse(original), urlparse(final)
        if before.netloc != self.origin or after.netloc != self.origin or after.scheme != 'https':
            return original
        if after.username or after.password:
            return original
        query = parse_qs(after.query)
        if query.get('cmd', [''])[0].lower() not in _READ_COMMANDS:
            return original
        original_id = parse_qs(before.query).get('ref_id')
        if original_id is None and (match := re.search(r'/go/(?:crs|grp|fold|exc)/(\d+)$', before.path)):
            original_id = [match[1]]
        if not original_id or original_id != query.get('ref_id') or 'cmdNode' not in query:
            return original
        if any(key.lower() in {'rtoken', 'phpsessid', 'token', 'auth', 'sid'} for key in query):
            return original
        return final

    async def _fetch(self, url):
        async with self.semaphore:
            await checkpoint()
            route = self.shortcut(url, self.old.get('routes', {}).get(url, url))
            try:
                return await self.fetch(route)
            except Exception:
                if route == url:
                    raise
                # A server upgrade can invalidate cmdNode routes; rediscover through the original permalink.
                return await self.fetch(url)

    async def page(self, url):
        self.used_urls.add(url)
        if url not in self.pending:
            self.pending[url] = asyncio.create_task(self._fetch(url))
        try:
            return await self.pending[url]
        except Exception:
            # A failed speculative read must not poison PFERD's later retry attempts.
            self.pending.pop(url, None)
            raise

    def start_prefetch(self):
        # Only replay same-server navigation already visited by the crawler, never POSTs or arbitrary actions.
        urls = self.old.get('urls', [])
        # Discover current memberships first, while the remaining known pages are read in parallel.
        urls = sorted(urls, key=lambda url: 'baseclass=ildashboardgui' not in url.lower())
        for url in urls:
            parts = urlparse(url)
            commands = parse_qs(parts.query).get('cmd', [''])
            if parts.scheme != 'https' or parts.netloc != self.origin or parts.username or parts.password:
                continue
            if commands[0].lower() not in _READ_COMMANDS:
                continue
            if url not in self.pending:
                self.pending[url] = asyncio.create_task(self._fetch(url))

    async def prefetch(self):
        self.start_prefetch()
        # Detached pages may now be inaccessible. Their errors matter only if current navigation still reaches them.
        await asyncio.gather(*self.pending.values(), return_exceptions=True)

    def key(self, url, parent):
        return json.dumps([url, parent.type.value if parent else None, parent.name if parent else None])

    def verified_empty_meeting(self, element):
        key = self.key(element.url, element)
        record = self.plans.get(key, self.old.get('plans', {}).get(key))
        if record:
            plan = record['plan']
            if not plan.get('stage') and not plan.get('elements') and not plan.get('description') and not plan.get('next'):
                self.plans[key] = record
                self.empty_meetings.add(element.url)
                return True
        return False

    async def plan(self, url, parent, parse):
        data = await self.page(url)
        digest = data.fingerprint()
        key = self.key(url, parent)
        cached = self.plans.get(key, self.old.get('plans', {}).get(key))
        if cached and cached['digest'] == digest:
            self.reused += 1
            plan = cached['plan']
        else:
            self.parsed += 1
            plan = parse(data, parent)
        self.plans[key] = {'digest': digest, 'plan': plan}
        return plan

    async def close(self, success):
        for task in self.pending.values():
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.pending.values(), return_exceptions=True)
        if success:
            routes = {}
            for url in self.used_urls:
                task = self.pending.get(url)
                if task and not task.cancelled() and task.exception() is None:
                    route = self.shortcut(url, task.result().url)
                    if route != url:
                        routes[url] = route
            write_json(self.path, {'schema': 1, 'config': self.config, 'urls': sorted(self.used_urls),
                                  'routes': routes, 'plans': self.plans})
