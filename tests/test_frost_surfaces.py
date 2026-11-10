"""Rendered carrier layers must not conceal the native window backdrop."""
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ilias_sync.gui import MainWindow, SettingsDialog, SourceDialog
from ilias_sync.storage import Settings, data_dir, write_json
from ilias_sync.theme import Theme


def test_native_pages_share_one_translucent_window_layer(source):
    app = QApplication.instance() or QApplication([])
    settings = Settings()
    settings.save_source(source)
    write_json(data_dir() / 'sources' / source.id / 'status.json', {'state': 'Up to date'})
    with patch('ilias_sync.theme.uses_native_backdrop', return_value=True), \
            patch('ilias_sync.native_compat.blur_window'):
        app.theme = Theme(app, 'dark')
        main = MainWindow()
        setup = SourceDialog(settings)
        preferences = SettingsDialog(settings, main)
        try:
            for mode in ('dark', 'light', 'dark'):
                app.theme.set_mode(mode)
                main.show()
                for tab in range(3):
                    main.workspace_tabs.setCurrentIndex(tab)
                    app.processEvents()
                    image = main.grab().toImage()
                    # Before the fix the two pane fills accumulated to alpha 240.
                    assert 0 < image.pixelColor(image.width() - 8, image.height() // 2).alpha() < 220
                    assert main.windowOpacity() == 1
                # Surface contrast is a light tint, not another nearly opaque
                # coat hiding the same backdrop under the sidebar and cards.
                for surface in (main.sidebar, main.recent_files.parentWidget()):
                    image = surface.grab().toImage()
                    alpha = image.pixelColor(image.width() - 8, image.height() // 2).alpha()
                    assert abs(alpha - (117 if mode == 'light' else 66)) <= 1
                card = main.recent_files.parentWidget().grab().toImage()
                # The single coat must retain the rounded card's visible border.
                assert card.pixelColor(card.width() // 2, 0).alpha() == 255
                setup.show()
                for index, page in enumerate(setup.pages):
                    setup.stack.setCurrentIndex(index)
                    app.processEvents()
                    assert page.grab().toImage().pixelColor(2, 2).alpha() == 0
                setup.hide()
                preferences.show()
                for tab in range(preferences.tabs.count()):
                    preferences.tabs.setCurrentIndex(tab)
                    app.processEvents()
                    image = preferences.grab().toImage()
                    assert 0 < image.pixelColor(image.width() - 8, image.height() // 2).alpha() < 220
                    assert preferences.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                preferences.hide()
        finally:
            for widget in (preferences, setup, main):
                widget.close()
