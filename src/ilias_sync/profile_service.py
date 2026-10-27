"""Validate profiles before credential side effects; restore failed saves."""
from copy import deepcopy
from pathlib import Path
import tempfile

from filelock import FileLock, Timeout

from .storage import atomic_write, data_dir


def commit_profile(settings, source, *, password='', session='', store, import_cookies):
    from .security import SERVICE, vault, forget_password
    settings.validate_source(source)
    # A scheduled worker must not observe a partly committed profile/vault pair.
    lock = FileLock(data_dir() / 'sync.lock', timeout=0)
    try:
        lock.acquire()
    except Timeout:
        raise RuntimeError('Let the current sync finish before changing settings.') from None
    previous = deepcopy(settings.value)
    config_existed = settings.path.exists()
    cookies = data_dir() / 'sources' / source.id / 'cache/.cookies'
    old_cookies = cookies.read_bytes() if session and cookies.exists() else None
    exists = any(row.id == source.id for row in settings.sources())
    old_password = None
    credential_attempted = False
    try:
        if password and exists:
            old_password = vault().get_password(SERVICE, source.id)
        with tempfile.TemporaryDirectory(prefix='ilias-profile-', dir=settings.root) as temporary:
            staged = Path(temporary) / 'cookies'
            if session:
                import_cookies(Path(session), source.url, staged)
            settings.save_source(source)
            if session:
                atomic_write(cookies, staged.read_bytes())
            if password:
                credential_attempted = True
                store(source.id, password)
    except Exception:
        settings.value = previous
        if config_existed:
            settings.save()
        else:
            settings.path.unlink(missing_ok=True)
        if session:
            if old_cookies is not None:
                atomic_write(cookies, old_cookies)
            else:
                cookies.unlink(missing_ok=True)
        if credential_attempted:
            try:
                store(source.id, old_password) if old_password is not None else forget_password(source.id)
            except Exception:
                raise RuntimeError('Credential storage failed. Check the saved sign-in details before syncing again.') from None
        raise
    finally:
        lock.release()
