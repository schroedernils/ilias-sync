"""Local, deduplicated sync notices. Dismissal never changes sync evidence."""
import ctypes
import hashlib
import json
from pathlib import Path
import sys
import time

from filelock import FileLock

from .storage import data_dir, read_json, write_json


def issues(status):
    from .recovery import needs_signin
    result = status.get('result') or {}
    rows = []
    if needs_signin(status) or status.get('state') == 'Needs attention':
        kind = 'signin' if needs_signin(status) else status.get('failure_kind') or status.get('recovery') or 'check'
        rows.append({'kind': kind, 'path': '', 'reason': '', 'count': 1, 'severity': 'error'})
    details = result.get('unavailable_details') or [
        {'path': path, 'reason': 'not_confirmed'} for path in result.get('unavailable_items', [])]
    for detail in details:
        rows.append({'kind': 'unavailable', 'path': detail['path'], 'reason': detail.get('reason', 'not_confirmed'),
                     'count': 1, 'severity': 'warning'})
    remaining = max(0, result.get('unavailable', 0) - len(details))
    if remaining:
        rows.append({'kind': 'unavailable', 'path': '', 'reason': '', 'count': remaining, 'severity': 'warning'})
    for key, severity in [('errors', 'error'), ('warnings', 'warning')]:
        if result.get(key):
            rows.append({'kind': key, 'path': '', 'reason': '', 'count': result[key], 'severity': severity})
    if result.get('partial') and not rows:
        rows.append({'kind': 'incomplete', 'path': '', 'reason': '', 'count': 1, 'severity': 'warning'})
    return rows


def observe_attempt(state, status, *, deliver=False):
    """Only completed attempts resolve/reopen notices; repeats stay dismissed."""
    if not status.get('finished') or status.get('state') in {'Stopped', 'Checking courses', 'Running'}:
        return []
    path = state / 'notices.json'
    attempt = [status.get('started'), status['finished'], status.get('scope')]
    # A read-only refresh must not touch the lock file: macOS directory watches
    # can report that write and otherwise create a self-sustaining refresh loop.
    if read_json(path, {}).get('attempt') == attempt:
        return []
    with FileLock(str(path) + '.lock', timeout=2):
        value = read_json(path, {'notices': [], 'attempt': None})
        if value.get('attempt') == attempt:
            return []
        previous = {row['id']: row for row in value['notices']}
        active, new = [], []
        for issue in issues(status):
            identity = hashlib.sha256(json.dumps([status.get('scope'), issue['kind'], issue['path'],
                                                 issue['reason']], sort_keys=True).encode()).hexdigest()[:24]
            old = previous.get(identity, {})
            reopened = not old or old.get('resolved', False) or issue['count'] > old.get('count', 0)
            row = {**issue, 'id': identity, 'first_seen': status['finished'] if reopened else old['first_seen'],
                   'last_seen': status['finished'], 'occurrences': 1 if reopened else old['occurrences'] + 1,
                   'dismissed': False if reopened else old.get('dismissed', False), 'resolved': False}
            active.append(row)
            if reopened:
                new.append(row)
        ids = {row['id'] for row in active}
        resolved = [{**row, 'resolved': True} for row in value['notices'] if row['id'] not in ids]
        write_json(path, {'attempt': attempt, 'notices': [*active, *resolved[:max(0, 200 - len(active))]]})
    if deliver and new and preferences().get('enabled'):
        # Generic content deliberately excludes paths, university credentials,
        # and server-provided messages from the lock-screen notification.
        from .storage import Settings
        body = ('New synchronization problems. Open IliasSync for details.' if Settings().value.get('language') == 'en' else
                'Neue Probleme bei der Synchronisierung. Details in IliasSync ansehen.')
        native_notify('IliasSync', body,
                      state.name + '-' + str(status['finished']))
    return new


def notices(source_id):
    return read_json(data_dir() / 'sources' / source_id / 'notices.json', {'notices': []})['notices']


def dismiss(source_id, identity, dismissed=True):
    path = data_dir() / 'sources' / source_id / 'notices.json'
    with FileLock(str(path) + '.lock', timeout=2):
        value = read_json(path, {'notices': []})
        for row in value['notices']:
            if row['id'] == identity:
                row['dismissed'] = dismissed
        write_json(path, value)


def preferences():
    return read_json(data_dir() / 'notification-settings.json', {'enabled': False})


def set_enabled(enabled):
    write_json(data_dir() / 'notification-settings.json', {'enabled': bool(enabled)})


def _native():
    if sys.platform != 'darwin' or not getattr(sys, 'frozen', False):
        return None
    path = Path(__file__).parent / 'assets/native/libilias_notifications.dylib'
    return ctypes.CDLL(str(path))


def permission(*, request=False):
    """0 unknown, 1 denied, 2 authorized, -1 unsupported/unavailable."""
    try:
        native = _native()
        if native is None:
            return -1
        native.ilias_notification_permission.argtypes = [ctypes.c_int]
        native.ilias_notification_permission.restype = ctypes.c_int
        return native.ilias_notification_permission(int(request))
    except (OSError, AttributeError):
        return -1


def native_notify(title, body, identity):
    try:
        native = _native()
        if native is None:
            return False
        native.ilias_notify.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        native.ilias_notify.restype = ctypes.c_int
        return bool(native.ilias_notify(title.encode(), body.encode(), identity.encode()))
    except (OSError, AttributeError):
        return False


def relative_time(timestamp, now=None):
    from .i18n import t
    seconds = max(0, (time.time() if now is None else now) - timestamp)
    if seconds < 60:
        return t('just now')
    if seconds < 3600:
        return t('{count} min ago', count=int(seconds // 60))
    if seconds < 86400:
        return t('{count} h ago', count=int(seconds // 3600))
    return t('{count} days ago', count=int(seconds // 86400))
