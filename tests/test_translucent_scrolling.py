"""Functional invalidation checks; no screenshots or visual inspection."""
import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QWidget

from ilias_sync.scrolling import TranslucentScrollArea


class TracedDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.paint_regions = []

    def paintEvent(self, event):
        self.paint_regions.append(event.region())
        super().paintEvent(event)


@pytest.mark.parametrize('axis', ['vertical', 'horizontal'])
def test_scrolling_invalidates_whole_translucent_window(axis):
    app = QApplication.instance() or QApplication([])
    window = TracedDialog()
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    window.resize(300, 240)
    layout = QVBoxLayout(window)
    layout.setContentsMargins(24, 40, 24, 40)
    scroll = TranslucentScrollArea()
    scroll.viewport().setAutoFillBackground(False)
    content = QWidget()
    content.resize(900, 900)
    scroll.setWidget(content)
    content.setAutoFillBackground(False)
    layout.addWidget(scroll)
    window.show()
    app.processEvents()
    bar = scroll.verticalScrollBar() if axis == 'vertical' else scroll.horizontalScrollBar()
    assert bar.maximum() > 100
    try:
        for offset in [40, 100, 30, bar.maximum(), 0]:
            window.paint_regions.clear()
            bar.setValue(offset)
            app.processEvents()
            assert bar.value() == offset
            assert any(region.contains(window.rect()) for region in window.paint_regions)
            assert content.y() == -offset if axis == 'vertical' else content.x() == -offset
    finally:
        window.close()


def test_scrolling_does_not_reenable_updates_disabled_by_caller():
    app = QApplication.instance() or QApplication([])
    window = TracedDialog()
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    layout = QVBoxLayout(window)
    scroll = TranslucentScrollArea()
    content = QWidget()
    content.resize(200, 900)
    scroll.setWidget(content)
    layout.addWidget(scroll)
    window.show()
    app.processEvents()
    try:
        window.setUpdatesEnabled(False)
        scroll.verticalScrollBar().setValue(50)
        app.processEvents()
        assert not window.updatesEnabled()
        assert scroll.verticalScrollBar().value() == 50
    finally:
        window.setUpdatesEnabled(True)
        window.close()
