from pathlib import Path
import time
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
    assert 'Letzte Synchronisation:' in window.sync_panel.meta.accessibleName()
    assert 'vor ' in window.sync_panel.meta.accessibleName()
    window.all_files_button.click()
    assert window.workspace.currentIndex() == 1
    assert window.files.rowCount() == 6
    assert window.files.isVisible()
    assert window.sync_button.isVisible()
    window.workspace_tabs.setCurrentIndex(2)
    assert window.sync_panel.report_host.isVisible()
    assert window.sync_button.isVisible()


def test_recent_open_uses_identity_after_filters_change_order(window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    window.files.sortItems(0, Qt.SortOrder.AscendingOrder)
    window.file_search.setText('Lecture 0')
    window.recent_files.selectRow(0)
    with patch('ilias_sync.gui.launch_local', return_value=True) as opened:
        window.recent_files.setFocus()
        QTest.keyClick(window.recent_files, Qt.Key.Key_Return)
        assert Path(opened.call_args.args[0]).read_bytes() == b'5'


@pytest.mark.parametrize('view', ['overview', 'materials'])
@pytest.mark.parametrize('platform', ['darwin', 'linux'])
def test_file_context_menu_reveals_the_clicked_entry_even_if_selection_changes(window, view, platform):
    from types import SimpleNamespace
    from ilias_sync import gui
    from ilias_sync.i18n import t

    table = window.recent_files if view == 'overview' else window.files
    if view == 'materials':
        window.workspace_tabs.setCurrentIndex(1)
    # Right-click the date/size cell, whose metadata lives in column zero.
    expected_entry = table.item(0, 0).data(gui.Qt.ItemDataRole.UserRole + 1)
    target = window.file_target(expected_entry)
    point = table.visualItemRect(table.item(0, 1)).center()

    def choose(menu, *_):
        table.selectRow(1)
        window.files.selectRow(window.files.rowCount() - 1)
        label = t('Show in Finder' if platform == 'darwin' else 'Open containing folder')
        next(action for action in menu.actions() if action.text() == label).trigger()

    with patch.object(gui, 'sys', SimpleNamespace(platform=platform)), \
            patch.object(gui.MotionMenu, 'exec', choose), \
            patch.object(gui.subprocess, 'run') as reveal, \
            patch.object(gui.QDesktopServices, 'openUrl') as folder:
        (window.recent_menu if view == 'overview' else window.file_menu)(point)
        if platform == 'darwin':
            reveal.assert_called_once_with(['/usr/bin/open', '-R', str(target)], check=False)
            folder.assert_not_called()
        else:
            folder.assert_called_once()
            assert folder.call_args.args[0].toLocalFile() == str(target.parent)
            reveal.assert_not_called()
    assert window.workspace.currentIndex() == (0 if view == 'overview' else 1)


def test_sync_actions_are_one_fixed_section_and_busy_start_never_pauses(window, source):
    from PySide6.QtCore import QPoint
    assert window.sync_panel.isAncestorOf(window.sync_button)
    assert window.sync_panel.isAncestorOf(window.pause_button)
    assert window.sync_panel.isAncestorOf(window.stop_button)
    origin = QPoint(0, 0)
    title = window.sync_panel.title.mapTo(window, origin)
    meta = window.sync_panel.meta.mapTo(window, origin)
    cluster = window.sync_cluster.geometry()
    pause = window.sync_cluster.pause.geometry()
    stop = window.sync_cluster.stop.geometry()
    run = {'state': 'paused', 'source': source.id, 'token': 'fixture'}
    with patch('ilias_sync.gui.active_run', return_value=run), patch('ilias_sync.gui.send_command') as command:
        window.run_info = run
        window.refresh_controls()
        assert window.sync_panel.title.mapTo(window, origin) == title
        assert window.sync_panel.meta.mapTo(window, origin) == meta
        assert window.sync_cluster.geometry() == cluster
        assert window.pause_button.geometry() == pause
        assert window.stop_button.geometry() == stop
        motion = window.sync_cluster._motion
        if motion is not None:
            motion.setCurrentTime(motion.duration())
        assert window.sync_panel.title.mapTo(window, origin) == title
        assert window.sync_panel.meta.mapTo(window, origin) == meta
        assert window.pause_button.geometry() == pause
        assert window.stop_button.geometry() == stop
        assert not window.sync_button.isEnabled()
        assert window.pause_button.isVisible() and window.stop_button.isVisible()
        assert window.pause_button.accessibleName() == 'Fortsetzen'
        assert window.stop_button.objectName() == 'stopControl'
        window.request_sync()
        command.assert_not_called()
        window.pause_button.click()
        command.assert_called_once_with(run, 'resume')


def test_sync_card_pairs_the_last_run_and_schedule_with_the_action(window, source, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication
    from ilias_sync.presentation import brief_stamp

    now = time.time()
    monkeypatch.setattr(time, 'time', lambda: now)
    root = data_dir() / 'sources' / source.id
    status = read_json(root / 'status.json', {})
    status.update(finished=now - 43 * 60, last_success=now - 43 * 60, next_run=now + 60 * 60)
    write_json(root / 'status.json', status)
    window.settings.value['scheduled'] = True
    window.refresh()
    QApplication.processEvents()

    panel = window.sync_panel
    assert 'vor 43 Min.' in panel.meta.text()
    assert brief_stamp(status['finished'], now=now)[0] in panel.meta.text()
    assert panel.schedule.text().startswith('Nächste Prüfung:')
    assert panel.progress.isHidden() and panel.detail.isHidden()
    assert panel.meta.y() - panel.title.geometry().bottom() < 10
    assert panel.schedule.y() - panel.meta.geometry().bottom() < 10
    assert panel.mapTo(window, QPoint()).x() == window.recent_files.parentWidget().mapTo(window, QPoint()).x()
    assert panel.rect().contains(window.sync_cluster.geometry())


@pytest.mark.parametrize('width', [820, 980, 1200])
@pytest.mark.parametrize('language', ['de', 'en'])
def test_signin_has_one_primary_action_and_no_overlapping_content(window, source, width, language):
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QApplication
    from ilias_sync.i18n import set_language

    set_language(language)
    write_json(data_dir() / 'sources' / source.id / 'status.json', {
        'state': 'Sign in again', 'login_required': True, 'finished': time.time(), 'scope': source_scope(source),
    })
    window.resize(width, 650)
    window.refresh()
    QApplication.processEvents()
    panel = window.sync_panel

    assert panel.detail.isVisible() and window.recovery_button.isVisible()
    assert not window.sync_button.isVisible()
    assert window.recovery_button.isEnabled()
    widgets = (panel.title, panel.detail, panel.meta, panel.schedule, window.recovery_button)
    rects = [QRect(widget.mapTo(panel, QPoint()), widget.size()) for widget in widgets]
    for i, rect in enumerate(rects):
        assert panel.rect().contains(rect)
        assert not any(rect.intersects(other) for other in rects[i + 1:])
    assert rects[1].top() >= rects[-1].bottom() + 8
    assert rects[1].left() == rects[0].left()
    assert rects[2].top() >= rects[1].bottom() + 6
    assert panel.detail.width() >= panel.title.width()
    assert panel.detail.height() >= panel.detail.heightForWidth(panel.detail.width())
    with patch.object(window, 'edit') as edit:
        window.recovery_button.click()
        assert edit.call_args.kwargs['signin'] is True
    status = read_json(data_dir() / 'sources' / source.id / 'status.json', {})
    status.update(state='Up to date', login_required=False, result={'counts': {'unchanged': 6}})
    write_json(data_dir() / 'sources' / source.id / 'status.json', status)
    window.refresh()
    QApplication.processEvents()
    assert window.sync_button.isVisible() and window.sync_button.isEnabled()
    assert not window.recovery_button.isVisible()


@pytest.mark.parametrize('width', [820, 980, 1200])
@pytest.mark.parametrize('language', ['de', 'en'])
def test_running_text_is_balanced_above_progress_and_clear_of_actions(window, source, width, language):
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QApplication, QBoxLayout
    from ilias_sync.i18n import set_language, t

    set_language(language)
    window.resize(width, 650)
    window.run_info = {'state': 'running', 'source': source.id, 'token': 'fixture'}
    window.refresh_controls()
    window.show_progress(t('Checking ILIAS…'))
    motion = window.sync_cluster._motion
    if motion:
        motion.setCurrentTime(motion.duration())
    QApplication.processEvents()
    panel = window.sync_panel

    def rect(widget):
        return QRect(widget.mapTo(panel, QPoint()), widget.size())

    labels = (panel.title, panel.detail, panel.meta, panel.schedule)
    for widget in (*labels, window.pause_button, window.stop_button, panel.progress):
        assert panel.rect().contains(rect(widget))
    for label in labels:
        assert not rect(label).intersects(rect(window.pause_button))
        assert not rect(label).intersects(rect(window.stop_button))
        assert label.height() >= label.heightForWidth(label.width())
    reference = rect(panel.title).bottom()
    if panel._card_row.direction() == QBoxLayout.Direction.TopToBottom:
        reference = max(reference, rect(window.stop_button).bottom())
    top_gap = rect(panel.detail).top() - reference - 1
    bottom_gap = rect(panel.progress).top() - rect(panel.schedule).bottom() - 1
    assert top_gap >= 12 and abs(top_gap - bottom_gap) <= 4, (top_gap, bottom_gap)


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
    window.workspace_tabs.setCurrentIndex(2)
    from PySide6.QtWidgets import QPushButton
    assert any(item.text() == 'Wieder anzeigen' for item in window.sync_panel.report_host.findChildren(QPushButton))
    assert read_json(root / 'status.json', {}) == failure


def test_notification_permission_feedback_survives_a_library_refresh(window):
    with patch('ilias_sync.notifications.permission', return_value=0):
        window.configure_notifications(True)
    feedback = window.notification_feedback
    assert 'macOS' in feedback
    window.refresh()
    assert window.notification_feedback == feedback


@pytest.mark.parametrize('authorization, expected', [(-1, 'nicht verfügbar'), (1, 'abgelehnt'), (0, 'Erlaube')])
def test_notification_opt_in_explains_when_macos_does_not_allow_it(window, authorization, expected):
    with patch('ilias_sync.notifications.permission', return_value=authorization):
        window.configure_notifications(True)
    assert expected in window.notification_feedback
    from ilias_sync.notifications import preferences
    assert preferences()['enabled'] is False
