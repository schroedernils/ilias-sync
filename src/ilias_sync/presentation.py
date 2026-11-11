"""Translate persisted sync facts into user-facing summaries, without changing policy."""
from dataclasses import dataclass
from functools import lru_cache
from html import escape
import os
import time

from .i18n import message, t


@dataclass(frozen=True)
class SyncSummary:
    title: str
    detail: str
    tone: str
    recovery: str = ''


def sync_summary(status, material_count):
    from .recovery import COURSE_LINK_DETAIL, needs_signin
    result = status.get('result') or {}
    counts = result.get('material_counts', result.get('counts', {}))
    state = status.get('state', '')
    if status.get('recovery') == 'folders':
        return SyncSummary(t('Check the folder names'), message(status.get('message', '')), 'error', 'folders')
    if state == 'Running':
        return SyncSummary(t('Synchronizing your materials'), t('The current run has no completed result yet.'), 'running')
    if status.get('server_deferred'):
        return SyncSummary(t('Waiting for the server'),
                           t('The server asked to retry later. Automatic sync will respect the requested time.'), 'warning', 'report')
    if needs_signin(status):
        return SyncSummary(t('Sign in to continue'), t('Check the saved sign-in details. Your local files are still available.'),
                           'error', 'signin')
    if status.get('failure_kind') == 'course_links':
        return SyncSummary(t('Check the saved course links'), t(COURSE_LINK_DETAIL), 'error', 'courses')
    if state == 'Needs attention' or result.get('errors'):
        return SyncSummary(t('Synchronization incomplete'),
                           message(status['message']) if status.get('message') else
                           t('Some files could not be checked. Your local files were kept. Try again.'), 'error', 'retry')
    if state == 'Stopped':
        return SyncSummary(t('Synchronization stopped'), t('Completed downloads were kept. You can continue with a new sync.'), 'neutral')
    if state == 'Checking courses':
        return SyncSummary(t('The last sync did not finish'), t('Your local files were kept. Start a new sync to check for updates.'), 'warning', 'retry')
    if not result:
        return SyncSummary(t('Ready for your first sync'), t('Choose your courses once. IliasSync keeps their materials available locally.'), 'neutral')
    unavailable = result.get('unavailable', 0)
    conflicts = counts.get('conflict', 0)
    if unavailable or conflicts or result.get('warnings') or result.get('partial') or state == 'Completed with warnings':
        facts = []
        if unavailable:
            facts.append(t('1 file unavailable') if unavailable == 1 else t('{count} files unavailable', count=unavailable))
        if conflicts:
            facts.append(t('1 local edit preserved') if conflicts == 1 else t('{count} local edits preserved', count=conflicts))
        if result.get('warnings'):
            facts.append(t('{count} warnings', count=result['warnings']))
        return SyncSummary(t('Sync completed with notes'),
                           '. '.join(facts) + ('. ' if facts else '') + t('See the report for details. Your local files were kept.'),
                           'warning', 'report')
    changed = counts.get('added', 0) + counts.get('updated', 0)
    detail = (t('{added} new · {updated} updated', added=counts.get('added', 0), updated=counts.get('updated', 0))
              if changed else t('No new materials in this run.') if material_count is None else
              t('No new materials. {count} files recorded in your archive.', count=material_count))
    return SyncSummary(t('Materials synchronized') if changed else t('Last check completed'), detail, 'success', 'recent' if changed else '')


def warning_facts(result):
    """Concrete exceptions only. No surrounding explanation."""
    result = result or {}
    counts = result.get('material_counts', result.get('counts', {}))
    facts = []
    unavailable = result.get('unavailable', 0) or 0
    if unavailable:
        facts.append(t('1 file unavailable') if unavailable == 1 else t('{count} files unavailable', count=unavailable))
    conflicts = counts.get('conflict', 0)
    if conflicts:
        facts.append(t('1 local edit preserved') if conflicts == 1 else t('{count} local edits preserved', count=conflicts))
    if result.get('warnings'):
        facts.append(t('{count} warnings', count=result['warnings']))
    return facts


def filtered_result(result, excluded):
    """Drop paths the person has chosen to skip. Unnamed leftovers stay visible."""
    result = dict(result or {})
    items = list(result.get('unavailable_items') or [])
    remaining = [path for path in items if path not in excluded]
    unnamed = max(0, int(result.get('unavailable') or 0) - len(items))
    details = [row for row in result.get('unavailable_details') or [] if row.get('path') not in excluded]
    result['unavailable_items'] = remaining
    result['unavailable_details'] = details
    result['unavailable'] = len(remaining) + unnamed
    return result, remaining


def schedule_expectation(settings, status, *, clock=None):
    if not settings.get('scheduled'):
        return t('Automatic sync is off')
    from .recovery import needs_signin
    if needs_signin(status):
        return t('Automatic sync waits for sign-in')
    now, stamp, retry_at, waiting_for_server = _schedule_moment(settings, status, clock)
    if waiting_for_server:
        return t('Server pause until {time}.', time=local_time(retry_at, now=now)) + ' ' + t('Next planned check: {time}', time=local_time(stamp, now=now))
    next_check = (t('Next check: when the operating system starts the scheduled run') if not stamp or stamp <= now
                  else t('Next planned check: {time}', time=local_time(stamp, now=now)))
    if status.get('deferred') == 'battery':
        return t('The last scheduled sync was skipped because your device was on battery power.') + ' ' + next_check
    return next_check


def _schedule_moment(settings, status, clock):
    import time
    from .policy import next_scheduled_run
    now = time.time() if clock is None else clock
    facts = status.get('result') or status.get('evidence') or {}
    retry_at = max(facts.get('http', {}).get('retry_at', 0), status.get('server_retry_at', 0))
    waiting_for_server = retry_at > now
    if settings.get('schedule_mode') in {'times', 'weekly'}:
        stamp = next_scheduled_run(settings, clock=max(now, retry_at - 0.001))
    else:
        stamp = max(status.get('next_run') or 0, retry_at)
    return now, stamp, retry_at, waiting_for_server


def brief_stamp(stamp, *, now=None):
    """A clock a person can read at a glance. Returns (text, today)."""
    if not stamp:
        return '', False
    zone = (os.environ.get('TZ'), time.tzname, time.timezone, time.daylight)
    value = _local_minute(int(stamp // 60), zone)
    today = _local_minute(int((time.time() if now is None else now) // 60), zone)
    clock = f'{value.tm_hour:02d}:{value.tm_min:02d}'
    if value[:3] == today[:3]:
        return clock, True
    if value.tm_year == today.tm_year:
        return f'{value.tm_mday:02d}.{value.tm_mon:02d}., {clock}', False
    return f'{value.tm_mday:02d}.{value.tm_mon:02d}.{value.tm_year}, {clock}', False


def schedule_brief(settings, status, *, clock=None):
    from .recovery import needs_signin
    if not settings.get('scheduled'):
        return t('Sync off')
    if needs_signin(status):
        return t('Waiting for sign-in')
    now, stamp, retry_at, waiting = _schedule_moment(settings, status, clock)
    if waiting:
        text, _today = brief_stamp(retry_at, now=now)
        return t('Paused until {time}', time=text)
    if not stamp or stamp <= now:
        return t('Next system run')
    text, today = brief_stamp(stamp, now=now)
    shown = (t('today') + ', ' + text) if today else text
    return t('Next check: {time}', time=shown)


def progress_copy(raw):
    """Put the operation first; keep full paths in the activity stream."""
    if raw.startswith('Checking '):
        content = raw[9:]
        if ' / ' in content:
            course, _, leaf = content.partition(' / ')
            return t('Checking course: {course}', course=course) + ' · ' + content.rsplit(' / ', 1)[-1]
    return message(raw)


@lru_cache(maxsize=8192)
def _local_minute(minute, zone):
    # Display precision is one minute. Share costly macOS timezone conversion
    # across table cells and paints, bounded independently of collection size.
    return time.localtime(minute * 60)


def local_time(stamp, *, now=None):
    if not stamp:
        return t('Not yet checked')
    zone = (os.environ.get('TZ'), time.tzname, time.timezone, time.daylight)
    value = _local_minute(int(stamp // 60), zone)
    today = _local_minute(int((time.time() if now is None else now) // 60), zone)
    clock = f'{value.tm_hour:02d}:{value.tm_min:02d}'
    if value[:3] == today[:3]:
        return t('Today at {time}', time=clock)
    return f'{value.tm_mday:02d}.{value.tm_mon:02d}.{value.tm_year:04d}, {clock}'


def file_size(size):
    if size < 1024:
        return f'{size} B'
    if size < 1024 ** 2:
        return f'{size / 1024:.0f} KB'
    if size < 1024 ** 3:
        return f'{size / 1024 ** 2:.1f} MB'
    return f'{size / 1024 ** 3:.1f} GB'


def is_course_info(entry):
    identity = entry.get('_identity', '')
    return identity.startswith('generated:') if identity else entry['path'].startswith('Course info/')


def file_context(entry):
    from pathlib import PurePosixPath
    path = PurePosixPath(entry['path'])
    context = str(path.parent).replace('/', '  /  ')
    if context == '.':
        context = entry.get('course_name', '')
    if entry.get('changed_at'):
        change = {'added': t('New'), 'updated': t('Updated'), 'conflict': t('Separate ILIAS copy')}.get(entry.get('change'), '')
        return ' · '.join(part for part in (change, local_time(entry['changed_at']), context) if part)
    return context


def report_html(status):
    """A readable result, with server-provided filenames escaped as text."""
    result = status.get('result') or {}
    counts = result.get('material_counts', result.get('counts', {}))
    chunks = []
    def section(title, paragraphs):
        chunks.append('<h3>' + escape(title) + '</h3>')
        chunks.extend('<p>' + escape(str(text)) + '</p>' for text in paragraphs)
    if status.get('message'):
        section(t('What needs attention'), [message(status['message'])])
    if result:
        section(t('Files'), [t('{added} new · {updated} updated', added=counts.get('added', 0), updated=counts.get('updated', 0)),
                             t('{count} unchanged', count=counts.get('unchanged', 0))])
        if counts.get('conflict'):
            section(t('Local edits preserved'), [t('Your edited files were kept. A separate ILIAS copy was saved beside them.')])
        if result.get('unavailable'):
            section(t('{count} files unavailable', count=result['unavailable']),
                    [t('These downloads were not available for publication in this run. Any existing local copies were kept.'),
                     *result.get('unavailable_items', [])])
        skipped = result.get('skipped', {})
        if skipped:
            names = {'forum': t('Forums'), 'test': t('Tests'), 'groups without membership': t('Groups you have not joined'),
                     'video': t('Videos'), 'scorm': t('SCORM modules')}
            section(t('Not downloaded automatically'),
                    [t('These are excluded content types or inaccessible groups, not failed file downloads.'),
                     *[f'{names.get(kind.casefold(), kind)}: {count}' for kind, count in skipped.items()]])
        if result.get('warnings') or result.get('errors'):
            section(t('Checks requiring attention'), [t('{count} warnings', count=result.get('warnings', 0)),
                                                      t('{count} errors', count=result.get('errors', 0))])
    else:
        section(t('No completed result yet'), [t('Run a sync to see what was downloaded and what needs attention.')])
    return ''.join(chunks)
