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
    assert window.files.accessibleName() == "Downloaded files"
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
