"""Read-only library projections. Browsing never changes synchronization targets."""
from hashlib import sha256
from pathlib import PurePosixPath

from .i18n import t
from .course_links import course_link, course_link_issues, is_manual_course
from .presentation import SyncSummary, is_course_info, sync_summary
from .storage import data_dir, read_json, source_scope


def cached_courses(source):
    rows = read_json(data_dir() / 'sources' / source.id / 'courses.json', [])
    saved = {course_link(source.url, url)[0] for url in source.targets}
    return [row for row in rows if not course_link(source.url, row.get('url', ''))[1]
            and (not is_manual_course(row) or row.get('url') in saved)]


def load_library(sources):
    """Namespace object/course IDs by source, retaining each file's actual root."""
    libraries = {}
    for source in sources:
        state = data_dir() / 'sources' / source.id
        cached = cached_courses(source)
        courses = {row['id']: row['name'] for row in cached}
        entries = []
        for identity, value in read_json(state / 'manifest.json', {'files': {}})['files'].items():
            course = value.get('course_id', '')
            if course and value.get('course_name'):
                courses.setdefault(course, value['course_name'])
            elif course and course not in courses:
                parts = PurePosixPath(value['path']).parts
                # Old manifests may have no display name. Keep the recorded ID
                # for generated entries rather than guessing a course from it.
                courses[course] = parts[0] if len(parts) > 1 and not identity.startswith('generated:') else course
            entries.append({**value, '_identity': identity, '_source_id': source.id,
                            '_source_name': source.name, '_destination': source.destination,
                            'course_name': value.get('course_name') or courses.get(course, '')})
        # Resolve names learned from later entries as well.
        for entry in entries:
            if not entry.get('course_name'):
                entry['course_name'] = courses.get(entry.get('course_id'), '')
        status = read_json(state / 'status.json', {})
        invalid = course_link_issues(source)
        # Older builds surfaced this exact failed pseudo-course as an auth error.
        # Keep the recorded attempt unchanged; offer the repair in the library.
        attempted = (status.get('evidence') or {}).get('course_scope', [])
        invalid_ids = {sha256(course_link(source.url, row['path'])[0].encode()).hexdigest()[:12]
                       for row in invalid}
        if (status.get('message') == 'Sign-in expired or was rejected by ILIAS.'
                and any(row['id'] in invalid_ids for row in attempted)):
            evidence = status['evidence']
            status = {**status, 'login_required': False, 'state': 'Needs attention', 'message': '',
                      'failure_kind': 'course_links', 'evidence': {**evidence, 'check_issues': invalid}}
        libraries[source.id] = {'source': source, 'courses': courses, 'entries': entries, 'status': status}
    return libraries


def course_key(entry, *, global_scope=False):
    course = entry.get('course_id', '')
    return entry['_source_id'] + '/' + course if course and global_scope else course


def source_summary(library):
    source, status = library['source'], library['status']
    count = sum(not is_course_info(entry) for entry in library['entries'])
    summary = sync_summary(status, count)
    if status.get('result') and not status.get('scope') and summary.tone == 'success':
        return SyncSummary(t('A new check is needed'),
                           t('This older result has no recorded course and destination scope. Sync once to confirm the current setup.'), 'neutral', 'retry')
    if status.get('scope') and status['scope'] != source_scope(source) and summary.tone != 'error':
        return SyncSummary(t('Settings changed since the last check'),
                           t('Start a sync to check the current courses and destinations.'), 'neutral', 'retry')
    return summary


def library_summary(libraries):
    """Never promote one university's successful check to the whole library."""
    rows = [(library, source_summary(library)) for library in libraries.values()]
    if len(rows) == 1:
        return rows[0][1]
    for tone in ('error', 'warning', 'neutral'):
        affected = [library['source'].name for library, summary in rows if summary.tone == tone]
        if affected:
            return SyncSummary(t('Universities need attention') if tone == 'error' else
                               t('Checks completed with notes') if tone == 'warning' else t('Not all universities checked'),
                               ' · '.join(affected), tone, 'report')
    return SyncSummary(t('University checks completed'),
                       t('Each university has its own last check. Expand the details to see individual results.'), 'success')
