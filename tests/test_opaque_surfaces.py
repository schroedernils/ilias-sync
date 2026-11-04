"""Windows without a native backdrop must not expose the desktop through content."""
from unittest.mock import patch

import pytest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QDialog

from ilias_sync.gui import Dropdown, MainWindow, SettingsDialog, SourceDialog
from ilias_sync.motion import MotionMenu
from ilias_sync.storage import Settings
from ilias_sync.theme import DARK, LIGHT, Theme, popup_color


@pytest.mark.parametrize('mode,colors', [('light', LIGHT), ('dark', DARK)])
def test_non_cocoa_window_dialog_and_popups_are_opaque(mode, colors, source):
    app = QApplication.instance() or QApplication([])
    assert app.platformName() != 'cocoa'
    with patch('ilias_sync.native_compat.blur_window') as blur:
        app.theme = Theme(app, mode)
        settings = Settings()
        settings.save_source(source)
        main = MainWindow()
        preferences = SettingsDialog(settings, main)
        setup = SourceDialog(settings)
        dialog = QDialog(main)
        menu = MotionMenu(main)
        menu.addAction('Example menu item')
        dropdown = Dropdown(dialog)
        dropdown.addItems(['First', 'Second'])
        windows = [main, preferences, setup, dialog]
        try:
            for window in windows:
                window.show()
                app.processEvents()
                assert not window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                image = window.grab().toImage()
                color = image.pixelColor(image.width() - 5, image.height() // 2)
                assert color.alpha() == 255
                assert color.name() == colors['window']

            assert popup_color(app.palette()).alpha() == 255
            for popup in (menu, dropdown):
                if popup is menu:
                    menu.popup(main.mapToGlobal(QPoint(60, 60)))
                    window = menu
                else:
                    dropdown.show()
                    dropdown.showPopup()
                    window = dropdown.view().window()
                assert window.isVisible()
                assert window.windowOpacity() == 1
                assert not window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                image = window.grab().toImage()
                color = image.pixelColor(image.width() - 8, image.height() // 2)
                assert color.alpha() == 255
                if popup is menu:
                    assert color.name() == colors['elevated']
                window.hide()
            blur.assert_not_called()
        finally:
            dropdown.hidePopup()
            menu.close()
            for window in reversed(windows):
                window.close()
