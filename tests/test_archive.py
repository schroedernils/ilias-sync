
import pytest

from ilias_sync.storage import Archive, clean_name, safe_path, sha256


def setup(tmp_path):
    raw = tmp_path / "raw.pdf"
    raw.write_bytes(b"%PDF-1.4 original")
    archive = Archive(tmp_path / "state", tmp_path / "out")
    return raw, archive


def test_repeat_is_idempotent_and_reuses_stat_metadata(tmp_path, monkeypatch):
    raw, archive = setup(tmp_path)
    assert archive.publish("file:1", raw, "Course/lecture.pdf") == "added"
    monkeypatch.setattr("ilias_sync.storage.sha256", lambda path: pytest.fail("No hashing for unchanged stat metadata"))
    assert archive.publish("file:1", raw, "Course/lecture.pdf") == "unchanged"


def test_remote_update_versions_and_restore(tmp_path):
    raw, archive = setup(tmp_path)
    archive.publish("file:1", raw, "Course/lecture.pdf")
    raw.write_bytes(b"%PDF-1.4 changed and longer")
    assert archive.publish("file:1", raw, "Course/lecture.pdf") == "updated"
    version = [p for p in (tmp_path / "out/Versions").rglob("*.pdf") if p.is_file()][0]
    assert version.read_bytes() == b"%PDF-1.4 original"
    restored = tmp_path / "restored.pdf"
    from ilias_sync.storage import copy_file
    copy_file(version, restored)
    assert sha256(restored) == sha256(version)


def test_user_annotations_survive(tmp_path):
    raw, archive = setup(tmp_path)
    archive.publish("file:1", raw, "Course/lecture.pdf")
    target = tmp_path / "out/Course/lecture.pdf"
    target.write_bytes(b"MY ANNOTATIONS")
    raw.write_bytes(b"%PDF-1.4 updated")
    assert archive.publish("file:1", raw, "Course/lecture.pdf") == "conflict"
    assert target.read_bytes() == b"MY ANNOTATIONS"
    assert archive.publish("file:1", raw, "Course/lecture.pdf") == "unchanged"
    assert archive.manifest['files']['file:1']['path'] == 'Course/lecture (ILIAS).pdf'


def test_unmanaged_identical_file_is_not_adopted(tmp_path):
    raw, archive = setup(tmp_path)
    target = tmp_path / "out/Course/lecture.pdf"
    target.parent.mkdir()
    target.write_bytes(raw.read_bytes())
    assert archive.publish("file:1", raw, "Course/lecture.pdf") == "conflict"
    raw.write_bytes(b"remote update")
    archive.publish("file:1", raw, "Course/lecture.pdf")
    assert target.read_bytes() == b"%PDF-1.4 original"


def test_identical_objects_have_independent_ownership(tmp_path):
    raw, archive = setup(tmp_path)
    archive.publish("file:1", raw, "Course/lecture.pdf")
    assert archive.publish("file:2", raw, "Course/lecture.pdf") == "conflict"
    paths = [v["path"] for v in archive.manifest["files"].values()]
    assert len(set(paths)) == 2


def test_multiple_protected_downloads_use_readable_names_and_keep_unrelated_copies(tmp_path):
    raw, archive = setup(tmp_path)
    plain = tmp_path / 'out/Course/lecture.pdf'
    plain.parent.mkdir()
    plain.write_bytes(b'personal notes')
    occupied = plain.with_name('lecture (ILIAS).pdf')
    occupied.write_bytes(raw.read_bytes())
    assert archive.publish('file:1', raw, 'Course/lecture.pdf') == 'conflict'
    assert archive.manifest['files']['file:1']['path'] == 'Course/lecture (ILIAS 2).pdf'
    assert archive.publish('file:1', raw, 'Course/lecture.pdf') == 'unchanged'
    assert archive.publish('file:2', raw, 'Course/lecture.pdf') == 'conflict'
    assert archive.manifest['files']['file:2']['path'] == 'Course/lecture (ILIAS 3).pdf'
    assert plain.read_bytes() == b'personal notes'
    assert occupied.read_bytes() == raw.read_bytes()


def legacy_copy(tmp_path):
    import hashlib
    raw, archive = setup(tmp_path)
    name = 'Course/lecture [ILIAS ' + hashlib.sha256(b'file:1').hexdigest()[:8] + '-' + sha256(raw)[:8] + '].pdf'
    archive.publish('file:1', raw, name)
    return raw, archive, name


@pytest.mark.parametrize('plain_exists', [False, True])
def test_legacy_hash_copy_becomes_readable_without_adopting_an_existing_file(tmp_path, plain_exists):
    raw, archive, old = legacy_copy(tmp_path)
    plain = archive.destination / 'Course/lecture.pdf'
    if plain_exists:
        plain.write_bytes(raw.read_bytes())
    assert archive.publish('file:1', raw, 'Course/lecture.pdf') == 'unchanged'
    relative = 'Course/lecture (ILIAS).pdf' if plain_exists else 'Course/lecture.pdf'
    assert archive.manifest['files']['file:1']['path'] == relative
    assert not (archive.destination / old).exists()
    assert (archive.destination / relative).read_bytes() == raw.read_bytes()
    assert not archive.file_rename_path.exists()
    raw.write_bytes(b'updated server document')
    assert archive.publish('file:1', raw, 'Course/lecture.pdf') == 'updated'
    if plain_exists:
        assert plain.read_bytes() == b'%PDF-1.4 original'


def test_legacy_name_recovery_commits_metadata_before_removing_old_file(tmp_path, monkeypatch):
    from ilias_sync import storage
    raw, archive, old = legacy_copy(tmp_path)
    original = storage.write_json
    def interrupted(path, value):
        if path.name == 'manifest.json':
            raise OSError('interrupted name migration')
        original(path, value)
    monkeypatch.setattr(storage, 'write_json', interrupted)
    with pytest.raises(OSError, match='interrupted'):
        archive.publish('file:1', raw, 'Course/lecture.pdf')
    assert (archive.destination / old).is_file()
    assert (archive.destination / 'Course/lecture.pdf').is_file()
    monkeypatch.setattr(storage, 'write_json', original)
    restored = Archive(archive.state, archive.destination)
    assert restored.manifest['files']['file:1']['path'] == 'Course/lecture.pdf'
    assert not (archive.destination / old).exists()
    assert restored.publish('file:1', raw, 'Course/lecture.pdf') == 'unchanged'


def test_edited_legacy_copy_is_preserved_and_not_silently_moved(tmp_path):
    raw, archive, old = legacy_copy(tmp_path)
    path = archive.destination / old
    path.write_bytes(b'notes added to existing download')
    assert archive.publish('file:1', raw, 'Course/lecture.pdf') == 'conflict'
    assert path.read_bytes() == b'notes added to existing download'
    assert archive.manifest['files']['file:1']['path'] == 'Course/lecture (ILIAS).pdf'


def test_legacy_migration_does_not_take_missing_path_owned_by_another_object(tmp_path):
    raw, archive = setup(tmp_path)
    archive.publish('file:2', raw, 'Course/lecture.pdf')
    (archive.destination / 'Course/lecture.pdf').unlink()
    import hashlib
    old = 'Course/lecture [ILIAS ' + hashlib.sha256(b'file:1').hexdigest()[:8] + '-' + sha256(raw)[:8] + '].pdf'
    archive.publish('file:1', raw, old)
    archive.publish('file:1', raw, 'Course/lecture.pdf')
    assert archive.manifest['files']['file:1']['path'] == 'Course/lecture (ILIAS).pdf'
    assert archive.manifest['files']['file:2']['path'] == 'Course/lecture.pdf'


def test_crash_after_readable_conflict_publish_does_not_create_numbered_duplicates(tmp_path, monkeypatch):
    from ilias_sync import storage
    raw, archive = setup(tmp_path)
    plain = archive.destination / 'Course/lecture.pdf'
    plain.parent.mkdir()
    plain.write_bytes(b'personal copy')
    original = storage.write_json
    def interrupted(path, value):
        if path.name == 'manifest.json':
            raise OSError('interrupted publish')
        original(path, value)
    monkeypatch.setattr(storage, 'write_json', interrupted)
    with pytest.raises(OSError):
        archive.publish('file:1', raw, 'Course/lecture.pdf')
    monkeypatch.setattr(storage, 'write_json', original)
    restored = Archive(archive.state, archive.destination)
    assert restored.publish('file:1', raw, 'Course/lecture.pdf') == 'conflict'
    assert len(list(plain.parent.glob('*.pdf'))) == 2


def test_restart_after_publish_before_manifest(tmp_path, monkeypatch):
    raw, archive = setup(tmp_path)
    from ilias_sync import storage
    original = storage.write_json

    def interrupted(path, value):
        if path.name == "manifest.json":
            raise OSError("interrupted")
        original(path, value)
    monkeypatch.setattr(storage, "write_json", interrupted)
    with pytest.raises(OSError):
        archive.publish("file:1", raw, "Course/lecture.pdf")
    monkeypatch.setattr(storage, "write_json", original)
    restarted = Archive(tmp_path / "state", tmp_path / "out")
    assert restarted.publish("file:1", raw, "Course/lecture.pdf") == "unchanged"
    assert len(list((tmp_path / "out").rglob("*.pdf"))) == 1


@pytest.mark.parametrize("path", ["../escape", "/absolute", "C:/Windows/a", "folder/../../a", "folder//a", "folder/./a", "\\server\\a"])
def test_path_escape_rejected(tmp_path, path):
    with pytest.raises(ValueError):
        safe_path(tmp_path, path)


@pytest.mark.parametrize("name", ["CON", "nul.pdf", "COM1.txt", "lpt9", "a/b:c*d?e", "..", "x" * 300])
def test_portable_names(name):
    cleaned = clean_name(name)
    assert len(cleaned) <= 70
    assert not any(c in cleaned for c in '/\\:*?"<>|')
    assert cleaned not in {".", "..", ""}


def test_corrupt_history_stops_replacement(tmp_path):
    raw, archive = setup(tmp_path)
    archive.publish("file:1", raw, "Course/lecture.pdf")
    digest = sha256(raw)
    history = tmp_path / "out/Versions/Course/lecture.pdf" / (digest[:16] + ".pdf")
    history.parent.mkdir(parents=True)
    history.write_bytes(b"CORRUPT")
    raw.write_bytes(b"remote update")
    with pytest.raises(OSError):
        archive.publish("file:1", raw, "Course/lecture.pdf")
    assert (tmp_path / "out/Course/lecture.pdf").read_bytes() == b"%PDF-1.4 original"


def test_long_filename_keeps_extension_and_distinguishes_names():
    from ilias_sync.storage import clean_filename
    a = clean_filename("Vorlesung" * 40 + ".pdf")
    b = clean_filename("Vorlesung" * 40 + " Ende.pdf")
    assert a.endswith(".pdf")
    assert len(a) <= 100
    assert a != b
