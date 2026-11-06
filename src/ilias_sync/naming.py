"""Human folder names; stable server identities remain in private metadata."""
from dataclasses import replace
from pathlib import Path

from .storage import clean_name, data_dir, FolderCollisionError, read_json, write_json


def validate_names(names):
    if not isinstance(names, dict):
        raise ValueError('Invalid folder naming settings.')
    for key, value in names.items():
        if not isinstance(key, str) or not key.startswith(('course/', 'path/')):
            raise ValueError('Invalid folder naming settings.')
        if not isinstance(value, str) or not value or clean_name(value, 80) != value:
            raise ValueError('Use a folder name without path separators or special characters.')


def course_folders(source, courses, *, persist=False):
    names = {course['id']: source.folder_names.get('course/' + course['id'], clean_name(
                 'Course' if course['name'] == 'Course ' + course['id'] else course['name'], 55))
             for course in courses}
    if source.include_course_ids:
        return {identity: name + f' [{identity}]' for identity, name in names.items()}
    path = data_dir() / 'sources' / source.id / 'course-folder-names.json'
    saved = read_json(path, {})
    saved = saved if isinstance(saved, dict) else {}
    result = {}
    reserved = {name.casefold() for name in names.values()}
    used = set()
    # Retain established numbers, including deselected courses. A newly joined
    # namesake must not take another course's existing local directory.
    for identity, entry in saved.items():
        if not isinstance(entry, dict) or not isinstance(entry.get('folder'), str):
            continue
        name = entry['folder']
        if clean_name(name, 120) != name:
            continue
        if identity in names and entry.get('base') != names[identity]:
            continue
        if name.casefold() in used:
            continue
        used.add(name.casefold())
        if identity in names:
            result[identity] = name
    for identity in sorted(names):
        if identity in result:
            continue
        name = names[identity]
        candidate = name
        number = 2
        while candidate.casefold() in used or (candidate != name and candidate.casefold() in reserved):
            candidate = f'{name} ({number})'
            number += 1
        result[identity] = candidate
        used.add(candidate.casefold())
    if persist:
        updated = {**saved, **{identity: {'base': names[identity], 'folder': folder}
                              for identity, folder in result.items()}}
        if updated != saved:
            write_json(path, updated)
    return result


def named_path(source, logical, proposed):
    parts = proposed.split('/')
    original = logical.split('/')
    for index in range(1, min(len(original), len(parts)) - 1):
        key = 'path/' + '/'.join(original[:index + 1])
        parts[index] = source.folder_names.get(key, parts[index])
    return '/'.join(parts)


def align_folders(archive, source, courses):
    """Rename owned directory trees in place, retaining annotations and all local contents."""
    from .routing import route_file
    folders = course_folders(source, courses)
    defaults = replace(source, folder_names={})
    for _ in range(max(1, len(archive.manifest['files']) * 5)):
        changed = False
        candidates = {}
        for identity, entry in archive.manifest['files'].items():
            logical, course_id = entry.get('logical'), entry.get('course_id')
            if identity.startswith('generated:'):
                original = identity[len('generated:'):].split('/')
                if original[0] not in folders:
                    continue
                logical = '/'.join(original)
                desired = 'Course info/' + named_path(source, logical, '/'.join([folders[original[0]], *original[1:]]))
                default = 'Course info/' + '/'.join([folders[original[0]], *original[1:]])
                course_index = 1
                root = Path(source.destination)
            elif logical and course_id in folders:
                proposed = '/'.join([folders[course_id], *logical.split('/')[1:]])
                root, desired, route = route_file(source, identity, course_id, logical, proposed)
                _, default, _ = route_file(defaults, identity, course_id, logical, proposed)
                course_index = 0 if not route else None
                if entry.get('route', '') != route:
                    continue  # Changed destinations retain their previous copies.
            else:
                continue
            if Path(entry.get('root', source.destination)).resolve() != root.resolve():
                continue
            old_parts, requested_parts = entry['path'].split('/'), desired.split('/')
            new_parts = list(old_parts)
            # The same server file can be linked from several ILIAS folders. Its
            # latest logical path need not describe its established local folder.
            # Rename only the course root and aliases of matching local paths.
            default_parts = default.split('/')
            logical_parts = logical.split('/')
            offset = len(logical_parts) - len(default_parts)
            previous_names = entry.get('folder_names_applied', {})
            matching = True
            for index, old in enumerate(old_parts[:-1]):
                if index == course_index:
                    new_parts[index] = requested_parts[index]
                    continue
                # Keep extra legacy directories such as "Submission" intact.
                if index >= len(default_parts) - 1:
                    break
                key = 'path/' + '/'.join(logical_parts[:offset + index + 1])
                matching = matching and old in {default_parts[index], previous_names.get(key), requested_parts[index]}
                if matching:
                    new_parts[index] = requested_parts[index]
            for index, (old, new) in enumerate(zip(old_parts[:-1], new_parts[:-1])):
                if old != new:
                    key = (str(root.resolve()), '/'.join(old_parts[:index + 1]))
                    candidates.setdefault(key, set()).add('/'.join(new_parts[:index + 1]))
                    break
        for (root, old), targets in sorted(candidates.items(), key=lambda row: row[0][1].count('/')):
            if len(targets) != 1:
                raise FolderCollisionError('A folder with this name already exists. Choose another name.')
            new = targets.pop()
            if (Path(root) / old).is_dir():
                archive.rename_folder(root, old, new)
                changed = True
                break
        if not changed:
            break


def validate_folder_changes(previous, candidate, courses, entries):
    from .routing import mapping_preview
    keys = {key for key in previous.folder_names.keys() | candidate.folder_names.keys()
            if previous.folder_names.get(key) != candidate.folder_names.get(key)}
    if previous.include_course_ids != candidate.include_course_ids:
        keys.update('course/' + row['id'] for row in courses)
    for key in keys:
        before, _ = mapping_preview(previous, courses, key, entries)
        after, _ = mapping_preview(candidate, courses, key, entries)
        if before != after and before.is_dir() and after.exists():
            raise FolderCollisionError('A folder with this name already exists. Choose another name.')
