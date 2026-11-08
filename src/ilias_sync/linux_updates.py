"""Signed Linux updates, with opt-in checks only while the GUI is open.

LinuxUpdates owns its consent, result and error dialogs. ``available`` emits a
LinuxRelease for observation; the host must not add a second result dialog.
``feedback`` emits the same plain text shown for manual checks. start()/check()
return whether they were accepted. All controller calls belong on the Qt thread.
Downloads require a click and verified bytes; installation requires a second
click to hand off to the native package manager. Portable installs use releases.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import platform
import re
import shutil
import stat
import struct
import sys
import tempfile
import time
from urllib.parse import urljoin, urlsplit

import aiohttp
from filelock import FileLock, Timeout
from PySide6.QtCore import QObject, QThread, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget

from .i18n import t
from .storage import data_dir, write_json

REPOSITORY_URL = 'https://github.com/schroedernils/ilias-sync'
FEED_URL = REPOSITORY_URL + '/releases/latest/download/linux-x64.json'
MAX_METADATA_BYTES = 64 * 1024
MAX_SIGNATURE_BYTES = 1024
MAX_PACKAGE_BYTES = 2 * 1024**3
REQUEST_TIMEOUT = 20
DOWNLOAD_TIMEOUT = 15 * 60
CHECK_INTERVAL = 24 * 60 * 60
_VERSION = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
_FIELDS = {'schema', 'version', 'platform', 'url', 'name', 'size', 'sha256', 'signature', 'release_url'}
_RUNNING_CHECKS = set()  # Threads outlive a closing window until cancellation completes.


class UpdateError(ValueError):
    """Untrusted or unavailable release metadata; never display its content."""


@dataclass(frozen=True)
class LinuxRelease:
    version: str
    url: str
    name: str
    size: int
    sha256: str
    signature: str
    release_url: str


@dataclass(frozen=True)
class _VerifiedPackage:
    release: LinuxRelease
    path: Path
    identity: tuple


def _version(value):
    if not isinstance(value, str) or len(value) > 64 or not re.fullmatch(_VERSION, value):
        raise UpdateError('Expected a stable semantic version')
    return tuple(int(component) for component in value.split('.'))


def _base64(value, size):
    try:
        encoded = value.encode('ascii') if isinstance(value, str) else value
        decoded = base64.b64decode(encoded, validate=True)
        if len(decoded) == size and base64.b64encode(decoded) == encoded:
            return decoded
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        pass
    raise UpdateError('Invalid signature or key encoding')


def _public_key(value):
    # Trust only the key supplied by the bundled configuration, never a feed key.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    raw = value if isinstance(value, bytes) and len(value) == 32 else _base64(value, 32)
    return Ed25519PublicKey.from_public_bytes(raw)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise UpdateError('Duplicate metadata field')
        result[key] = value
    return result


def parse_signed_release(metadata: bytes, signature: bytes, public_key, current_version: str) -> LinuxRelease | None:
    """Verify the exact signed bytes before parsing schema 1; never offer a downgrade.

    The detached .sig is canonical base64 (one trailing newline is allowed), or
    64 raw Ed25519 bytes. The package signature field is canonical base64. Package
    bytes are fetched and independently verified only after a download click.
    """
    if not 0 < len(metadata) <= MAX_METADATA_BYTES or not 0 < len(signature) <= MAX_SIGNATURE_BYTES:
        raise UpdateError('Metadata exceeds its size limit')
    from cryptography.exceptions import InvalidSignature
    detached = signature if len(signature) == 64 else _base64(signature.strip(), 64)
    try:
        _public_key(public_key).verify(detached, metadata)
    except InvalidSignature:
        raise UpdateError('Invalid metadata signature') from None
    try:
        value = json.loads(metadata.decode('utf-8'), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError, RecursionError):
        raise UpdateError('Invalid metadata JSON') from None
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise UpdateError('Unexpected metadata fields')
    if type(value['schema']) is not int or value['schema'] != 1 or value['platform'] != 'Linux-x64':
        raise UpdateError('Unsupported release schema or platform')
    latest, current = _version(value['version']), _version(current_version)
    name = f'IliasSync-{value["version"]}-Linux-x64.deb'
    release_url = f'{REPOSITORY_URL}/releases/tag/v{value["version"]}'
    if (value['name'] != name or value['release_url'] != release_url
            or value['url'] != f'{REPOSITORY_URL}/releases/download/v{value["version"]}/{name}'):
        raise UpdateError('Unexpected release origin, tag or package name')
    if type(value['size']) is not int or not 0 < value['size'] <= MAX_PACKAGE_BYTES:
        raise UpdateError('Invalid package size')
    if not isinstance(value['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['sha256']):
        raise UpdateError('Invalid package hash')
    _base64(value['signature'], 64)
    if latest <= current:
        return None
    return LinuxRelease(**{key: value[key] for key in _FIELDS - {'schema', 'platform'}})


def _allowed_transport_url(url):
    try:
        parts = urlsplit(url)
        return (parts.scheme == 'https' and parts.netloc in {
            'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com',
        } and not parts.fragment and not any(ord(char) <= 32 or ord(char) == 127 for char in url))
    except ValueError:
        return False


async def _response_chunks(session, url, limit, expected_size=None):
    for _ in range(6):
        if not _allowed_transport_url(url):
            raise UpdateError('Unapproved metadata redirect')
        async with session.get(url, allow_redirects=False) as response:
            if response.status in {301, 302, 303, 307, 308}:
                location = response.headers.get('Location')
                if not location:
                    raise UpdateError('Missing redirect location')
                url = urljoin(url, location)
                continue
            if (response.status != 200 or response.headers.get('Content-Encoding', 'identity') != 'identity'
                    or (response.content_length is not None and not 0 <= response.content_length <= limit)):
                raise UpdateError('Invalid metadata response')
            if expected_size is not None and response.content_length not in {None, expected_size}:
                raise UpdateError('Unexpected package response length')
            received = 0
            async for chunk in response.content.iter_chunked(64 * 1024):
                received += len(chunk)
                if received > limit:
                    raise UpdateError('Metadata exceeds its size limit')
                yield chunk
            if not received or (expected_size is not None and received != expected_size):
                raise UpdateError('Empty metadata response')
            return
    raise UpdateError('Too many metadata redirects')


async def _bounded_response(session, url, limit):
    content = bytearray()
    async for chunk in _response_chunks(session, url, limit):
        content.extend(chunk)
    return bytes(content)


async def _fetch_release(public_key, feed_url, version):
    if feed_url != FEED_URL:
        raise UpdateError('Unapproved update feed')
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT, sock_connect=5, sock_read=5)
    async with asyncio.timeout(REQUEST_TIMEOUT):
        async with aiohttp.ClientSession(
            timeout=timeout, cookie_jar=aiohttp.DummyCookieJar(), trust_env=False, auto_decompress=False,
            headers={'User-Agent': 'IliasSync-Update-Check', 'Accept-Encoding': 'identity'},
        ) as session:
            metadata = await _bounded_response(session, feed_url, MAX_METADATA_BYTES)
            signature = await _bounded_response(session, feed_url + '.sig', MAX_SIGNATURE_BYTES)
    return parse_signed_release(metadata, signature, public_key, version)


def _can_install_packages():
    # This is the exact installed executable path produced by scripts/installers.py.
    # A frozen portable directory must never be overwritten with the Debian install.
    executable = Path(getattr(sys, 'executable', ''))
    return (executable.resolve() == Path('/opt/iliassync/IliasSync') and any(shutil.which(name) for name in (
        'gnome-software', 'plasma-discover', 'gdebi-gtk', 'qapt-deb-installer', 'io.elementary.appcenter', 'snap-store',
    )))


def _identity(value):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _verify_package(path, release, public_key):
    from cryptography.exceptions import InvalidSignature
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != release.size:
            raise UpdateError('Unexpected package size or file type')
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != release.sha256:
            raise UpdateError('Package hash mismatch')
        # Pure Ed25519 needs the complete message. Map the bounded private file
        # instead of allocating a second package-sized bytes object in memory.
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            try:
                _public_key(public_key).verify(_base64(release.signature, 64), data)
            except InvalidSignature:
                raise UpdateError('Invalid package signature') from None
        if _identity(before) != _identity(os.fstat(stream.fileno())):
            raise UpdateError('Package changed during verification')


async def _download_package(public_key, release, progress):
    # These values came from authenticated metadata; assert their path and size
    # invariants again before using them as local filesystem or network targets.
    _version(release.version)
    expected_name = f'IliasSync-{release.version}-Linux-x64.deb'
    if (release.name != expected_name or type(release.size) is not int or not 0 < release.size <= MAX_PACKAGE_BYTES
            or release.url != f'{REPOSITORY_URL}/releases/download/v{release.version}/{expected_name}'):
        raise UpdateError('Invalid download target')
    directory = data_dir() / 'updates'
    for folder in (directory, directory / release.version):
        folder.mkdir(mode=0o700, exist_ok=True)
        if folder.is_symlink() or not folder.is_dir():
            raise UpdateError('Untrusted update directory')
        folder.chmod(0o700)
    destination = directory / release.version / release.name
    if destination.is_symlink():
        raise UpdateError('Untrusted package destination')
    descriptor, temporary = tempfile.mkstemp(prefix='.download-', suffix='.part', dir=destination.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT, sock_connect=10, sock_read=30)
            async with asyncio.timeout(DOWNLOAD_TIMEOUT):
                async with aiohttp.ClientSession(
                    timeout=timeout, cookie_jar=aiohttp.DummyCookieJar(), trust_env=False, auto_decompress=False,
                    headers={'User-Agent': 'IliasSync-Update-Check', 'Accept-Encoding': 'identity'},
                ) as session:
                    received, previous = 0, -1
                    async for chunk in _response_chunks(session, release.url, release.size, release.size):
                        stream.write(chunk)
                        received += len(chunk)
                        percent = min(99, received * 100 // release.size)
                        if percent != previous:
                            progress(percent)
                            previous = percent
            stream.flush()
            os.fsync(stream.fileno())
        _verify_package(temporary, release, public_key)
        os.replace(temporary, destination)
        verified = _VerifiedPackage(release, destination, _identity(destination.lstat()))
        progress(100)
        return verified
    finally:
        temporary.unlink(missing_ok=True)


class _CheckThread(QThread):
    def __init__(self, public_key, feed_url, version, manual):
        super().__init__()  # No QWidget parent: closing the window cannot destroy a running QThread.
        self.arguments = public_key, feed_url, version
        self.manual = manual
        self.result = None
        self.failed = False
        self.cancelled = False
        self._loop = self._task = None

    def _execute(self):
        return _fetch_release(*self.arguments)

    def run(self):
        loop = asyncio.new_event_loop()
        try:
            self._loop = loop
            task = loop.create_task(self._execute())
            self._task = task
            if self.isInterruptionRequested():
                task.cancel()
            loop.run_until_complete(task)
            self.result = task.result()
            self.cancelled = self.isInterruptionRequested()
        except asyncio.CancelledError:
            self.cancelled = True
        except Exception:
            # Network errors and untrusted exception text never enter a rich-text dialog.
            self.failed = True
        finally:
            self._task = self._loop = None
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor(timeout=1))
            loop.close()

    def cancel(self):
        self.requestInterruption()
        loop, task = self._loop, self._task
        if loop is not None and task is not None:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass  # The request finished between reading and cancelling the task.


class _DownloadThread(_CheckThread):
    progress = Signal(int)

    def __init__(self, public_key, release):
        super().__init__(public_key, '', '', manual=True)
        self.arguments = public_key, release, self.progress.emit

    def _execute(self):
        return _download_package(*self.arguments)


class LinuxUpdates(QObject):
    shutdown_requested = Signal()  # Linux never requests shutdown or installs silently.
    changed = Signal()
    feedback = Signal(str)
    available = Signal(object)  # LinuxRelease, with authenticated metadata only.

    def __init__(self, public_key, feed_url, version, parent=None):
        super().__init__(parent)
        self._public_key, self._feed_url, self._version = public_key, feed_url, version
        self._supported = False
        self._started = self._closed = self._busy = False
        self._worker = self._notice = self._open_button = self._notice_release = None
        self._download_worker = self._progress = self._download_button = self._install_button = None
        self._ready_package = self._notice_package = None
        self._pending_notice = None
        self._notified_version = ''
        self._consent, self._auto_check, self._last_check = None, False, 0
        self.last_error = ''
        self._timer = QTimer(self)
        self._timer.setInterval(60 * 60 * 1000)
        self._timer.setTimerType(Qt.TimerType.VeryCoarseTimer)
        self._timer.timeout.connect(self._automatic_check)
        if (sys.platform != 'linux' or not getattr(sys, 'frozen', False)
                or platform.machine().lower() not in {'x86_64', 'amd64'} or struct.calcsize('P') != 8):
            return
        try:
            _public_key(public_key)
            _version(version)
            if feed_url != FEED_URL:
                return
        except (ImportError, ValueError, TypeError):
            return
        self._supported = True
        self._load_preferences()

    @property
    def supported(self):
        return self._supported and not self._closed

    @property
    def can_check(self):
        return (self.supported and self._started and not self._busy
                and self._worker is None and self._download_worker is None
                and self._notice is None and self._ready_package is None)

    @property
    def auto_check(self):
        return self.supported and self._auto_check

    @auto_check.setter
    def auto_check(self, enabled):
        if not self.supported:
            return
        previous = self._consent, self._auto_check
        self._consent = self._auto_check = bool(enabled)
        if not self._save_preferences():
            self._consent, self._auto_check = previous
        self._update_timer()
        self.changed.emit()

    @property
    def auto_download(self):
        return False

    def _parent_widget(self):
        return self.parent() if isinstance(self.parent(), QWidget) else None

    def _load_preferences(self):
        try:
            with (data_dir() / 'updates.json').open('rb') as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                return
            value = json.loads(raw, object_pairs_hook=_unique_object)
            if (not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 1
                    or type(value.get('consent')) is not bool or type(value.get('auto_check')) is not bool):
                return
            self._consent = value['consent']
            self._auto_check = self._consent and value['auto_check']
            checked = value.get('last_check', 0)
            if type(checked) in {int, float} and 0 <= checked <= time.time() and math.isfinite(checked):
                self._last_check = checked
        except (OSError, ValueError, RecursionError):
            pass  # A damaged preference file never grants consent.

    def _save_preferences(self):
        try:
            write_json(data_dir() / 'updates.json', {
                'schema': 1, 'consent': self._consent, 'auto_check': self._auto_check, 'last_check': self._last_check,
            })
            return True
        except OSError:
            self._inform('App update preferences could not be saved. Check access to the application data folder.')
            return False

    def start(self):
        if not self.supported:
            return False
        if self._started:
            return True
        self._started = True
        if self._consent is None:
            answer = QMessageBox.question(
                self._parent_widget(), t('App updates'),
                t('Check for app updates automatically? IliasSync will contact GitHub once a day while open. '
                  'You can change this in Settings. Updates are installed manually.'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
            )
            if self._closed:
                return False
            self.auto_check = answer == QMessageBox.StandardButton.Yes
        else:
            self._update_timer()
        self.changed.emit()
        return True

    def _update_timer(self):
        if self._started and self.auto_check:
            self._timer.start()
            self._automatic_check()
        else:
            self._timer.stop()

    @Slot()
    def _automatic_check(self):
        if not self.auto_check or not self.can_check:
            return
        elapsed = time.time() - self._last_check
        if self._last_check and 0 <= elapsed < CHECK_INTERVAL:
            return
        self._begin_check(manual=False)

    def check(self):
        return self._begin_check(manual=True)

    def _begin_check(self, manual):
        if not self.can_check:
            return False
        self._last_check = time.time()  # Persist attempts too, so failures cannot cause hourly request loops.
        if not self._save_preferences() and not manual:
            return False
        worker = _CheckThread(self._public_key, self._feed_url, self._version, manual)
        self._worker = worker
        _RUNNING_CHECKS.add(worker)
        worker.finished.connect(self._check_finished)
        worker.finished.connect(lambda: _RUNNING_CHECKS.discard(worker))
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self.changed.emit()
        return True

    @Slot()
    def _check_finished(self):
        worker, self._worker = self._worker, None
        if self._closed or worker is None:
            return
        self.changed.emit()
        if worker.failed:
            self.last_error = t('App updates could not be checked. Check your connection and try again.')
            if worker.manual:
                self._inform('App updates could not be checked. Check your connection and try again.')
        elif worker.result is None:
            self.last_error = ''
            if worker.manual:
                self._inform('IliasSync is up to date.')
        else:
            self.last_error = ''
            self.available.emit(worker.result)
            if worker.manual or worker.result.version != self._notified_version:
                self._pending_notice = worker.result
                self._show_notice()

    def _inform(self, text):
        translated = t(text)
        self.feedback.emit(translated)
        QMessageBox.information(self._parent_widget(), t('App updates'), translated)

    def _show_notice(self):
        if self._closed or self._busy or self._notice is not None:
            return
        if self._ready_package is not None:
            self._notice_package, self._ready_package = self._ready_package, None
            release = self._notice_package.release
        elif self._pending_notice is not None:
            release, self._pending_notice = self._pending_notice, None
        else:
            return
        notice = QMessageBox(self._parent_widget())
        notice.setWindowTitle(t('App updates'))
        notice.setIcon(QMessageBox.Icon.Information)
        notice.setTextFormat(Qt.TextFormat.PlainText)
        if self._notice_package is not None:
            notice.setText(t('IliasSync {version} is ready to install.', version=release.version))
            notice.setInformativeText(t('The download has been verified. Install update opens your system package '
                                       'manager. Confirm the installation there.'))
            self._install_button = notice.addButton(t('Install update'), QMessageBox.ButtonRole.AcceptRole)
        else:
            notice.setText(t('IliasSync {version} is available.', version=release.version))
            if _can_install_packages():
                notice.setInformativeText(t('Download the update, then open your system package manager to install it.'))
                self._download_button = notice.addButton(t('Download update'), QMessageBox.ButtonRole.AcceptRole)
            else:
                notice.setInformativeText(t('Open the release page to update this portable installation or choose '
                                           'a package supported by your system.'))
        self._open_button = notice.addButton(t('Open release'), QMessageBox.ButtonRole.AcceptRole)
        later = notice.addButton(t('Later'), QMessageBox.ButtonRole.RejectRole)
        notice.setDefaultButton(later)
        notice.setEscapeButton(later)
        self._notice, self._notice_release = notice, release
        self._notified_version = release.version
        notice.buttonClicked.connect(self._notice_clicked)
        notice.finished.connect(self._notice_finished)
        notice.open()
        self.changed.emit()

    @Slot(object)
    def _notice_clicked(self, button):
        if not self.supported or self._busy or self._notice_release is None:
            return
        if button is self._download_button:
            self._begin_download(self._notice_release)
        elif button is self._install_button:
            self._install_package(self._notice_package)
        elif button is self._open_button:
            if not QDesktopServices.openUrl(QUrl(self._notice_release.release_url)):
                self._inform('The release page could not be opened. Try again after checking your default browser.')

    @Slot(int)
    def _notice_finished(self, result):
        notice, self._notice = self._notice, None
        self._open_button = self._notice_release = None
        self._download_button = self._install_button = self._notice_package = None
        if notice is not None:
            notice.deleteLater()
        self.changed.emit()

    def _sync_busy(self):
        window = self.parent()
        return self._busy or bool(getattr(window, 'process', None) or getattr(window, 'run_info', None))

    def _begin_download(self, release):
        if not self.supported or self._sync_busy() or self._download_worker is not None or not _can_install_packages():
            return False
        try:
            # Recheck the same lock used by the parent, including CLI/scheduled syncs.
            with FileLock(data_dir() / 'sync.lock', timeout=0):
                pass
        except (OSError, Timeout):
            self._pending_notice = release
            return False
        progress = QProgressDialog(t('Downloading update…'), t('Cancel'), 0, 100, self._parent_widget())
        progress.setWindowTitle(t('App updates'))
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        self._progress = progress
        worker = _DownloadThread(self._public_key, release)
        self._download_worker = worker
        worker.progress.connect(progress.setValue)
        progress.canceled.connect(worker.cancel)
        _RUNNING_CHECKS.add(worker)
        worker.finished.connect(self._download_finished)
        worker.finished.connect(lambda: _RUNNING_CHECKS.discard(worker))
        worker.finished.connect(worker.deleteLater)
        worker.start()
        progress.show()
        self.changed.emit()
        return True

    @Slot()
    def _download_finished(self):
        worker, self._download_worker = self._download_worker, None
        if self._progress is not None:
            self._progress.canceled.disconnect()
            self._progress.close()
            self._progress.deleteLater()
            self._progress = None
        if self._closed or worker is None:
            return
        if worker.failed:
            self._inform('The update download could not be verified. Check your connection and try again.')
        elif not worker.cancelled and worker.result is not None:
            self._ready_package = worker.result
            self._show_notice()
        self.changed.emit()

    def _install_package(self, package):
        if package is None or not self.supported:
            return False
        if self._sync_busy():
            self._ready_package = package
            return False
        if not _can_install_packages():
            self._inform('No supported package manager was found. Open the release page to install the update manually.')
            return False
        try:
            # Hold the sync lock through handoff. A scheduled sync cannot start
            # between the final idle check and opening the native installer.
            with FileLock(data_dir() / 'sync.lock', timeout=0):
                current = package.path.lstat()
                if not stat.S_ISREG(current.st_mode) or _identity(current) != package.identity:
                    raise UpdateError('Verified package changed before installation')
                if self._sync_busy():
                    self._ready_package = package
                    return False
                opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(package.path)))
        except Timeout:
            self._ready_package = package
            return False
        except (OSError, UpdateError):
            self._inform('The verified update is no longer available. Check for updates and download it again.')
            return False
        if not opened:
            self._inform('The package manager could not be opened. Open the release page to install the update manually.')
        return bool(opened)

    def set_busy(self, busy):
        if self._busy == bool(busy):
            if not self._busy and not self._closed:
                self._show_notice()
            return
        self._busy = bool(busy)
        for button in (self._open_button, self._download_button, self._install_button):
            if button is not None:
                button.setEnabled(not self._busy)
        self.changed.emit()
        if not self._busy and not self._closed:
            self._show_notice()
            self._automatic_check()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._timer.stop()
        self._pending_notice = None
        self._ready_package = None
        if self._worker is not None:
            self._worker.cancel()
        if self._download_worker is not None:
            self._download_worker.cancel()
        if self._progress is not None:
            self._progress.hide()
        if self._notice is not None:
            self._notice.reject()
        self.changed.emit()
