from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from ilias_sync.engine import make_crawler, memberships, ref, synchronize


def test_discover_without_favorites():
    html = '<p>No favorites</p><a href="/go/crs/123">Algorithms</a><a href="/go/grp/456">Group 1</a>' \
           '<a href="https://unrelated.example/go/crs/99">Other</a><a href="/go/crs/123">Duplicate</a>'
    rows = memberships(BeautifulSoup(html, "html.parser"), "https://campus.example.edu")
    assert [r["id"] for r in rows] == ["crs-123", "grp-456"]
    assert ref("https://campus.example.edu/goto.php?target=crs_123") == ("crs", "123")


class Content:
    def __init__(self, body):
        self.body = body
        self.sent = False

    async def read(self, size=-1):
        self.sent = True
        return self.body

    async def iter_chunked(self, size):
        if not self.sent:
            yield self.body


class Response:
    def __init__(self, url, body, status=200, kind="text/html"):
        from yarl import URL
        self.url = URL(url)
        self.body = body
        self.status = status
        self.content_type = kind
        self.content_length = len(body)
        self.headers = {}
        self.content = Content(body)

    def raise_for_status(self):
        if self.status >= 400:
            raise OSError("server error")

    async def read(self):
        return self.body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def page(contents):
    return ('<div class="il-maincontrols-metabar"></div>' + contents).encode()


def file_html():
    return '<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="file.svg" alt="Inline Datei"/>' \
           '<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/ilias/ilias.php?cmd=sendfile&amp;ref_id=987">Lecture</a>' \
           '<div class="il_ItemProperties"><span class="il_ItemProperty">pdf</span><span>20. Okt 2026, 12:00</span></div></div></div>'


class FixtureSession:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def get(self, url, **kwargs):
        if "Dashboard" in str(url):
            body = page('<a href="/go/crs/123">Algorithms</a>')
        elif "sendfile" in str(url):
            return Response(url, b"%PDF-1.4 synthetic lecture", kind="application/pdf")
        else:
            body = page(file_html() + file_html())
        return Response(url, body)


async def test_full_synthetic_sync_and_repeat(source, monkeypatch):
    monkeypatch.setattr("aiohttp.ClientSession", FixtureSession)
    events = []
    result = await synchronize(source, events.append)
    assert result["files"] == 1
    assert result["counts"]["added"] == 1
    files = list(Path(source.destination).rglob("*.pdf"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"%PDF-1.4 synthetic lecture"
    second = await synchronize(source)
    assert second["counts"] == {"unchanged": 1}
    assert not list(Path(source.destination).rglob("*ILIAS*"))
    messages = [event['message'] for event in events if event['event'] == 'progress']
    assert 'Checking Algorithms (1/1)' in messages
    assert 'Checking Algorithms (1/1) / Lecture.pdf' in messages
    assert 'Downloading Lecture.pdf' in messages
    assert 'Saving files…' in messages
    assert 'Saving course information…' in messages


async def test_repository_copy_wins_over_session_and_survives_removed_links(source, monkeypatch):
    from ilias_sync.storage import Archive, clean_name, data_dir, read_json

    title = '2026-10-20, 15:45 - 17:15: Lecture'
    sheet = file_html().replace('>Lecture<', '>sheet_01<')
    course = '<a href="/go/crs/123">Algorithms</a>'
    meeting = ('<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="icon_sess.svg" alt="Sitzung"/>'
               f'<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/go/sess/91">{title}</a></div></div>')
    folder = ('<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="fold.svg" alt="Ordner"/>'
              '<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/go/fold/456">Übungsblätter</a></div></div>')
    nested = folder.replace('456', '789').replace('Übungsblätter', 'Aufgaben 1-6')
    listed_in_folder, listed_in_meeting = True, True
    downloads = []

    class Session(FixtureSession):
        def get(self, url, **kwargs):
            if 'Dashboard' in url:
                return Response(url, page(course))
            if '/go/crs/123' in url:
                return Response(url, page(meeting + folder))
            if '/go/fold/456' in url:
                return Response(url, page(nested))
            if '/go/fold/789' in url:
                return Response(url, page(sheet if listed_in_folder else '<p>Empty</p>'))
            if '/go/sess/91' in url:
                return Response(url, page(sheet if listed_in_meeting else '<p>Empty</p>'))
            if 'sendfile' in url:
                downloads.append(url)
                return Response(url, b'%PDF-1.4 original', kind='application/pdf')
            return super().get(url, **kwargs)

    monkeypatch.setattr('aiohttp.ClientSession', Session)
    root = Path(source.destination)
    state = data_dir() / 'sources' / source.id
    raw = data_dir() / 'old.pdf'
    raw.write_bytes(b'%PDF-1.4 original')
    old = f'Algorithms/{clean_name(title, 50)}/sheet 01.pdf'
    archive = Archive(state, root)
    archive.publish('file:987', raw, old, metadata={'course_id': 'crs-123', 'original_path': old})
    canonical = 'Algorithms/Übungsblätter/Aufgaben 1-6/sheet 01.pdf'

    def entry():
        return read_json(archive.path, {})['files']['file:987']

    await synchronize(source)
    assert len(downloads) == 1
    assert entry()['path'] == canonical
    assert not (root / old).exists() and (root / canonical).is_file()
    assert entry()['prior_locations'][0]['path'] == old

    listed_in_folder = False
    await synchronize(source)
    assert entry()['original_path'] == canonical and not entry()['retained_locally']
    listed_in_meeting = False
    await synchronize(source)
    assert entry()['retained_locally'] and (root / canonical).is_file()
    listed_in_folder = True
    await synchronize(source)
    assert not entry()['retained_locally']
    assert list(root.rglob('*.pdf')) == [root / canonical]


async def test_submissions_and_feedback_with_the_same_exercise_ref_are_independent(source, monkeypatch):
    from pathlib import PurePath
    from PFERD.crawl.ilias.kit_ilias_html import IliasElementType, IliasPageElement

    downloads = []

    class Session(FixtureSession):
        def get(self, url, **kwargs):
            downloads.append(str(url))
            marker = str(url).rsplit('=', 1)[-1].encode()
            return Response(url, b'%PDF-1.4 copy ' + marker, kind='application/pdf')

    def crawler_with_exercise(source, emit, *, discover):
        crawler = make_crawler(source, emit, discover=discover)

        async def traverse():
            course = {'id': 'crs-123', 'name': 'Algorithms', 'url': source.url + '/go/crs/123'}
            crawler.current = course
            crawler.active_roots = [course]
            crawler.course_folders = {course['id']: course['name']}
            base = source.url + '/ilias.php?ref_id=42&'
            fixtures = [
                ('Blatt 01', 'cmdClass=ilExSubmissionFileGUI&ass_id=11&cmd=download&delivered=7', b'7'),
                ('Blatt 02', 'cmdClass=ilExSubmissionFileGUI&ass_id=12&cmd=download&delivered=8', b'8'),
                ('Blatt 02', 'cmdClass=ilExSubmissionGUI&ass_id=12&cmd=downloadFeedbackFile&file=9', b'9'),
            ]
            for folder, query, marker in fixtures:
                filename = 'Feedback.pdf' if marker == b'9' else 'Lösung.pdf'
                element = IliasPageElement(IliasElementType.FILE, base + query, filename)
                task = await crawler._handle_file(element, PurePath(course['id'], folder, filename))
                if task:
                    await task
                same_link = IliasPageElement(element.type, base + 'cmdNode=changed&' + query, filename)
                assert await crawler._handle_file(same_link, PurePath(course['id'], folder, filename)) is None

        crawler._run = traverse
        return crawler

    monkeypatch.setattr('aiohttp.ClientSession', Session)
    monkeypatch.setattr('ilias_sync.engine.make_crawler', crawler_with_exercise)
    result = await synchronize(source)
    assert result['material_counts'] == {'added': 3}
    assert len(downloads) == 3
    course = Path(source.destination) / 'Algorithms'
    assert (course / 'Blatt 01/Lösung.pdf').read_bytes().endswith(b'7')
    assert (course / 'Blatt 02/Lösung.pdf').read_bytes().endswith(b'8')
    assert (course / 'Blatt 02/Feedback.pdf').read_bytes().endswith(b'9')


async def test_legacy_direct_web_link_cannot_interrupt_valid_course_sync(source, monkeypatch):
    from types import SimpleNamespace
    from ilias_sync.__main__ import worker
    from ilias_sync.storage import Settings, data_dir, read_json

    invalid = source.url + '/ilias.php?baseClass=ilLinkResourceHandlerGUI&ref_id=4675434&cmd=calldirectlink'

    class Session(FixtureSession):
        def get(self, url, **kwargs):
            assert 'calldirectlink' not in str(url)
            return super().get(url, **kwargs)

    settings = Settings()
    settings.save_source(source)
    settings.value['sources'][0].update(automatic_courses=False, targets=[source.url + '/go/crs/123', invalid])
    settings.save()
    monkeypatch.setattr('aiohttp.ClientSession', Session)
    assert await worker(SimpleNamespace(probe=None, profile=source.id, sync=True, discover=False)) == 0
    status = read_json(data_dir() / 'sources' / source.id / 'status.json', {})
    assert status['state'] == 'Completed with warnings'
    assert status['failure_kind'] == 'course_links' and not status['login_required']
    assert status['result']['material_counts'] == {'added': 1}
    assert status['result']['course_link_issues'][0]['path'] == invalid
    assert not status['last_success']


async def test_unexpected_course_page_checks_session_before_reauth(source, monkeypatch):
    from PFERD.crawl.crawler import CrawlError

    class Session(FixtureSession):
        def get(self, url, **kwargs):
            if 'Dashboard' in str(url):
                return super().get(url, **kwargs)
            return Response(url, b'<html><p>Unexpected response</p></html>')

    crawler = make_crawler(source, lambda _: None)
    crawler.session = Session()
    crawler.authenticate = AsyncMock()
    with pytest.raises(CrawlError, match='while the session was active'):
        await crawler._fetch_page(source.url + '/go/crs/123')
    crawler.authenticate.assert_not_awaited()


async def test_nested_folder_progress_identifies_current_course_and_folder(source, monkeypatch):
    folder = '<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="fold.svg" alt="Ordner"/>' \
             '<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/go/fold/456">Material</a></div></div>'

    class NestedSession(FixtureSession):
        def get(self, url, **kwargs):
            if '/go/crs/123' in str(url):
                return Response(url, page(folder))
            return super().get(url, **kwargs)

    monkeypatch.setattr('aiohttp.ClientSession', NestedSession)
    events = []
    result = await synchronize(source, events.append)
    assert result['files'] == 1
    messages = [event['message'] for event in events if event['event'] == 'progress']
    assert 'Checking Algorithms (1/1) / Material' in messages
    assert 'Checking Algorithms (1/1) / Material / Lecture.pdf' in messages


async def test_parallel_folder_checks_preserve_files_course_ownership_and_routes(source, tmp_path, monkeypatch):
    import asyncio
    from urllib.parse import parse_qs, urlparse
    from ilias_sync.storage import data_dir, read_json
    active = 0
    peak = 0
    downloads = []

    class DelayedPage(Response):
        async def read(self):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0.01)
                return self.body
            finally:
                active -= 1

    class ParallelSession(FixtureSession):
        def get(self, url, **kwargs):
            if 'Dashboard' in url:
                body = ''.join(f'<a href="/go/crs/{i}">Course {i}</a>' for i in (1, 2))
            elif '/go/crs/' in url:
                course = int(url.rsplit('/', 1)[1])
                body = ''.join(
                    '<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="fold.svg" alt="Ordner"/>'
                    f'<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/go/fold/{course * 100 + i}">'
                    f'Material {i}</a></div></div>' for i in range(12))
            elif '/go/fold/' in url:
                identity = url.rsplit('/', 1)[1]
                body = file_html().replace('ref_id=987', 'ref_id=' + identity).replace('>Lecture<', f'>Lecture {identity}<')
            else:
                identity = parse_qs(urlparse(url).query)['ref_id'][0]
                downloads.append(identity)
                return Response(url, b'%PDF-1.4 lecture ' + identity.encode(), kind='application/pdf')
            return DelayedPage(url, page(body))

    source.folder_rules = {'course/crs-2': str(tmp_path / 'Other destination')}
    monkeypatch.setattr('aiohttp.ClientSession', ParallelSession)
    result = await synchronize(source)
    assert result['counts'] == {'added': 24}
    assert result['unavailable'] == result['warnings'] == result['errors'] == 0
    assert not result['partial']
    assert 1 < peak <= 8
    assert len(downloads) == len(set(downloads)) == 24
    manifest = read_json(data_dir() / 'sources' / source.id / 'manifest.json', {})['files']
    for entry in manifest.values():
        course = int(entry['course_id'].removeprefix('crs-'))
        assert entry['course_name'] == f'Course {course}'
        prefix = f'Course {course}/' if course == 1 else ''
        assert entry['path'].startswith(prefix + 'Material ')
        assert entry['logical'].startswith(f'crs-{course}/Material ')
        assert entry['root'] == (source.destination if course == 1 else source.folder_rules['course/crs-2'])
        assert (Path(entry['root']) / entry['path']).read_bytes().startswith(b'%PDF-1.4 lecture ')
    repeat = await synchronize(source)
    assert repeat['counts'] == {'unchanged': 24}
    assert len(downloads) == 24
    assert active == 0


async def test_stop_cancels_parallel_page_reads_before_publication(source, monkeypatch):
    import asyncio
    from ilias_sync.control import RunControl, send_command
    from ilias_sync.storage import data_dir
    entered = asyncio.Event()
    active = 0
    reads = []

    class PendingPage(Response):
        async def read(self):
            nonlocal active
            active += 1
            reads.append(asyncio.current_task())
            if active == 8:
                entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                active -= 1

    class PendingSession(FixtureSession):
        def get(self, url, **kwargs):
            if '/go/crs/123' in url:
                folders = ''.join(
                    '<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="fold.svg" alt="Ordner"/>'
                    f'<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/go/fold/{i}">'
                    f'Material {i}</a></div></div>' for i in range(12))
                return Response(url, page(folders))
            if '/go/fold/' in url:
                return PendingPage(url, page(file_html()))
            return super().get(url, **kwargs)

    monkeypatch.setattr('aiohttp.ClientSession', PendingSession)
    control = RunControl(source, lambda event: None)
    task = asyncio.create_task(control.run(synchronize(source)))
    async with asyncio.timeout(4):
        await entered.wait()
        send_command(control.row, 'stop')
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.gather(*reads, return_exceptions=True)
    assert active == 0
    assert not (data_dir() / 'sources' / source.id / 'manifest.json').exists()
    assert not list(Path(source.destination).rglob('*.pdf'))


async def test_http_error_is_not_a_download(source):
    crawler = make_crawler(source)
    crawler._current_auth_id = AsyncMock(return_value=0)

    class ErrorSession:
        def get(self, url, **kwargs):
            return Response(url, b"broken", status=500)
    crawler.session = ErrorSession()
    from PFERD.crawl.ilias.kit_ilias_html import IliasPageElement, IliasElementType
    element = IliasPageElement(IliasElementType.FILE, source.url + "/file/1", "Lecture.pdf")
    with pytest.raises(OSError):
        await crawler._stream_from_url(element, None, None, False)


async def test_session_expiry_stops_login(source):
    from ilias_sync.security import LoginRequired
    source.login = "session"
    crawler = make_crawler(source)
    with pytest.raises(LoginRequired):
        await crawler._authenticate()


async def test_shibboleth_has_no_console_mfa_prompt(source):
    from ilias_sync.security import LoginRequired
    source.login = "shibboleth"
    source.idp_host = "idp.example.edu"
    crawler = make_crawler(source)
    captured = []

    async def login(session):
        captured.append(session)
        with pytest.raises(LoginRequired):
            await crawler._shibboleth_login._tfa_auth.password()
        with pytest.raises(LoginRequired):
            session.post("https://evil.example/steal", data={"password": "test"})
    crawler._shibboleth_login.login = login
    crawler.session = object()
    await crawler._authenticate()
    assert captured


async def test_failed_subtree_without_enumerated_files_persists_attempted_scope(source, monkeypatch):
    from types import SimpleNamespace
    from ilias_sync.storage import Settings, data_dir, read_json
    from ilias_sync.__main__ import worker
    from ilias_sync.gui import SyncReportDialog
    from PySide6.QtWidgets import QApplication
    folder = '<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="fold.svg" alt="Ordner"/>' \
             '<div class="il_ContainerListItem"><a class="il_ContainerItemTitle" href="/go/fold/456">Material</a></div></div>'
    class FailedFolder(FixtureSession):
        def get(self, url, **kwargs):
            if 'Dashboard' in str(url):
                return Response(url, page('<a href="/go/crs/123">Algorithms</a><a href="/go/crs/999">Not reached</a>'))
            if '/go/fold/456' in str(url):
                raise OSError('synthetic unavailable subtree')
            if '/go/crs/123' in str(url):
                return Response(url, page(folder))
            return super().get(url, **kwargs)
    monkeypatch.setattr('aiohttp.ClientSession', FailedFolder)
    Settings().save_source(source)
    assert await worker(SimpleNamespace(probe=None, profile=source.id, sync=True, discover=False)) == 1
    state = data_dir()/'sources'/source.id
    status = read_json(state/'status.json', {})
    evidence = status.get('evidence') or status.get('result')
    assert evidence['enumeration_complete']
    assert evidence['course_scope'] == [{'id':'crs-123','name':'Algorithms'}]
    assert evidence['intended_scope'] == [{'id':'crs-123','name':'Algorithms'}, {'id':'crs-999','name':'Not reached'}]
    assert evidence['check_issues'][0]['path'].endswith('Material')
    assert evidence['check_issues'][0]['reason'] == 'check_failed'
    assert 'result' not in status or status['result']['files'] == 0
    app = QApplication.instance() or QApplication([])
    report = SyncReportDialog(status, '')
    assert any('Material' in report.issues.topLevelItem(i).text(0) for i in range(report.issues.topLevelItemCount()))
    report.close()
    app.processEvents()
    assert read_json(state/'history.json', [])[0] == status


async def test_equal_mtime_does_not_pretend_to_be_remote_byte_revalidation(source, monkeypatch):
    downloaded = []
    contents = b'%PDF-1.4 original version'
    class SameMetadata(FixtureSession):
        def get(self, url, **kwargs):
            if 'sendfile' in str(url):
                downloaded.append(str(url))
                return Response(url, contents, kind='application/pdf')
            return super().get(url, **kwargs)
    monkeypatch.setattr('aiohttp.ClientSession', SameMetadata)
    await synchronize(source)
    contents = b'%PDF-1.4 replaced on server without metadata change'
    second = await synchronize(source)
    assert second['material_counts'] == {'unchanged':1}
    assert len(downloaded) == 1
    assert list(Path(source.destination).rglob('*.pdf'))[0].read_bytes() == b'%PDF-1.4 original version'


@pytest.mark.parametrize('failure', ['cancel', 'publish', 'result_write'])
async def test_evidence_survives_failures_through_publication(source, monkeypatch, failure):
    import asyncio
    from ilias_sync.storage import Archive
    monkeypatch.setattr('aiohttp.ClientSession', FixtureSession)
    def emit(event):
        if failure == 'cancel' and event.get('message') == 'Saving files…':
            asyncio.current_task().cancel()
    if failure == 'publish':
        monkeypatch.setattr(Archive, 'publish', lambda *args, **kwargs: (_ for _ in ()).throw(OSError('synthetic publish failure')))
    if failure == 'result_write':
        from ilias_sync import engine
        real_write = engine.write_json
        def failed_write(path, value):
            if path.name == 'last-result.json':
                raise OSError('synthetic result write failure')
            return real_write(path, value)
        monkeypatch.setattr(engine, 'write_json', failed_write)
    with pytest.raises(asyncio.CancelledError if failure == 'cancel' else OSError) as error:
        await synchronize(source, emit)
    facts = error.value.sync_evidence
    assert facts['course_scope'] == facts['intended_scope'] == [{'id':'crs-123','name':'Algorithms'}]
    assert facts['enumeration_complete']
    assert 'counts' not in facts
