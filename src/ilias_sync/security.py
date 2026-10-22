"""Credentials only in an OS-backed vault. Never silently fall back to a plaintext backend."""
import http.cookiejar
from pathlib import Path
from urllib.parse import urlparse

SERVICE = "org.iliassync.desktop"


class LoginRequired(RuntimeError):
    pass


def vault():
    import keyring
    backend = keyring.get_keyring()
    candidates = getattr(backend, "backends", [backend])
    for item in candidates:
        module = type(item).__module__
        if module.startswith(("keyring.backends.macOS", "keyring.backends.Windows", "keyring.backends.SecretService",
                              "keyring.backends.kwallet")):
            return item
    raise LoginRequired("No secure credential store is available. On Linux, unlock a Secret Service or KWallet vault.")


def store_password(source_id, password):
    vault().set_password(SERVICE, source_id, password)


def get_password(source_id):
    password = vault().get_password(SERVICE, source_id)
    if not password:
        raise LoginRequired("Sign in again. No password is stored for this source.")
    return password


def forget_password(source_id):
    backend = vault()
    if backend.get_password(SERVICE, source_id):
        backend.delete_password(SERVICE, source_id)


def import_session(file: Path, url: str, destination: Path):
    """Read Netscape cookies exported by the user; ignore unrelated cookies and never evaluate code."""
    if file.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Cookie file is unexpectedly large.")
    jar = http.cookiejar.MozillaCookieJar(str(file))
    jar.load(ignore_discard=True, ignore_expires=False)
    host = urlparse(url).hostname
    lines = []
    for cookie in jar:
        domain = cookie.domain.lstrip(".")
        if cookie.is_expired() or not (host == domain or (cookie.domain_initial_dot and host.endswith("." + domain))):
            continue
        # PFERD only loads Set-Cookie lines. Drop non-session data and reject header injection.
        if any(c in cookie.name + cookie.value for c in "\r\n;"):
            raise ValueError("Invalid cookie format.")
        lines.append(f"Set-Cookie: {cookie.name}={cookie.value}; Domain={cookie.domain}; Path={cookie.path}; Secure")
    if not lines:
        raise ValueError("No unexpired cookies for this ILIAS host were found.")
    from .storage import atomic_write
    atomic_write(destination, ("\n".join(lines) + "\n").encode())
    return len(lines)
