"""Translate persisted sync facts into user-facing summaries, without changing policy."""
from dataclasses import dataclass
from datetime import datetime
from html import escape

from .i18n import message, t


@dataclass(frozen=True)
class SyncSummary:
    title: str
    detail: str
    tone: str
    recovery: str = ''


def sync_summary(status, material_count):
    result = status.get('result') or {}
    counts = result.get('material_counts', result.get('counts', {}))
    state = status.get('state', '')
    if status.get('recovery') == 'folders':
        return SyncSummary(t('Check the folder names'), message(status.get('message', '')), 'error', 'folders')
    if state == 'Running':
        return SyncSummary(t('Synchronizing your materials'), t('The current run has no completed result yet.'), 'running')
    if status.get('login_required') or state == 'Sign in again':
        return SyncSummary(t('Sign in to continue'), t('Check the saved sign-in details. Your local files are still available.'),
                           'error', 'signin')
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
    return SyncSummary(t('Last check completed'), detail, 'success', 'recent' if changed else '')


def schedule_expectation(settings, status, *, clock=None):
    import time
    from .policy import next_scheduled_run
    if not settings.get('scheduled'):
        return t('Automatic sync is off')
    if status.get('login_required'):
        return t('Automatic sync waits for sign-in')
    now = time.time() if clock is None else clock
    if settings.get('schedule_mode') == 'times':
        stamp = next_scheduled_run(settings, clock=now)
    else:
        stamp = status.get('next_run')
    if status.get('deferred') == 'battery':
        return t('Last automatic run deferred on battery. Next attempt follows the schedule.')
    if not stamp or stamp <= now:
        return t('Next check: when the operating system starts the scheduled run')
    return t('Next planned check: {time}', time=local_time(stamp))


def progress_copy(raw):
    """Put the operation first; keep full paths in the activity stream."""
    if raw.startswith('Checking '):
        content = raw[9:]
        if ' / ' in content:
            course, _, leaf = content.partition(' / ')
            return t('Checking course: {course}', course=course) + ' · ' + content.rsplit(' / ', 1)[-1]
    return message(raw)


def local_time(stamp, *, now=None):
    if not stamp:
        return t('Not yet checked')
    value = datetime.fromtimestamp(stamp)
    today = datetime.fromtimestamp(now) if now is not None else datetime.now()
    if value.date() == today.date():
        return t('Today at {time}', time=value.strftime('%H:%M'))
    return value.strftime('%d.%m.%Y, %H:%M')


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
