from scripts.build_metadata import metadata


def test_build_identity_changes_with_source_and_does_not_include_local_paths(tmp_path):
    source = tmp_path/'src/ilias_sync'
    source.mkdir(parents=True)
    (source/'module.py').write_text('original')
    first = metadata(tmp_path, 'preview')
    (source/'module.py').write_text('changed')
    second = metadata(tmp_path, 'preview')
    assert first['id'] != second['id']
    assert str(tmp_path) not in str(second)
    (source/'ignored.pyc').write_bytes(b'cache')
    assert metadata(tmp_path, 'preview')['id'] == second['id']


def test_source_runtime_has_explicit_development_build_identity():
    from ilias_sync.build_info import build_info
    assert build_info()['id'] == 'development'
