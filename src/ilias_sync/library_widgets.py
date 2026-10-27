"""Small native widgets for readable materials and non-modal synchronization feedback."""
from pathlib import PurePosixPath

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPalette, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar, QStyle,
                              QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QVBoxLayout, QWidget)

from .i18n import t
from .presentation import file_context
from .theme import DARK, LIGHT


class MaterialDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() != 0:
            return super().paint(painter, option, index)
        entry = index.data(Qt.ItemDataRole.UserRole + 1) or {}
        if not entry:
            return super().paint(painter, option, index)
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.text = ''
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, option.widget)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        color = option.palette.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text)
        colors = DARK if option.palette.color(QPalette.ColorRole.Base).lightness() < 128 else LIGHT
        high_contrast = getattr(getattr(QApplication.instance(), 'theme', None), 'high_contrast', False)
        muted = color if selected or high_contrast else QColor(colors['muted'])
        painter.save()
        icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        icon.paint(painter, QRect(option.rect.left() + 12, option.rect.center().y() - 10, 20, 20))
        text_rect = option.rect.adjusted(44, 7, -12, -7)
        font = QFont(option.font)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(color)
        title = PurePosixPath(entry['path']).name
        line_height = max(20, painter.fontMetrics().height())
        painter.drawText(QRect(text_rect.left(), text_rect.top(), text_rect.width(), line_height),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(title, Qt.TextElideMode.ElideMiddle, text_rect.width()))
        font.setPixelSize(max(11, round(option.fontMetrics.height() * 0.78)))
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(muted)
        painter.drawText(QRect(text_rect.left(), text_rect.top() + line_height + 1, text_rect.width(), max(18, painter.fontMetrics().height())),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(file_context(entry), Qt.TextElideMode.ElideMiddle, text_rect.width()))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(super().sizeHint(option, index).width(), 58)


class SourceDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.text = ''
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, option.widget)
        lines = str(index.data() or '').split('\n', 1)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        painter.save()
        text = option.palette.color(QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text)
        muted = text if selected else option.palette.color(QPalette.ColorRole.PlaceholderText)
        rect = option.rect.adjusted(12, 8, -36, -8)
        for i, line in enumerate(lines):
            font = QFont(option.font)
            font.setWeight(QFont.Weight.Medium if i == 0 else QFont.Weight.Normal)
            if i:
                font.setPixelSize(max(11, round(option.fontMetrics.height() * 0.78)))
            painter.setFont(font)
            painter.setPen(text if i == 0 else muted)
            painter.drawText(QRect(rect.left(), rect.top() + i * 20, rect.width(), 20),
                             Qt.AlignmentFlag.AlignVCenter,
                             painter.fontMetrics().elidedText(line, Qt.TextElideMode.ElideRight, rect.width()))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(180, 60)


class StatusMark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tone = 'neutral'
        self.setFixedSize(42, 42)
        self.setAccessibleName(t('Synchronization status'))

    def set_tone(self, tone):
        self.tone = tone
        self.update()

    def paintEvent(self, event):
        colors = DARK if self.palette().color(QPalette.ColorRole.Window).lightness() < 128 else LIGHT
        key = {'success': 'success', 'warning': 'warning', 'error': 'error', 'running': 'accent'}.get(self.tone, 'muted')
        color = QColor(colors[key])
        if getattr(getattr(QApplication.instance(), 'theme', None), 'high_contrast', False):
            color = self.palette().color(QPalette.ColorRole.Text)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill = QColor(color)
        fill.setAlpha(22)
        p.setBrush(fill)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawEllipse(10, 10, 22, 22)
        if self.tone == 'success':
            p.drawLine(15, 21, 19, 25)
            p.drawLine(19, 25, 27, 17)
        elif self.tone in {'warning', 'error'}:
            p.drawLine(21, 15, 21, 22)
            p.drawPoint(21, 27)
        else:
            p.drawLine(21, 15, 21, 21)
            p.drawLine(21, 21, 25, 23)


class MaterialTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self.empty = QWidget(self.viewport())
        self.empty.setObjectName('libraryEmpty')
        self.empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self.empty)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.addStretch()
        self.empty_title = QLabel()
        self.empty_title.setObjectName('sectionTitle')
        self.empty_body = QLabel()
        self.empty_body.setObjectName('subtitle')
        for item in (self.empty_title, self.empty_body):
            item.setWordWrap(True)
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(item)
        layout.addStretch()
        self.empty.hide()

    def set_empty(self, title, detail):
        self.empty_title.setText(title)
        self.empty_body.setText(detail)
        self.empty.setGeometry(self.viewport().rect())
        self.empty.setVisible(bool(title))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.empty.setGeometry(self.viewport().rect())


class SyncPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('syncPanel')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 17, 18, 15)
        outer.setSpacing(10)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.mark = StatusMark()
        row.addWidget(self.mark, alignment=Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(4)
        self.title = QLabel()
        self.title.setObjectName('statusTitle')
        self.title.setWordWrap(True)
        self.detail = QLabel()
        self.detail.setObjectName('subtitle')
        self.detail.setWordWrap(True)
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setAccessibleName(t('Synchronization status'))
        text.addWidget(self.title)
        text.addWidget(self.detail)
        row.addLayout(text, 1)
        self.recovery_layout = row
        outer.addLayout(row)
        self.progress = QProgressBar()
        self.progress.setAccessibleName(t('Synchronization progress'))
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.hide()
        outer.addWidget(self.progress)
        self.meta = QLabel()
        self.meta.setObjectName('statusMeta')
        self.meta.setWordWrap(True)
        self.meta.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(self.meta)

    def set_state(self, title, detail, tone, *, busy=False):
        self.title.setText(title)
        self.detail.setText(detail)
        self.detail.setAccessibleName(detail)
        self.mark.set_tone(tone)
        self.progress.setVisible(busy)
