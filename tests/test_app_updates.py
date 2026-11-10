from types import SimpleNamespace
from unittest.mock import Mock, patch

from filelock import FileLock
import pytest


@pytest.fixture(scope='module')
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_source_launch_does_not_load_native_updater_or_contact_github(app, monkeypatch):
    from PySide6.QtWidgets import QWidget
    import ilias_sync.updates as updates
    monkeypatch.setattr(updates.sys, 'frozen', False, raising=False)
    window = QWidget()
    with patch('ctypes.CDLL', side_effect=AssertionError('Unexpected native updater load')):
        updater = updates.UpdateController(window)
        updater.start()
        assert not updater.supported
        assert not updater.auto_check
        updater.close()
    window.close()


def test_external_sync_lock_vetoes_installation(app):
    from ilias_sync.storage import data_dir
    from ilias_sync.updates import synchronization_busy
    window = SimpleNamespace(process=None, run_info=None)
    assert not synchronization_busy(window)
    with FileLock(data_dir() / 'sync.lock', timeout=0):
        assert synchronization_busy(window)
    assert not synchronization_busy(window)
    window.process = object()
    assert synchronization_busy(window)


def test_automatic_update_consent_is_a_settings_draft_and_keeps_schedule(app, monkeypatch):
    from ilias_sync.gui import MainWindow, SettingsDialog
    from ilias_sync.storage import Settings
    from ilias_sync.i18n import set_language
    set_language('en')
    settings = Settings()
    settings.value.update(scheduled=True, schedule_mode='weekly',
                          weekly_times={str(i): ['10:30'] if i == 0 else [] for i in range(7)})
    settings.save()
    window = MainWindow()
    preferences = SimpleNamespace(supported=True, auto_check=False, auto_download=False,
                                  supports_auto_download=True, save_preferences=Mock(), check=Mock())
    window.app_updates = preferences
    dialog = SettingsDialog(window.settings, window)
    dialog.update_check.setChecked(True)
    dialog.update_download.setChecked(True)
    dialog.reject()
    preferences.save_preferences.assert_not_called()
    before = Settings().value
    dialog = SettingsDialog(window.settings, window)
    dialog.update_check.setChecked(True)
    dialog.update_download.setChecked(True)
    with patch('ilias_sync.gui.install') as install, patch('ilias_sync.gui.uninstall') as uninstall, \
            patch('ilias_sync.gui.registration_matches', return_value=True):
        dialog.save()
        install.assert_not_called()
        uninstall.assert_not_called()
    preferences.save_preferences.assert_called_once_with(True, True)
    assert Settings().value == before
    window.app_updates = None
    window.close()


def test_windows_shutdown_is_queued_and_rechecks_the_sync_lock(app):
    from PySide6.QtWidgets import QWidget
    from ilias_sync.storage import data_dir
    from ilias_sync.updates import UpdateController
    window = QWidget()
    window.close = Mock()
    updater = UpdateController(window)
    with FileLock(data_dir() / 'sync.lock', timeout=0):
        updater.finish_for_update()
        window.close.assert_not_called()
    updater.finish_for_update()
    window.close.assert_called_once()


def test_language_rebuild_retains_single_updater_and_its_preferences(app):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog
    from ilias_sync.gui import MainWindow, SettingsDialog
    from ilias_sync.updates import UpdateController
    from ilias_sync.storage import Settings
    settings = Settings()
    settings.value['language'] = 'de'
    settings.save()
    window = MainWindow()
    updater = UpdateController(window)
    window.app_updates = updater

    def save_language():
        dialog = next(d for d in app.topLevelWidgets() if isinstance(d, SettingsDialog) and d.isVisible())
        dialog.language.setCurrentIndex(dialog.language.findData('en'))
        dialog.save()
        assert dialog.result() == QDialog.DialogCode.Accepted

    QTimer.singleShot(0, save_language)
    window.background()
    replacement = app.main_window
    assert replacement.app_updates is updater
    assert updater.window is replacement and updater.parent() is replacement
    assert window.app_updates is None
    replacement.close()


def test_check_from_settings_saves_then_exits_the_modal_before_invoking_updater(app):
    from PySide6.QtCore import QTimer
    from ilias_sync.gui import MainWindow, SettingsDialog

    window = MainWindow()
    observed = []
    updater = SimpleNamespace(supported=True, auto_check=False, auto_download=False,
                              supports_auto_download=True, save_preferences=Mock(), refresh_busy=Mock(),
                              check=lambda: observed.append(app.activeModalWidget()))
    window.app_updates = updater

    def click():
        dialog = next(d for d in app.topLevelWidgets() if isinstance(d, SettingsDialog) and d.isVisible())
        assert app.activeModalWidget() is dialog
        dialog.update_check.setChecked(True)
        dialog.check_updates_button.click()
        assert not observed

    QTimer.singleShot(0, click)
    with patch('ilias_sync.gui.uninstall'), patch('ilias_sync.gui.registration_matches', return_value=True):
        window.background(3)
    app.processEvents()
    assert observed == [None]
    updater.save_preferences.assert_called_once_with(True, False)
    window.close()


def test_macos_manual_check_waits_for_modal_and_reports_a_busy_sync(app, monkeypatch):
    from PySide6.QtWidgets import QDialog, QWidget
    import ilias_sync.updates as updates

    monkeypatch.setattr(updates, 'sys', SimpleNamespace(platform='darwin'))
    window = QWidget()
    controller = updates.UpdateController(window)
    controller.backend = SimpleNamespace(supported=True, can_check=True, set_busy=Mock(), check=Mock(), close=Mock())
    dialog = QDialog(window)
    dialog.open()
    controller.check()
    controller.backend.check.assert_not_called()
    assert controller.check_timer.isActive()
    dialog.close()
    controller.check_timer.stop()
    with patch.object(updates.QMessageBox, 'information') as info:
        with FileLock(updates.data_dir() / 'sync.lock', timeout=0):
            controller.check()
        info.assert_called_once()
        controller.backend.check.assert_not_called()
    controller.check()
    controller.backend.check.assert_called_once()
    controller.close()
    window.close()
