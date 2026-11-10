"""Exercise native signed-update downloads using disposable keys and hosts only."""
from contextlib import contextmanager
from functools import partial
import base64
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from ilias_sync import __version__  # noqa: E402
from update_feeds import _signed_appcast, SPARKLE_NAMESPACE  # noqa: E402


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextmanager
def server(root):
    service = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
    thread = threading.Thread(target=service.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{service.server_port}'
    finally:
        service.shutdown()
        service.server_close()
        thread.join(timeout=3)


def feed(root, key, base, package, version, *, mac=False):
    rss = ET.Element('rss', version='2.0')
    item = ET.SubElement(ET.SubElement(rss, 'channel'), 'item')
    ET.SubElement(item, f'{{{SPARKLE_NAMESPACE}}}version').text = version
    ET.SubElement(item, 'title').text = 'Disposable signed integration-test update'
    ET.SubElement(item, 'enclosure', {
        'url': base + '/' + package.name, 'length': str(package.stat().st_size),
        'type': 'application/octet-stream',
        f'{{{SPARKLE_NAMESPACE}}}edSignature': base64.b64encode(key.sign(package.read_bytes())).decode(),
    })
    data = ET.tostring(rss, encoding='utf-8', xml_declaration=True) + b'\n'
    (root / 'feed.xml').write_bytes(_signed_appcast(key, data) if mac else data)


def macos(root, key):
    sdk = ROOT / 'build/updaters/sparkle'
    current = ROOT / 'dist/IliasSync.app'
    old = root / 'Installed/IliasSync.app'
    new = root / 'Payload/IliasSync.app'
    identifier = 'org.iliassync.update-probe-' + uuid.uuid4().hex
    public = base64.b64encode(key.public_key().public_bytes_raw()).decode()
    log = root / 'probe.log'
    log.write_text('')
    for app in (old, new):
        app.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(current, app, symlinks=True)
    with server(root) as base:
        for app in (old, new):
            path = app / 'Contents/Info.plist'
            info = plistlib.loads(path.read_bytes())
            info.update(CFBundleIdentifier=identifier, SUPublicEDKey=public, SUEnableAutomaticChecks=False,
                        SUFeedURL=base + '/feed.xml', SUAutomaticallyUpdate=False,
                        SUVerifyUpdateBeforeExtraction=True, SURequireSignedFeed=True)
            # Loopback HTTP is confined to this disposable probe bundle, never production.
            info['NSAppTransportSecurity'] = {'NSAllowsArbitraryLoads': True}
            if app == old:
                info.update(CFBundleVersion='0.0.1', CFBundleShortVersionString='0.0.1', CFBundleExecutable='UpdateProbe')
            path.write_bytes(plistlib.dumps(info))
        executable = old / 'Contents/MacOS/UpdateProbe'
        subprocess.run(['xcrun', 'clang++', '-std=c++17', '-fobjc-arc', '-mmacosx-version-min=13.0', '-framework', 'AppKit',
                        '-I', str(ROOT / 'src/ilias_sync/native'),
                        '-F' + str(sdk), '-framework', 'Sparkle', '-Wl,-rpath,@executable_path/../Frameworks',
                        '-o', str(executable), str(ROOT / 'tests/native/update_install_probe.mm')], check=True)
        for app in (old, new):
            subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
        package = root / 'update.dmg'
        subprocess.run(['hdiutil', 'create', '-volname', 'IliasSync Update Probe', '-srcfolder', str(new.parent),
                        '-format', 'UDZO', str(package)], check=True)
        feed(root, key, base, package, __version__, mac=True)
        env = {**os.environ, 'ILIAS_UPDATE_PROBE_LOG': str(log), 'ILIAS_SYNC_DATA_DIR': str(root / 'user-data')}
        worker = subprocess.Popen([str(executable)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            assert worker.wait(timeout=150) == 0, log.read_text()
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                try:
                    info = plistlib.loads((old / 'Contents/Info.plist').read_bytes())
                    if info['CFBundleVersion'] == __version__:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError('Sparkle failed to install update: ' + log.read_text())
            steps = log.read_text()
            assert 'ERROR' not in steps and 'clicked native Install Update' in steps and 'clicked native Install and Relaunch' in steps, steps
            subprocess.run([str(old / 'Contents/MacOS/IliasSync'), '--self-test'], env=env, check=True, timeout=90)
            print('Native Sparkle buttons, signed DMG download and app replacement passed.')
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=10)
            if worker.stdout:
                print(worker.stdout.read().decode(errors='replace')[-3000:])
            print(log.read_text())


def windows(root, key):
    import ctypes
    import winreg
    package = root / 'update.exe'
    shutil.copy2(ROOT / f'dist/IliasSync-{__version__}-Windows-x64-Setup.exe', package)
    expected = hashlib.sha256(package.read_bytes()).hexdigest()
    target = root / 'Installed App'
    registry = 'Software\\IliasSync\\UpdateProbe-' + uuid.uuid4().hex
    library = ctypes.CDLL(str(ROOT / 'src/ilias_sync/assets/native/WinSparkle.dll'))
    callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_wchar_p)
    error_callback = ctypes.CFUNCTYPE(None)
    done = threading.Event()
    outcome = []

    def install(path):
        try:
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
            subprocess.run([path, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
                            f'/DIR={target}'], check=True, timeout=180)
            outcome.append('installed verified Setup')
        except Exception as error:
            outcome.append(str(error))
        finally:
            done.set()
        return 1

    def failed():
        outcome.append('WinSparkle update error')
        done.set()

    install_hook, error_hook = callback(install), error_callback(failed)
    with server(root) as base:
        feed(root, key, base, package, __version__)
        for name in ('set_appcast_url', 'set_eddsa_public_key', 'set_registry_path'):
            getattr(library, 'win_sparkle_' + name).argtypes = [ctypes.c_char_p]
        library.win_sparkle_set_app_details.argtypes = [ctypes.c_wchar_p] * 3
        library.win_sparkle_set_user_run_installer_callback.argtypes = [callback]
        library.win_sparkle_set_error_callback.argtypes = [error_callback]
        library.win_sparkle_set_app_details('IliasSync test', 'IliasSync', '0.0.1')
        library.win_sparkle_set_registry_path(registry.encode())
        library.win_sparkle_set_appcast_url((base + '/feed.xml').encode())
        assert library.win_sparkle_set_eddsa_public_key(base64.b64encode(key.public_key().public_bytes_raw()))
        library.win_sparkle_set_automatic_check_for_updates(0)
        library.win_sparkle_set_user_run_installer_callback(install_hook)
        library.win_sparkle_set_error_callback(error_hook)
        try:
            library.win_sparkle_init()
            library.win_sparkle_check_update_with_ui_and_install()
            assert done.wait(240), 'WinSparkle signed-update installation timed out'
            assert outcome == ['installed verified Setup'], outcome
            subprocess.run([str(target / 'IliasSync.exe'), '--self-test'], check=True, timeout=90)
            print('Native WinSparkle download, Ed25519 verification and Setup handoff passed.')
        finally:
            library.win_sparkle_cleanup()
            uninstall = target / 'unins000.exe'
            if uninstall.exists():
                subprocess.run([str(uninstall), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], check=True, timeout=180)
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, registry + '\\WinSparkle')
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, registry)
            except FileNotFoundError:
                pass


def linux(root, key):
    from ilias_sync.linux_updates import LinuxRelease, _verify_package
    package = ROOT / f'dist/IliasSync-{__version__}-Linux-x64.deb'
    content = package.read_bytes()
    release = LinuxRelease(__version__, 'unused', package.name, len(content), hashlib.sha256(content).hexdigest(),
                           base64.b64encode(key.sign(content)).decode(), 'unused')
    _verify_package(package, release, key.public_key().public_bytes_raw())
    print('Built Linux DEB verified with size, SHA-256 and Ed25519; native install round-trip is checked separately.')


def main():
    if os.environ.get('CI') != 'true':
        raise RuntimeError('Native update installation probes run only on disposable CI runners.')
    with tempfile.TemporaryDirectory(prefix='ilias-updater-integration-') as folder:
        root = Path(folder)
        {'darwin': macos, 'win32': windows, 'linux': linux}[sys.platform](root, Ed25519PrivateKey.generate())


if __name__ == '__main__':
    main()
