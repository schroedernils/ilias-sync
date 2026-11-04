"""Inspect the generated package layout before the native CI install round-trip."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installers', ROOT / 'scripts/installers.py')
installers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installers)


@pytest.mark.skipif(__import__('sys').platform == 'win32', reason='POSIX package layout')
@pytest.mark.parametrize('architecture', ['amd64', 'arm64'])
def test_debian_payload_retains_runtime_and_has_a_stable_desktop_entry(tmp_path, architecture):
    root = tmp_path / 'root'
    payload = root / 'dist/IliasSync'
    internal = payload / '_internal'
    internal.mkdir(parents=True)
    binary = payload / 'IliasSync'
    binary.write_bytes(b'executable fixture')
    binary.chmod(0o755)
    (internal / 'libpython3.12.so').write_bytes(b'runtime fixture')
    (payload / 'IliasSync.png').write_bytes(b'icon fixture')
    (root / 'LICENSE').write_text('GPL-3.0-or-later')
    stage = tmp_path / 'package'
    installers.stage_debian(root, stage, '1.2.3', architecture)
    assert (stage / 'opt/iliassync/IliasSync').read_bytes() == binary.read_bytes()
    assert (stage / 'opt/iliassync/IliasSync').stat().st_mode & 0o111
    assert (stage / 'opt/iliassync/_internal/libpython3.12.so').read_bytes() == b'runtime fixture'
    assert (stage / 'usr/bin/ilias-sync').readlink() == Path('/opt/iliassync/IliasSync')
    desktop = (stage / 'usr/share/applications/org.iliassync.desktop.desktop').read_text()
    assert 'Exec=ilias-sync\n' in desktop
    assert 'Icon=org.iliassync.desktop\n' in desktop
    assert (stage / 'usr/share/icons/hicolor/256x256/apps/org.iliassync.desktop.png').read_bytes() == b'icon fixture'
    control = (stage / 'DEBIAN/control').read_text()
    assert f'Architecture: {architecture}\n' in control
    assert 'Version: 1.2.3\n' in control
    assert 'libc6 (>= 2.35)' in control and 'libxcb-cursor0' in control
    assert not (stage / 'home').exists() and not (stage / 'etc').exists()


def test_unsupported_debian_architecture_is_rejected_before_staging(tmp_path):
    with pytest.raises(ValueError, match='Unsupported Debian architecture'):
        installers.stage_debian(tmp_path, tmp_path / 'package', '1.2.3', 'i386')
    assert not (tmp_path / 'package').exists()
