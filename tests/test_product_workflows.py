"""Product-level regressions: settings, routing consequences, setup, keyboard and truthful outcomes."""
from pathlib import Path
from unittest.mock import Mock, patch
import time

import pytest

from ilias_sync.storage import Settings, data_dir, read_json, write_json, record_attempt
from ilias_sync.i18n import set_language


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    set_language('de')
    return QApplication.instance() or QApplication([])








def mapping_fixture(source):
    state = data_dir() / 'sources' / source.id
    courses = [{'id':'crs-1','name':'Algorithms','url':source.url+'/go/crs/1'}]
    write_json(state/'courses.json', courses)
    write_json(state/'manifest.json', {'files': {'file:1': {'path':'Algorithms/Week 1/Lecture.pdf',
        'logical':'crs-1/Week 1/Lecture.pdf','course_id':'crs-1'}}})
    return courses


def test_folder_preview_inherits_actual_parent_and_resets_only_selected_override(app, source, tmp_path):
    from ilias_sync.gui import FolderMappingDialog
    courses = mapping_fixture(source)
    source.folder_rules = {'course/crs-1': str(tmp_path/'Custom')}
    settings = Settings()
    settings.save_source(source)
    dialog = FolderMappingDialog(source, settings)
    course = dialog.tree.topLevelItem(0)
    child = course.child(0)
    dialog.tree.setCurrentItem(child)
    assert dialog.target.text() == str(tmp_path/'Custom/Week 1')
    assert not dialog.reset_button.isEnabled()
    dialog.rules['path/crs-1/Week 1'] = str(tmp_path/'Nested')
    dialog.selected(child)
    assert dialog.target.text() == str(tmp_path/'Nested')
    assert dialog.reset_button.isEnabled()
    dialog.reset_rule()
    assert dialog.rules == {'course/crs-1': str(tmp_path/'Custom')}
    assert dialog.target.text() == str(tmp_path/'Custom/Week 1')
    from ilias_sync.routing import mapping_preview
    file_path, _ = mapping_preview(source, courses, 'file/file:1', dialog.entries)
    assert file_path == tmp_path/'Custom/Week 1/Lecture.pdf'
    # Custom root names mean a new destination; the UI must state that and undo it.
    dialog.tree.setCurrentItem(course)
    dialog.rename_selected('Renamed')
    assert 'neue Kopie' in dialog.mapping_effect.text()
    assert dialog.reset_name_button.isEnabled()
    dialog.reset_name()
    assert dialog.rules['course/crs-1'] == str(tmp_path/'Custom')
    # Cancel never changes the saved settings or moves anything.
    dialog.reject()
    assert settings.sources()[0].folder_rules == source.folder_rules
    assert not (tmp_path/'Renamed').exists()


def test_mapping_search_retains_descendants_and_context(app, source):
    from ilias_sync.gui import FolderMappingDialog
    mapping_fixture(source)
    dialog = FolderMappingDialog(source, Settings())
    dialog.search.setText('Algorithms')
    parent = dialog.tree.topLevelItem(0)
    assert not parent.isHidden() and not parent.child(0).isHidden() and not parent.child(0).child(0).isHidden()
    dialog.search.setText('Lecture')
    assert not parent.isHidden() and not parent.child(0).isHidden()
    dialog.close()


def test_schedule_draft_edit_remove_cancel_and_atomic_rollback(app):
    from ilias_sync.gui import SettingsDialog
    from PySide6.QtCore import QTime
    settings = Settings()
    previous = dict(settings.value)
    dialog = SettingsDialog(settings)
    dialog.enabled.setChecked(True)
    dialog.schedule_mode.setCurrentIndex(1)
    for value in ('08:00', '18:30'):
        dialog.week_plan.add_time(0, value)
    first = dialog.week_plan.rows[0]['slots'][0]
    first['edit'].setTime(QTime(9, 0))
    assert dialog.week_plan.values()['0'] == ['09:00', '18:30']
    dialog.week_plan.remove_time(0, first)
    assert dialog.week_plan.values()['0'] == ['18:30']
    dialog.tabs.setCurrentIndex(0)
    dialog.tabs.setCurrentIndex(1)
    assert dialog.week_plan.values()['0'] == ['18:30']
    dialog.reject()
    assert settings.value == previous
    assert not settings.path.exists()
    from ilias_sync.settings_service import apply_settings
    settings.save()
    install = Mock(side_effect=OSError('native failure'))
    uninstall = Mock()
    with pytest.raises(OSError):
        apply_settings(settings, {**settings.value, 'scheduled':True}, install=install, uninstall=uninstall)
    assert settings.value == previous and read_json(settings.path,{}) == previous
    uninstall.assert_called_once()


def test_attempt_history_preserves_last_success_and_does_not_reuse_old_result(tmp_path):
    success = {'state':'Up to date','finished':100,'result':{'files':1,'counts':{'added':1}}}
    record_attempt(tmp_path, success, {})
    failure = {'state':'Needs attention','finished':200,'message':'network failure'}
    record_attempt(tmp_path, failure, success)
    assert read_json(tmp_path/'status.json',{})['last_success'] == 100
    assert 'result' not in read_json(tmp_path/'status.json',{})
    assert len(read_json(tmp_path/'history.json',[])) == 2
    stopped = {'state':'Stopped','finished':300}
    record_attempt(tmp_path, stopped, failure)
    assert stopped['last_success'] == 100
    for i in range(30):
        record_attempt(tmp_path, {'state':'Stopped','finished':400+i}, stopped)
    assert len(read_json(tmp_path/'history.json',[])) == 20


def test_truthful_freshness_scheduling_and_report_history(app):
    from ilias_sync.presentation import sync_summary, schedule_expectation
    from ilias_sync.gui import SyncReportDialog
    old = {'state':'Up to date','finished':100,'result':{'material_counts':{'unchanged':53},'counts':{'unchanged':66}}}
    summary = sync_summary(old, 53)
    assert 'abgeschlossen' in summary.title and 'erfasst' in summary.detail
    assert 'lokal verfügbar' not in summary.detail
    assert 'ausgeschaltet' in schedule_expectation({'scheduled':False}, old)
    report = SyncReportDialog({'state':'Needs attention','finished':200}, '', history=[{'state':'Needs attention','finished':200},old])
    report.attempts.setCurrentIndex(1)
    assert '53' in report.summary.text() and '13' in report.summary.text()
    report.attempts.setCurrentIndex(0)
    assert 'neu' not in report.summary.text()
    report.close()


def test_inline_filters_share_one_search_and_count_current_view(app, source):
    from ilias_sync.gui import MainWindow
    from test_presentation import prepare_library
    prepare_library(source)
    window = MainWindow()
    window.show()
    window.filter_files()
    assert window.filter_panel.search is window.file_search
    panel = window.filter_panel
    panel.kind.setCurrentIndex(panel.kind.findData('.pdf'))
    assert panel.count.text() == window.file_count.text()
    assert '3 von 3' in panel.count.text()
    window.clear_file_filters()
    assert panel.kind.currentIndex() == 0
    panel.size.setCurrentIndex(panel.size.findData('small'))
    assert not window.file_filters['kind']
    window.close()


def test_readonly_table_allows_tab_escape_and_restart_restores_view(app, source):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ilias_sync.gui import MainWindow
    from test_presentation import prepare_library
    prepare_library(source)
    window = MainWindow()
    window.show()
    app.processEvents()
    window.files.setFocus()
    QTest.keyClick(window.files, Qt.Key.Key_Tab)
    assert app.focusWidget() is not window.files
    QTest.keyClick(app.focusWidget(), Qt.Key.Key_Backtab)
    window.library_view.setCurrentIndex(window.library_view.findData('recent'))
    window.close()
    replacement = MainWindow()
    assert replacement.library_view.currentData() == 'recent'
    assert not replacement.progress_timer.isActive()
    replacement.close()


def test_dst_preview_never_invents_another_wall_clock_time(monkeypatch):
    import os
    from datetime import datetime
    from ilias_sync.policy import next_scheduled_run
    if not hasattr(time, 'tzset'):
        pytest.skip('POSIX timezone test')
    previous = os.environ.get('TZ')
    try:
        monkeypatch.setenv('TZ', 'Europe/Berlin')
        time.tzset()
        now = datetime(2026,3,29,0,0).timestamp()
        value = datetime.fromtimestamp(next_scheduled_run({'schedule_mode':'times','sync_times':['02:30'],'interval_hours':6}, clock=now))
        assert (value.day,value.hour,value.minute) == (30,2,30)
    finally:
        if previous is None:
            os.environ.pop('TZ',None)
        else:
            os.environ['TZ']=previous
        time.tzset()






def test_alias_collision_is_rejected_before_save_and_recovery_targets_folders(app, source):
    from ilias_sync.gui import FolderMappingDialog, MainWindow
    mapping_fixture(source)
    base=Path(source.destination)/'Algorithms'
    (base/'Week 1').mkdir(parents=True)
    (base/'Week 1/Lecture.pdf').write_bytes(b'original')
    (base/'Existing').mkdir()
    (base/'Existing/notes.txt').write_text('keep')
    settings=Settings()
    settings.save_source(source)
    dialog=FolderMappingDialog(source,settings)
    dialog.tree.setCurrentItem(dialog.tree.topLevelItem(0).child(0))
    dialog.rename_selected('Existing')
    dialog.save()
    assert 'existiert bereits' in dialog.error.text()
    assert settings.sources()[0].folder_names == {}
    assert (base/'Existing/notes.txt').read_text() == 'keep'
    dialog.reject()
    write_json(data_dir()/'sources'/source.id/'status.json', {'state':'Needs attention','recovery':'folders',
            'message':'A folder with this name already exists. Choose another name.'})
    window=MainWindow()
    with patch.object(window,'folder_mapping') as mapping:
        window.recovery_button.click()
        mapping.assert_called_once_with(verify=True)
    window.close()


@pytest.mark.parametrize('outcome', ['Stopped', 'Needs attention'])
def test_changed_source_does_not_inherit_success_for_previous_scope(app, source, outcome):
    from ilias_sync.storage import source_scope
    from ilias_sync.gui import MainWindow
    settings=Settings()
    settings.save_source(source)
    state=data_dir()/'sources'/source.id
    previous={'state':'Up to date','finished':100,'scope':source_scope(source),'result':{'counts':{'unchanged':1}}}
    record_attempt(state,previous,{})
    source.targets=['https://campus.example.edu/go/crs/2']
    source.automatic_courses=False
    settings.save_source(source)
    window=MainWindow()
    assert 'Einstellungen seit' in window.sync_panel.title.text()
    window.close()
    record_attempt(state,{'state':outcome,'finished':200,'scope':source_scope(source)},previous)
    assert read_json(state/'status.json',{})['last_success'] is None
    restarted = MainWindow()
    assert 'Letzte vollständige' not in restarted.sync_panel.meta.text()
    assert 'result' not in read_json(state/'status.json',{})
    restarted.close()


async def test_failed_course_discovery_preserves_previous_sync_outcome(source,monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from ilias_sync.__main__ import worker
    settings=Settings()
    settings.save_source(source)
    state=data_dir()/'sources'/source.id
    previous={'state':'Up to date','finished':100,'result':{'counts':{'unchanged':1}}}
    write_json(state/'status.json',previous)
    monkeypatch.setattr('ilias_sync.engine.synchronize',AsyncMock(side_effect=OSError('fixture offline')))
    args=SimpleNamespace(probe=None,profile=source.id,sync=False,discover=True)
    assert await worker(args)==1
    assert read_json(state/'status.json',{})==previous
    assert not (state/'history.json').exists()


def test_required_input_contours_have_nontext_contrast():
    from ilias_sync.theme import LIGHT,DARK
    def luminance(color):
        channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        channels=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in channels]
        return sum(c*w for c,w in zip(channels,(0.2126,0.7152,0.0722)))
    for palette in (LIGHT,DARK):
        for background in ('window','surface'):
            values=sorted([luminance(palette['input_border']),luminance(palette[background])])
            assert (values[1]+0.05)/(values[0]+0.05)>=3


def test_help_topics_are_read_only_and_have_no_save_action(app):
    from ilias_sync.gui import HelpDialog
    from PySide6.QtWidgets import QDialogButtonBox
    help=HelpDialog()
    assert help.topics.count()>=7
    for row in range(help.topics.count()):
        help.topics.setCurrentRow(row)
        assert help.info.toPlainText()
    assert help.findChild(QDialogButtonBox) is None
    help.close()


def test_cosmetic_source_rename_and_legacy_scope_are_truthful(app,source):
    from ilias_sync.storage import source_scope
    from ilias_sync.gui import MainWindow
    before=source_scope(source)
    source.name='Cosmetic rename'
    assert source_scope(source)==before
    settings=Settings()
    settings.save_source(source)
    write_json(data_dir()/'sources'/source.id/'status.json', {'state':'Up to date','result':{'counts':{'unchanged':1}}})
    window=MainWindow()
    assert window.sync_panel.mark.tone=='neutral'
    assert 'Neue Prüfung' in window.sync_panel.title.text()
    window.close()


def test_schedule_recovery_still_restores_native_job_when_config_recovery_fails():
    from ilias_sync.settings_service import apply_settings, ScheduleRestoreError
    settings = Settings()
    settings.save()
    native = Mock(side_effect=OSError('injected native failure'))
    uninstall = Mock()
    with patch('ilias_sync.storage.atomic_write', side_effect=OSError('injected recovery failure')):
        # The candidate save succeeds; only the recovery's raw write fails.
        with patch.object(settings, 'save'):
            settings.path.write_text('{}')
            original = settings.path.read_bytes()
            def install(*args, **kwargs):
                settings.path.write_text('{"changed":true}')
                return native(*args, **kwargs)
            with pytest.raises(ScheduleRestoreError, match='settings could not be restored'):
                apply_settings(settings, {**settings.value, 'scheduled':True}, install=install, uninstall=uninstall)
            assert settings.path.read_bytes() != original
    uninstall.assert_called_once()


def test_folder_target_reset_does_not_discard_invalid_name_draft(app, source):
    from ilias_sync.gui import FolderMappingDialog
    mapping_fixture(source)
    dialog = FolderMappingDialog(source, Settings())
    item = dialog.tree.topLevelItem(0)
    dialog.tree.setCurrentItem(item)
    dialog.rename_selected('..')
    assert dialog.name_errors
    dialog.reset_rule()
    assert dialog.name_errors and dialog.folder_name.text() == '..'
    dialog.reset_name()
    assert not dialog.name_errors
    dialog.reject()


def test_filters_refresh_available_courses_and_types_after_manifest_change(app, source):
    from ilias_sync.gui import MainWindow
    mapping_fixture(source)
    Settings().save_source(source)
    window = MainWindow()
    window.filter_files()
    window.filter_panel.kind.setCurrentIndex(window.filter_panel.kind.findData('.pdf'))
    state = data_dir() / 'sources' / source.id
    manifest = read_json(state/'manifest.json', {})
    manifest['files']['file:2'] = {'path':'Math/Data.csv', 'course_id':'crs-2', 'course_name':'Math'}
    write_json(state/'manifest.json', manifest)
    window.refresh()
    assert window.filter_panel.kind.findData('.csv') >= 0
    assert window.filter_panel.course.findData('crs-2') >= 0
    assert window.file_filters['kind'] == '.pdf'
    window.close()


def test_report_does_not_invent_zero_counts_for_old_unavailable_only_result(app):
    from ilias_sync.gui import SyncReportDialog
    dialog = SyncReportDialog({'result':{'unavailable':2}}, '')
    assert '0 neu' not in dialog.summary.text()
    assert 'keine einzelnen Dateizahlen' in dialog.summary.text()
    dialog.close()


def test_settings_write_failure_keeps_draft_and_does_not_blame_scheduler(app):
    from ilias_sync.gui import SettingsDialog
    settings = Settings()
    settings.save()
    original = settings.path.read_bytes()
    dialog = SettingsDialog(settings)
    dialog.language.setCurrentIndex(dialog.language.findData('en'))
    with patch.object(settings, 'save', side_effect=OSError('injected disk write failure')), patch('ilias_sync.gui.install') as install, patch('ilias_sync.gui.uninstall') as uninstall:
        dialog.save()
    assert 'Einstellungen konnten nicht gespeichert' in dialog.error.text()
    assert 'Zeitplan' not in dialog.error.text()
    assert dialog.tabs.currentIndex() == 0
    assert dialog.language.currentData() == 'en'
    assert settings.value['language'] == 'de'
    assert settings.path.read_bytes() == original
    install.assert_not_called()
    uninstall.assert_not_called()
    dialog.reject()


def test_last_complete_claim_requires_current_scope_including_legacy_states(app, source):
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import source_scope
    settings = Settings()
    settings.save_source(source)
    state = data_dir()/'sources'/source.id
    for scope in (None, 'old-configuration'):
        status = {'state':'Needs attention','finished':200,'last_success':100}
        if scope:
            status['scope'] = scope
        write_json(state/'status.json', status)
        window = MainWindow()
        assert 'Letzte vollständige' not in window.sync_panel.meta.text()
        window.close()
    status['scope'] = source_scope(source)
    write_json(state/'status.json', status)
    window = MainWindow()
    assert 'Letzte vollständige' in window.sync_panel.meta.accessibleName()
    window.close()


def test_scope_covers_material_policy_but_not_cosmetic_name_or_enabled(source):
    from dataclasses import replace
    from ilias_sync.storage import source_scope
    original = source_scope(source)
    for field, value in {'url':'https://other.example.edu', 'username':'different', 'login':'session',
        'client_id':'other', 'destination':source.destination+'2', 'targets':[source.url+'/go/crs/2'],
        'automatic_courses':False, 'videos':True, 'folder_rules':{'course/crs-2':source.destination+'2'},
        'folder_names':{'course/crs-2':'Alias'}, 'include_course_ids':True}.items():
        assert source_scope(replace(source, **{field:value})) != original, field
    assert source_scope(replace(source, name='Renamed', enabled=not source.enabled)) == original


def test_compact_status_keeps_full_schedule_accessible(app, source):
    from ilias_sync.gui import MainWindow
    Settings().save_source(source)
    window = MainWindow()
    window.sidebar.setFixedWidth(190)
    window.resize(820, 560)
    window.show()
    app.processEvents()
    assert window.sync_panel.schedule.isVisible()
    assert window.sync_panel.schedule.accessibleName()
    assert window.sync_panel.schedule.toolTip()
    window.close()


def test_mapping_filter_selects_visible_context_and_disables_editor_on_no_results(app, source):
    from ilias_sync.gui import FolderMappingDialog
    mapping_fixture(source)
    dialog = FolderMappingDialog(source, Settings())
    dialog.search.setText('Lecture')
    assert not dialog.tree.currentItem().isHidden()
    dialog.search.setText('no such item')
    assert dialog.tree.currentItem() is None
    assert not dialog.choose_button.isEnabled() and not dialog.folder_name.isEnabled()
    assert not dialog.effective_path.text()
    dialog.close()


def test_fixed_schedule_explains_server_pause_and_uses_next_real_calendar_time():
    from datetime import datetime
    from ilias_sync.presentation import schedule_expectation
    now = datetime(2026,10,28,11,0).timestamp()
    retry = datetime(2026,10,28,13,0).timestamp()
    settings = {'scheduled':True,'schedule_mode':'times','sync_times':['12:00','18:00'],'interval_hours':4}
    text = schedule_expectation(settings, {'next_run':retry,'evidence':{'http':{'retry_at':retry}}},clock=now)
    assert 'Serverpause' in text and '13:00' in text and '18:00' in text
    assert '12:00' not in text


def test_report_prefers_actual_exclusions_without_an_attention_task(app):
    from ilias_sync.gui import SyncReportDialog
    dialog = SyncReportDialog({'state':'Up to date','result':{'material_counts':{'unchanged':2},
        'counts':{'unchanged':2},'skipped':{'forum':1}}}, '')
    assert dialog.sections.currentIndex() == 1
    assert dialog.sections.tabText(0) == 'Dateien'
    dialog.close()
