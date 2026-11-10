"""Style-sheet surfaces with a single background coat."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFrame, QStyle, QStyleOption


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
