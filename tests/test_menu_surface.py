"""The rounded popup must follow Qt's final size, including late layout."""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication
import pytest

from ilias_sync.motion import MotionMenu
from ilias_sync.theme import Theme


@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_cocoa_menu_rebuilds_mask_when_actions_expand_after_show(monkeypatch, mode):
    app = QApplication.instance() or QApplication([])
    app.theme = Theme(app, mode)
    monkeypatch.setattr('ilias_sync.motion.uses_native_backdrop', lambda app: True)
    menu = MotionMenu()
    menu.addAction('Sync-Kurse auswählen …')
    menu.popup(QPoint(100, 100))
    app.processEvents()
    initial_height = menu.height()
    for name in ('Ordner zuordnen', 'Ordner öffnen', 'Bearbeiten'):
        menu.addAction(name)
    menu.adjustSize()
    app.processEvents()
    assert menu.height() > initial_height
    for action in menu.actions():
        rect = menu.actionGeometry(action).adjusted(8, 5, -8, -5)
        assert menu.rect().contains(rect)
        assert menu.mask().contains(rect.center())
        assert menu.mask().contains(rect.bottomRight())
        assert menu.actionGeometry(action).width() >= menu.fontMetrics().horizontalAdvance(action.text())
    position = menu.pos()
    menu._motion.setCurrentTime(menu._motion.duration())
    assert menu.pos() == position
    menu.close()


def test_ordinary_menu_keeps_native_opaque_surface(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr('ilias_sync.motion.uses_native_backdrop', lambda app: False)
    menu = MotionMenu()
    menu.addAction('Ordner zuordnen')
    menu.popup(QPoint(100, 100))
    app.processEvents()
    assert menu.mask().isEmpty()
    assert not menu.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    menu.close()
