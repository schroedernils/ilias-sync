from pathlib import Path
from unittest.mock import patch

import pytest

from ilias_sync.storage import Settings, data_dir, read_json, source_scope, write_json


@pytest.fixture
def window(source):
    from PySide6.QtWidgets import QApplication
    from ilias_sync.gui import MainWindow
    from ilias_sync.theme import Theme
    app = QApplication.instance() or QApplication([])
    app.theme = Theme(app, 'dark')
    Settings().save_source(source)
    root = data_dir() / 'sources' / source.id
    entries = {}
    for i in range(6):
        entries[str(i)] = {'path': f'Course/Lecture {i}.pdf', 'course_id': 'crs-1', 'course_name': 'Course',
                           'changed_at': 100 + i, 'change': 'added', 'target_stat': [1000]}
        file = Path(source.destination) / entries[str(i)]['path']
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(str(i).encode())
    write_json(root / 'manifest.json', {'files': entries})
    write_json(root / 'status.json', {'state': 'Up to date', 'finished': 105, 'started': 99,
        'scope': source_scope(source), 'result': {'counts': {'added': 6}}, 'last_success': 105})
    widget = MainWindow()
    widget.resize(820, 560)
    widget.show()
    app.processEvents()
    yield widget
    widget.process = None
    widget.run_info = None
    widget.close()


def test_overview_has_three_newest_files_and_all_materials_retains_full_library(window):
    from PySide6.QtCore import Qt
    assert window.workspace.currentIndex() == 0
    assert window.recent_files.rowCount() == 3
    assert [window.recent_files.item(i, 0).data(Qt.ItemDataRole.UserRole + 1)['changed_at'] for i in range(3)] == [105, 104, 103]
    assert 'Letzte Synchronisation:' in window.sync_panel.meta.text()
    assert 'vor ' in window.sync_panel.meta.text()
    window.all_files_button.click()
    assert window.workspace.currentIndex() == 1
    assert window.files.rowCount() == 6
    assert window.files.isVisible()
    assert window.sync_button.isVisible()
    window.workspace_tabs.setCurrentIndex(3)
    assert window.sync_panel.report_host.isVisible()
    assert window.sync_button.isVisible()


def test_recent_open_uses_identity_after_filters_change_order(window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    window.files.sortItems(0, Qt.SortOrder.AscendingOrder)
    window.file_search.setText('Lecture 0')
    window.recent_files.selectRow(0)
    with patch('ilias_sync.gui.QDesktopServices.openUrl', return_value=True) as opened:
        window.recent_files.setFocus()
        QTest.keyClick(window.recent_files, Qt.Key.Key_Return)
        assert Path(opened.call_args.args[0].toLocalFile()).read_bytes() == b'5'


def test_sync_actions_are_one_fixed_section_and_busy_start_never_pauses(window, source):
    assert window.sync_panel.isAncestorOf(window.sync_button)
    assert window.sync_panel.isAncestorOf(window.pause_button)
    assert window.sync_panel.isAncestorOf(window.stop_button)
    run = {'state': 'paused', 'source': source.id, 'token': 'fixture'}
    with patch('ilias_sync.gui.active_run', return_value=run), patch('ilias_sync.gui.send_command') as command:
        window.run_info = run
        window.refresh_controls()
        assert not window.sync_button.isEnabled()
        assert window.pause_button.isVisible() and window.stop_button.isVisible()
        assert window.pause_button.accessibleName() == 'Fortsetzen'
        assert window.stop_button.objectName() == 'stopControl'
        window.request_sync()
        command.assert_not_called()
        window.pause_button.click()
        command.assert_called_once_with(run, 'resume')


def test_dismissed_notice_remains_in_details_and_error_does_not_become_success(window, source):
    from ilias_sync.notifications import notices
    root = data_dir() / 'sources' / source.id
    failure = {'state': 'Needs attention', 'failure_kind': 'network', 'started': 110, 'finished': 120,
               'scope': source_scope(source), 'last_success': 105}
    write_json(root / 'status.json', failure)
    window.refresh()
    entry = notices(source.id)[0]
    before = (root / 'status.json').read_bytes()
    window.dismiss_notice(source.id, entry['id'], True)
    assert (root / 'status.json').read_bytes() == before
    assert '1 ausgeblendet' in window.overview_notes.text()
    assert window.sync_panel.tone == 'error'
    assert window.sync_button.isVisible() and window.sync_button.isEnabled()
    window.workspace_tabs.setCurrentIndex(3)
    from PySide6.QtWidgets import QPushButton
    assert any(item.text() == 'Wieder anzeigen' for item in window.sync_panel.report_host.findChildren(QPushButton))
    assert read_json(root / 'status.json', {}) == failure


def test_notification_permission_feedback_survives_a_library_refresh(window):
    window.workspace_tabs.setCurrentIndex(2)
    with patch('ilias_sync.notifications.permission', return_value=0):
        window.configure_notifications(True)
    feedback = window.notification_permission_note.text()
    assert 'macOS' in feedback
    window.refresh()
    assert window.notification_permission_note.text() == feedback


@pytest.mark.parametrize('authorization, expected', [(-1, 'nicht verfügbar'), (1, 'abgelehnt'), (0, 'erlaube')])
def test_notification_test_explains_native_permission_state(window, authorization, expected):
    with patch('ilias_sync.notifications.permission', return_value=authorization), patch('ilias_sync.notifications.native_notify') as notify:
        window.test_notification()
    assert expected in window.notification_permission_note.text()
    notify.assert_not_called()
