from pathlib import Path
from unittest.mock import patch

import pytest

from ilias_sync.i18n import set_language
from ilias_sync.presentation import file_size, report_html, sync_summary
from ilias_sync.storage import Archive, Settings, data_dir, write_json


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    set_language('de')
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('status,tone,recovery', [
    ({}, 'neutral', ''),
    ({'state': 'Stopped'}, 'neutral', ''),
    ({'state': 'Checking courses', 'result': {'counts': {'unchanged': 7}}}, 'warning', 'retry'),
    ({'state': 'Sign in again', 'login_required': True}, 'error', 'signin'),
    ({'state': 'Needs attention', 'message': 'OSError: sync could not complete.'}, 'error', 'retry'),
    ({'state': 'Up to date', 'result': {'counts': {'unchanged': 7}, 'skipped': {'forum': 12}}}, 'success', ''),
    ({'state': 'Up to date', 'result': {'unavailable': 2}}, 'warning', 'report'),
    ({'state': 'Completed with warnings', 'result': {'counts': {'conflict': 1}}}, 'warning', 'report'),
    ({'state': 'Completed with warnings', 'result': {'errors': 1}}, 'error', 'retry'),
])
def test_status_distinguishes_success_exclusions_partial_errors_and_login(status, tone, recovery):
    summary = sync_summary(status, 7)
    assert summary.tone == tone
    assert summary.recovery == recovery
    assert summary.title and summary.detail
    assert 'OSError:' not in summary.detail


def test_generated_course_information_is_not_presented_as_new_materials():
    set_language('de')
    summary = sync_summary({'result': {'counts': {'added': 10}, 'material_counts': {'unchanged': 5}}}, 5)
    assert 'Keine neuen' in summary.detail
    html = report_html({'result': {'unavailable': 1, 'unavailable_items': ['<script>evil</script>.pdf'],
                                    'skipped': {'forum': 2, 'test': 1}}})
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'Foren: 2' in html and 'Tests: 1' in html
    assert 'nicht um fehlgeschlagene' in html


def test_archive_records_real_changes_without_resetting_history_on_noop(tmp_path, monkeypatch):
    raw = tmp_path / 'raw.pdf'
    raw.write_bytes(b'%PDF-1.4 one')
    archive = Archive(tmp_path / 'state', tmp_path / 'out')
    monkeypatch.setattr('ilias_sync.storage.time.time', lambda: 100)
    archive.publish('file:1', raw, 'Course/File.pdf')
    assert archive.manifest['files']['file:1']['changed_at'] == 100
    assert archive.manifest['files']['file:1']['change'] == 'added'
    monkeypatch.setattr('ilias_sync.storage.time.time', lambda: 200)
    archive.publish('file:1', raw, 'Course/File.pdf')
    assert archive.manifest['files']['file:1']['changed_at'] == 100
    raw.write_bytes(b'%PDF-1.4 new content')
    archive.publish('file:1', raw, 'Course/File.pdf')
    assert archive.manifest['files']['file:1']['changed_at'] == 200
    assert archive.manifest['files']['file:1']['change'] == 'updated'
    # Existing schema-1 files acquire no fictional recency on their next sync.
    archive.manifest['files']['file:1'].pop('changed_at')
    archive.manifest['files']['file:1'].pop('change')
    archive.publish('file:1', raw, 'Course/File.pdf')
    assert 'changed_at' not in archive.manifest['files']['file:1']


def prepare_library(source):
    settings = Settings()
    settings.save_source(source)
    entries = {
        'file:1': {'path': 'Algorithms/Week 1/A.pdf', 'course_id': 'crs-1', 'course_name': 'Theoretical Computer Science', 'target_stat': [1024]},
        'file:2': {'path': 'Math/B.pdf', 'course_id': 'crs-2', 'target_stat': [2048], 'changed_at': 200, 'change': 'updated'},
        'file:3': {'path': 'Math/C.pdf', 'course_id': 'crs-2', 'target_stat': [4096], 'changed_at': 300, 'change': 'added'},
        'generated:crs-1/Description.html': {'path': 'Course info/Algorithms/Description.html', 'course_id': 'crs-1', 'target_stat': [120]},
    }
    state = data_dir() / 'sources' / source.id
    write_json(state / 'manifest.json', {'files': entries})
    for entry in entries.values():
        target = Path(source.destination) / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'test material')
    return entries


def test_material_views_search_recency_and_open_selected_file(app, source):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ilias_sync.gui import MainWindow
    prepare_library(source)
    window = MainWindow()
    window.show()
    app.processEvents()
    assert window.apply_file_filters() == 3
    window.library_view.setCurrentIndex(window.library_view.findData('recent'))
    assert window.apply_file_filters() == 2
    assert window.files.item(0, 0).text() == 'Math/C.pdf'
    window.library_view.setCurrentIndex(window.library_view.findData('info'))
    assert window.apply_file_filters() == 1
    window.library_view.setCurrentIndex(window.library_view.findData('materials'))
    window.file_search.setText('Theoretical Computer Science')
    assert window.apply_file_filters() == 1
    window.file_search.setText('A.pdf')
    assert window.apply_file_filters() == 1
    row = next(row for row in range(window.files.rowCount()) if not window.files.isRowHidden(row))
    window.files.selectRow(row)
    with patch('ilias_sync.gui.QDesktopServices.openUrl', return_value=True) as opened:
        window.files.setFocus()
        QTest.keyClick(window.files, Qt.Key.Key_Return)
        opened.assert_called_once()
        assert opened.call_args.args[0].toLocalFile() == str(Path(source.destination) / 'Algorithms/Week 1/A.pdf')
    target = Path(source.destination) / 'Algorithms/Week 1/A.pdf'
    target.unlink()
    window.open_file()
    assert 'fehlt lokal' in window.status.text()
    assert window.sync_panel.mark.tone == 'error'
    window.file_search.setText('no-such-file')
    assert window.files.empty.isVisible()
    assert 'Keine passenden' in window.files.empty_title.text()
    assert not window.file_open_button.isEnabled()
    window.clear_file_filters()
    assert window.apply_file_filters() == 3
    window.close()


def test_filter_selection_resets_when_switching_sources(app, source, tmp_path):
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Source
    prepare_library(source)
    settings = Settings()
    second = Source('Second', 'https://second.example.edu', str(tmp_path / 'Second'), client_id='test')
    settings.save_source(second)
    window = MainWindow()
    window.file_search.setText('Algorithms')
    window.sources.setCurrentRow(1)
    assert window.file_search.text() == ''
    assert not any(window.file_filters.values())
    window.close()


def test_login_and_retry_have_specific_actions_and_keep_library_available(app, source):
    from ilias_sync.gui import MainWindow
    prepare_library(source)
    status_path = data_dir() / 'sources' / source.id / 'status.json'
    write_json(status_path, {'state': 'Sign in again', 'login_required': True})
    window = MainWindow()
    window.show()
    assert window.recovery_button.isVisible()
    with patch.object(window, 'edit') as edit:
        window.recovery_button.click()
        edit.assert_called_once_with(signin=True)
    assert window.apply_file_filters() == 3
    write_json(status_path, {'state': 'Needs attention'})
    window.refresh()
    assert window.sync_button.text() == 'Erneut versuchen'
    window.refresh_controls()
    assert window.sync_button.text() == 'Erneut versuchen'
    with patch.object(window, 'start') as start:
        window.sync_button.click()
        start.assert_called_once_with('sync')
    window.close()


def test_file_sizes_do_not_show_small_links_as_zero_kilobytes():
    assert file_size(120) == '120 B'
    assert file_size(1024) == '1 KB'
    assert file_size(2 * 1024 ** 2) == '2.0 MB'


def test_status_and_report_expose_actual_content_to_accessibility(app):
    from ilias_sync.gui import SyncReportDialog
    from ilias_sync.library_widgets import SyncPanel
    panel = SyncPanel()
    panel.set_state('Prüfung läuft', 'Lade Skript.pdf herunter', 'running', busy=True)
    assert panel.detail.accessibleName() == 'Lade Skript.pdf herunter'
    assert panel.progress.maximum() == 0
    panel.set_state('Pausiert', 'Die Dateien bleiben verfügbar.', 'neutral')
    assert panel.progress.isHidden()
    report = SyncReportDialog({'result': {'unavailable': 1, 'unavailable_items': ['Vorlesung/Skript.pdf']}}, '')
    assert 'Vorlesung/Skript.pdf' in report.summary.accessibleDescription()
    report.close()


def test_local_dates_remain_correct_across_midnight_language_and_timezone(monkeypatch):
    import time
    from ilias_sync.presentation import local_time
    if not hasattr(time, 'tzset'):
        pytest.skip('POSIX timezone switch')
    previous = __import__('os').environ.get('TZ')
    try:
        monkeypatch.setenv('TZ', 'Europe/Berlin')
        time.tzset()
        stamp = 1793136600  # 2026-10-27 21:30 UTC
        set_language('en')
        assert local_time(stamp, now=stamp) == 'Today at 22:30'
        assert local_time(stamp, now=stamp+7200) == '27.10.2026, 22:30'
        set_language('de')
        assert local_time(stamp, now=stamp) == 'Heute, 22:30'
        monkeypatch.setenv('TZ', 'UTC')
        time.tzset()
        assert local_time(stamp, now=stamp) == 'Heute, 21:30'
    finally:
        if previous is None:
            monkeypatch.delenv('TZ', raising=False)
        else:
            monkeypatch.setenv('TZ', previous)
        time.tzset()
