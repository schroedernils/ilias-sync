"""Native installable packages, built alongside the portable distribution."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


def windows_installer(root, version):
    compiler = shutil.which('iscc')
    if not compiler:
        compiler = str(Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) /
                       'Inno Setup 6' / 'ISCC.exe')
    if not Path(compiler).is_file():
        raise RuntimeError('Inno Setup 6 is required to build the Windows installer.')
    subprocess.run([compiler, f'/DAppVersion={version}', str(root / 'scripts/windows-installer.iss')], check=True)
    return root / f'dist/IliasSync-{version}-Windows-x64-Setup.exe'


def stage_debian(root, stage, version, architecture):
    if architecture not in {'amd64', 'arm64'}:
        raise ValueError('Unsupported Debian architecture: ' + architecture)
    payload = stage / 'opt/iliassync'
    shutil.copytree(root / 'dist/IliasSync', payload, symlinks=True)
    binary = stage / 'usr/bin'
    binary.mkdir(parents=True)
    (binary / 'ilias-sync').symlink_to('/opt/iliassync/IliasSync')
    desktop = stage / 'usr/share/applications'
    desktop.mkdir(parents=True)
    (desktop / 'org.iliassync.desktop.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=IliasSync\n'
        'Comment=Keep ILIAS course files on this computer\n'
        'Comment[de]=ILIAS-Kursdateien auf diesem Computer synchronisieren\n'
        'Exec=ilias-sync\nIcon=org.iliassync.desktop\nTerminal=false\n'
        'Categories=Education;Network;\nStartupWMClass=IliasSync\n', encoding='utf-8')
    icon = stage / 'usr/share/icons/hicolor/256x256/apps'
    icon.mkdir(parents=True)
    shutil.copy2(payload / 'IliasSync.png', icon / 'org.iliassync.desktop.png')
    documentation = stage / 'usr/share/doc/iliassync'
    documentation.mkdir(parents=True)
    shutil.copy2(root / 'LICENSE', documentation / 'copyright')
    control = stage / 'DEBIAN'
    control.mkdir()
    size = sum(file.stat().st_size for file in stage.rglob('*') if file.is_file() and not file.is_symlink())
    dependencies = ('libc6 (>= 2.35), libgcc-s1, libstdc++6, libegl1, libgl1, libopengl0, '
        'libdbus-1-3, libfontconfig1, libfreetype6, libglib2.0-0 | libglib2.0-0t64, '
        'libice6, libsm6, libx11-6, libx11-xcb1, libxext6, libxfixes3, libxi6, libxrender1, '
        'libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, '
        'libxcb-render0, libxcb-render-util0, libxcb-shape0, libxcb-shm0, libxcb-sync1, '
        'libxcb-xfixes0, libxcb-xkb1, libxkbcommon0, libxkbcommon-x11-0, '
        'libwayland-client0, libwayland-cursor0, libwayland-egl1, zlib1g')
    (control / 'control').write_text(
        f'Package: iliassync\nVersion: {version}\nArchitecture: {architecture}\n'
        'Section: education\nPriority: optional\nMaintainer: IliasSync contributors\n'
        f'Installed-Size: {(size + 1023) // 1024}\nDepends: {dependencies}\n'
        'Recommends: gnome-keyring | kwalletmanager, dbus-user-session\n'
        'Homepage: https://github.com/schroedernils/ilias-sync\n'
        'Description: Local ILIAS course-material library\n'
        ' Synchronize selected university courses into your own folders.\n'
        ' Includes Python and Qt; credentials and materials stay outside the application.\n', encoding='utf-8')
    # Packages are built with root ownership, without touching per-user settings or data.
    for folder in [stage, *stage.rglob('*')]:
        if folder.is_dir() and not folder.is_symlink():
            folder.chmod(0o755)


def debian_package(root, version, arch):
    architecture = {'x64': 'amd64', 'arm64': 'arm64'}[arch]
    package = root / f'dist/IliasSync-{version}-Linux-{arch}.deb'
    with tempfile.TemporaryDirectory(prefix='debian-', dir=root / 'build') as temporary:
        stage = Path(temporary) / 'package'
        stage_debian(root, stage, version, architecture)
        subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(stage), str(package)], check=True)
    return package
