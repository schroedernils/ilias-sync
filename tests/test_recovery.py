"""Recovery evidence and complete correction/check/result flows."""
import errno
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ilias_sync.recovery import failure_kind, needs_signin, recovery_plan
from ilias_sync.storage import Settings, data_dir, read_json, source_scope, write_json


@pytest.mark.parametrize('status,kind,action', [
    ({'state': 'Sign in again'}, 'signin', 'signin'),
    ({'state': 'Needs attention', 'message': 'Sign-in expired or was rejected by ILIAS.'}, 'signin', 'signin'),
    ({'state': 'Needs attention', 'failure_kind': 'network'}, 'network', 'retry'),
    ({'state': 'Needs attention'}, 'unknown', 'retry'),
    ({'recovery': 'folders'}, 'folders', 'folders'),
    ({'server_deferred': True}, 'server', 'browser'),
    ({'failure_kind': 'permission'}, 'permission', 'storage'),
    ({'failure_kind': 'storage_full'}, 'storage_full', 'storage'),
    ({'result': {'unavailable': 2}}, 'partial', 'browser'),
    ({'failure_kind': 'missing'}, 'missing', 'retry'),
])
def test_recovery_offers_steps_matching_known_facts(status, kind, action):
    plan = recovery_plan(status)
    assert plan.kind == kind and plan.action == action
    assert plan.explanation and len(plan.steps) >= 2


def test_failure_cause_is_not_guessed_from_arbitrary_exception_text():
    import aiohttp
    assert failure_kind(PermissionError()) == 'permission'
    assert failure_kind(OSError(errno.ENOSPC, 'fixture')) == 'storage_full'
    assert failure_kind(aiohttp.ClientConnectionError()) == 'network'
    assert failure_kind(TimeoutError()) == 'network'
    assert failure_kind(RuntimeError('permission login network timeout')) == ''
    assert not needs_signin({'state': 'Needs attention', 'message': 'filename: Sign-in expired or was rejected by ILIAS.'})


async def test_legacy_signin_failure_waits_for_manual_repair_instead_of_automatic_retries(source, monkeypatch):
    from ilias_sync.__main__ import worker
    Settings().save_source(source)
    path = data_dir() / 'sources' / source.id / 'status.json'
    previous = {'state': 'Needs attention', 'message': 'Sign-in expired or was rejected by ILIAS.'}
    write_json(path, previous)
    sync = AsyncMock()
    monkeypatch.setattr('ilias_sync.engine.synchronize', sync)
    assert await worker(SimpleNamespace(sync=True, discover=False, profile=None, probe=None, scheduled_time=True)) == 0
    sync.assert_not_called()
    assert read_json(path, {}) == previous


async def test_worker_records_connection_cause_without_disclosing_exception_details(source, monkeypatch):
    import aiohttp
    from ilias_sync.__main__ import worker
    Settings().save_source(source)
    monkeypatch.setattr('ilias_sync.engine.synchronize', AsyncMock(side_effect=aiohttp.ClientConnectionError('private-test-token')))
    assert await worker(SimpleNamespace(sync=True, discover=False, profile=source.id, probe=None)) == 1
    status = read_json(data_dir() / 'sources' / source.id / 'status.json', {})
    assert status['failure_kind'] == 'network'
    assert 'private-test-token' not in status['message']


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('method', ['local', 'session'])
def test_signin_repair_opens_correct_page_requires_fresh_input_and_cancel_keeps_profile(app, source, method):
    from ilias_sync.gui import SourceDialog
    source.login = method
    settings = Settings()
    settings.save_source(source)
    original = settings.path.read_bytes()
    dialog = SourceDialog(settings, source, signin_recovery=True)
    assert dialog.stack.currentIndex() == 1
    assert dialog.next_button.text() == 'Speichern und prüfen'
    with patch('ilias_sync.profile_service.commit_profile') as commit:
        dialog.save()
        commit.assert_not_called()
    assert dialog.error.text()
    assert not dialog.password.text() and not dialog.session.text()
    dialog.reject()
    assert settings.path.read_bytes() == original


def test_cancel_does_not_retry_but_saved_signin_starts_a_verifying_check(app, source):
    from ilias_sync.gui import MainWindow
    Settings().save_source(source)
    path = data_dir() / 'sources' / source.id / 'status.json'
    write_json(path, {'state': 'Sign in again', 'login_required': True})
    window = MainWindow()
    with patch('ilias_sync.gui.SourceDialog') as dialog, patch.object(window, 'start') as start:
        dialog.return_value.exec.return_value = False
        window.recover()
        start.assert_not_called()
        assert window.sync_panel.mark.tone == 'error'
        dialog.return_value.exec.return_value = True
        dialog.return_value.source = source
        window.recover()
        start.assert_called_once_with('sync', source)
        assert window.repair_checks[source.id]['phase'] == 'checking'
    window.close()


@pytest.mark.parametrize('outcome', ['success', 'notes', 'failure', 'stale-success'])
def test_correction_is_confirmed_only_after_a_new_successful_check(app, source, outcome):
    from ilias_sync.gui import MainWindow
    Settings().save_source(source)
    window = MainWindow()
    window.repair_checks[source.id] = {'kind': 'signin', 'phase': 'checking', 'started': 100}
    window.job = ('sync', source)
    window.process = Mock()
    status = {'state': 'Up to date', 'finished': 200, 'scope': source_scope(source), 'result': {'counts': {'unchanged': 1}}}
    if outcome == 'notes':
        status.update(state='Completed with warnings', result={'unavailable': 2})
    elif outcome == 'failure':
        status = {'state': 'Sign in again', 'login_required': True, 'finished': 200}
    elif outcome == 'stale-success':
        status['finished'] = 50
    write_json(data_dir() / 'sources' / source.id / 'status.json', status)
    with patch.object(window, 'read_output'):
        window.finished(1 if outcome == 'failure' else 0, None)
    if outcome in {'success', 'notes'}:
        assert window.repair_checks[source.id]['phase'] == 'verified'
        assert 'Anmeldung bestätigt' in window.sync_panel.title.full_text
        assert window.sync_panel.mark.tone == ('warning' if outcome == 'notes' else 'success')
    else:
        assert window.repair_checks[source.id]['phase'] == 'failed'
        assert window.sync_panel.mark.tone == 'error'
        assert 'Anmeldung bestätigt' not in window.sync_panel.title.full_text
    window.close()


def test_missing_file_repair_does_not_claim_restoration_when_server_no_longer_offers_it(app, source):
    from ilias_sync.gui import MainWindow
    Settings().save_source(source)
    state = data_dir() / 'sources' / source.id
    write_json(state / 'manifest.json', {'files': {'file:1': {'path': 'Absent.pdf'}}})
    window = MainWindow()
    window.files.selectRow(0)
    window.open_file()
    assert window.recovery_button.text() == 'Datei wiederherstellen'
    with patch.object(window, 'start') as start:
        window.recover()
        start.assert_called_once_with('sync', source)
    repair = window.repair_checks[source.id]
    window.job = ('sync', source)
    window.process = Mock()
    write_json(state / 'status.json', {'state': 'Up to date', 'finished': repair['started'] + 1,
        'scope': source_scope(source), 'result': {'counts': {'unchanged': 0}}})
    with patch.object(window, 'read_output'):
        window.finished(0, None)
    assert window.repair_checks[source.id]['phase'] == 'failed'
    assert window.sync_panel.mark.tone == 'error'
    assert 'fehlt weiterhin' in window.sync_panel.detail.text()
    assert window.recovery_button.text() == 'Datei wiederherstellen'
    window.close()


def test_successful_recovery_label_is_not_reused_after_a_later_failure(app, source):
    from ilias_sync.gui import MainWindow
    Settings().save_source(source)
    path = data_dir() / 'sources' / source.id / 'status.json'
    write_json(path, {'state': 'Needs attention', 'finished': 300})
    window = MainWindow()
    window.repair_checks[source.id] = {'kind': 'signin', 'phase': 'verified', 'started': 100, 'finished': 200}
    window.refresh()
    assert 'Anmeldung bestätigt' not in window.sync_panel.title.full_text
    assert window.sync_panel.mark.tone == 'error'
    assert window.recovery_button.text() == 'Erneut prüfen'
    window.close()


def test_file_repair_keeps_the_failed_file_identity_after_another_row_is_selected(app, source):
    from ilias_sync.gui import MainWindow
    from test_presentation import prepare_library
    prepare_library(source)
    window = MainWindow()
    window.files.selectRow(0)
    failed = window.selected_entry()
    window.file_target().unlink()
    window.open_file()
    window.files.selectRow(1)
    assert window.selected_entry()['_identity'] != failed['_identity']
    with patch.object(window, 'start'):
        window.recover()
    assert window.repair_checks[source.id]['identity'] == failed['_identity']
    window.close()


def test_leaving_missing_file_scope_does_not_replace_later_signin_recovery(app, source):
    from ilias_sync.gui import MainWindow
    Settings().save_source(source)
    state = data_dir() / 'sources' / source.id
    write_json(state / 'manifest.json', {'files': {'file:1': {'path': 'Absent.pdf'}}})
    write_json(state / 'status.json', {'state': 'Sign in again', 'login_required': True})
    window = MainWindow()
    window.files.selectRow(0)
    window.open_file()
    window.sources.select_scope()
    assert not window.ui_error_kind
    assert window.recovery_button.text() == 'Anmeldung erneuern'
    with patch.object(window, 'edit') as edit:
        window.recover()
        edit.assert_called_once_with(signin=True, source=source)
    window.close()
