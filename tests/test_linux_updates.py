"""Fail-closed Linux update verification and opt-in Qt controller behavior."""
import asyncio
import base64
from dataclasses import replace
import hashlib
import json
import os
import stat
import time
from types import SimpleNamespace
from unittest.mock import Mock

from filelock import FileLock
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from ilias_sync import linux_updates as updates
from ilias_sync.storage import data_dir, read_json, write_json

pytestmark = pytest.mark.skipif(os.name == 'nt', reason='Linux updater requires POSIX file protection; covered on Linux CI.')


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def signing():
    key = Ed25519PrivateKey.generate()
    public = base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
    version = '1.2.3'
    name = f'IliasSync-{version}-Linux-x64.deb'
    value = {
        'schema': 1, 'version': version, 'platform': 'Linux-x64', 'name': name,
        'url': f'{updates.REPOSITORY_URL}/releases/download/v{version}/{name}',
        'size': 123456, 'sha256': 'a' * 64,
        'signature': base64.b64encode(key.sign(b'package')).decode('ascii'),
        'release_url': f'{updates.REPOSITORY_URL}/releases/tag/v{version}',
    }

    def signed(value=value):
        raw = json.dumps(value, sort_keys=True, indent=2).encode() + b'\n'
        return raw, base64.b64encode(key.sign(raw)) + b'\n'

    return SimpleNamespace(key=key, public=public, value=value, signed=signed)


@pytest.fixture
def packaged(app, monkeypatch, signing):
    monkeypatch.setattr(updates, 'sys', SimpleNamespace(platform='linux', frozen=True))
    monkeypatch.setattr(updates, 'platform', SimpleNamespace(machine=lambda: 'x86_64'))
    # Every Qt test fails if it accidentally reaches a real network transport.
    transport = Mock(side_effect=AssertionError('Tests must not access the network'))
    monkeypatch.setattr(updates.aiohttp, 'ClientSession', transport)
    question = Mock(return_value=QMessageBox.StandardButton.No)
    monkeypatch.setattr(updates.QMessageBox, 'question', question)
    monkeypatch.setattr(updates.QMessageBox, 'information', Mock())
    instances = []

    def controller(**kwargs):
        instance = updates.LinuxUpdates(signing.public, updates.FEED_URL, '1.0.4', **kwargs)
        instances.append(instance)
        return instance

    yield SimpleNamespace(controller=controller, question=question, transport=transport)
    for instance in instances:
        instance.close()
    deadline = time.monotonic() + 3
    while updates._RUNNING_CHECKS and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert not updates._RUNNING_CHECKS, 'A test leaked an update thread'


def finish(app, controller):
    deadline = time.monotonic() + 3
    while controller._worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert controller._worker is None, 'Update check did not finish'
    app.processEvents()


def test_signed_release_and_numerical_version_order(signing):
    release = updates.parse_signed_release(*signing.signed(), signing.public, '1.2.2')
    assert release.version == '1.2.3'
    assert release.name.endswith('-Linux-x64.deb')
    assert release.release_url == signing.value['release_url']
    assert updates.parse_signed_release(*signing.signed(), signing.public, '1.2.3') is None
    assert updates.parse_signed_release(*signing.signed(), signing.public, '1.2.10') is None
    assert updates.parse_signed_release(*signing.signed(), signing.public, '2.0.0') is None


def test_raw_public_key_and_detached_signature(signing):
    raw, signature = signing.signed()
    assert updates.parse_signed_release(raw, base64.b64decode(signature),
                                        signing.key.public_key().public_bytes_raw(), '1.0.0')


@pytest.mark.parametrize('corruption', ['message', 'signature', 'wrong-key', 'malformed-signature'])
def test_corrupted_signatures_are_rejected_before_parsing(signing, monkeypatch, corruption):
    raw, signature = signing.signed()
    public = signing.public
    if corruption == 'message':
        raw += b' '
    elif corruption == 'signature':
        damaged = bytearray(base64.b64decode(signature))
        damaged[10] ^= 1
        signature = base64.b64encode(damaged)
    elif corruption == 'wrong-key':
        public = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    else:
        signature = b'not a signature'
    parse = Mock(side_effect=AssertionError('Unverified JSON must never be parsed'))
    monkeypatch.setattr(updates.json, 'loads', parse)
    with pytest.raises(updates.UpdateError):
        updates.parse_signed_release(raw, signature, public, '1.0.0')
    parse.assert_not_called()


@pytest.mark.parametrize(('field', 'value'), [
    ('schema', True), ('schema', 2), ('platform', 'Linux-arm64'), ('platform', 'Windows-x64'),
    ('version', '1.2.4-rc.1'), ('version', '1.2.3+build'), ('version', 'v1.2.3'),
    ('version', '01.2.3'), ('version', '1.2'), ('version', 123),
    ('size', True), ('size', 0), ('size', -1), ('size', 2**31 + 1), ('size', '123'), ('size', 1.5),
    ('sha256', 'invalid'), ('sha256', 'A' * 64), ('sha256', None),
    ('signature', ''), ('signature', 'a' * 88), ('signature', True),
    ('name', '../IliasSync-1.2.3-Linux-x64.deb'), ('name', 'IliasSync-1.2.3-Linux-x64.tar.gz'),
    ('url', 'https://evil.example/IliasSync-1.2.3-Linux-x64.deb'),
    ('url', 'https://github.com.evil.example/schroedernils/ilias-sync/releases/download/v1.2.3/package.deb'),
    ('url', updates.REPOSITORY_URL.replace('https:', 'http:') +
     '/releases/download/v1.2.3/IliasSync-1.2.3-Linux-x64.deb'),
    ('url', updates.REPOSITORY_URL + '/releases/download/v1.2.2/IliasSync-1.2.3-Linux-x64.deb'),
    ('url', updates.REPOSITORY_URL + '/releases/download/v1.2.3/IliasSync-1.2.3-Linux-x64.deb?token=1'),
    ('release_url', updates.REPOSITORY_URL + '/releases/tag/v1.2.2'),
    ('release_url', updates.REPOSITORY_URL + '/releases/latest'),
    ('release_url', 'https://github.com/other/repo/releases/tag/v1.2.3'),
])
def test_signed_but_invalid_metadata_fails_closed(signing, field, value):
    metadata = {**signing.value, field: value}
    with pytest.raises(updates.UpdateError):
        updates.parse_signed_release(*signing.signed(metadata), signing.public, '1.0.0')


@pytest.mark.parametrize('raw', [
    b'null', b'[]', b'{', b'\xff', b'{"schema":1,"schema":1}',
    b'[' * 1200 + b']' * 1200,
])
def test_signed_malformed_json_fails_closed(signing, raw):
    with pytest.raises(updates.UpdateError):
        updates.parse_signed_release(raw, signing.key.sign(raw), signing.public, '1.0.0')


def test_metadata_schema_is_complete_and_has_no_ignored_fields(signing):
    for metadata in ({**signing.value, 'prerelease': True},
                     {key: value for key, value in signing.value.items() if key != 'sha256'}):
        with pytest.raises(updates.UpdateError):
            updates.parse_signed_release(*signing.signed(metadata), signing.public, '1.0.0')


def test_metadata_and_signature_have_hard_byte_limits(signing):
    raw, signature = signing.signed()
    for metadata, detached in [(b'', signature), (b'x' * (updates.MAX_METADATA_BYTES + 1), signature),
                               (raw, b''), (raw, b'x' * (updates.MAX_SIGNATURE_BYTES + 1))]:
        with pytest.raises(updates.UpdateError):
            updates.parse_signed_release(metadata, detached, signing.public, '1.0.0')


def test_constructor_and_declined_consent_never_access_network_or_schedule(packaged):
    settings = data_dir() / 'settings.json'
    write_json(settings, {'scheduled': True, 'weekly_times': {'0': ['09:00']}})
    before = settings.read_bytes()
    controller = packaged.controller()
    assert controller.supported and not controller.can_check
    assert not controller.auto_check and not controller.auto_download
    packaged.question.assert_not_called()
    packaged.transport.assert_not_called()
    assert not (data_dir() / 'updates.json').exists()
    assert controller.start()
    assert controller.can_check and not controller.auto_check
    assert controller.start()
    controller._automatic_check()
    assert not controller._timer.isActive()
    packaged.transport.assert_not_called()
    assert packaged.question.call_count == 1
    assert settings.read_bytes() == before
    saved = read_json(data_dir() / 'updates.json', {})
    assert saved['consent'] is False and saved['auto_check'] is False
    assert stat.S_IMODE((data_dir() / 'updates.json').stat().st_mode) == 0o600
    second = packaged.controller()
    second.start()
    assert packaged.question.call_count == 1
    packaged.transport.assert_not_called()


@pytest.mark.parametrize(('system', 'frozen', 'machine'), [
    ('linux', False, 'x86_64'), ('linux', True, 'aarch64'), ('linux', True, 'arm64'),
    ('darwin', True, 'x86_64'), ('win32', True, 'AMD64'),
])
def test_source_and_unsupported_platforms_are_inert(packaged, monkeypatch, system, frozen, machine):
    monkeypatch.setattr(updates, 'sys', SimpleNamespace(platform=system, frozen=frozen))
    monkeypatch.setattr(updates, 'platform', SimpleNamespace(machine=lambda: machine))
    controller = packaged.controller()
    assert not controller.supported and not controller.can_check
    assert not controller.start() and not controller.check()
    controller.auto_check = True
    controller.set_busy(False)
    assert not controller.auto_check and not controller.auto_download
    packaged.question.assert_not_called()
    packaged.transport.assert_not_called()
    assert not (data_dir() / 'updates.json').exists()


def test_invalid_key_or_feed_disables_controller(packaged, signing):
    for key, url in [('', updates.FEED_URL), ('not-a-key', updates.FEED_URL),
                     (signing.public, updates.FEED_URL.replace('https:', 'http:')),
                     (signing.public, updates.FEED_URL + '?token=1')]:
        controller = updates.LinuxUpdates(key, url, '1.0.4')
        assert not controller.supported and not controller.start()
        controller.close()
    packaged.question.assert_not_called()
    packaged.transport.assert_not_called()


@pytest.mark.parametrize('preferences', [
    b'{', b'[]', b'x' * 8193,
    b'{"schema":1,"consent":"yes","auto_check":true}',
    b'{"schema":true,"consent":true,"auto_check":true}',
    b'{"schema":1,"consent":true,"consent":false,"auto_check":true}',
])
def test_damaged_preferences_never_grant_consent(packaged, preferences):
    (data_dir() / 'updates.json').write_bytes(preferences)
    controller = packaged.controller()
    assert not controller.auto_check
    controller.start()
    assert packaged.question.call_count == 1
    packaged.transport.assert_not_called()


def test_accepted_consent_runs_once_daily_on_worker_and_preserves_preferences(packaged, app, monkeypatch):
    packaged.question.return_value = QMessageBox.StandardButton.Yes
    now = [1000000]
    monkeypatch.setattr(updates.time, 'time', lambda: now[0])
    calls = []

    async def fetch(*args):
        calls.append(QThread.currentThread() is app.thread())
        return None

    monkeypatch.setattr(updates, '_fetch_release', fetch)
    controller = packaged.controller()
    controller.start()
    finish(app, controller)
    assert calls == [False]
    assert controller.auto_check and controller._timer.isActive()
    assert controller._timer.interval() == 3600000
    controller._automatic_check()
    assert calls == [False]
    now[0] += updates.CHECK_INTERVAL
    controller._automatic_check()
    finish(app, controller)
    assert calls == [False, False]
    second = packaged.controller()
    second.start()
    assert second._worker is None and second.auto_check
    assert packaged.question.call_count == 1
    second.auto_check = False
    assert not second._timer.isActive()
    assert read_json(data_dir() / 'updates.json', {})['auto_check'] is False


def test_manual_checks_allowed_after_declining_and_do_not_enable_automatic_checks(packaged, app, monkeypatch):
    fetched = []

    async def fetch(*args):
        fetched.append(args)
        return None

    monkeypatch.setattr(updates, '_fetch_release', fetch)
    controller = packaged.controller()
    feedback = []
    controller.feedback.connect(feedback.append)
    controller.start()
    assert not fetched
    assert controller.check()
    assert not controller.check()
    finish(app, controller)
    assert len(fetched) == 1 and feedback
    assert not controller.auto_check and controller.can_check
    assert updates.QMessageBox.information.call_count == 1


def test_sync_busy_defers_check_and_disables_explicit_release_open(packaged, app, monkeypatch, signing):
    release = updates.parse_signed_release(*signing.signed(), signing.public, '1.0.0')

    async def fetch(*args):
        return release

    monkeypatch.setattr(updates, '_fetch_release', fetch)
    browser = Mock(return_value=True)
    monkeypatch.setattr(updates.QDesktopServices, 'openUrl', browser)
    controller = packaged.controller()
    available, shutdown = [], []
    controller.available.connect(available.append)
    controller.shutdown_requested.connect(lambda: shutdown.append(True))
    controller.start()
    controller.set_busy(True)
    assert not controller.can_check and not controller.check()
    controller.set_busy(False)
    assert controller.check()
    controller.set_busy(True)
    finish(app, controller)
    assert available == [release] and controller._notice is None
    browser.assert_not_called()
    controller.set_busy(False)
    assert controller._notice is not None
    assert not controller.can_check
    controller.set_busy(True)
    assert not controller._open_button.isEnabled()
    controller._notice_clicked(controller._open_button)
    browser.assert_not_called()
    controller.set_busy(False)
    controller._open_button.click()
    assert browser.call_count == 1
    assert browser.call_args.args[0].toString() == signing.value['release_url']
    assert not shutdown


def test_close_cancels_pending_request_without_feedback_or_dialog(packaged, app, monkeypatch):
    started = []

    async def fetch(*args):
        started.append(True)
        await asyncio.sleep(60)

    monkeypatch.setattr(updates, '_fetch_release', fetch)
    parent = QWidget()
    controller = packaged.controller(parent=parent)
    controller.start()
    assert controller.check()
    deadline = time.monotonic() + 3
    while not started and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert started
    controller.close()
    parent.deleteLater()
    assert not controller.supported and not controller.check()
    # Cancellation is asynchronous; closing the UI never waits for a network timeout.
    finish(app, controller)
    assert controller._notice is None
    updates.QMessageBox.information.assert_not_called()


def test_preference_write_failure_never_grants_unsaved_consent(packaged, monkeypatch):
    packaged.question.return_value = QMessageBox.StandardButton.Yes
    monkeypatch.setattr(updates, 'write_json', Mock(side_effect=OSError('permission denied')))
    controller = packaged.controller()
    controller.start()
    assert not controller.auto_check and not controller._timer.isActive()
    packaged.transport.assert_not_called()
    assert updates.QMessageBox.information.call_count == 1


def test_manual_failures_are_generic_and_automatic_failures_are_quiet(packaged, app, monkeypatch):
    async def fetch(*args):
        raise updates.UpdateError('<script>untrusted server error</script>')

    monkeypatch.setattr(updates, '_fetch_release', fetch)
    controller = packaged.controller()
    controller.start()
    assert controller.check()
    finish(app, controller)
    assert controller.last_error and 'script' not in controller.last_error
    assert updates.QMessageBox.information.call_count == 1
    updates.QMessageBox.information.reset_mock()
    controller._last_check = 0
    controller.auto_check = True
    finish(app, controller)
    assert controller.last_error
    updates.QMessageBox.information.assert_not_called()
    controller._automatic_check()
    assert controller._worker is None


class Response:
    def __init__(self, chunks, *, status=200, headers=None, length=None):
        self.status, self.headers, self.content_length = status, headers or {}, length
        self.chunks, self.content = chunks, self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def iter_chunked(self, size):
        for chunk in self.chunks:
            yield chunk


@pytest.mark.asyncio
async def test_bounded_transport_rejects_chunked_overflow_bad_length_and_compression():
    for response in [Response([b'123', b'456']), Response([b'x'], length=6),
                     Response([b'x'], headers={'Content-Encoding': 'gzip'}), Response([], status=404), Response([])]:
        session = Mock(get=Mock(return_value=response))
        with pytest.raises(updates.UpdateError):
            await updates._bounded_response(session, updates.FEED_URL, 5)


@pytest.mark.asyncio
@pytest.mark.parametrize('destination', [
    'http://github.com/file', 'https://evil.example/file', 'https://github.com.evil.example/file',
    'https://github.com@evil.example/file', 'https://github.com:443/file',
    'file:///tmp/metadata', 'https://github.com/file#fragment',
])
async def test_transport_redirects_never_reach_unapproved_destinations(destination):
    session = Mock(get=Mock(return_value=Response([], status=302, headers={'Location': destination})))
    with pytest.raises(updates.UpdateError):
        await updates._bounded_response(session, updates.FEED_URL, 100)
    assert session.get.call_count == 1


@pytest.mark.asyncio
async def test_approved_github_asset_redirect_and_limit():
    session = Mock(get=Mock(side_effect=[
        Response([], status=302, headers={'Location': 'https://release-assets.githubusercontent.com/file?token=123'}),
        Response([b'ab', b'cd'], length=4),
    ]))
    assert await updates._bounded_response(session, updates.FEED_URL, 4) == b'abcd'
    assert session.get.call_args.kwargs == {'allow_redirects': False}
    session = Mock(get=Mock(return_value=Response([], status=302, headers={'Location': updates.FEED_URL})))
    with pytest.raises(updates.UpdateError):
        await updates._bounded_response(session, updates.FEED_URL, 4)
    assert session.get.call_count == 6


@pytest.mark.asyncio
async def test_fetch_uses_bounded_signed_metadata_with_private_transport(signing, monkeypatch):
    raw, signature = signing.signed()
    session = Mock(get=Mock(side_effect=[Response([raw]), Response([signature])]))

    class Session:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    factory = Mock(return_value=Session())
    monkeypatch.setattr(updates.aiohttp, 'ClientSession', factory)
    release = await updates._fetch_release(signing.public, updates.FEED_URL, '1.0.0')
    assert release.version == '1.2.3'
    assert [call.args[0] for call in session.get.call_args_list] == [updates.FEED_URL, updates.FEED_URL + '.sig']
    options = factory.call_args.kwargs
    assert not options['trust_env'] and not options['auto_decompress']
    assert options['timeout'].total == updates.REQUEST_TIMEOUT
    assert isinstance(options['cookie_jar'], updates.aiohttp.DummyCookieJar)


@pytest.mark.asyncio
async def test_fetch_total_deadline_includes_streaming(monkeypatch, signing):
    async def stalled(*args):
        await asyncio.sleep(60)

    monkeypatch.setattr(updates, '_bounded_response', stalled)
    monkeypatch.setattr(updates, 'REQUEST_TIMEOUT', .01)
    with pytest.raises(TimeoutError):
        await updates._fetch_release(signing.public, updates.FEED_URL, '1.0.0')


@pytest.fixture
def package(signing):
    content = b'!<arch>\n' + bytes(range(256)) * 1024
    value = {**signing.value, 'size': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
             'signature': base64.b64encode(signing.key.sign(content)).decode('ascii')}
    release = updates.parse_signed_release(*signing.signed(value), signing.public, '1.0.0')
    return SimpleNamespace(content=content, release=release)


def package_transport(monkeypatch, response):
    session = Mock(get=Mock(return_value=response))

    class Session:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    factory = Mock(return_value=Session())
    monkeypatch.setattr(updates.aiohttp, 'ClientSession', factory)
    return factory, session


def finish_download(app, controller):
    deadline = time.monotonic() + 3
    while controller._download_worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert controller._download_worker is None, 'Update download did not finish'
    app.processEvents()


@pytest.mark.asyncio
async def test_download_stream_is_private_and_published_only_after_all_checks(monkeypatch, signing, package):
    chunks = [package.content[:100000], package.content[100000:]]
    factory, session = package_transport(monkeypatch, Response(chunks, length=len(package.content)))
    progress = []
    result = await updates._download_package(signing.public, package.release, progress.append)
    assert result.path == data_dir() / 'updates' / package.release.version / package.release.name
    assert result.path.read_bytes() == package.content
    assert result.identity == updates._identity(result.path.lstat())
    assert stat.S_IMODE(result.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(result.path.parent.stat().st_mode) == 0o700
    assert not list(result.path.parent.glob('*.part'))
    assert progress[-1] == 100 and all(value <= 99 for value in progress[:-1])
    assert session.get.call_args.args[0] == package.release.url
    assert factory.call_args.kwargs['timeout'].total == updates.DOWNLOAD_TIMEOUT
    assert not factory.call_args.kwargs['trust_env']


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['truncated', 'oversize', 'bad-hash', 'bad-signature', 'wrong-key', 'length'])
async def test_package_corruption_never_publishes_ready_deb(monkeypatch, signing, package, failure):
    release, content, public = package.release, package.content, signing.public
    length = None
    if failure == 'truncated':
        content = content[:-1]
    elif failure == 'oversize':
        content += b'x'
    elif failure == 'bad-hash':
        content = b'x' + content[1:]
    elif failure == 'bad-signature':
        release = replace(release, signature=base64.b64encode(signing.key.sign(b'other package')).decode('ascii'))
    elif failure == 'wrong-key':
        public = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    else:
        length = release.size + 1
    package_transport(monkeypatch, Response([content[:100000], content[100000:]], length=length))
    progress = []
    with pytest.raises(updates.UpdateError):
        await updates._download_package(public, release, progress.append)
    folder = data_dir() / 'updates' / release.version
    assert not list(folder.iterdir())
    assert 100 not in progress


@pytest.mark.asyncio
async def test_download_does_not_follow_local_directory_symlinks(monkeypatch, tmp_path, signing, package):
    target = tmp_path / 'outside'
    target.mkdir()
    (data_dir() / 'updates').symlink_to(target, target_is_directory=True)
    session = Mock(side_effect=AssertionError('No network before checking the target directory'))
    monkeypatch.setattr(updates.aiohttp, 'ClientSession', session)
    with pytest.raises(updates.UpdateError):
        await updates._download_package(signing.public, package.release, lambda value: None)
    session.assert_not_called()
    assert not list(target.iterdir())


@pytest.mark.asyncio
async def test_cancelled_download_removes_partial_file(monkeypatch, signing, package):
    class InterruptedResponse(Response):
        async def iter_chunked(self, size):
            yield package.content[:1000]
            raise asyncio.CancelledError

    package_transport(monkeypatch, InterruptedResponse([]))
    with pytest.raises(asyncio.CancelledError):
        await updates._download_package(signing.public, package.release, lambda value: None)
    assert not list((data_dir() / 'updates' / package.release.version).iterdir())


def test_download_click_then_install_click_hands_off_verified_local_file(packaged, app, monkeypatch, package):
    async def fetch(*args):
        return package.release

    monkeypatch.setattr(updates, '_fetch_release', fetch)
    monkeypatch.setattr(updates, '_can_install_packages', lambda: True)
    browser = Mock(return_value=True)
    monkeypatch.setattr(updates.QDesktopServices, 'openUrl', browser)
    controller = packaged.controller()
    controller.start()
    assert controller.check()
    finish(app, controller)
    assert controller._download_button is not None
    packaged.transport.assert_not_called()
    browser.assert_not_called()
    package_transport(monkeypatch, Response([package.content], length=len(package.content)))
    controller._download_button.click()
    assert controller._download_worker is not None
    assert not controller.can_check
    finish_download(app, controller)
    assert controller._install_button is not None
    browser.assert_not_called()
    path = controller._notice_package.path
    controller._install_button.click()
    assert browser.call_count == 1
    assert browser.call_args.args[0].isLocalFile()
    assert browser.call_args.args[0].toLocalFile() == str(path)


def test_download_finishing_during_sync_defers_install_notice(packaged, app, monkeypatch, package):
    monkeypatch.setattr(updates, '_can_install_packages', lambda: True)
    package_transport(monkeypatch, Response([package.content]))
    controller = packaged.controller()
    controller.start()
    assert controller._begin_download(package.release)
    controller.set_busy(True)
    finish_download(app, controller)
    assert controller._ready_package is not None
    assert controller._notice is None
    controller.set_busy(False)
    assert controller._install_button is not None and controller._notice is not None


@pytest.fixture
def verified_package(monkeypatch, signing, package):
    path = data_dir() / 'updates' / package.release.version / package.release.name
    path.parent.mkdir(parents=True, mode=0o700)
    path.write_bytes(package.content)
    updates._verify_package(path, package.release, signing.public)
    return updates._VerifiedPackage(package.release, path, updates._identity(path.lstat()))


def test_install_rechecks_actual_sync_lock_and_defers_handoff(packaged, monkeypatch, verified_package):
    monkeypatch.setattr(updates, '_can_install_packages', lambda: True)
    browser = Mock(return_value=True)
    monkeypatch.setattr(updates.QDesktopServices, 'openUrl', browser)
    controller = packaged.controller()
    controller.start()
    with FileLock(data_dir() / 'sync.lock', timeout=0):
        assert not controller._install_package(verified_package)
        assert controller._ready_package is verified_package
        browser.assert_not_called()
    # Even when the cached busy flag never changed, the parent's next poll
    # reopens the deferred ready notice. There is no automatic handoff.
    controller.set_busy(False)
    assert controller._install_button is not None
    browser.assert_not_called()
    controller._install_button.click()
    assert browser.call_count == 1


def test_install_rechecks_parent_process_and_busy_flag(packaged, monkeypatch, verified_package):
    monkeypatch.setattr(updates, '_can_install_packages', lambda: True)
    browser = Mock(return_value=True)
    monkeypatch.setattr(updates.QDesktopServices, 'openUrl', browser)
    parent = QWidget()
    controller = packaged.controller(parent=parent)
    controller.start()
    for field in ('process', 'run_info'):
        setattr(parent, field, object())
        assert not controller._install_package(verified_package)
        setattr(parent, field, None)
    controller.set_busy(True)
    assert not controller._install_package(verified_package)
    browser.assert_not_called()
    controller.close()
    parent.close()


@pytest.mark.parametrize('change', ['contents', 'symlink', 'missing'])
def test_changed_verified_package_cannot_reach_package_manager(packaged, monkeypatch, verified_package, change):
    monkeypatch.setattr(updates, '_can_install_packages', lambda: True)
    browser = Mock(return_value=True)
    monkeypatch.setattr(updates.QDesktopServices, 'openUrl', browser)
    controller = packaged.controller()
    controller.start()
    path = verified_package.path
    if change == 'contents':
        path.write_bytes(b'x' * path.stat().st_size)
    elif change == 'symlink':
        path.unlink()
        path.symlink_to('/tmp/untrusted.deb')
    else:
        path.unlink()
    assert not controller._install_package(verified_package)
    browser.assert_not_called()
    assert updates.QMessageBox.information.call_count == 1


def test_download_button_rechecks_sync_lock_before_network(packaged, monkeypatch, package):
    monkeypatch.setattr(updates, '_can_install_packages', lambda: True)
    controller = packaged.controller()
    controller.start()
    with FileLock(data_dir() / 'sync.lock', timeout=0):
        assert not controller._begin_download(package.release)
    assert controller._download_worker is None
    assert controller._pending_notice is package.release
    packaged.transport.assert_not_called()


def test_portable_or_no_gui_package_manager_uses_release_fallback(packaged, monkeypatch, package):
    monkeypatch.setattr(updates, '_can_install_packages', lambda: False)
    controller = packaged.controller()
    controller.start()
    controller._pending_notice = package.release
    controller._show_notice()
    assert controller._download_button is None and controller._install_button is None
    assert controller._open_button is not None
    assert not controller._begin_download(package.release)
    packaged.transport.assert_not_called()


def test_close_cancels_download_without_install_or_ready_notice(packaged, app, monkeypatch, package):
    started = []

    async def download(*args):
        started.append(True)
        await asyncio.sleep(60)

    monkeypatch.setattr(updates, '_download_package', download)
    monkeypatch.setattr(updates, '_can_install_packages', lambda: True)
    controller = packaged.controller()
    controller.start()
    assert controller._begin_download(package.release)
    deadline = time.monotonic() + 3
    while not started and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.001)
    assert started
    controller.close()
    finish_download(app, controller)
    assert controller._ready_package is None and controller._notice is None
    updates.QMessageBox.information.assert_not_called()


def test_installed_detector_requires_debian_install_and_gui_package_tool(monkeypatch):
    monkeypatch.setattr(updates, 'sys', SimpleNamespace(executable='/opt/iliassync/IliasSync'))
    monkeypatch.setattr(updates.shutil, 'which', lambda name: '/usr/bin/gnome-software' if name == 'gnome-software' else None)
    assert updates._can_install_packages()
    monkeypatch.setattr(updates.shutil, 'which', lambda name: None)
    assert not updates._can_install_packages()
    monkeypatch.setattr(updates.shutil, 'which', lambda name: '/usr/bin/gnome-software')
    monkeypatch.setattr(updates, 'sys', SimpleNamespace(executable='/home/user/Downloads/IliasSync/IliasSync'))
    assert not updates._can_install_packages()


@pytest.mark.asyncio
async def test_release_builder_metadata_and_package_interoperate_end_to_end(tmp_path, monkeypatch):
    from scripts.update_feeds import generate_feeds, package_names

    key = Ed25519PrivateKey.generate()
    public = base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
    # Ephemeral local fixture only; this does not provision a production secret.
    monkeypatch.setenv('UPDATE_SIGNING_KEY', base64.b64encode(key.private_bytes_raw()).decode('ascii'))
    public_file = tmp_path / 'public-key.txt'
    public_file.write_text(public + '\n')
    assets = tmp_path / 'release-assets'
    assets.mkdir()
    for name in package_names('2.3.4'):
        payload = b'Synthetic signed package ' + name.encode()
        (assets / name).write_bytes(payload)
        (assets / (name + '.sha256')).write_text(hashlib.sha256(payload).hexdigest() + '  ' + name + '\n')
    generate_feeds(assets, '2.3.4', public_file)
    release = updates.parse_signed_release((assets / 'linux-x64.json').read_bytes(),
                                            (assets / 'linux-x64.json.sig').read_bytes(), public, '1.0.4')
    content = (assets / release.name).read_bytes()
    package_transport(monkeypatch, Response([content], length=len(content)))
    verified = await updates._download_package(public, release, lambda value: None)
    assert verified.path.read_bytes() == content
    assert verified.release.version == '2.3.4'


@pytest.mark.asyncio
async def test_package_download_deadline_cleans_up_stalled_stream(monkeypatch, package, signing):
    async def stalled(*args):
        yield package.content[:1000]
        await asyncio.sleep(60)

    package_transport(monkeypatch, Response([]))
    monkeypatch.setattr(updates, '_response_chunks', stalled)
    monkeypatch.setattr(updates, 'DOWNLOAD_TIMEOUT', .01)
    with pytest.raises(TimeoutError):
        await updates._download_package(signing.public, package.release, lambda value: None)
    assert not list((data_dir() / 'updates' / package.release.version).iterdir())
