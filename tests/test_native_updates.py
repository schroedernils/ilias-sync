"""No feeds, real preference writes or update checks: C mocks and a delegate probe."""
import ctypes
import gc
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from types import SimpleNamespace
import weakref

import pytest

from ilias_sync import native_updates as updates


class Function:
    def __init__(self, result=None, effect=None):
        self.result = result
        self.effect = effect
        self.calls = []

    def __call__(self, *args):
        # Native code retains only function pointers, not Python references.
        self.calls.append(tuple(ctypes.cast(arg, ctypes.c_void_p).value
                                if isinstance(arg, ctypes._CFuncPtr) else arg for arg in args))
        return self.effect(*args) if self.effect else self.result


def mac_library():
    library = SimpleNamespace()
    for name in ('init', 'start', 'check', 'can_check'):
        setattr(library, 'ilias_updates_' + name, Function(1))
    for name in ('auto_check', 'auto_download'):
        get = Function(0)
        setattr(library, 'ilias_updates_get_' + name, get)
        setattr(library, 'ilias_updates_set_' + name,
                Function(effect=lambda value, get=get: setattr(get, 'result', value)))
    library.ilias_updates_set_busy = Function()
    library.ilias_updates_set_presentation_guard = Function()
    library.ilias_updates_close = Function()
    library.ilias_updates_last_error = Function(b'Sparkle configuration is invalid')
    return library


def windows_library():
    library = SimpleNamespace()
    for name in ('init', 'cleanup', 'check_update_with_ui', 'set_app_details', 'set_appcast_url',
                 'set_lang', 'set_can_shutdown_callback', 'set_shutdown_request_callback'):
        setattr(library, 'win_sparkle_' + name, Function())
    library.win_sparkle_set_eddsa_public_key = Function(1)
    get = library.win_sparkle_get_automatic_check_for_updates = Function(0)
    library.win_sparkle_set_automatic_check_for_updates = Function(
        effect=lambda value: setattr(get, 'result', value))
    return library


@pytest.fixture
def native(monkeypatch, tmp_path):
    libraries = []

    def configure(platform, library=None, *, frozen=True):
        library = library or (mac_library() if platform == 'darwin' else windows_library())
        monkeypatch.setattr(updates, 'sys', SimpleNamespace(platform=platform, frozen=frozen,
                                                         _MEIPASS=str(tmp_path)))
        monkeypatch.setattr(updates, '__file__', str(tmp_path / 'ilias_sync/native_updates.py'))
        loader = Function(library)
        monkeypatch.setattr(updates.ctypes, 'CDLL', loader)
        libraries.append(library)
        return library, loader

    yield configure
    if updates._owner is not None:
        updates._owner.close()


def windows(**kwargs):
    return updates.NativeUpdates('base64-key', 'https://updates.example.test/windows.xml', '1.0.4', **kwargs)


@pytest.mark.parametrize('platform,frozen', [('darwin', False), ('win32', False), ('linux', True)])
def test_source_and_unsupported_platforms_are_inert(native, platform, frozen):
    _, loader = native(platform, frozen=frozen)
    updater = updates.NativeUpdates()
    assert not updater.supported
    assert not updater.start() and not updater.check() and not updater.can_check
    updater.auto_check = True
    updater.auto_download = True
    updater.set_busy(True)
    assert not updater.auto_check and not updater.auto_download
    updater.close()
    updater.close()
    assert loader.calls == []


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_missing_library_or_symbols_are_reported_without_starting(native, platform):
    _, loader = native(platform)
    loader.effect = lambda *_: (_ for _ in ()).throw(OSError('missing native library'))
    updater = windows()
    assert not updater.supported
    assert updater.last_error == 'missing native library'
    assert not updater.start()
    loader.effect = None
    loader.result = SimpleNamespace()
    updater = windows()
    assert not updater.supported and updater.last_error


def test_mac_loads_from_frozen_package_and_preserves_native_preferences(native):
    library, loader = native('darwin')
    library.ilias_updates_get_auto_check.result = 1
    library.ilias_updates_get_auto_download.result = 1
    updater = updates.NativeUpdates()
    assert updater.supported and updater.auto_check and updater.auto_download
    assert loader.calls == [(str(Path(updates.__file__).parent / 'assets/native/libilias_updates.dylib'),)]
    assert library.ilias_updates_init.calls == [()]
    assert not library.ilias_updates_start.calls
    assert not library.ilias_updates_check.calls
    assert not library.ilias_updates_set_auto_check.calls
    assert not library.ilias_updates_set_auto_download.calls
    assert library.ilias_updates_set_busy.argtypes == [ctypes.c_int]
    assert library.ilias_updates_init.restype is ctypes.c_int
    assert library.ilias_updates_close.restype is None


def test_mac_start_check_and_preferences_use_native_state(native):
    library, _ = native('darwin')
    updater = updates.NativeUpdates()
    assert not updater.can_check and not updater.check()
    assert updater.start() and updater.start()
    assert library.ilias_updates_start.calls == [()]
    library.ilias_updates_can_check.result = 0
    assert not updater.check()
    library.ilias_updates_can_check.result = 1
    assert updater.check()
    updater.auto_check = True
    updater.auto_download = True
    assert updater.auto_check and updater.auto_download
    # Simulate a later change in Sparkle's own UI; getters cannot be cached.
    library.ilias_updates_get_auto_check.result = 0
    assert not updater.auto_check
    updater.auto_download = False
    assert not updater.auto_download
    updater.set_busy(True)
    updater.set_busy(False)
    assert library.ilias_updates_set_busy.calls == [(1,), (0,)]
    updater.close()
    updater.close()
    assert library.ilias_updates_close.calls == [()]
    assert not updater.supported and not updater.start() and not updater.check()


def test_mac_init_start_and_check_failures_leave_actionable_errors(native):
    library, _ = native('darwin')
    library.ilias_updates_init.result = 0
    updater = updates.NativeUpdates()
    assert not updater.supported and 'configuration' in updater.last_error
    assert not library.ilias_updates_start.calls
    library.ilias_updates_init.result = 1
    updater = updates.NativeUpdates()
    library.ilias_updates_start.result = 0
    assert not updater.start() and not updater.can_check
    assert 'configuration' in updater.last_error
    library.ilias_updates_start.result = 1
    assert updater.start() and updater.last_error == ''
    library.ilias_updates_check.result = 0
    assert not updater.check() and 'configuration' in updater.last_error


def test_windows_configures_cdecl_metadata_key_language_before_start(native):
    library, loader = native('win32')
    updater = windows()
    assert updater.supported and not updater.can_check
    assert loader.calls == [(str(Path(updates.__file__).parent / 'assets/native/WinSparkle.dll'),)]
    assert library.win_sparkle_set_app_details.calls == [('IliasSync', 'IliasSync', '1.0.4')]
    assert library.win_sparkle_set_app_details.argtypes == [ctypes.c_wchar_p] * 3
    assert library.win_sparkle_set_eddsa_public_key.calls == [(b'base64-key',)]
    assert library.win_sparkle_set_eddsa_public_key.restype is ctypes.c_int
    assert library.win_sparkle_set_appcast_url.calls == [(b'https://updates.example.test/windows.xml',)]
    assert library.win_sparkle_set_lang.calls == [(b'de',)]
    assert not library.win_sparkle_init.calls
    assert not library.win_sparkle_set_automatic_check_for_updates.calls
    assert updater.start() and updater.start() and updater.can_check and updater.check()
    assert library.win_sparkle_init.calls == [()]
    assert library.win_sparkle_check_update_with_ui.calls == [()]
    updater.auto_check = True
    assert updater.auto_check
    library.win_sparkle_get_automatic_check_for_updates.result = 0
    assert not updater.auto_check
    updater.auto_download = True
    assert not updater.auto_download


def test_windows_language_is_configurable(native):
    library, _ = native('win32')
    windows(language='en')
    assert library.win_sparkle_set_lang.calls == [(b'en',)]


@pytest.mark.parametrize('field,value', [('public_key', ''), ('feed_url', ''), ('version', ''),
                                       ('language', ''), ('public_key', 'bad\0key'), ('version', None)])
def test_windows_missing_or_invalid_config_never_loads_dll(native, field, value):
    _, loader = native('win32')
    config = dict(public_key='key', feed_url='https://updates.example.test/feed.xml', version='1.0.4')
    config[field] = value
    updater = updates.NativeUpdates(**config)
    assert not updater.supported and field in updater.last_error
    assert not loader.calls


def test_windows_rejected_signing_key_cannot_start_unsigned_updates(native):
    library, _ = native('win32')
    library.win_sparkle_set_eddsa_public_key.result = 0
    updater = windows()
    assert not updater.supported and 'EdDSA' in updater.last_error
    assert not updater.start()
    assert not library.win_sparkle_init.calls
    assert not library.win_sparkle_set_can_shutdown_callback.calls


def windows_callbacks(library):
    can = updates._CAN_SHUTDOWN(library.win_sparkle_set_can_shutdown_callback.calls[-1][0])
    request = updates._SHUTDOWN_REQUEST(library.win_sparkle_set_shutdown_request_callback.calls[-1][0])
    return can, request


def test_windows_foreign_thread_callbacks_veto_busy_and_only_invoke_host_hook(native):
    library, _ = native('win32')
    delivered = []
    updater = windows()
    updater.shutdown_requested = lambda: delivered.append(threading.get_ident())
    can, request = windows_callbacks(library)
    updater.set_busy(True)
    results = []

    def callback():
        results.append(can())
        request()

    worker = threading.Thread(target=callback)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive() and results == [0] and not delivered
    updater.set_busy(False)
    worker = threading.Thread(target=callback)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive() and results == [0, 1]
    assert delivered == [worker.ident]
    updater.shutdown_requested = None
    assert can() == 0
    request()
    assert delivered == [worker.ident]


def test_windows_hook_exceptions_do_not_escape_the_c_callback(native, caplog):
    library, _ = native('win32')

    def fail():
        raise RuntimeError('queued signal failed')

    windows(shutdown_requested=fail)
    _, request = windows_callbacks(library)
    request()
    assert 'queued signal failed' in caplog.text


def test_windows_preinstaller_callback_checks_real_lock_on_foreign_thread(native):
    from filelock import FileLock
    from ilias_sync.storage import data_dir
    library, _ = native('win32')
    updater = windows(shutdown_requested=lambda: None)
    updater.set_busy(False)  # Simulate a stale GUI poll just before a scheduled sync.
    can, _ = windows_callbacks(library)
    answers = []

    def query():
        answers.append(can())

    with FileLock(data_dir() / 'sync.lock', timeout=0):
        worker = threading.Thread(target=query)
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive() and answers == [0]
    worker = threading.Thread(target=query)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive() and answers == [0, 1]


def test_windows_preinstaller_callback_fails_closed_on_unreadable_lock(native, monkeypatch):
    library, _ = native('win32')
    windows(shutdown_requested=lambda: None)

    def denied(*args, **kwargs):
        raise PermissionError('Test lock access denied')

    monkeypatch.setattr(updates, 'FileLock', denied)
    can, _ = windows_callbacks(library)
    assert can() == 0


def test_windows_shutdown_hook_names_share_one_callback(native):
    library, _ = native('win32')
    updater = windows()
    can, request = windows_callbacks(library)
    delivered = []

    def callback():
        delivered.append(True)

    updater.on_shutdown = callback
    assert updater.shutdown_requested is callback and can() == 1
    request()
    assert delivered == [True]
    updater.shutdown_requested = None
    assert updater.on_shutdown is None and can() == 0
    updater.shutdown_requested = callback
    updater.on_shutdown = None
    assert updater.shutdown_requested is None and can() == 0


def test_windows_queued_shutdown_rechecks_the_parent_sync_lock(native):
    from filelock import FileLock
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QApplication

    from ilias_sync.storage import data_dir
    from ilias_sync.updates import UpdateController

    application = QApplication.instance() or QApplication([])

    class Window(QObject):
        process = None
        run_info = None

        def __init__(self):
            super().__init__()
            self.closed_on = []

        def close(self):
            self.closed_on.append(threading.get_ident())

    library, _ = native('win32')
    window = Window()
    controller = UpdateController(window)
    controller.backend = windows()
    controller.backend.on_shutdown = controller.shutdown_requested.emit
    can, request = windows_callbacks(library)
    # Simulate a scheduled sync starting since the parent's last busy poll.
    with FileLock(data_dir() / 'sync.lock', timeout=0):
        worker = threading.Thread(target=request)
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive() and not window.closed_on
        application.processEvents()
        assert not window.closed_on and can() == 0
    controller.refresh_busy()
    assert can() == 1
    worker = threading.Thread(target=request)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive() and not window.closed_on
    application.processEvents()
    assert window.closed_on == [threading.get_ident()]
    controller.close()


def test_callbacks_survive_gc_and_cleanup_vetoes_inflight_requests(native):
    library, _ = native('win32')
    delivered = []
    updater = windows(shutdown_requested=lambda: delivered.append(True))
    can, request = windows_callbacks(library)
    refs = [weakref.ref(callback) for callback in updater._callbacks]
    owner_ref = weakref.ref(updater)
    updater.start()
    del updater
    gc.collect()
    assert owner_ref() is not None and all(ref() is not None for ref in refs)
    assert can() == 1
    during_cleanup = []

    def cleanup():
        during_cleanup.append(can())
        request()
        assert all(ref() is not None for ref in refs)

    library.win_sparkle_cleanup.effect = cleanup
    owner_ref().close()
    assert during_cleanup == [0] and not delivered
    assert updates._owner is None


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_only_one_owner_and_close_is_idempotent_before_start(native, platform):
    library, _ = native(platform)
    first = windows()
    second = windows()
    assert first.supported and not second.supported and 'already' in second.last_error
    second.close()
    assert first.supported and updates._owner is first
    first.close()
    first.close()
    name = 'ilias_updates_close' if platform == 'darwin' else 'win_sparkle_cleanup'
    assert getattr(library, name).calls == [()]
    assert windows().supported


@pytest.mark.parametrize('platform', ['darwin', 'win32'])
def test_public_ctypes_operations_reject_worker_threads(native, platform):
    library, _ = native(platform)
    updater = windows()
    before = sum(len(function.calls) for function in vars(library).values())
    operations = [windows, updater.start, updater.check, lambda: updater.can_check,
                  lambda: updater.auto_check, lambda: setattr(updater, 'auto_check', True),
                  lambda: updater.auto_download, lambda: setattr(updater, 'auto_download', True),
                  lambda: updater.set_busy(True), updater.close]
    errors = []

    def worker():
        for operation in operations:
            try:
                operation()
            except RuntimeError as error:
                errors.append(str(error))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive() and len(errors) == len(operations)
    assert all('main thread' in error for error in errors)
    assert sum(len(function.calls) for function in vars(library).values()) == before


@pytest.mark.skipif(sys.platform != 'darwin', reason='Sparkle delegate needs the macOS SDK')
def test_sparkle_delegate_defers_resumes_and_discards_without_network(tmp_path):
    root = Path(__file__).resolve().parents[1]
    framework = root / 'build/updaters/sparkle/Sparkle.framework'
    if not framework.is_dir() or not shutil.which('xcrun'):
        pytest.skip('Sparkle 2.10.1 SDK or Xcode command line tools unavailable')
    # Compile the actual bridge and call only its delegate, never init/start/check.
    source = tmp_path / 'delegate.mm'
    source.write_text('''
#import "''' + str(root / 'src/ilias_sync/native/updates.mm') + '''"
#include <cassert>
#include <thread>
static int qtModal = 0;
static int allowPresentation() { return !qtModal; }
static int presentations = 0;
@interface DriverProbe : IliasUpdateUserDriver
@end
@implementation DriverProbe
- (void)presentUpdate:(SUAppcastItem *)item state:(SPUUserUpdateState *)state
    reply:(void (^)(SPUUserUpdateChoice))reply
{
    ++presentations;
    reply(SPUUserUpdateChoiceDismiss);
}
@end
static void drain() {
    [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.03]];
}
int main() {
    @autoreleasepool {
        closed.store(false);
        updateDelegate = [IliasUpdateDelegate new];
        // These delegate arguments are unused; do not initialize a real updater.
        SPUUpdater *sender = (SPUUpdater *)[NSObject new];
        SUAppcastItem *item = (SUAppcastItem *)[NSObject new];
        __block int installs = 0;
        void (^handler)(void) = ^{ ++installs; };
        // Test the actual standard-driver subclass without displaying a window.
        userDriver = [DriverProbe alloc];
        ilias_updates_set_presentation_guard(allowPresentation);
        qtModal = 1;
        __block int replies = 0;
        [userDriver showUpdateFoundWithAppcastItem:item state:(SPUUserUpdateState *)[NSObject new]
            reply:^(SPUUserUpdateChoice choice) { assert(choice == SPUUserUpdateChoiceDismiss); ++replies; }];
        [userDriver showUpdateInFocus];
        ilias_updates_set_busy(0);
        drain();
        assert(presentations == 0 && replies == 0);
        qtModal = 0;
        ilias_updates_set_busy(0);
        ilias_updates_set_busy(0);
        drain();
        assert(presentations == 1 && replies == 1);
        assert(![updateDelegate updater:sender shouldPostponeRelaunchForUpdate:item untilInvokingBlock:handler]);
        assert(![updateDelegate updater:sender willInstallUpdateOnQuit:item immediateInstallationBlock:handler]);
        ilias_updates_set_busy(1);
        assert([updateDelegate updater:sender shouldPostponeRelaunchForUpdate:item untilInvokingBlock:handler]);
        ilias_updates_set_busy(0);
        ilias_updates_set_busy(1);
        drain();
        assert(installs == 0 && updateDelegate.pendingInstallation != nil);
        ilias_updates_set_busy(0);
        ilias_updates_set_busy(0);
        drain();
        assert(installs == 1 && updateDelegate.pendingInstallation == nil);
        ilias_updates_set_busy(1);
        assert([updateDelegate updater:sender willInstallUpdateOnQuit:item immediateInstallationBlock:handler]);
        ilias_updates_set_busy(0);
        drain();
        assert(installs == 2);
        std::thread worker([] {
            assert(!ilias_updates_start());
            assert(!ilias_updates_check());
            assert(!ilias_updates_can_check());
            ilias_updates_set_busy(1);
            ilias_updates_close();
        });
        worker.join();
        assert(!busy.load() && !closed.load());
        ilias_updates_set_busy(1);
        assert([updateDelegate updater:sender shouldPostponeRelaunchForUpdate:item untilInvokingBlock:handler]);
        ilias_updates_set_busy(0);
        ilias_updates_close();
        drain();
        assert(installs == 2 && closed.load() && updater == nil);
        assert(!ilias_updates_start() && !ilias_updates_check());
    }
}
''')
    executable = tmp_path / 'delegate'
    compilation = subprocess.run(['xcrun', 'clang++', '-std=c++17', '-fobjc-arc', '-Werror',
                                  '-mmacosx-version-min=13.0', '-F', str(framework.parent),
                                  '-framework', 'AppKit', '-framework', 'Sparkle',
                                  '-Wl,-rpath,' + str(framework.parent), str(source), '-o', str(executable)],
                                 capture_output=True, text=True, timeout=60)
    assert compilation.returncode == 0, compilation.stderr
    result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
