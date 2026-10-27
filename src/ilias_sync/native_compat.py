"""Narrow Cocoa compatibility for the pinned Qt runtime; never disable AT."""
import ctypes
from pathlib import Path
import sys

_library = None


def protect_accessibility(application):
    global _library
    from PySide6.QtCore import qVersion
    if sys.platform != 'darwin' or application.platformName() != 'cocoa':
        return False
    if qVersion() != '6.10.0':
        raise RuntimeError('Review the Cocoa accessibility compatibility layer before changing Qt.')
    path = Path(__file__).parent / 'assets/native/libilias_qt_accessibility.dylib'
    _library = ctypes.CDLL(str(path))
    _library.ilias_fix_qt_accessibility.restype = ctypes.c_int
    if not _library.ilias_fix_qt_accessibility():
        raise RuntimeError('The Qt Cocoa accessibility compatibility layer could not be initialized.')
    return True
