
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
