"""Only the current theme manager may restyle the shared QApplication."""
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from ilias_sync.theme import LIGHT, Theme


def test_replaced_theme_manager_cannot_reapply_an_old_palette():
    app = QApplication.instance() or QApplication([])
    old = Theme(app, 'dark')
    new = Theme(app, 'light')
    old.set_mode('dark')
    assert not old._active and new._active
    assert app.palette().color(QPalette.ColorRole.Text).name() == LIGHT['text']
