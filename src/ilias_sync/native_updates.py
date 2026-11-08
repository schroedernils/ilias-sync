"""Explicit, main-thread access to the bundled Sparkle/WinSparkle updaters.

Construction never starts a check. Source runs and unsupported platforms are
inert. The host polls its sync FileLock and calls set_busy() before start() and
as that state changes; it must also veto application termination during sync.
Sparkle's consent and preferences belong to Sparkle/NSUserDefaults, not JSON.
"""
from collections.abc import Callable
import ctypes
import logging
from pathlib import Path
import sys
import threading


_CAN_SHUTDOWN = ctypes.CFUNCTYPE(ctypes.c_int)
_SHUTDOWN_REQUEST = ctypes.CFUNCTYPE(None)
_owner = None  # SDKs are process singletons; retain their callbacks until close.
_log = logging.getLogger(__name__)


def _main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Native updater calls require the main thread.')


def _bind(library, name, args=(), result=None):
    function = getattr(library, name)
    function.argtypes = list(args)
    function.restype = result
    return function


class NativeUpdates:
    """One updater per process; close on GUI shutdown, from the main thread.

    Windows requires public_key, feed_url and version. language defaults to de;
    Sparkle uses the app bundle's native localization and its Info.plist config.
    shutdown_requested runs on a WinSparkle worker: bind a queued Qt Signal.emit here,
    never QApplication.quit or close() directly. Without a hook installation is
    vetoed. The GUI must recheck sync state when handling the queued signal.

    start()/check() return whether the operation was accepted. Missing libraries
    or configuration leave supported=False and an explanation in last_error.
    auto_check persists natively on both platforms; auto_download is macOS only.
    """

    def __init__(self, public_key: str = '', feed_url: str = '', version: str = '', *,
                 language: str = 'de', shutdown_requested: Callable[[], None] | None = None):
        global _owner
        _main_thread()
        self._library = None
        self._platform = sys.platform
        self._started = False
        self._closed = threading.Event()
        self._busy = threading.Event()
        self._callbacks = ()
        self.shutdown_requested = shutdown_requested
        self.last_error = ''
        if not getattr(sys, 'frozen', False) or self._platform not in {'darwin', 'win32'}:
            return
        if _owner is not None:
            self.last_error = 'An updater already owns the native SDK.'
            return
        try:
            # PyInstaller sets __file__ below sys._MEIPASS, including in an app
            # bundle. Do not resolve a symlink out of the bundled asset tree.
            assets = Path(__file__).parent / 'assets/native'
            if self._platform == 'darwin':
                library = ctypes.CDLL(str(assets / 'libilias_updates.dylib'))
                self._bind_mac(library)
                if not library.ilias_updates_init():
                    self.last_error = self._mac_error(library)
                    return
            else:
                for name, value in [('public_key', public_key), ('feed_url', feed_url),
                                    ('version', version), ('language', language)]:
                    if not isinstance(value, str) or not value.strip() or '\0' in value:
                        raise ValueError(f'Windows updater requires a nonempty {name} without NUL characters.')
                # WinSparkle exports __cdecl, including its callbacks (not stdcall).
                library = ctypes.CDLL(str(assets / 'WinSparkle.dll'))
                self._bind_windows(library)
                if not library.win_sparkle_set_eddsa_public_key(public_key.encode('ascii')):
                    raise ValueError('WinSparkle rejected the EdDSA public key.')
                library.win_sparkle_set_app_details('IliasSync', 'IliasSync', version)
                library.win_sparkle_set_appcast_url(feed_url.encode('utf-8'))
                library.win_sparkle_set_lang(language.encode('ascii'))
                self._callbacks = (_CAN_SHUTDOWN(self._can_shutdown), _SHUTDOWN_REQUEST(self._shutdown_request))
                library.win_sparkle_set_can_shutdown_callback(self._callbacks[0])
                library.win_sparkle_set_shutdown_request_callback(self._callbacks[1])
            self._library = library
            _owner = self
        except (OSError, AttributeError, ValueError) as error:
            self.last_error = str(error)

    @staticmethod
    def _bind_mac(library):
        for name in ('init', 'start', 'check', 'can_check', 'get_auto_check', 'get_auto_download'):
            _bind(library, 'ilias_updates_' + name, result=ctypes.c_int)
        for name in ('set_auto_check', 'set_auto_download', 'set_busy'):
            _bind(library, 'ilias_updates_' + name, (ctypes.c_int,))
        _bind(library, 'ilias_updates_close')
        _bind(library, 'ilias_updates_last_error', result=ctypes.c_char_p)

    @staticmethod
    def _bind_windows(library):
        for name in ('init', 'cleanup', 'check_update_with_ui'):
            _bind(library, 'win_sparkle_' + name)
        _bind(library, 'win_sparkle_set_app_details', (ctypes.c_wchar_p,) * 3)
        _bind(library, 'win_sparkle_set_eddsa_public_key', (ctypes.c_char_p,), ctypes.c_int)
        for name in ('set_appcast_url', 'set_lang'):
            _bind(library, 'win_sparkle_' + name, (ctypes.c_char_p,))
        _bind(library, 'win_sparkle_get_automatic_check_for_updates', result=ctypes.c_int)
        _bind(library, 'win_sparkle_set_automatic_check_for_updates', (ctypes.c_int,))
        _bind(library, 'win_sparkle_set_can_shutdown_callback', (_CAN_SHUTDOWN,))
        _bind(library, 'win_sparkle_set_shutdown_request_callback', (_SHUTDOWN_REQUEST,))

    @staticmethod
    def _mac_error(library):
        message = library.ilias_updates_last_error()
        return message.decode('utf-8', errors='replace') if message else 'Sparkle is unavailable.'

    def _can_shutdown(self):
        # Called on a foreign thread: read Python state only, no ctypes or Qt UI.
        return int(not self._closed.is_set() and not self._busy.is_set() and callable(self.shutdown_requested))

    def _shutdown_request(self):
        if self._can_shutdown():
            try:
                self.shutdown_requested()
            except Exception:
                _log.exception('Native update shutdown hook failed')

    @property
    def on_shutdown(self) -> Callable[[], None] | None:
        """Compatibility name for hosts assigning the queued shutdown signal."""
        return self.shutdown_requested

    @on_shutdown.setter
    def on_shutdown(self, callback: Callable[[], None] | None):
        self.shutdown_requested = callback

    @property
    def supported(self) -> bool:
        return self._library is not None and not self._closed.is_set()

    def start(self) -> bool:
        _main_thread()
        if not self.supported:
            return False
        if not self._started:
            if self._platform == 'darwin':
                if not self._library.ilias_updates_start():
                    self.last_error = self._mac_error(self._library)
                    return False
            else:
                self._library.win_sparkle_init()
            self._started = True
            self.last_error = ''
        return True

    @property
    def can_check(self) -> bool:
        _main_thread()
        if not self.supported or not self._started:
            return False
        # WinSparkle has no readiness query; its UI coalesces manual checks.
        return self._platform == 'win32' or bool(self._library.ilias_updates_can_check())

    def check(self) -> bool:
        _main_thread()
        if not self.can_check:
            return False
        if self._platform == 'darwin':
            accepted = bool(self._library.ilias_updates_check())
            if not accepted:
                self.last_error = self._mac_error(self._library)
            return accepted
        self._library.win_sparkle_check_update_with_ui()
        return True

    @property
    def auto_check(self) -> bool:
        _main_thread()
        if not self.supported:
            return False
        if self._platform == 'darwin':
            return bool(self._library.ilias_updates_get_auto_check())
        return bool(self._library.win_sparkle_get_automatic_check_for_updates())

    @auto_check.setter
    def auto_check(self, enabled: bool):
        _main_thread()
        if self.supported:
            if self._platform == 'darwin':
                self._library.ilias_updates_set_auto_check(int(bool(enabled)))
            else:
                self._library.win_sparkle_set_automatic_check_for_updates(int(bool(enabled)))

    @property
    def auto_download(self) -> bool:
        _main_thread()
        return (self.supported and self._platform == 'darwin'
                and bool(self._library.ilias_updates_get_auto_download()))

    @auto_download.setter
    def auto_download(self, enabled: bool):
        _main_thread()
        if self.supported and self._platform == 'darwin':
            self._library.ilias_updates_set_auto_download(int(bool(enabled)))

    def set_busy(self, busy: bool):
        _main_thread()
        if busy:
            self._busy.set()
        else:
            self._busy.clear()
        if self.supported and self._platform == 'darwin':
            self._library.ilias_updates_set_busy(int(bool(busy)))

    def close(self):
        global _owner
        _main_thread()
        if self._closed.is_set():
            return
        self._closed.set()  # Any callbacks already in flight now veto shutdown.
        if self._library is not None:
            if self._platform == 'darwin':
                self._library.ilias_updates_close()
            else:
                # Joins WinSparkle's worker threads; keep callbacks alive until
                # after cleanup has returned, including when start wasn't called.
                self._library.win_sparkle_cleanup()
            self._library = None
        self._callbacks = ()
        if _owner is self:
            _owner = None
