"""Most-specific local folder rules. No remote changes or automatic removal of old copies."""
import hashlib
from pathlib import Path

from .storage import data_dir


def validate_routes(routes):
    if not isinstance(routes, dict):
        raise ValueError('Invalid folder rules.')
    for key, folder in routes.items():
        if not isinstance(key, str) or not key.startswith(('course/', 'path/', 'file/')):
            raise ValueError('Invalid folder rule key.')
        target = Path(folder).expanduser()
        if not target.is_absolute():
            raise ValueError('Choose an absolute destination folder.')
        root = data_dir().resolve()
        if target.resolve().is_relative_to(root) or root.is_relative_to(target.resolve()):
            raise ValueError('Choose a dedicated download folder outside application data.')


def route_file(source, identity, course_id, logical, proposed):
    """Return destination root, portable relative path and explicit rule fingerprint."""
    from .naming import named_path
    proposed = named_path(source, logical, proposed)
    routes = source.folder_rules
    file_key = 'file/' + identity
    if file_key in routes:
        key, relative = file_key, Path(proposed).name
    else:
        parts = logical.split('/')
        key = next(('path/' + '/'.join(parts[:n]) for n in range(len(parts)-1, 0, -1)
                    if 'path/' + '/'.join(parts[:n]) in routes), None)
        if key:
            renamed = proposed.split('/')
            relative = '/'.join(renamed[len(key[5:].split('/')):])
        elif 'course/' + course_id in routes:
            key = 'course/' + course_id
            relative = '/'.join(proposed.split('/')[1:])
        else:
            return Path(source.destination), proposed, ''
    destination = Path(routes[key]).expanduser().resolve()
    fingerprint = hashlib.sha256((key + '\0' + str(destination)).encode()).hexdigest()
    return destination, relative, fingerprint


def mapping_preview(source, courses, key, entries):
    """Resolve the exact effective destination using the engine's routing rules."""
    from .naming import course_folders
    folders = course_folders(source, courses)
    if key.startswith('file/'):
        identity = key[5:]
        entry = entries[identity]
        logical = entry['logical']
        course_id = entry['course_id']
    else:
        identity = '__preview__'
        logical = key[7:] if key.startswith('course/') else key[5:]
        course_id = logical.split('/')[0]
        logical += '/__preview__'
    proposed = '/'.join([folders.get(course_id, course_id), *logical.split('/')[1:]])
    root, relative, _ = route_file(source, identity, course_id, logical, proposed)
    effective = root / relative if key.startswith('file/') else (root / relative).parent
    matches = ['file/' + identity] + ['path/' + '/'.join(logical.split('/')[:n])
                                     for n in range(len(logical.split('/')) - 1, 0, -1)] + ['course/' + course_id]
    inherited_from = next((candidate for candidate in matches if candidate in source.folder_rules), '')
    return effective, inherited_from
