"""Native appearance state checks with hidden windows; no visual tests."""
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != 'darwin', reason='AppKit window appearance')
def test_hidden_native_window_follows_repeated_theme_changes(tmp_path):
    root = Path(__file__).resolve().parents[1]
    binary = tmp_path / 'check-window-appearance'
    compilation = subprocess.run(['xcrun', 'clang++', '-std=c++17', '-fno-objc-arc', '-mmacosx-version-min=13.0',
                    '-framework', 'Foundation', '-framework', 'AppKit',
                    str(root/'tests/native/check_window_appearance.mm'),
                    str(root/'src/ilias_sync/native/qt_accessibility.mm'), '-o', str(binary)],
                   capture_output=True, text=True, timeout=60)
    assert compilation.returncode == 0, compilation.stderr
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(sys.platform != 'darwin', reason='Cocoa pane geometry')
def test_hidden_cocoa_panes_keep_positions_and_sizes_in_sync():
    root = Path(__file__).resolve().parents[1]
    compilation = subprocess.run([sys.executable, str(root/'scripts/build_qt_compat.py')],
                                 capture_output=True, text=True, timeout=60)
    assert compilation.returncode == 0, compilation.stderr
    result = subprocess.run([sys.executable, str(root/'tests/native/check_sidebar_geometry.py')],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
