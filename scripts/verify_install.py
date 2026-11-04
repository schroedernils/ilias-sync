"""Exercise the actual installer, installed runtime, upgrade and removal in CI."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ilias_sync import __version__  # noqa: E402


def runtime(binary, temporary):
    event = temporary / 'installed-self-test.jsonl'
    event.unlink(missing_ok=True)
    subprocess.run([str(binary), '--self-test', '--event-file', str(event)], check=True, timeout=90)
    result = json.loads(event.read_text(encoding='utf-8').strip())
    assert result['ok'] and result['version'] == __version__, result


def windows(temporary):
    import winreg
    installer = ROOT / f'dist/IliasSync-{__version__}-Windows-x64-Setup.exe'
    destination = temporary / 'Installed App'
    command = [str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
               f'/DIR={destination}', f'/LOG={temporary / "setup.log"}']
    binary = destination / 'IliasSync.exe'
    shortcut = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/IliasSync.lnk'
    key_name = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8669D68D-2240-4B64-81E1-40357B3A35BE}_is1'
    assert subprocess.run(['schtasks', '/Query', '/TN', 'IliasSync'], capture_output=True).returncode != 0, 'Existing task must not be overwritten'
    try:
        for _ in range(2):
            subprocess.run(command, check=True, timeout=180)
            assert shortcut.is_file()
            assert (destination / '_internal/python312.dll').is_file()
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
                assert winreg.QueryValueEx(key, 'DisplayVersion')[0] == __version__
            runtime(binary, temporary)
            subprocess.run(['schtasks', '/Delete', '/TN', 'IliasSync', '/F'], capture_output=True)
            for expected in (True, False):
                event = temporary / 'schedule-check.jsonl'
                event.unlink(missing_ok=True)
                subprocess.run([str(binary), '--repair-schedule', '--event-file', str(event)], check=True, timeout=60)
                result = json.loads(event.read_text(encoding='utf-8').strip())
                assert result['ok'] and result['repaired'] is expected, result
    finally:
        subprocess.run(['schtasks', '/Delete', '/TN', 'IliasSync', '/F'], capture_output=True)
        uninstaller = destination / 'unins000.exe'
        if uninstaller.exists():
            subprocess.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'],
                           check=True, timeout=180)
            deadline = time.monotonic() + 30
            while binary.exists() and time.monotonic() < deadline:
                time.sleep(0.2)
    assert not binary.exists() and not shortcut.exists()
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name).Close()
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('Windows uninstall registration remains')


def linux(temporary):
    package = ROOT / f'dist/IliasSync-{__version__}-Linux-x64.deb'
    binary = Path('/usr/bin/ilias-sync')
    desktop = Path('/usr/share/applications/org.iliassync.desktop.desktop')
    try:
        for _ in range(2):
            subprocess.run(['sudo', 'apt-get', 'install', '-y', '--reinstall', '--no-install-recommends', str(package)],
                           check=True, timeout=180)
            assert binary.resolve() == Path('/opt/iliassync/IliasSync')
            assert desktop.is_file()
            subprocess.run(['desktop-file-validate', str(desktop)], check=True)
            runtime(binary, temporary)
    finally:
        subprocess.run(['sudo', 'apt-get', 'remove', '-y', 'iliassync'], check=True, timeout=90)
    assert not binary.exists() and not desktop.exists()


def main():
    if not os.environ.get('CI'):
        raise RuntimeError('Installer verification changes installed applications; run only in disposable CI runners.')
    if sys.platform not in {'win32', 'linux'}:
        print('Native installer round-trip applies to Windows and Linux; DMG runtime is checked during packaging.')
        return
    with tempfile.TemporaryDirectory(prefix='ilias-installed-') as temporary:
        temporary = Path(temporary)
        data = temporary / 'user-data'
        data.mkdir()
        sentinel = data / 'retained-material.pdf'
        sentinel.write_bytes(b'%PDF-1.4 user data must survive installation and removal')
        settings = data / 'settings.json'
        calendar = json.dumps({'schema': 1, 'sources': [], 'scheduled': True, 'interval_hours': 6,
                              'schedule_mode': 'weekly', 'weekly_times': {'0': ['10:30'], '4': ['09:40', '13:50']}}).encode()
        settings.write_bytes(calendar)
        os.environ['ILIAS_SYNC_DATA_DIR'] = str(data)
        (windows if sys.platform == 'win32' else linux)(temporary)
        assert sentinel.read_bytes() == b'%PDF-1.4 user data must survive installation and removal'
        assert settings.read_bytes() == calendar, 'Saved weekly schedule was changed by installation or removal'
    print('Installed runtime, reinstall and uninstall verified; weekly schedule and user data retained.')


if __name__ == '__main__':
    main()
