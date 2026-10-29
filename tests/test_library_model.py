"""Library projections keep sources, archive identities and sync evidence separate."""
from dataclasses import replace

from ilias_sync.library import course_key, library_summary, load_library, source_summary
from ilias_sync.storage import Source, data_dir, source_scope, write_json


def test_projection_retains_custom_roots_and_namespaces_ids(source, tmp_path):
    other = Source('Another', 'https://b.example.edu', str(tmp_path / 'B'), client_id='test')
    for row in (source, other):
        state = data_dir() / 'sources' / row.id
        write_json(state / 'courses.json', [{'id': 'crs-1', 'name': 'Algorithms'}])
        write_json(state / 'manifest.json', {'files': {
            'file:1': {'path': 'Custom/File.pdf', 'root': str(tmp_path / row.id), 'course_id': 'crs-1'},
            'generated:crs-1/Description.html': {'path': 'Course info/Algorithms/Description.html', 'course_id': 'crs-1'}}})
    libraries = load_library([source, other])
    entries = [library['entries'][0] for library in libraries.values()]
    assert {entry['_identity'] for entry in entries} == {'file:1'}
    assert len({course_key(entry, global_scope=True) for entry in entries}) == 2
    assert {entry['course_name'] for entry in entries} == {'Algorithms'}
    assert entries[0]['root'] == str(tmp_path / source.id)
    assert libraries[source.id]['entries'][1]['_identity'].startswith('generated:')


def test_aggregate_success_does_not_hide_another_universitys_missing_check_or_error(source, tmp_path):
    other = Source('Another', 'https://b.example.edu', str(tmp_path / 'B'), client_id='test')
    write_json(data_dir() / 'sources' / source.id / 'status.json', {
        'state': 'Up to date', 'scope': source_scope(source), 'result': {'counts': {'unchanged': 1}}})
    assert library_summary(load_library([source, other])).tone == 'neutral'
    write_json(data_dir() / 'sources' / other.id / 'status.json', {'state': 'Needs attention', 'scope': 'old'})
    libraries = load_library([source, other])
    assert source_summary(libraries[other.id]).tone == 'error'
    assert library_summary(libraries).tone == 'error'
    assert other.name in library_summary(libraries).detail
    renamed = replace(source, name='Cosmetic rename')
    assert source_summary(load_library([renamed])[source.id]).tone == 'success'
