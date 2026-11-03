"""Compile the pinned Qt 6.10 Cocoa ownership compatibility layer on macOS."""
from pathlib import Path
import subprocess
import sys


def build():
    if sys.platform != 'darwin':
        return
    root = Path(__file__).resolve().parents[1]
    output = root / 'src/ilias_sync/assets/native/libilias_qt_accessibility.dylib'
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['xcrun', 'clang++', '-dynamiclib', '-std=c++17', '-fno-objc-arc',
                    '-mmacosx-version-min=13.0', '-framework', 'Foundation', '-framework', 'AppKit',
                    '-o', str(output), str(root / 'src/ilias_sync/native/qt_accessibility.mm')], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(output)], check=True)
    notifications = output.parent / 'libilias_notifications.dylib'
    subprocess.run(['xcrun', 'clang++', '-dynamiclib', '-std=c++17', '-fobjc-arc',
                    '-mmacosx-version-min=13.0', '-framework', 'Foundation', '-framework', 'UserNotifications',
                    '-o', str(notifications), str(root / 'src/ilias_sync/native/notifications.mm')], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(notifications)], check=True)
    return output


if __name__ == '__main__':
    print(build())
