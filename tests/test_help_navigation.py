"""State and redraw-event checks for help navigation; no screenshots."""
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout

from ilias_sync.help_widgets import HelpTopicList


class TracedDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.paint_regions = []

    def paintEvent(self, event):
        self.paint_regions.append(event.region())
        super().paintEvent(event)


def move_to(app, topics, row):
    position = QPointF(topics.visualItemRect(topics.item(row)).center())
    event = QMouseEvent(QEvent.Type.MouseMove, position, position,
                        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    app.sendEvent(topics.viewport(), event)
    app.processEvents()


def test_hover_transition_repaints_background_without_changing_selection():
    app = QApplication.instance() or QApplication([])
    window = TracedDialog()
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    window.resize(300, 300)
    layout = QVBoxLayout(window)
    topics = HelpTopicList()
    topics.addItems([f'Topic {index}' for index in range(20)])
    layout.addWidget(topics)
    window.show()
    app.processEvents()
    topics.setCurrentRow(2)
    try:
        for row in [0, 1, 3, 1]:
            window.paint_regions.clear()
            move_to(app, topics, row)
            assert topics._hovered_row == row
            assert topics.currentRow() == 2
            assert len(topics.selectedItems()) == 1
            assert any(region.contains(window.rect()) for region in window.paint_regions)
        window.paint_regions.clear()
        app.sendEvent(topics.viewport(), QEvent(QEvent.Type.Leave))
        app.processEvents()
        assert topics._hovered_row == -1
        assert topics.currentRow() == 2
        assert any(region.contains(window.rect()) for region in window.paint_regions)
        window.paint_regions.clear()
        topics.verticalScrollBar().setValue(topics.verticalScrollBar().maximum())
        app.processEvents()
        assert topics._hovered_row == -1
        assert any(region.contains(window.rect()) for region in window.paint_regions)
        topics.hide()
        assert topics._hovered_row == -1
    finally:
        window.close()


def test_help_keyboard_selection_updates_content_and_survives_focus_changes():
    from ilias_sync.gui import HelpDialog
    from ilias_sync.i18n import set_language
    app = QApplication.instance() or QApplication([])
    set_language('de')
    dialog = HelpDialog()
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dialog.show()
    app.processEvents()
    try:
        assert isinstance(dialog.topics, HelpTopicList)
        dialog.topics.setFocus()
        QTest.keyClick(dialog.topics, Qt.Key.Key_Down)
        app.processEvents()
        assert dialog.topics.currentRow() == 1
        title = dialog.topics_data[1][0]
        assert title in dialog.info.toPlainText()
        dialog.info.setFocus()
        app.processEvents()
        assert dialog.topics.currentRow() == 1
        assert len(dialog.topics.selectedItems()) == 1
        assert not dialog.info.viewport().autoFillBackground()
    finally:
        dialog.close()
