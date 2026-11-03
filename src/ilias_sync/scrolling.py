"""Scroll transparent content without leaving previous frames in the window surface."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea


class TranslucentScrollArea(QScrollArea):
    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        window = self.window()
        if (dx or dy) and self.isVisible() and window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
            # The moved contents and their translucent ancestors must be composited
            # together, including the old positions. update() coalesces wheel events.
            window.update()
