import plistlib
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_empty_window_accessibility_and_no_idle_polling(app):
    from ilias_sync.gui import MainWindow
    window = MainWindow()
    assert window.sources.count() == 0
    assert not window.sync_button.isEnabled()
    assert not window.progress_timer.isActive()
    assert window.files.accessibleName() == "Heruntergeladene Dateien"
    window.close()


def test_source_dialog_never_displays_password(app, source):
    from PySide6.QtWidgets import QLineEdit
    from ilias_sync.gui import SourceDialog
    from ilias_sync.storage import Settings
    dialog = SourceDialog(Settings(), source)
    assert dialog.password.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.password.text() == ""
    dialog.close()


def test_mac_schedule_is_oneshot(tmp_path, monkeypatch):
    import ilias_sync.scheduler as schedule
    monkeypatch.setattr(schedule.sys, "platform", "darwin")
    monkeypatch.setattr(schedule.os, "getuid", lambda: 501, raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with patch.object(schedule.subprocess, "run") as run:
        schedule.install(6)
    plist = plistlib.loads((tmp_path / "Library/LaunchAgents/org.iliassync.desktop.plist").read_bytes())
    assert plist["StartInterval"] == 21600
    assert not plist.get("KeepAlive")
    assert plist["ProgramArguments"][-1] == "--sync"
    assert run.call_count == 2


def test_windows_schedule_uses_current_user_and_no_shell(monkeypatch):
    import ilias_sync.scheduler as schedule
    monkeypatch.setattr(schedule.sys, "platform", "win32")
    with patch.object(schedule.subprocess, "run") as run:
        schedule.install(12)
    args = run.call_args.args[0]
    assert args[0] == "schtasks"
    assert "/RU" not in args
    assert args[args.index("/MO") + 1] == "12"
    assert not run.call_args.kwargs.get("shell")


def test_linux_timer_has_no_resident_loop(tmp_path, monkeypatch):
    import ilias_sync.scheduler as schedule
    monkeypatch.setattr(schedule.sys, "platform", "linux")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with patch.object(schedule.subprocess, "run"):
        schedule.install(6)
    service = (tmp_path / ".config/systemd/user/org.iliassync.desktop.service").read_text()
    timer = (tmp_path / ".config/systemd/user/org.iliassync.desktop.timer").read_text()
    assert "Type=oneshot" in service
    assert "RandomizedDelaySec=5min" in timer
    assert "OnUnitActiveSec=6h" in timer


def test_language_change_is_immediate_and_persisted(app):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QPushButton
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Settings
    window = MainWindow()
    window.show()
    assert window.sync_button.text() == "Jetzt synchronisieren"

    def change():
        dialog = next(w for w in app.topLevelWidgets() if isinstance(w, QDialog) and w.isVisible())
        language = next(w for w in dialog.findChildren(QComboBox) if w.findData("en") >= 0)
        language.setCurrentIndex(language.findData("en"))
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
    QTimer.singleShot(30, change)
    window.background()
    assert Settings().value["language"] == "en"
    replacement = app.main_window
    assert replacement.sync_button.text() == "Sync now"
    assert any(b.text() == "Settings" for b in replacement.findChildren(QPushButton))
    assert not replacement.progress_timer.isActive()
    replacement.close()


def test_source_dialog_only_shows_relevant_login_fields(app, source):
    from ilias_sync.gui import SourceDialog
    from ilias_sync.i18n import set_language
    from ilias_sync.storage import Settings
    set_language("de")
    dialog = SourceDialog(Settings(), source)
    dialog.show()
    assert dialog.password.isVisible()
    assert not dialog.idp.isVisible()
    assert not dialog.note.isVisible()
    assert not dialog.targets.isVisible()
    dialog.mode.setCurrentIndex(dialog.mode.findData("session"))
    assert not dialog.password.isVisible()
    assert dialog.note.isVisible()
    assert dialog.session.isVisible()
    dialog.automatic.setChecked(False)
    assert dialog.targets.isVisible()
    dialog.close()


def test_file_status_summarizes_skipped_types(app, source):
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Settings, data_dir, write_json
    settings = Settings()
    settings.save_source(source)
    write_json(data_dir() / "sources" / source.id / "status.json", {
        "state": "Up to date", "result": {"files": 2, "skipped": {"FORUM": 1, "TEST": 3}, "warnings": 0}
    })
    window = MainWindow()
    assert "4 übersprungen" in window.status.text()
    assert "FORUM" not in window.status.text()
    window.close()
