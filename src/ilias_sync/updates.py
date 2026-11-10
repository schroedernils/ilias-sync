"""App updates are independent of university credentials and sync preferences."""
import json
from pathlib import Path
import platform
import sys

from filelock import FileLock, Timeout
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .i18n import t
from .storage import data_dir

RELEASES_URL = 'https://github.com/schroedernils/ilias-sync/releases'


class UpdatePreferencesError(RuntimeError):
    pass


def synchronization_busy(window):
    if getattr(window, 'process', None) or getattr(window, 'run_info', None):
        return True
    try:
        with FileLock(data_dir() / 'sync.lock', timeout=0):
            return False
    except (Timeout, OSError):
        # Unreadable lock state must not be interpreted as a safe installation window.
        return True


class UpdateController(QObject):
    shutdown_requested = Signal()

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.backend = None
        self.error = ''
        self.check_timer = QTimer(self)
        self.check_timer.setSingleShot(True)
        self.check_timer.timeout.connect(self.check)
        self.shutdown_requested.connect(self.finish_for_update)
        if not getattr(sys, 'frozen', False):
            return
        try:
            config = json.loads((Path(__file__).parent / 'assets/update-config.json').read_text())
            key = config['public_key']
            if config['releases'] != RELEASES_URL:
                raise ValueError('Invalid release origin')
            if sys.platform in {'darwin', 'win32'}:
                from .native_updates import NativeUpdates
                target = 'windows-x64' if sys.platform == 'win32' else 'macOS-' + (
                    'arm64' if platform.machine().lower() in {'arm64', 'aarch64'} else 'x64')
                self.backend = NativeUpdates(key, RELEASES_URL + f'/latest/download/{target}.xml', __version__)
                self.backend.on_shutdown = self.shutdown_requested.emit
                if sys.platform == 'darwin':
                    self.backend.set_presentation_guard(lambda: QApplication.activeModalWidget() is None)
            elif sys.platform == 'linux' and platform.machine().lower() in {'x86_64', 'amd64'}:
                from .linux_updates import LinuxUpdates
                self.backend = LinuxUpdates(key, RELEASES_URL + '/latest/download/linux-x64.json', __version__, parent=window)
            if self.backend is not None and not self.backend.supported:
                self.error = t('App updates could not be initialized. Reinstall the latest release to repair them.')
        except (OSError, ValueError, AttributeError, RuntimeError):
            self.error = t('App updates could not be initialized. Reinstall the latest release to repair them.')
            self.backend = None
        self.busy_timer = QTimer(self)
        self.busy_timer.setInterval(1000)
        self.busy_timer.timeout.connect(self.refresh_busy)

    @property
    def supported(self):
        return self.backend is not None and bool(self.backend.supported)

    @property
    def auto_check(self):
        return bool(self.supported and self.backend.auto_check)

    @property
    def auto_download(self):
        return bool(self.supported and self.backend.auto_download)

    @property
    def supports_auto_download(self):
        return self.supported and sys.platform == 'darwin'

    def start(self):
        if not self.supported:
            return
        self.refresh_busy()
        try:
            if self.backend.start() is not False:
                self.busy_timer.start()
            else:
                self.error = t('App updates could not be initialized. Reinstall the latest release to repair them.')
        except (OSError, RuntimeError):
            self.error = t('App updates could not be initialized. Reinstall the latest release to repair them.')

    def refresh_busy(self):
        if self.supported:
            busy = synchronization_busy(self.window)
            self.backend.set_busy(busy)
            return busy
        return False

    def check(self):
        self.check_timer.stop()
        if not self.supported:
            QMessageBox.information(self.window, t('App updates'), self.error or
                                    t('App updates are available in installed releases.'))
            return
        if sys.platform == 'darwin' and QApplication.activeModalWidget() is not None:
            self.check_timer.start(250)
            return
        busy = self.refresh_busy()
        if sys.platform == 'darwin' and busy:
            QMessageBox.information(self.window, t('App updates'),
                                    t('Wait for the current sync to finish, then check for app updates again.'))
            return
        if self.backend.can_check:
            if self.backend.check() is not False:
                return
            QMessageBox.information(self.window, t('App updates'),
                                    t('App updates could not be checked. Check your connection and try again.'))
        else:
            QMessageBox.information(self.window, t('App updates'), self.error or
                                    t('An update check is already running. Try again in a moment.'))

    def save_preferences(self, automatic, download):
        if not self.supported:
            return
        # Change native defaults only in direct response to the user's saved choices.
        try:
            if self.backend.auto_check != automatic:
                self.backend.auto_check = automatic
            if self.supports_auto_download and self.backend.auto_download != download:
                self.backend.auto_download = download
        except (OSError, RuntimeError) as error:
            raise UpdatePreferencesError(t('Update preferences could not be saved. Please try again.')) from error

    def finish_for_update(self):
        if synchronization_busy(self.window):
            self.refresh_busy()
            return
        # Reuse the regular close flow: view state is saved and an active sync refuses closing.
        self.window.close()

    def close(self):
        self.check_timer.stop()
        if hasattr(self, 'busy_timer'):
            self.busy_timer.stop()
        if self.backend:
            self.backend.close()
