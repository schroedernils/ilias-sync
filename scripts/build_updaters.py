"""Pin native update libraries and embed only the public verification key."""
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / 'build/updaters'
RELEASES = 'https://github.com/schroedernils/ilias-sync/releases'
SPARKLE = ('https://github.com/sparkle-project/Sparkle/releases/download/2.10.1/Sparkle-2.10.1.tar.xz',
           '1a856d2a9edb8e628de88121d7be04cf0e2167f8641650b78fca00b14244cf27')
WINSPARKLE = ('https://github.com/vslavik/winsparkle/releases/download/v0.9.4/WinSparkle-0.9.4.zip',
              '6037df37fc263bd1650a1c4949681a9d40ffe991d01f35892a406cb5d103c976')


def public_key():
    value = (ROOT / 'updates/public-key.txt').read_text().strip()
    decoded = base64.b64decode(value, validate=True)
    if len(decoded) != 32 or not any(decoded):
        raise ValueError('A valid production Ed25519 public key is required to package updates.')
    return value


def sdk_archive(spec):
    url, expected = spec
    SDK.mkdir(parents=True, exist_ok=True)
    target = SDK / url.rsplit('/', 1)[1]
    if not target.exists():
        part = target.with_suffix(target.suffix + '.part')
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'IliasSync-build'})
            with urllib.request.urlopen(request, timeout=90) as source, part.open('wb') as out:
                size = 0
                while block := source.read(1024 * 1024):
                    size += len(block)
                    if size > 100 * 1024 * 1024:
                        raise ValueError('Updater SDK exceeds the allowed archive size.')
                    out.write(block)
            part.replace(target)
        finally:
            part.unlink(missing_ok=True)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise ValueError('Native updater SDK checksum mismatch.')
    return target


def prepare():
    key = public_key()
    config = {'public_key': key, 'releases': RELEASES}
    (ROOT / 'src/ilias_sync/assets/update-config.json').write_text(json.dumps(config) + '\n')
    native = ROOT / 'src/ilias_sync/assets/native'
    native.mkdir(parents=True, exist_ok=True)
    notices = ROOT / 'build/updater-notices'
    notices.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'darwin':
        archive = sdk_archive(SPARKLE)
        sdk = SDK / 'sparkle'
        if sdk.exists():
            shutil.rmtree(sdk)
        with tarfile.open(archive) as packed:
            packed.extractall(sdk, filter='data')
        subprocess.run(['xcrun', 'clang++', '-dynamiclib', '-std=c++17', '-fobjc-arc',
                        '-mmacosx-version-min=13.0', '-framework', 'AppKit', '-framework', 'Foundation',
                        '-F' + str(sdk), '-framework', 'Sparkle',
                        '-Wl,-rpath,@executable_path/../Frameworks', '-Wl,-rpath,@loader_path/../../..',
                        '-o', str(native / 'libilias_updates.dylib'),
                        str(ROOT / 'src/ilias_sync/native/updates.mm')], check=True)
        shutil.copy2(sdk / 'LICENSE', notices / 'Sparkle-LICENSE.txt')
    elif sys.platform == 'win32':
        archive = sdk_archive(WINSPARKLE)
        sdk = SDK / 'winsparkle'
        if sdk.exists():
            shutil.rmtree(sdk)
        with zipfile.ZipFile(archive) as packed:
            packed.extractall(sdk)
        library = sdk / 'WinSparkle-0.9.4'
        shutil.copy2(library / 'x64/Release/WinSparkle.dll', native / 'WinSparkle.dll')
        for path in library.glob('COPYING*'):
            shutil.copy2(path, notices / ('WinSparkle-' + path.name))
    return config


def embed(app, arch, key):
    """Called after freezing, before the final app signature and DMG creation."""
    framework = app / 'Contents/Frameworks/Sparkle.framework'
    shutil.copytree(SDK / 'sparkle/Sparkle.framework', framework, symlinks=True)
    # PyInstaller normalizes dynamic-library dependencies to their basename.
    # Sparkle must retain its framework layout for its XPC services/resources.
    bridge = app / 'Contents/Frameworks/ilias_sync/assets/native/libilias_updates.dylib'
    subprocess.run(['install_name_tool', '-change', '@rpath/Sparkle',
                    '@rpath/Sparkle.framework/Versions/B/Sparkle', str(bridge)], check=True)
    import plistlib
    path = app / 'Contents/Info.plist'
    info = plistlib.loads(path.read_bytes())
    info.update(SUFeedURL=RELEASES + f'/latest/download/macOS-{arch}.xml', SUPublicEDKey=key,
                SUEnableSystemProfiling=False, SUAutomaticallyUpdate=False,
                SUVerifyUpdateBeforeExtraction=True, SURequireSignedFeed=True, LSMinimumSystemVersion='13.0')
    # Sparkle's native consent prompt owns the opt-in; do not enable checks by default.
    info.pop('SUEnableAutomaticChecks', None)
    path.write_bytes(plistlib.dumps(info))


if __name__ == '__main__':
    prepare()
