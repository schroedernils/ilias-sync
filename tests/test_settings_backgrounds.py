"""Check transparent container state without screenshots or visual assertions."""
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QStackedWidget

from ilias_sync.gui import SettingsDialog
from ilias_sync.storage import Settings
from ilias_sync.theme import Theme


def test_settings_tab_containers_stay_transparent_when_changing_theme():
    app = QApplication.instance() or QApplication([])
    app.theme = Theme(app, 'light')
    settings = Settings()
    settings.value['appearance'] = 'light'
    dialog = SettingsDialog(settings)
    dialog.show()
    try:
        for mode in ['light', 'dark', 'light']:
            app.theme.set_mode(mode)
            app.processEvents()
            assert not dialog.tabs.tabBar().drawBase()
            containers = [dialog.tabs, dialog.tabs.tabBar(), dialog.buttons,
                          dialog.tabs.findChild(QStackedWidget)]
            for widget in containers:
                assert widget.palette().color(QPalette.ColorRole.Window).alpha() == 0, type(widget).__name__
                assert not widget.autoFillBackground(), type(widget).__name__
    finally:
        dialog.reject()
