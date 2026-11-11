"""Classify course selections without opening or following pasted URLs."""
from urllib.parse import parse_qs, urljoin, urlsplit


WEB_LINK = 'This is a link to external content, not an ILIAS course. Copy the course, group, or folder link instead.'
WRONG_SERVER = 'Paste a course, group, or folder link from this university.'
NOT_CONTAINER = 'This link points to an item, not an ILIAS course, group, or folder.'


def course_link(base, value):
    """Return (absolute URL, issue). Preserve custom same-site course URLs."""
    try:
        absolute = urljoin(base.rstrip('/') + '/', value)
        parts, origin = urlsplit(absolute), urlsplit(base)
        if parts.scheme != 'https' or parts.netloc.lower() != origin.netloc.lower():
            return absolute, WRONG_SERVER
    except ValueError:
        return value, WRONG_SERVER
    query = {key.lower(): vals[0].lower() for key, vals in parse_qs(parts.query).items()}
    target = query.get('target', '')
    command = query.get('cmd', '')
    handler = query.get('baseclass', '')
    path = parts.path.lower().split('/')
    if (handler == 'illinkresourcehandlergui' or query.get('cmdclass') == 'illinkresourcehandlergui'
            or command in {'calldirectlink', 'exporthtml'} or target.startswith('webr_') or 'webr' in path):
        return absolute, WEB_LINK
    if (command in {'sendfile', 'download'} or handler == 'ilfilegui'
            or target.startswith('file_') or 'file' in path):
        return absolute, NOT_CONTAINER
    return absolute, ''


def course_link_issues(source):
    return [{'path': url, 'reason': 'course_link', 'message': problem}
            for url in source.targets if (problem := course_link(source.url, url)[1])]


def is_manual_course(row):
    return row.get('manual', row['name'] == 'Course ' + row['id'])
