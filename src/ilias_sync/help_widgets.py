"""Help navigation that redraws hover transitions on a translucent dialog."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QListWidget


class HelpTopicList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row = -1
        self.setObjectName('helpTopics')
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().setAutoFillBackground(False)
        self.currentRowChanged.connect(self._redraw_window)

    def _redraw_window(self, *_):
        window = self.window()
        if self.isVisible() and window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
            # Recompose the previous row and its background, not only the new chip.
            window.update()

    def viewportEvent(self, event):
        handled = super().viewportEvent(event)
        if event.type() == QEvent.Type.MouseMove:
            row = self.indexAt(event.position().toPoint()).row()
        elif event.type() == QEvent.Type.Leave:
            row = -1
        else:
            return handled
        if row != self._hovered_row:
            self._hovered_row = row
            self._redraw_window()
        return handled

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._hovered_row = -1
        self._redraw_window()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._redraw_window()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._redraw_window()

    def hideEvent(self, event):
        self._hovered_row = -1
        super().hideEvent(event)
