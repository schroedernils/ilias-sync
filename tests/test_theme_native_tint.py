"""Check theme-to-native dispatch order without native UI or screenshots."""
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from ilias_sync.theme import DARK, LIGHT, Theme


def test_open_windows_receive_new_native_tint_after_stylesheet_changes():
    app = QApplication.instance() or QApplication([])
    app.theme = Theme(app, 'light')
    windows = [QDialog(), QDialog()]
    try:
        with patch('ilias_sync.native_compat.blur_window') as blur:
            for window in windows:
                window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                window.show()
            app.processEvents()
            for mode, colors in [('dark', DARK), ('light', LIGHT), ('dark', DARK)]:
                blur.reset_mock()
                app.theme.set_mode(mode)
                app.processEvents()
                for window in windows:
                    assert any(call.args == (int(window.winId()), colors['window']) for call in blur.call_args_list)
    finally:
        for window in windows:
            window.close()
