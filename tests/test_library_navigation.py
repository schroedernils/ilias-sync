"""Material-first flows across universities, including collisions and background work."""
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from ilias_sync.storage import Settings, Source, data_dir, read_json, source_scope, write_json


@pytest.fixture
def library_app():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase
    from ilias_sync.i18n import set_language
    from ilias_sync.theme import Theme
    app = QApplication.instance() or QApplication([])
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    set_language('de')
    app.theme = Theme(app, 'dark')
    return app


def university(source, *, name='Algorithms', root=None, error=False, files=3):
    Settings().save_source(source)
    state = data_dir() / 'sources' / source.id
    write_json(state / 'courses.json', [{'id': 'crs-1', 'name': name, 'url': source.url + '/go/crs/1'}])
    entries = {'file:' + str(index): {'path': f'{name}/Chapter {index}/Lecture.pdf', 'course_id': 'crs-1',
               'course_name': name, 'logical': f'crs-1/Chapter {index}/Lecture.pdf',
               'target_stat': [(index + 1) * 1024], **({'root': str(root)} if root else {})}
               for index in range(files)}
    for entry in entries.values():
        path = Path(entry.get('root', source.destination)) / entry['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source.id.encode())
    write_json(state / 'manifest.json', {'files': entries})
    status = {'state': 'Needs attention', 'message': 'Sync could not complete. Existing files were retained. Check your connection and try again.'} if error else {
        'state': 'Up to date', 'scope': source_scope(source), 'finished': 100,
        'result': {'counts': {'unchanged': files}, 'material_counts': {'unchanged': files}}}
    write_json(state / 'status.json', status)
    return state


def second_source(tmp_path):
    return Source('Second university', 'https://b.example.edu', str(tmp_path / 'B'), client_id='test')


def visible_entries(window):
    from PySide6.QtCore import Qt
    return [window.files.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
            for row in range(window.files.rowCount()) if not window.files.isRowHidden(row)]


def test_hierarchy_browses_global_university_and_course_without_changing_sync_selection(library_app, source, tmp_path):
    from ilias_sync.gui import MainWindow
    university(source)
    second = second_source(tmp_path)
    university(second)
    before = Settings().path.read_bytes()
    window = MainWindow()
    assert window.sources.scope() == ('', '')
    assert len(visible_entries(window)) == 6
    assert window.sources.select_scope(source.id)
    assert len(visible_entries(window)) == 3
    assert window.sources.select_scope(second.id, 'crs-1')
    assert window.source_title.full_text == 'Algorithms'
    assert window.source_host.full_text == second.name
    assert len(visible_entries(window)) == 3
    assert all(entry['_source_id'] == second.id for entry in visible_entries(window))
    assert Settings().path.read_bytes() == before
    window.close()


def test_global_duplicate_ids_open_correct_source_and_custom_root(library_app, source, tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ilias_sync.gui import MainWindow
    university(source)
    second = second_source(tmp_path)
    custom = tmp_path / 'Custom'
    university(second, root=custom)
    window = MainWindow()
    window.show()
    library_app.processEvents()
    for row in range(window.files.rowCount()):
        window.files.selectRow(row)
        entry = window.selected_entry()
        assert window.file_target().read_bytes() == entry['_source_id'].encode()
        with patch('ilias_sync.gui.QDesktopServices.openUrl', return_value=True) as opened:
            window.files.setFocus()
            QTest.keyClick(window.files, Qt.Key.Key_Return)
            target = Path(opened.call_args.args[0].toLocalFile())
            assert target.read_bytes() == entry['_source_id'].encode()
            if entry['_source_id'] == second.id:
                assert target.is_relative_to(custom)
    window.close()


def test_global_course_filter_namespaces_equal_course_ids_and_searches_university(library_app, source, tmp_path):
    from ilias_sync.gui import MainWindow
    university(source)
    second = second_source(tmp_path)
    university(second)
    window = MainWindow()
    window.show()
    window.filter_files()
    panel = window.filter_panel
    assert panel.course.count() == 3
    panel.course.setCurrentIndex(panel.course.findData(second.id + '/crs-1'))
    assert len(visible_entries(window)) == 3
    assert {entry['_source_id'] for entry in visible_entries(window)} == {second.id}
    window.clear_file_filters()
    window.file_search.setText(source.name)
    assert {entry['_source_id'] for entry in visible_entries(window)} == {source.id}
    window.sources.select_scope(second.id)
    assert not window.file_search.text() and not any(window.file_filters.values())
    window.close()


def test_global_error_stays_visible_and_has_one_inline_report_entry(library_app, source, tmp_path):
    from ilias_sync.gui import MainWindow, SyncReportDialog
    university(source)
    second = second_source(tmp_path)
    university(second, error=True)
    window = MainWindow()
    window.show()
    library_app.processEvents()
    assert window.sync_panel.mark.tone == 'error'
    assert window.sync_panel.detail.isVisible()
    assert second.name in window.sync_panel.detail.text()
    assert not window.sync_panel.report_host.isVisible()
    window.details_button.click()
    library_app.processEvents()
    assert window.sync_panel.report_host.isVisible()
    assert window.report_source.count() == 2
    window.report_source.setCurrentIndex(window.report_source.findData(second.id))
    assert window.report_widget.history[0]['state'] == 'Needs attention'
    assert not any(widget.isModal() for widget in window.findChildren(SyncReportDialog))
    window.details_button.click()
    assert not window.sync_panel.report_host.isVisible()
    assert window.sync_panel.detail.isVisible()
    window.close()


def test_background_sync_does_not_steal_navigation_or_block_local_files(library_app, source, tmp_path):
    from ilias_sync.gui import MainWindow
    university(source)
    second = second_source(tmp_path)
    university(second)
    window = MainWindow()
    window.sources.select_scope(second.id, 'crs-1')
    run = {'state': 'running', 'source': source.id, 'token': 'fixture'}
    with patch('ilias_sync.gui.active_run', return_value=run):
        window.check_active_run()
        assert window.sources.scope() == (second.id, 'crs-1')
        assert window.sources.isEnabled()
        window.files.selectRow(0)
        assert window.file_target().is_file()
        assert source.name in window.sync_panel.title.full_text
        window.sources.select_scope()
        assert len(visible_entries(window)) == 6
        with patch('ilias_sync.gui.send_command') as command:
            window.sync_or_pause()
            command.assert_called_once_with(run, 'pause')
    window.run_info = None
    window.close()


def test_global_sync_queues_only_enabled_universities_and_stop_discards_remainder(library_app, source, tmp_path):
    from ilias_sync.gui import MainWindow
    university(source)
    second = second_source(tmp_path)
    university(second)
    from uuid import uuid4
    disabled = replace(second, id=str(uuid4()), name='Disabled', destination=str(tmp_path / 'Disabled'), enabled=False)
    Settings().save_source(disabled)
    window = MainWindow()
    with patch.object(window, 'start') as start, patch('ilias_sync.gui.active_run', return_value=None):
        window.sync_or_pause()
        assert start.call_args.args == ('sync', source)
        assert [row.id for row in window.sync_queue] == [second.id]
        window.stop_sync()
        assert not window.sync_queue
    window.close()


def test_course_navigation_does_not_limit_the_actual_sync_request(library_app, source):
    from ilias_sync.gui import MainWindow
    university(source)
    window = MainWindow()
    window.sources.select_scope(source.id, 'crs-1')
    with patch.object(window, 'start') as start, patch('ilias_sync.gui.active_run', return_value=None):
        window.sync_or_pause()
        start.assert_called_once_with('sync')
    assert Settings().sources()[0].automatic_courses == source.automatic_courses
    window.close()


@pytest.mark.parametrize('size', [(820, 560), (980, 700), (1280, 800)])
def test_compact_geometry_density_keyboard_and_sidebar_toggle(library_app, source, size):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ilias_sync.gui import MainWindow
    university(source, files=40)
    window = MainWindow()
    window.resize(*size)
    window.show()
    library_app.processEvents()
    assert (window.width(), window.height()) == size
    assert window.files.viewport().height() // window.files.verticalHeader().defaultSectionSize() >= {560: 5, 700: 9, 800: 11}[size[1]]
    assert window.files.verticalHeader().defaultSectionSize() <= 48
    assert not window.sync_panel.meta.isVisible()
    assert not window.sync_panel.detail.isVisible()
    for widget in (window.file_search, window.files, window.sync_panel, window.sync_button, window.management_button):
        origin = widget.mapTo(window, widget.rect().topLeft())
        assert 0 <= origin.x() and origin.x() + widget.width() <= size[0]
        assert 0 <= origin.y() and origin.y() + widget.height() <= size[1]
    window.files.setFocus()
    QTest.keyClick(window.files, Qt.Key.Key_Tab)
    assert library_app.focusWidget() is not window.files
    window.toggle_sidebar()
    assert not window.sidebar.isVisible()
    assert window.sidebar_button.accessibleName() == 'Seitenleiste einblenden'
    window.toggle_sidebar()
    assert window.sidebar.isVisible()
    window.close()


def test_library_refresh_retains_selected_duplicate_and_navigated_course(library_app, source, tmp_path):
    from ilias_sync.gui import MainWindow
    university(source)
    second = second_source(tmp_path)
    state = university(second)
    window = MainWindow()
    row = next(index for index, entry in enumerate(visible_entries(window)) if entry['_source_id'] == second.id)
    window.files.selectRow(row)
    selected = window.selected_entry()
    window.refresh()
    assert window.selected_entry()['_source_id'] == second.id
    assert window.selected_entry()['_identity'] == selected['_identity']
    window.sources.select_scope(second.id, 'crs-1')
    manifest = read_json(state / 'manifest.json', {})
    manifest['files']['file:5'] = {'path': 'Algorithms/New.pdf', 'course_id': 'crs-1'}
    write_json(state / 'manifest.json', manifest)
    window.refresh()
    assert window.sources.scope() == (second.id, 'crs-1')
    assert len(visible_entries(window)) == 4
    window.close()
    restored = MainWindow()
    assert restored.sources.scope() == (second.id, 'crs-1')
    restored.close()


def test_stale_configuration_never_hides_a_critical_error_and_files_have_distinct_types(library_app, source):
    from ilias_sync.library import load_library, source_summary
    from ilias_sync.library_widgets import file_family, material_context
    university(source, error=True)
    changed = replace(source, destination=source.destination + '-changed')
    state = data_dir() / 'sources' / source.id / 'status.json'
    status = read_json(state, {})
    status['scope'] = source_scope(source)
    write_json(state, status)
    assert source_summary(load_library([changed])[source.id]).tone == 'error'
    assert len({file_family('a' + suffix) for suffix in ('.pdf', '.zip', '.png', '.mp4', '.java', '.xlsx', '.docx')}) == 7
    assert material_context({'path': 'Algorithms/Folder/a.pdf', 'logical': 'crs-1/Folder/a.pdf'}, 'course') == 'Folder'
