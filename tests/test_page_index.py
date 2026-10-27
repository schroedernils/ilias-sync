import asyncio
from pathlib import Path

import pytest

from ilias_sync.page_index import PAGE_REQUESTS, PageData, PageIndex
from ilias_sync.storage import data_dir, read_json
from test_engine import FixtureSession, Response, file_html, page


def fingerprint(contents):
    return PageData(('<div id="ilContentContainer">' + contents + '</div>').encode(),
                    'https://campus.example.edu/ilias.php').fingerprint()


def test_fingerprint_ignores_only_form_ui_ids_and_assignment_countdown():
    before = '<form action="?rtoken=aaa" name="table_' + 'a' * 32 + '">' \
             '<input type="hidden" value="secret"/></form>' \
             '<div id="il_ui_fw_12345_678">Material</div>' \
             '<div class="caption">Verbleibende Bearbeitungsdauer:<strong>3 Tage, 5 Minuten</strong></div>'
    after = before.replace('aaa', 'bbb').replace('a' * 32, 'b' * 32).replace('12345_678', '76543_210') \
                  .replace('secret', 'renewed').replace('5 Minuten', '4 Minuten')
    assert fingerprint(before) == fingerprint(after)


@pytest.mark.parametrize('before,after', [
    ('<a href="file/1">Lecture.pdf</a>', '<a href="file/2">Lecture.pdf</a>'),
    ('<a href="file/1">Lecture.pdf</a>', '<a href="file/1">New lecture.pdf</a>'),
    ('<p>first  line</p>', '<p>first line</p>'),
    ('<button data-action="file/1">Download</button>', '<button data-action="file/2">Download</button>'),
    ('<p>27. Okt 2026, 12:00</p>', '<p>27. Okt 2026, 13:00</p>'),
    ('<img src="image1.png"/>', '<img src="image2.png"/>'),
    ('<div class="ilc_Paragraph">Old description</div>', '<div class="ilc_Paragraph">New description</div>'),
])
def test_fingerprint_detects_content_and_download_target_changes(before, after):
    assert fingerprint(before) != fingerprint(after)


def test_fingerprint_includes_navigation_and_script_download_targets():
    template = b'<div id="ilContentContainer">unchanged</div><li id="tab_submission"><a href="/submission/1">Files</a></li>' \
               b'<script>window.open("/file/1");</script>'
    original = PageData(template, 'https://campus.example.edu').fingerprint()
    assert original != PageData(template.replace(b'/submission/1', b'/submission/2'), 'https://campus.example.edu').fingerprint()
    assert original != PageData(template.replace(b'/file/1', b'/file/2'), 'https://campus.example.edu').fingerprint()


async def test_prefetch_is_bounded_deduplicated_and_cancellable(source, tmp_path):
    active = peak = calls = 0
    entered = asyncio.Event()

    async def fetch(url):
        nonlocal active, peak, calls
        active += 1
        calls += 1
        peak = max(peak, active)
        if active == PAGE_REQUESTS:
            entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            active -= 1

    index = PageIndex(tmp_path / 'index.json', source, fetch)
    index.old = {'urls': [source.url + f'/folder/{i}' for i in range(PAGE_REQUESTS + 4)]}
    task = asyncio.create_task(index.prefetch())
    await asyncio.wait_for(entered.wait(), timeout=2)
    duplicate = asyncio.create_task(index.page(source.url + '/folder/0'))
    await asyncio.sleep(0)
    assert calls == peak == PAGE_REQUESTS
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await index.close(False)
    await asyncio.gather(duplicate, return_exceptions=True)
    assert active == 0
    assert not index.path.exists()


async def test_pipeline_consumes_ready_pages_without_waiting_for_detached_pages(source, tmp_path):
    slow_started = asyncio.Event()
    slow_cancelled = asyncio.Event()
    calls = []
    dashboard = source.url + '/ilias.php?baseClass=ilDashboardGUI&cmd=show'
    detached = source.url + '/folder/removed'

    async def fetch(url):
        calls.append(url)
        if url == detached:
            slow_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                slow_cancelled.set()
        return PageData(page('Current memberships'), url)

    index = PageIndex(tmp_path / 'index.json', source, fetch)
    index.old = {'urls': [detached, dashboard]}
    index.start_prefetch()
    async with asyncio.timeout(2):
        data = await index.page(dashboard)
        await slow_started.wait()
        assert b'Current memberships' in data.body
        assert calls[0] == dashboard
        assert not slow_cancelled.is_set()
        await index.close(True)
    assert slow_cancelled.is_set()
    assert read_json(index.path, {})['urls'] == [dashboard]


async def test_prefetch_runs_during_membership_discovery_and_does_not_publish_removed_course(source, monkeypatch):
    from ilias_sync.engine import synchronize
    root_read = asyncio.Event()
    dashboard_read = asyncio.Event()
    removed = False
    original_files = None

    class DelayedResponse(Response):
        async def read(self):
            if 'Dashboard' in str(self.url):
                dashboard_read.set()
                async with asyncio.timeout(2):
                    await root_read.wait()
            else:
                root_read.set()
            await asyncio.sleep(0)
            return self.body

    class PipelinedSession(FixtureSession):
        def get(self, url, **kwargs):
            if 'Dashboard' in url:
                return DelayedResponse(url, page('' if removed else '<a href="/go/crs/123">Algorithms</a>'))
            if '/go/crs/123' in url:
                return DelayedResponse(url, page(file_html()))
            return super().get(url, **kwargs)

    # Establish the known navigation inventory using the regular synthetic server.
    monkeypatch.setattr('aiohttp.ClientSession', FixtureSession)
    await synchronize(source)
    original_files = {str(p): p.read_bytes() for p in Path(source.destination).rglob('*.pdf')}
    monkeypatch.setattr('aiohttp.ClientSession', PipelinedSession)
    repeated = await synchronize(source)
    assert repeated['counts'] == {'unchanged': 1}
    assert dashboard_read.is_set() and root_read.is_set()
    removed = True
    root_read.clear()
    dashboard_read.clear()
    from PFERD.crawl import CrawlError
    with pytest.raises(CrawlError, match='No courses found'):
        await synchronize(source)
    assert {str(p): p.read_bytes() for p in Path(source.destination).rglob('*.pdf')} == original_files


async def test_nested_updates_are_checked_fresh_even_when_the_course_page_does_not_change(source, monkeypatch):
    from ilias_sync.engine import synchronize
    contents = {'extra': False, 'updated': False, 'removed': False}
    reads = []
    folder = '<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="fold.svg" alt="Ordner"/>' \
             '<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/go/fold/456">Material</a></div></div>'

    class MutableSession(FixtureSession):
        def get(self, url, **kwargs):
            reads.append(url)
            if '/go/crs/123' in url:
                return Response(url, page(folder if not contents['removed'] else '<p>Folder removed</p>'))
            if '/go/fold/456' in url:
                if contents['removed']:
                    return Response(url, b'no access', status=403)
                body = file_html()
                if contents['updated']:
                    body = body.replace('20. Okt', '21. Okt')
                if contents['extra']:
                    body += file_html().replace('ref_id=987', 'ref_id=988').replace('>Lecture<', '>New nested file<')
                return Response(url, page(body))
            if 'sendfile' in url and contents['updated']:
                return Response(url, b'%PDF-1.4 changed contents', kind='application/pdf')
            return super().get(url, **kwargs)

    monkeypatch.setattr('aiohttp.ClientSession', MutableSession)
    first = await synchronize(source)
    assert first['counts'] == {'added': 1}
    reads.clear()
    repeat = await synchronize(source)
    assert repeat['counts'] == {'unchanged': 1}
    assert repeat['pages']['reused'] > 0
    assert repeat['pages']['parsed'] == 0
    assert any('/go/fold/456' in url for url in reads)
    assert not any('sendfile' in url for url in reads)
    contents['extra'] = True
    added = await synchronize(source)
    assert added['counts'] == {'unchanged': 1, 'added': 1}
    assert added['pages']['parsed'] == 1
    contents['updated'] = True
    updated = await synchronize(source)
    assert updated['counts'] == {'updated': 1, 'unchanged': 1}
    assert list(Path(source.destination).rglob('Versions/*'))
    contents['removed'] = True
    removed = await synchronize(source)
    assert removed['files'] == 0
    assert not removed['partial']
    assert len(list(Path(source.destination).rglob('*.pdf'))) >= 2


async def test_missing_local_file_is_restored_during_a_warm_check(source, monkeypatch):
    from ilias_sync.engine import synchronize
    monkeypatch.setattr('aiohttp.ClientSession', FixtureSession)
    await synchronize(source)
    target = next(Path(source.destination).rglob('*.pdf'))
    original = target.read_bytes()
    target.unlink()
    result = await synchronize(source)
    assert target.read_bytes() == original
    assert result['pages']['parsed'] == 0


async def test_cached_pages_do_not_mask_expired_login(source, monkeypatch):
    from ilias_sync.engine import synchronize
    from ilias_sync.security import LoginRequired
    source.login = 'session'
    monkeypatch.setattr('aiohttp.ClientSession', FixtureSession)
    await synchronize(source)

    class LoggedOut(FixtureSession):
        def get(self, url, **kwargs):
            return Response(url, b'<div class="il-maincontrols-metabar"><a href="login.php">Login</a></div>')

    monkeypatch.setattr('aiohttp.ClientSession', LoggedOut)
    with pytest.raises(LoginRequired):
        await synchronize(source)
    # Last successful index remains intact for the next authenticated attempt.
    assert read_json(data_dir() / 'sources' / source.id / 'page-index.json', {})['plans']


async def test_stable_redirects_are_revalidated_and_fall_back_when_routes_expire(source, tmp_path):
    original = source.url + '/go/fold/123'
    final = source.url + '/ilias.php?baseClass=ilrepositorygui&cmdNode=xi:md&cmdClass=ilObjFolderGUI&ref_id=123'
    calls = []

    async def fetch(url):
        calls.append(url)
        return PageData(page('<div id="ilContentContainer">Files</div>'), final)

    path = tmp_path / 'index.json'
    index = PageIndex(path, source, fetch)
    await index.page(original)
    await index.close(True)
    warm = PageIndex(path, source, fetch)
    await warm.page(original)
    assert calls == [original, final]
    await warm.close(True)
    calls.clear()

    async def changed_server(url):
        calls.append(url)
        if url == final:
            raise OSError('cmdNode no longer exists')
        return PageData(page('Files'), original)

    upgraded = PageIndex(path, source, changed_server)
    await upgraded.page(original)
    await upgraded.close(True)
    assert calls == [final, original]
    assert not read_json(path, {})['routes']
    assert upgraded.shortcut(original, final.replace('ref_id=123', 'ref_id=999')) == original
    assert upgraded.shortcut(original, final + '&rtoken=secret') == original
    assert upgraded.shortcut(original, final.replace('campus.example.edu', 'other.example.edu')) == original


async def test_changed_profile_and_failed_run_do_not_reuse_or_replace_the_index(source, tmp_path):
    path = tmp_path / 'index.json'
    async def fetch(url):
        return PageData(page('Files'), url)
    index = PageIndex(path, source, fetch)
    await index.page(source.url)
    await index.close(True)
    previous = path.read_bytes()
    source.targets = [source.url + '/go/crs/999']
    changed = PageIndex(path, source, fetch)
    assert not changed.old
    await changed.close(False)
    assert path.read_bytes() == previous


async def test_empty_meeting_is_revisited_when_its_fresh_material_count_changes(source, monkeypatch):
    from PFERD.crawl.ilias.kit_ilias_html import IliasElementType
    from ilias_sync.engine import synchronize
    populated = False
    reads = []

    def meetings():
        rows = []
        for identity, count in ((10, 1), (20, 1 if populated else 0)):
            count_html = f'<span class="il_ItemProperty">Materialien zur Sitzung: {count}</span>' if count else ''
            rows.append('<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="icon_sess.svg" alt="Sitzung"/>'
                        '<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" '
                        f'href="/go/sess/{identity}">27. Okt 2026: Session {identity}</a>'
                        f'<div class="il_ItemProperties">{count_html}</div></div></div>')
        return ''.join(rows)

    class SessionMaterials(FixtureSession):
        def get(self, url, **kwargs):
            reads.append(url)
            if '/go/crs/123' in url:
                return Response(url, page(meetings()))
            if '/go/sess/10' in url:
                return Response(url, page(file_html()))
            if '/go/sess/20' in url:
                body = file_html().replace('ref_id=987', 'ref_id=988').replace('>Lecture<', '>New material<') if populated else ''
                return Response(url, page(body))
            return super().get(url, **kwargs)

    monkeypatch.setattr('aiohttp.ClientSession', SessionMaterials)
    first = await synchronize(source)
    assert first['pages']['empty_meetings'] == 0
    assert any('/go/sess/20' in u for u in reads)
    await synchronize(source)  # Establish that the known empty session is covered by the current parent summary.
    reads.clear()
    repeat = await synchronize(source)
    assert repeat['pages']['empty_meetings'] == 1
    assert not any('/go/sess/20' in u for u in reads)
    assert repeat['counts'] == {'unchanged': 1}
    reads.clear()
    populated = True
    changed = await synchronize(source)
    assert any('/go/sess/20' in u for u in reads)
    assert changed['counts'] == {'unchanged': 1, 'added': 1}
    assert changed['pages']['empty_meetings'] == 0

    # Without a positive sibling count, the layout has no proof of the summary convention.
    from ilias_sync.page_index import encode_element, decode_element
    from PFERD.crawl.ilias.kit_ilias_html import IliasPageElement
    element = IliasPageElement(IliasElementType.MEETING, source.url + '/go/sess/20', 'Session')
    assert decode_element(encode_element(element)).url == element.url
    minimal = PageData(page('<div class="ilContainerListItemOuter"><a class="il_ContainerItemTitle" '
                            'href="/go/sess/20">Session</a></div>'), source.url)
    assert not minimal.empty_meeting_candidates([element])
