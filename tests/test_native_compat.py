"""Exercise the Qt Cocoa ownership bug without disabling accessibility."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_non_cocoa_platform_does_not_load_native_layer():
    from ilias_sync.native_compat import protect_accessibility
    from unittest.mock import Mock
    assert not protect_accessibility(Mock(platformName=lambda: 'offscreen'))


@pytest.mark.skipif(sys.platform != 'darwin', reason='Cocoa ownership regression')
def test_native_placeholder_release_keeps_qt_table_interface_alive():
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root/'scripts/build_qt_compat.py')], check=True, capture_output=True)
    code = '''
import ctypes
from PySide6.QtWidgets import QApplication, QTableWidget
from PySide6.QtGui import QAccessible
from ilias_sync.native_compat import protect_accessibility
app = QApplication([])
assert protect_accessibility(app)
table = QTableWidget(2, 2)
interface = QAccessible.queryAccessibleInterface(table)
identity = QAccessible.uniqueId(interface)
objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
objc.objc_getClass.argtypes = [ctypes.c_char_p]
objc.objc_getClass.restype = ctypes.c_void_p
objc.sel_registerName.argtypes = [ctypes.c_char_p]
objc.sel_registerName.restype = ctypes.c_void_p
send = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
simple = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(send)
initialize = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)(send)
release = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)(send)
appkit = ctypes.CDLL('/System/Library/Frameworks/AppKit.framework/AppKit')
role = ctypes.c_void_p.in_dll(appkit, 'NSAccessibilityCellRole').value
klass = objc.objc_getClass(b'QMacAccessibilityElement')
for _ in range(25):
    placeholder = simple(klass, objc.sel_registerName(b'alloc'))
    placeholder = initialize(placeholder, objc.sel_registerName(b'initWithId:role:'), identity, role)
    assert placeholder
    release(placeholder, objc.sel_registerName(b'release'))
    surviving = QAccessible.accessibleInterface(identity)
    assert surviving is not None and surviving.isValid()
    assert surviving.object() is table
table.close()
print('25 native placeholder releases preserved the table interface')
'''
    result = subprocess.run([sys.executable, '-c', code], env={**os.environ, 'QT_QPA_PLATFORM':'cocoa'},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert '25 native placeholder releases' in result.stdout
