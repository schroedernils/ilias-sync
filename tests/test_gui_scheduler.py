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
    from ilias_sync.storage import Settings, data_dir, write_json, source_scope
    settings = Settings()
    settings.save_source(source)
    write_json(data_dir() / "sources" / source.id / "status.json", {
        "state": "Up to date", "scope": source_scope(source), "result": {"files": 2, "skipped": {"FORUM": 1, "TEST": 3}, "warnings": 0}
    })
    window = MainWindow()
    from ilias_sync.presentation import report_html
    report = report_html({'result': {'skipped': {'FORUM': 1, 'TEST': 3}}})
    assert 'Foren: 1' in report and 'Tests: 3' in report
    assert window.sync_panel.mark.tone == 'success'
    assert "FORUM" not in window.status.text()
    window.close()


def test_onboarding_keeps_fields_wide_and_validates_each_step(app, source):
    from ilias_sync.gui import SourceDialog
    from ilias_sync.storage import Settings
    dialog = SourceDialog(Settings())
    dialog.url.setText(source.url)
    dialog.name.setText(source.name)
    dialog.client.setText(source.client_id)
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
    assert window.sync_button.text() in ('Pausieren', 'Fortsetzen')
    assert window.sync_button.accessibleName() == 'Pausieren'
    assert window.stop_button.accessibleName() == 'Beenden'
    assert window.stop_button.text() == 'Diesen Sync beenden'
    assert window.stop_button.isVisible()
    window.sync_or_pause()
    assert read_json(data_dir() / 'run-command.json', {})['action'] == 'pause'
    write_json(data_dir() / 'active-run.json', {**row,'state':'paused'})
    window.check_active_run()
    assert window.sync_button.text() in ('Pausieren', 'Fortsetzen')
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
    assert window.width() <= 1000
    for action in (window.routing_button, window.edit_button, window.open_button):
        assert action.text() == ''
        assert action.toolTip()
        assert action.accessibleName()
        assert action.width() == 34
    window.close()


def test_folder_actions_sit_after_course_selection(app, source):
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Settings
    settings = Settings()
    settings.save_source(source)
    window = MainWindow()
    window.show()
    app.processEvents()
    assert window.courses_button.geometry().right() < window.routing_button.geometry().left()
    assert window.routing_button.geometry().right() < window.open_button.geometry().left()
    assert window.routing_button.parentWidget() == window.courses_button.parentWidget()
    assert abs(window.courses_button.geometry().center().y() - window.open_button.geometry().center().y()) <= 1
    window.close()


def test_file_headers_sort_numerically_and_filters_survive_refresh(app, source):
    from PySide6.QtCore import Qt, QPoint
    from PySide6.QtTest import QTest
    from ilias_sync.gui import MainWindow, FileFilterDialog
    from ilias_sync.storage import Settings, data_dir, write_json
    settings = Settings()
    settings.save_source(source)
    entries = {
        '1': {'path': 'Zeta/notes.txt', 'target_stat': [102400], 'course_id': 'crs-1', 'course_name': 'Zeta'},
        '2': {'path': 'Alpha/a.pdf', 'target_stat': [3072], 'course_id': 'crs-2', 'course_name': 'Alpha'},
        '3': {'path': 'Alpha/b.pdf', 'target_stat': [20 * 1024 ** 2], 'course_id': 'crs-2', 'course_name': 'Alpha'},
    }
    write_json(data_dir() / 'sources' / source.id / 'manifest.json', {'files': entries})
    window = MainWindow()
    window.show()
    app.processEvents()
    header = window.files_header
    size_header = QPoint(header.sectionViewportPosition(1) + header.sectionSize(1) // 2, header.height() // 2)
    QTest.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=size_header)
    assert header.sortIndicatorSection() == 1
    initial_order = header.sortIndicatorOrder()
    QTest.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=size_header)
    assert header.sortIndicatorOrder() != initial_order
    values = [window.files.item(row, 1).data(Qt.ItemDataRole.UserRole) for row in range(3)]
    assert values == sorted(values, reverse=header.sortIndicatorOrder() == Qt.SortOrder.DescendingOrder)
    QTest.mouseClick(header.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(12, header.height() // 2))
    assert header.sortIndicatorSection() == 0
    window.files.sortItems(1, Qt.SortOrder.AscendingOrder)
    assert [window.files.item(row, 1).data(Qt.ItemDataRole.UserRole) for row in range(3)] == [3072, 102400, 20 * 1024 ** 2]
    window.files.sortItems(1, Qt.SortOrder.DescendingOrder)
    assert window.files.item(0, 1).data(Qt.ItemDataRole.UserRole) == 20 * 1024 ** 2
    window.files.sortItems(0, Qt.SortOrder.AscendingOrder)
    assert window.files.item(0, 0).text() == 'Alpha/a.pdf'
    dialog = FileFilterDialog(window)
    dialog.course.setCurrentIndex(dialog.course.findData('crs-2'))
    dialog.kind.setCurrentIndex(dialog.kind.findData('.pdf'))
    dialog.size.setCurrentIndex(dialog.size.findData('small'))
    assert window.apply_file_filters() == 1
    assert window.files_header.filter_button.isChecked()
    window.refresh()
    assert window.apply_file_filters() == 1
    assert [window.files.item(row, 0).text() for row in range(3) if not window.files.isRowHidden(row)] == ['Alpha/a.pdf']
    dialog.reset()
    assert window.apply_file_filters() == 3
    assert not window.files_header.filter_button.isChecked()
    assert window.files_header.filter_button.geometry().left() > 20
    dialog.close()
    window.close()


def test_folder_mapping_saves_custom_names_and_id_opt_in(app, source):
    from ilias_sync.gui import FolderMappingDialog
    from ilias_sync.storage import Settings, data_dir, write_json
    settings = Settings()
    settings.save_source(source)
    write_json(data_dir() / 'sources' / source.id / 'courses.json', [{'id': 'crs-1', 'name': 'PSE', 'url': source.url + '/go/crs/1'}])
    dialog = FolderMappingDialog(source, settings)
    assert not dialog.show_ids.isChecked()
    row = dialog.tree.topLevelItem(0)
    dialog.tree.setCurrentItem(row)
    dialog.folder_name.setText('Meine Vorlesung')
    dialog.folder_name.textEdited.emit('Meine Vorlesung')
    dialog.show_ids.setChecked(True)
    assert row.text(1) == 'Meine Vorlesung [crs-1]'
    dialog.save()
    saved = Settings().sources()[0]
    assert saved.folder_names == {'course/crs-1': 'Meine Vorlesung'}
    assert saved.include_course_ids
    dialog.close()


def test_settings_expose_multiple_daily_times_and_validate_empty_list(app):
    from PySide6.QtCore import QTime
    from ilias_sync.gui import SettingsDialog
    from ilias_sync.storage import Settings
    settings = Settings()
    dialog = SettingsDialog(settings)
    dialog.enabled.setChecked(True)
    dialog.schedule_mode.setCurrentIndex(dialog.schedule_mode.findData('times'))
    dialog.tabs.setCurrentIndex(1)
    dialog.show()
    app.processEvents()
    assert dialog.times_panel.isVisible() and not dialog.hours.isVisible()
    dialog.save()
    assert dialog.error.isVisible()
    for hour, minute in [(18, 30), (8, 0), (8, 0)]:
        dialog.time_edit.setTime(QTime(hour, minute))
        dialog.add_time()
    assert [dialog.times_list.item(i).text() for i in range(dialog.times_list.count())] == ['08:00', '18:30']
    with patch('ilias_sync.gui.install') as install:
        dialog.save()
    install.assert_called_once_with(6, times=['08:00', '18:30'])
    assert Settings().value['sync_times'] == ['08:00', '18:30']
    assert Settings().value['schedule_mode'] == 'times'
    dialog.close()


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


def test_source_context_menu_edits_the_clicked_row(app):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMenu
    from ilias_sync.gui import SourceList
    listing = SourceList()
    listing.addItems(['A', 'B'])
    listing.resize(240, 240)
    listing.show()
    app.processEvents()
    requested = []
    listing.editRequested.connect(lambda: requested.append(listing.currentRow()))

    def activate():
        menu = listing.findChild(QMenu)
        assert menu.actions()[0].text() == 'Bearbeiten'
        menu.actions()[0].trigger()
        menu.close()

    QTimer.singleShot(20, activate)
    listing.show_menu(listing.visualItemRect(listing.item(1)).center())
    assert requested == [1]
    listing.close()


@pytest.mark.parametrize('background', [False, True])
def test_progress_survives_directory_notifications_pause_and_resume(app, source, background):
    import json
    import os
    import psutil
    from PySide6.QtCore import QProcess
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Settings, data_dir, write_json
    settings = Settings()
    settings.save_source(source)
    row = {'token': 'progress-run', 'source': source.id, 'pid': os.getpid(),
           'created': psutil.Process().create_time(), 'state': 'running'}
    progress = 'Checking Algorithms (1/2) / Material'
    if background:
        row['message'] = progress
    write_json(data_dir() / 'active-run.json', row)
    window = MainWindow()
    if not background:
        window.process = QProcess(window)
        window.job = ('sync', source)
        window.event_path.write_text(json.dumps({'event': 'progress', 'message': progress}) + '\n', encoding='utf-8')
        window.read_output()
    expected = 'Kurs wird geprüft: Algorithms (1/2) · Material'
    try:
        assert window.status.text() == expected
        window.check_active_run()
        assert window.status.text() == expected
        write_json(data_dir() / 'active-run.json', {**row, 'state': 'paused'})
        window.check_active_run()
        assert window.status.text() == 'Pausiert'
        write_json(data_dir() / 'active-run.json', row)
        window.check_active_run()
        assert window.status.text() == expected
        write_json(data_dir() / 'active-run.json', {**row, 'token': 'next-run', 'message': ''})
        window.check_active_run()
        assert window.status.text() == 'ILIAS wird geprüft …'
    finally:
        if window.process:
            window.process.deleteLater()
            window.process = None
        write_json(data_dir() / 'active-run.json', {**row, 'state': 'finished'})
        window.check_active_run()
        window.close()
