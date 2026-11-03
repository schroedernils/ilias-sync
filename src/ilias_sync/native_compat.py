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


def blur_window(view_id, tint='#181818'):
    """Blur the desktop behind a Cocoa window. No-op when the layer is absent."""
    if _library is None or not view_id:
        return False
    try:
        from PySide6.QtGui import QColor
        color = QColor(tint)
        function = _library.ilias_blur_window
        function.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        function.restype = ctypes.c_int
        return bool(function(ctypes.c_void_p(view_id), color.red(), color.green(), color.blue()))
    except (OSError, AttributeError):
        return False
