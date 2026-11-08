"""Native on-directory packages with replaceable Qt libraries, notices and SHA-256."""
import hashlib
import importlib.metadata
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from icon_assets import windows_icon

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault("PYINSTALLER_CONFIG_DIR", str(ROOT / "build/pyinstaller-cache"))
sys.path.insert(0, str(ROOT / "src"))
from ilias_sync import __version__  # noqa: E402


def notices():
    output = ROOT / "build/notices"
    output.mkdir(parents=True, exist_ok=True)
    versions = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        versions[name] = dist.version
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ("license", "copying", "copyright", "notice")):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = output / name / str(file).replace("../", "").replace("..\\", "")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    (output / "versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "README.md"):
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / "docs", output / "docs", dirs_exist_ok=True)
    return output


def main():
    from build_qt_compat import build
    from build_metadata import metadata
    from build_updaters import prepare, embed
    build()
    update_config = prepare()
    build_info = ROOT/'build/build-info.json'
    build_info.parent.mkdir(parents=True, exist_ok=True)
    build_info.write_text(json.dumps(metadata(ROOT, __version__), indent=2))
    notice_dir = notices()
    shutil.copytree(ROOT / 'build/updater-notices', notice_dir / 'updaters', dirs_exist_ok=True)
    icons = ROOT / "src/ilias_sync/assets/icons"
    native_icon = (icons / "macOS/IliasSync-Dark.icns" if sys.platform == "darwin"
                   else windows_icon(icons, ROOT / "build/IliasSync.ico") if sys.platform == "win32"
                   else icons / "PNG/Dark/IliasSync-Dark-256.png")
    updater_binary = []
    if sys.platform in {'darwin', 'win32'}:
        library = 'libilias_updates.dylib' if sys.platform == 'darwin' else 'WinSparkle.dll'
        updater_binary = ['--add-binary', str(ROOT / 'src/ilias_sync/assets/native' / library)
                          + os.pathsep + 'ilias_sync/assets/native']
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                    "--name", "IliasSync", "--icon", str(native_icon), "--paths", "src",
                    "--collect-data", "ilias_sync", "--collect-all", "PFERD",
                    "--collect-submodules", "keyring.backends", "--recursive-copy-metadata", "PFERD",
                    "--copy-metadata", "keyring", "--add-data", str(notice_dir) + os.pathsep + "third-party-licenses",
                    "--add-data", str(ROOT / 'src/ilias_sync/assets/update-config.json') + os.pathsep + 'ilias_sync/assets',
                    "--add-data", str(build_info) + os.pathsep + "ilias_sync/assets",
                    "--osx-bundle-identifier", "org.iliassync.desktop", *updater_binary, "scripts/launch.py"], check=True)
    dist = ROOT / "dist"
    if sys.platform == "darwin":
        app = dist / "IliasSync.app"
        binary = app / "Contents/MacOS/IliasSync"
        info_path = app / "Contents/Info.plist"
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleShortVersionString=__version__, CFBundleVersion=__version__,
                    NSHumanReadableCopyright="IliasSync contributors · GPL-3.0-or-later")
        info_path.write_bytes(plistlib.dumps(info))
        arch = 'arm64' if platform.machine().lower() in {'arm64', 'aarch64'} else 'x64'
        embed(app, arch, update_config['public_key'])
        assert (app / "Contents/Resources" / info["CFBundleIconFile"]).read_bytes() == native_icon.read_bytes()
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
    else:
        binary = dist / "IliasSync" / ("IliasSync.exe" if sys.platform == "win32" else "IliasSync")
    # Windowed Windows processes do not expose stdout: require a checked event file.
    event = ROOT / "build/packaged-self-test.jsonl"
    event.unlink(missing_ok=True)
    subprocess.run([str(binary), "--self-test", "--event-file", str(event)], check=True, timeout=90)
    result = json.loads(event.read_text(encoding="utf-8").strip())
    if not result.get("ok"):
        raise RuntimeError("Packaged self-test failed")
    arch = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
    target = {"darwin": "macOS", "win32": "Windows"}.get(sys.platform, "Linux")
    prefix = f"IliasSync-{__version__}-{target}-{arch}"
    if sys.platform == "darwin":
        package = dist / (prefix + ".dmg")
        with tempfile.TemporaryDirectory(prefix="dmg-", dir=ROOT / "build") as staging:
            stage = Path(staging)
            shutil.copytree(app, stage / app.name, symlinks=True)
            (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
            subprocess.run(["hdiutil", "create", "-volname", "IliasSync", "-srcfolder", str(stage),
                            "-ov", "-format", "UDZO", str(package)], check=True)
    else:
        if sys.platform.startswith("linux"):
            shutil.copy2(ROOT / "scripts/install-desktop.sh", dist / "IliasSync/install-desktop.sh")
            (dist / "IliasSync/install-desktop.sh").chmod(0o755)
            shutil.copy2(icons / "PNG/Dark/IliasSync-Dark-256.png", dist / "IliasSync/IliasSync.png")
        fmt = "zip" if sys.platform == "win32" else "gztar"
        package = Path(shutil.make_archive(str(dist / prefix), fmt, root_dir=dist, base_dir="IliasSync"))
    packages = [package]
    from installers import debian_package, windows_installer
    if sys.platform == 'win32':
        packages.append(windows_installer(ROOT, __version__))
    elif sys.platform.startswith('linux'):
        packages.append(debian_package(ROOT, __version__, arch))
    for package in packages:
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        (dist / (package.name + ".sha256")).write_text(digest + "  " + package.name + "\n", encoding="utf-8")
        print(package)


if __name__ == "__main__":
    main()
