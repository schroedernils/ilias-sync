"""Private application state; completed files only are published to the chosen destination."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from copy import deepcopy
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from platformdirs import user_data_path


def data_dir() -> Path:
    override = os.environ.get("ILIAS_SYNC_DATA_DIR")
    root = Path(override) if override else user_data_path("IliasSync", "IliasSync", roaming=False)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def write_json(path: Path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def record_attempt(state: Path, status, previous):
    """Keep attempt outcomes distinct from the last fully successful check."""
    from .build_info import build_info
    status['build'] = build_info()['id']
    result = status.get('result') or {}
    success = status.get('state') == 'Up to date' and not any(
        result.get(key) for key in ('partial', 'warnings', 'errors', 'unavailable'))
    same_scope = not status.get('scope') or status.get('scope') == previous.get('scope')
    last_success = previous.get('last_success') if same_scope else None
    old_result = previous.get('result') or {}
    if same_scope and not last_success and previous.get('state') == 'Up to date' and not any(
            old_result.get(key) for key in ('partial', 'warnings', 'errors', 'unavailable')):
        last_success = previous.get('finished')
    status['last_success'] = status.get('finished') if success else last_success
    write_json(state / 'status.json', status)
    history = read_json(state / 'history.json', [])
    write_json(state / 'history.json', [status, *history][:20])
    # Notification bookkeeping cannot turn a completed sync into a failure.
    try:
        from .notifications import observe_attempt
        observe_attempt(state, status, deliver=True)
    except Exception:
        pass


def source_scope(source):
    value = asdict(source)
    value.pop('enabled', None)
    value.pop('name', None)
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def atomic_write(path: Path, value: bytes):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".sync-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(value)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def server_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parts = urlparse(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("Enter the HTTPS address of your ILIAS installation, without credentials.")
    if parts.query or parts.fragment:
        raise ValueError("Use the installation address, without a query or fragment.")
    return value


def clean_name(text: str, limit=70):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r'[\x00-\x1f<>:"/\\|?*]', " ", text)
    text = re.sub(r"[_\s]+", " ", text).strip(" .")
    if not text or text in (".", ".."):
        text = "Untitled"
    if re.match(r"(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", text):
        text = "_" + text
    if len(text) > limit:
        digest = hashlib.sha256(text.encode()).hexdigest()[:7]
        text = text[:limit - 9].rstrip() + "~" + digest
    return text


def clean_filename(text: str, limit=100):
    suffix = Path(text).suffix
    if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", suffix):
        suffix = ""
    if suffix:
        return clean_name(text[:-len(suffix)], limit - len(suffix)) + suffix
    return clean_name(text, limit)


def safe_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    parts = relative.replace("\\", "/").split("/")
    if not parts or any(p in ("", ".", "..") for p in parts) or relative.startswith(("/", "\\")):
        raise ValueError("Unsafe archive path.")
    if ":" in parts[0]:
        raise ValueError("Absolute paths are not allowed.")
    target = root.joinpath(*parts)
    current = target
    while current != root:
        if current.is_symlink():
            raise ValueError("A symbolic link is present in the destination path.")
        current = current.parent
    if not target.resolve().is_relative_to(root):
        raise ValueError("Archive path escapes its destination.")
    return target


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def copy_file(source: Path, target: Path, *, replace=False):
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".sync-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out, source.open("rb") as inp:
            shutil.copyfileobj(inp, out)
            out.flush()
            os.fsync(out.fileno())
        if sha256(Path(name)) != sha256(source):
            raise OSError("Copied file failed its integrity check.")
        if replace:
            os.replace(name, target)
        else:
            # Same-filesystem exclusive publish, so an unrelated file is never replaced.
            os.link(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@dataclass
class Source:
    name: str
    url: str
    destination: str
    username: str = ""
    client_id: str = ""
    login: str = "local"
    idp_host: str = ""
    automatic_courses: bool = True
    targets: list[str] = field(default_factory=list)
    videos: bool = False
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))
    folder_rules: dict[str, str] = field(default_factory=dict)
    include_course_ids: bool = False
    folder_names: dict[str, str] = field(default_factory=dict)

    def validate(self):
        from .routing import validate_routes
        validate_routes(self.folder_rules)
        from .naming import validate_names
        validate_names(self.folder_names)
        if not isinstance(self.include_course_ids, bool):
            raise ValueError('Invalid folder naming settings.')
        UUID(self.id)
        self.url = server_url(self.url)
        if self.login not in {"local", "shibboleth", "session"}:
            raise ValueError("Unsupported sign-in method.")
        if not self.name.strip():
            raise ValueError("Give this source a name.")
        destination = Path(self.destination).expanduser()
        if not destination.is_absolute():
            raise ValueError("Choose an absolute destination folder.")
        if destination.resolve().is_relative_to(data_dir().resolve()) or data_dir().resolve().is_relative_to(destination.resolve()):
            raise ValueError("Choose a dedicated download folder outside application data.")
        self.destination = str(destination)
        if self.login == "local" and not self.client_id:
            raise ValueError("Detect or enter the ILIAS client ID first.")
        if self.login == "shibboleth" and not re.fullmatch(r"[A-Za-z0-9.-]+", self.idp_host):
            raise ValueError("Enter the trusted identity-provider hostname for SSO.")
        if not self.automatic_courses and not self.targets:
            raise ValueError("Select at least one course or folder, or enable course discovery.")


class Settings:
    def __init__(self):
        self.root = data_dir()
        self.path = self.root / "settings.json"
        self.value = read_json(self.path, {"schema": 1, "sources": [], "interval_hours": 6,
                                          "battery_saver": True, "scheduled": False, "language": "de", "appearance": "system"})
        if self.value.get("schema") != 1:
            raise ValueError("This configuration was created by an incompatible app version.")
        self.value.setdefault('schedule_mode', 'interval')
        self.value.setdefault('sync_times', [])
        self.value.setdefault('weekly_times', {})

    def sources(self):
        return [Source(**s) for s in self.value["sources"]]

    def validate_source(self, source: Source):
        source.validate()
        for other in self.sources():
            if other.id != source.id:
                a, b = Path(other.destination).resolve(), Path(source.destination).resolve()
                if a == b or a.is_relative_to(b) or b.is_relative_to(a):
                    raise ValueError("Each source needs its own non-overlapping download folder.")

    def save_source(self, source: Source):
        self.validate_source(source)
        previous = deepcopy(self.value)
        self.value["sources"] = [asdict(source) if s["id"] == source.id else s for s in self.value["sources"]]
        if not any(s["id"] == source.id for s in self.value["sources"]):
            self.value["sources"].append(asdict(source))
        try:
            self.save()
        except Exception:
            self.value = previous
            raise

    def save(self):
        write_json(self.path, self.value)


class FolderCollisionError(ValueError):
    """A safe, actionable conflict; retrying cannot resolve it by itself."""


class Archive:
    def __init__(self, state: Path, destination: Path):
        self.state = state
        self.destination = destination
        destination.mkdir(parents=True, exist_ok=True)
        self.path = state / "manifest.json"
        self.manifest = read_json(self.path, {"schema": 1, "files": {}})
        self.journal_path = state / "publish-intents.json"
        self.journal = read_json(self.journal_path, {})
        self.rename_path = state / 'folder-rename.json'
        pending = read_json(self.rename_path, None)
        if pending:
            self._finish_folder_rename(pending)

    def rename_folder(self, root, old, new):
        if old == new:
            return
        before, after = safe_path(Path(root), old), safe_path(Path(root), new)
        if not before.exists():
            return
        if not before.is_dir() or after.exists():
            raise FolderCollisionError('A folder with this name already exists. Choose another name.')
        pending = {'root': str(Path(root).resolve()), 'old': old, 'new': new}
        write_json(self.rename_path, pending)
        self._finish_folder_rename(pending)

    def _finish_folder_rename(self, pending):
        root, old, new = Path(pending['root']), pending['old'], pending['new']
        before, after = safe_path(root, old), safe_path(root, new)
        if before.exists():
            if after.exists():
                self.rename_path.unlink(missing_ok=True)
                raise FolderCollisionError('A folder with this name already exists. Choose another name.')
            after.parent.mkdir(parents=True, exist_ok=True)
            before.rename(after)
        elif not after.is_dir():
            raise OSError('The folder rename could not be recovered.')
        for entry in self.manifest['files'].values():
            if Path(entry.get('root', self.destination)).resolve() != root.resolve():
                continue
            for field_name in ('path', 'original_path'):
                relative = entry.get(field_name, '')
                if relative.startswith(old + '/'):
                    entry[field_name] = new + relative[len(old):]
        for entry in self.journal.values():
            if Path(entry.get('root', self.destination)).resolve() == root.resolve() and entry['path'].startswith(old + '/'):
                entry['path'] = new + entry['path'][len(old):]
        write_json(self.path, self.manifest)
        write_json(self.journal_path, self.journal)
        self.rename_path.unlink(missing_ok=True)

    def publish(self, identity: str, raw: Path, proposed: str, *, destination=None, route='', metadata=None):
        original_destination = self.destination
        old = self.manifest["files"].get(identity)
        self.destination = Path(destination) if destination else original_destination
        self.destination.mkdir(parents=True, exist_ok=True)
        # A changed explicit rule publishes a new safe copy. Never delete old or annotated files.
        moved = old and (old.get('route', '') != route or
                         Path(old.get('root', str(original_destination))).resolve() != self.destination.resolve())
        if moved:
            del self.manifest['files'][identity]
        self._publication_metadata = {'root':str(self.destination.resolve()), 'route':route, **(metadata or {})}
        if moved:
            self._publication_metadata['prior_locations'] = [*old.get('prior_locations', []),
                                                              {'root':old.get('root',str(original_destination)), 'path':old['path']}]
        try:
            action = self._publish(identity, raw, proposed)
            entry = self.manifest['files'][identity]
            changes = {key: value for key, value in self._publication_metadata.items() if entry.get(key) != value}
            if changes:
                entry.update(changes)
                write_json(self.path, self.manifest)
            return action
        except BaseException:
            if moved:
                self.manifest['files'][identity] = old
            raise
        finally:
            self.destination = original_destination

    def _publish(self, identity: str, raw: Path, proposed: str):
        old = self.manifest["files"].get(identity)
        relative = old["path"] if old else proposed
        target = safe_path(self.destination, relative)
        raw_stat = [raw.stat().st_size, raw.stat().st_mtime_ns]
        if old and raw_stat == old.get("raw_stat") and target.is_file():
            stat = [target.stat().st_size, target.stat().st_mtime_ns]
            if stat == old.get("target_stat"):
                return "unchanged"
        digest = sha256(raw)
        action = "added"
        if target.exists():
            actual = sha256(target)
            owned = old is not None or self.journal.get(identity) == {"path": relative, "sha256": digest, "root": str(self.destination.resolve())}
            if actual == digest and owned:
                action = "unchanged"
            elif old and actual == old["sha256"]:
                history = safe_path(self.destination, "Versions/" + relative + "/" + actual[:16] + target.suffix)
                if not history.exists():
                    copy_file(target, history)
                elif sha256(history) != actual:
                    raise OSError("An archived version is corrupt. No file was replaced.")
                copy_file(raw, target, replace=True)
                action = "updated"
            else:
                marker = hashlib.sha256(identity.encode()).hexdigest()[:8]
                target = target.with_name(f"{target.stem} [ILIAS {marker}-{digest[:8]}]{target.suffix}")
                relative = target.relative_to(self.destination.resolve()).as_posix()
                action = "conflict"
                if not target.exists():
                    self._intent(identity, relative, digest)
                    copy_file(raw, target)
                elif sha256(target) != digest:
                    raise OSError("A conflict copy has unexpected contents.")
        else:
            self._intent(identity, relative, digest)
            copy_file(raw, target)
        self.manifest["files"][identity] = {**(old or {}), **self._publication_metadata, "path": relative, "sha256": digest, "raw_stat": raw_stat,
                                           "target_stat": [target.stat().st_size, target.stat().st_mtime_ns]}
        if action != 'unchanged':
            self.manifest['files'][identity].update(changed_at=time.time(), change=action)
        write_json(self.path, self.manifest)
        return action

    def _intent(self, identity, path, digest):
        self.journal[identity] = {"path": path, "sha256": digest, "root": str(self.destination.resolve())}
        write_json(self.journal_path, self.journal)
