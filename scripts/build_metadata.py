"""Identify a local preview without including paths, account data or Git credentials."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess


def metadata(root: Path, version: str):
    digest = hashlib.sha256()
    paths = [root/'pyproject.toml', *root.joinpath('src/ilias_sync').rglob('*'), *root.joinpath('scripts').glob('*.py')]
    for path in sorted(set(paths)):
        if path.is_file() and path.suffix in {'.py', '.mm', '.toml', '.svg', '.png', '.icns'}:
            digest.update(path.relative_to(root).as_posix().encode() + b'\0' + path.read_bytes())
    try:
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=normal','--','src','scripts','pyproject.toml'],cwd=root,text=True))
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = 'source', True
    fingerprint = digest.hexdigest()
    return {'id':revision[:12]+'-'+fingerprint[:12], 'revision':revision, 'source_sha256':fingerprint,
            'dirty':dirty, 'version':version, 'built_at':datetime.now(timezone.utc).isoformat()}
