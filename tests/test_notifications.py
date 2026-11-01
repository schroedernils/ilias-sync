from unittest.mock import patch

from ilias_sync.notifications import dismiss, notices, observe_attempt, relative_time, set_enabled
from ilias_sync.storage import data_dir, read_json, write_json


def attempt(finished, **changes):
    return {'state': 'Needs attention', 'failure_kind': 'network', 'scope': 'same-courses',
            'started': finished - 5, 'finished': finished, **changes}


def state(source):
    root = data_dir() / 'sources' / source.id
    root.mkdir(parents=True)
    return root


def test_repeated_dismissed_problem_stays_dismissed_but_recurrence_after_recovery_notifies(source):
    root = state(source)
    set_enabled(True)
    with patch('ilias_sync.notifications.native_notify', return_value=True) as notify:
        assert len(observe_attempt(root, attempt(10), deliver=True)) == 1
        row = notices(source.id)[0]
        dismiss(source.id, row['id'])
        assert observe_attempt(root, attempt(20), deliver=True) == []
        repeated = notices(source.id)[0]
        assert repeated['dismissed'] and repeated['occurrences'] == 2
        assert not repeated['resolved']
        assert notify.call_count == 1
        observe_attempt(root, attempt(30, state='Up to date', failure_kind='', result={'counts': {'unchanged': 3}}), deliver=True)
        assert notices(source.id)[0]['resolved']
        assert len(observe_attempt(root, attempt(40), deliver=True)) == 1
        assert notify.call_count == 2
        assert not notices(source.id)[0]['dismissed']


def test_cancelled_and_in_progress_attempts_never_resolve_notices_and_replaying_is_idempotent(source):
    root = state(source)
    observe_attempt(root, attempt(10))
    assert observe_attempt(root, attempt(10)) == []
    observe_attempt(root, attempt(20, state='Stopped'))
    observe_attempt(root, attempt(30, state='Checking courses'))
    assert notices(source.id)[0]['occurrences'] == 1
    assert not notices(source.id)[0]['resolved']


def test_new_file_issue_notifies_once_and_dismissal_never_modifies_evidence(source):
    root = state(source)
    result = {'unavailable': 1, 'unavailable_details': [{'path': '<lecture>.pdf', 'reason': 'forbidden'}]}
    status = attempt(10, state='Completed with warnings', result=result)
    write_json(root / 'status.json', status)
    write_json(root / 'history.json', [status])
    before = [(root / name).read_bytes() for name in ['status.json', 'history.json']]
    observe_attempt(root, status)
    row = notices(source.id)[0]
    dismiss(source.id, row['id'])
    assert [(root / name).read_bytes() for name in ['status.json', 'history.json']] == before
    observe_attempt(root, {**status, 'finished': 20, 'result': {'unavailable': 2,
        'unavailable_details': [*result['unavailable_details'], {'path': 'new.pdf', 'reason': 'forbidden'}]}})
    assert sum(not row['dismissed'] for row in notices(source.id)) == 1
    assert read_json(root / 'status.json', {}) == status


def test_opt_in_and_generic_native_payload_do_not_disclose_paths_or_server_messages(source):
    root = state(source)
    with patch('ilias_sync.notifications.native_notify') as notify:
        observe_attempt(root, attempt(10), deliver=True)
        notify.assert_not_called()
        set_enabled(True)
        observe_attempt(root, attempt(20, failure_kind='permission', message='secret-credential',
            result={'unavailable': 1, 'unavailable_items': ['private-course.pdf']}), deliver=True)
        assert notify.call_count == 1
        assert 'secret-credential' not in str(notify.call_args)
        assert 'private-course.pdf' not in str(notify.call_args)


def test_relative_times_are_nonnegative_and_change_at_minute_boundaries():
    from ilias_sync.i18n import set_language
    set_language('de')
    assert relative_time(100, 100) == 'gerade eben'
    assert relative_time(100, 99) == 'gerade eben'
    assert relative_time(100, 160) == 'vor 1 Min.'
    assert relative_time(100, 3700) == 'vor 1 Std.'


def test_notification_failure_never_changes_a_successful_recorded_sync(source):
    from ilias_sync.storage import record_attempt
    root = state(source)
    status = {'state': 'Up to date', 'finished': 100, 'result': {'counts': {'added': 2}}}
    with patch('ilias_sync.notifications.observe_attempt', side_effect=RuntimeError('notification unavailable')):
        record_attempt(root, status, {})
    assert read_json(root / 'status.json', {})['state'] == 'Up to date'
    assert read_json(root / 'history.json', [])[0]['last_success'] == 100
