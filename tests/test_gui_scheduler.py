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
    assert window.width() <= 700
    assert window.height() <= 450
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
    from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox
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
    assert replacement.settings_button.accessibleName() == "Settings"
    assert not replacement.progress_timer.isActive()
    replacement.close()


def test_source_dialog_only_shows_relevant_login_fields(app, source):
    from ilias_sync.gui import SourceDialog
    from ilias_sync.i18n import set_language
    from ilias_sync.storage import Settings
    set_language("de")
    dialog = SourceDialog(Settings(), source)
    dialog.stack.setCurrentIndex(1)
    dialog.update_step()
    dialog.show()
    assert dialog.password.isVisible()
    assert not dialog.idp.isVisible()
    assert not dialog.note.isVisible()
    assert not dialog.targets.isVisible()
    dialog.mode.setCurrentIndex(dialog.mode.findData("session"))
    assert not dialog.password.isVisible()
    assert dialog.note.isVisible()
    assert dialog.session.isVisible()
    dialog.stack.setCurrentIndex(2)
    dialog.update_step()
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


def test_onboarding_keeps_fields_wide_and_validates_each_step(app, source):
    from ilias_sync.gui import SourceDialog
    from ilias_sync.storage import Settings
    dialog = SourceDialog(Settings(), source)
    dialog.show()
    app.processEvents()
    assert dialog.url.width() > 420
    assert dialog.stack.currentIndex() == 0
    dialog.advance()
    assert dialog.stack.currentIndex() == 1
    dialog.user.clear()
    dialog.advance()
    assert dialog.stack.currentIndex() == 1
    assert dialog.error.isVisible()
    dialog.close()


def test_theme_uses_os_signal_and_covers_scroll_content(app):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPalette
    from ilias_sync.theme import Theme, DARK, LIGHT
    theme = Theme(app, 'system')
    original = app.styleHints().colorScheme()
    try:
        app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Dark)
        app.processEvents()
        assert app.palette().color(QPalette.ColorRole.Window).name() == DARK['window']
        assert app.palette().color(QPalette.ColorRole.Text).name() == DARK['text']
        app.styleHints().colorSchemeChanged.emit(Qt.ColorScheme.Light)
        app.processEvents()
        assert app.palette().color(QPalette.ColorRole.Base).name() == LIGHT['surface']
    finally:
        app.styleHints().setColorScheme(original)
        theme.set_mode('light')
        theme.deleteLater()


def test_controls_switch_to_pause_and_stop_for_background_run(app, source):
    import os
    import psutil
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Settings, data_dir, read_json, write_json
    settings = Settings()
    settings.save_source(source)
    row = {'token':'test-run','source':source.id,'pid':os.getpid(),'created':psutil.Process().create_time(),'state':'running'}
    write_json(data_dir() / 'active-run.json', row)
    window = MainWindow()
    window.show()
    window.check_active_run()
    assert window.sync_button.text() == ''
    assert window.sync_button.accessibleName() == 'Pausieren'
    assert window.stop_button.accessibleName() == 'Beenden'
    assert window.stop_button.text() == ''
    assert window.stop_button.isVisible()
    window.sync_or_pause()
    assert read_json(data_dir() / 'run-command.json', {})['action'] == 'pause'
    write_json(data_dir() / 'active-run.json', {**row,'state':'paused'})
    window.check_active_run()
    assert window.sync_button.text() == ''
    assert window.sync_button.accessibleName() == 'Fortsetzen'
    window.stop_sync()
    assert read_json(data_dir() / 'run-command.json', {})['action'] == 'stop'
    write_json(data_dir() / 'active-run.json', {**row,'state':'stopped'})
    window.check_active_run()
    assert window.sync_button.text() == 'Jetzt synchronisieren'
    assert not window.progress_timer.isActive()
    window.close()


def test_course_list_reports_total_and_searches_beyond_first_view(app, source):
    from ilias_sync.gui import CoursesDialog
    from ilias_sync.storage import Settings
    courses = [{'id':f'crs-{i}', 'name':f'Kurs {i:02}', 'url':f'https://campus.example.edu/go/crs/{i}'} for i in range(20)]
    dialog = CoursesDialog(courses,source,Settings(),None)
    assert dialog.listing.count() == 20
    dialog.search.setText('Kurs 19')
    assert sum(not dialog.listing.item(i).isHidden() for i in range(20)) == 1
    dialog.close()


def test_mapping_menu_builds_course_folder_file_hierarchy(app, source):
    from ilias_sync.gui import FolderMappingDialog
    from ilias_sync.storage import Settings, data_dir, write_json
    state=data_dir()/'sources'/source.id
    write_json(state/'courses.json',[{'id':'crs-1','name':'PSE','url':source.url+'/go/crs/1'}])
    write_json(state/'manifest.json',{'files':{'file:1':{'path':'PSE/Material/Intro.pdf','logical':'crs-1/Material/Intro.pdf','course_id':'crs-1'}}})
    dialog=FolderMappingDialog(source,Settings())
    course=dialog.tree.topLevelItem(0)
    assert course.text(0) == 'PSE'
    assert course.child(0).text(0) == 'Material'
    assert course.child(0).child(0).text(0) == 'Intro.pdf'
    dialog.close()


def test_source_actions_are_compact_accessible_icons(app, source):
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Settings
    settings=Settings()
    settings.save_source(source)
    window=MainWindow()
    assert window.width() <= 950
    for action in (window.routing_button, window.edit_button, window.open_button):
        assert action.text() == ''
        assert action.toolTip()
        assert action.accessibleName()
        assert action.width() == 34
    window.close()


def test_hover_edit_targets_its_source_and_keyboard_respects_busy(app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ilias_sync.gui import SourceList
    listing = SourceList()
    listing.addItems(['Hochschule A\na.example.edu', 'Hochschule B\nb.example.edu'])
    listing.resize(260, 260)
    listing.show()
    app.processEvents()
    assert not listing.edit_button.isVisible()
    requested = []
    listing.editRequested.connect(lambda: requested.append(listing.currentRow()))
    QTest.mouseMove(listing.viewport(), listing.visualItemRect(listing.item(1)).center())
    app.processEvents()
    assert listing.edit_button.isVisible()
    listing.edit_button.click()
    assert requested == [1]
    listing.setCurrentRow(0)
    QTest.keyClick(listing, Qt.Key.Key_F2)
    assert requested == [1, 0]
    listing.edit_button.setEnabled(False)
    QTest.keyClick(listing, Qt.Key.Key_F2)
    assert requested == [1, 0]
    listing.close()
