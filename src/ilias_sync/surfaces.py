"""Style-sheet surfaces with a single background coat."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QStyle, QStyleOption

from .theme import TITLEBAR_OPACITY


def paint_window_background(widget):
    if not widget.isWindow() or not widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
        return
    painter = QPainter(widget)
    # Clear moved/invalidated regions before repainting translucent surfaces.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.fillRect(widget.rect(), Qt.GlobalColor.transparent)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    option = QStyleOption()
    option.initFrom(widget)
    widget.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, widget)

    handle = widget.windowHandle()
    title_height = handle.safeAreaMargins().top() if handle else 0
    theme = getattr(QApplication.instance(), '_ilias_theme_manager', None)
    if title_height and theme and theme.native_backdrop and not theme.high_contrast:
        # Replace just the paint under the native traffic lights. Qt keeps
        # layouts below this inset and updates it as the window chrome changes.
        tint = widget.palette().color(QPalette.ColorRole.Window)
        tint.setAlphaF(TITLEBAR_OPACITY)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(0, 0, widget.width(), title_height, tint)
    painter.end()


class SurfaceDialog(QDialog):
    def paintEvent(self, event):
        paint_window_background(self)
        super().paintEvent(event)


class SurfaceFrame(QFrame):
    def event(self, event):
        handled = super().event(event)
        if event.type() in (QEvent.Type.Polish, QEvent.Type.StyleChange):
            # Draw the complete styled surface once in our paintEvent.
            # QWidget's automatic pass would apply a translucent fill twice.
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        return handled

    def paintEvent(self, event):
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)
