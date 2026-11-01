"""Small native widgets for readable materials and non-modal synchronization feedback."""
from pathlib import PurePosixPath

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPalette, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar, QStyle,
                              QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QVBoxLayout, QWidget,
                              QTreeWidget, QTreeWidgetItem, QPushButton)
from PySide6.QtWidgets import QScrollArea

from .i18n import t
from .theme import DARK, LIGHT


class ElidedLabel(QLabel):
    """A single-line label that retains its complete text for tooltips and AT."""
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.full_text = text
        self.setMinimumWidth(0)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setText(text)

    def minimumSizeHint(self):
        return QSize(0, self.fontMetrics().height() + 4)

    def sizeHint(self):
        return QSize(min(400, self.fontMetrics().horizontalAdvance(self.full_text)), self.fontMetrics().height() + 4)

    def setText(self, text):
        self.full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        super().setText(self.fontMetrics().elidedText(text, Qt.TextElideMode.ElideMiddle, max(1, self.width())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        super().setText(self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideMiddle, max(1, self.width())))


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
        paint_file_icon(painter, QRect(option.rect.left() + 10, option.rect.center().y() - 12, 26, 26), entry, muted)
        text_rect = option.rect.adjusted(46, 3, -10, -3)
        font = QFont(option.font)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(color)
        title = PurePosixPath(entry['path']).name
        line_height = painter.fontMetrics().height() + 1
        painter.drawText(QRect(text_rect.left(), text_rect.top(), text_rect.width(), line_height),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(title, Qt.TextElideMode.ElideMiddle, text_rect.width()))
        font.setPixelSize(max(11, round(option.fontMetrics.height() * 0.78)))
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(muted)
        context = material_context(entry, getattr(option.widget, 'library_scope', 'source'))
        painter.drawText(QRect(text_rect.left(), text_rect.top() + line_height, text_rect.width(), painter.fontMetrics().height() + 2),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(context, Qt.TextElideMode.ElideRight, text_rect.width()))
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(super().sizeHint(option, index).width(), max(44, option.fontMetrics.height() * 2 + 10))


def material_context(entry, scope):
    """Course/source context leads in aggregate views; folders lead within a course."""
    parent = str(PurePosixPath(entry['path']).parent)
    if scope == 'course':
        logical = entry.get('logical', '')
        parent = str(PurePosixPath(logical).parent) if logical else parent
        if '/' in parent:
            parent = parent.split('/', 1)[1]
        elif parent == entry.get('course_name') or logical:
            parent = ''
        return parent if parent != '.' else ''
    parts = [entry.get('_source_name', '')] if scope == 'global' else []
    parts.append(entry.get('course_name') or (parent if parent != '.' else ''))
    logical = entry.get('logical', '')
    folder = str(PurePosixPath(logical).parent) if logical else parent
    if '/' in folder:
        parts.append(folder.split('/', 1)[1])
    return ' · '.join(part for part in parts if part)


def file_family(path):
    suffix = PurePosixPath(path).suffix.casefold()
    for kind, extensions in [('PDF', {'.pdf'}), ('ZIP', {'.zip', '.7z', '.tar', '.gz', '.rar'}),
                             ('IMG', {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.heic'}),
                             ('VID', {'.mp4', '.mov', '.mkv', '.webm'}), ('AUD', {'.mp3', '.wav', '.m4a'}),
                             ('XLS', {'.csv', '.xlsx', '.xls', '.ods'}), ('DOC', {'.docx', '.doc', '.odt', '.rtf'}),
                             ('PPT', {'.pptx', '.ppt', '.odp'}), ('WEB', {'.url', '.html', '.htm'}),
                             ('</>', {'.py', '.java', '.js', '.c', '.cpp', '.json', '.xml'})]:
        if suffix in extensions:
            return kind
    return 'TXT' if suffix in {'.txt', '.md'} else 'FILE'


def paint_file_icon(painter, rect, entry, color):
    # Extension-only classification: drawing rows never opens/stat-checks files
    # or hydrates cloud placeholders. Text distinguishes types without color.
    painter.save()
    painter.setPen(QPen(color, 1.1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(rect.adjusted(3, 1, -3, -1), 2, 2)
    font = QFont(painter.font())
    font.setPixelSize(8)
    font.setWeight(QFont.Weight.DemiBold)
    painter.setFont(font)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, file_family(entry['path']))
    painter.restore()


class LibraryNavigation(QTreeWidget):
    """Two-level, read-only university/course navigation with stable identities."""
    scopeChanged = Signal()
    manageRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('libraryNavigation')
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setAccessibleName(t('Library navigation'))
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setIndentation(16)
        self.setUniformRowHeights(True)
        self.setExpandsOnDoubleClick(False)
        self.currentItemChanged.connect(lambda *_: self.scopeChanged.emit())

    def scope(self):
        item = self.currentItem()
        return tuple(item.data(0, Qt.ItemDataRole.UserRole)) if item else ('', '')

    def select_scope(self, source_id='', course_id=''):
        for index in range(self.topLevelItemCount()):
            parent = self.topLevelItem(index)
            for item in [parent, *[parent.child(i) for i in range(parent.childCount())]]:
                if tuple(item.data(0, Qt.ItemDataRole.UserRole)) == (source_id, course_id):
                    if item.parent():
                        item.parent().setExpanded(True)
                    self.setCurrentItem(item)
                    return True
        return False

    def populate(self, libraries, scope=None):
        scope = scope if scope is not None else self.scope()
        expanded = {self.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)[0]: self.topLevelItem(i).isExpanded()
                    for i in range(self.topLevelItemCount())}
        scroll = self.verticalScrollBar().value()
        self.blockSignals(True)
        self.clear()
        root = QTreeWidgetItem(self, [t('All materials')])
        root.setData(0, Qt.ItemDataRole.UserRole, ('', ''))
        root.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        for identity, library in libraries.items():
            source = library['source']
            parent = QTreeWidgetItem(self, [source.name])
            parent.setData(0, Qt.ItemDataRole.UserRole, (identity, ''))
            parent.setToolTip(0, source.name + '\n' + source.url)
            from .library import source_summary
            summary = source_summary(library)
            if summary.tone in {'error', 'warning'}:
                parent.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical if summary.tone == 'error'
                                                          else QStyle.StandardPixmap.SP_MessageBoxWarning))
                parent.setToolTip(0, source.name + '\n' + summary.title + '\n' + summary.detail)
            font = parent.font(0)
            font.setWeight(QFont.Weight.DemiBold)
            parent.setFont(0, font)
            for course, name in sorted(library['courses'].items(), key=lambda row: row[1].casefold()):
                child = QTreeWidgetItem(parent, [name])
                child.setData(0, Qt.ItemDataRole.UserRole, (identity, course))
                child.setToolTip(0, name + '\n' + source.name)
            parent.setExpanded(expanded.get(identity, True))
        if not self.select_scope(*scope):
            self.select_scope(scope[0]) or self.select_scope()
        self.verticalScrollBar().setValue(scroll)
        self.blockSignals(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F2 and self.scope()[0]:
            self.manageRequested.emit(self.scope()[0])
        else:
            super().keyPressEvent(event)


class StatusMark(QWidget):
    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.tone = 'neutral'
        self.compact = compact
        self.setFixedSize(22 if compact else 42, 22 if compact else 42)
        self.setAccessibleName(t('Synchronization status'))

    def set_tone(self, tone):
        self.tone = tone
        size = 32 if self.compact and tone == 'error' else 22 if self.compact else 42
        self.setFixedSize(size, size)
        self.setAccessibleName(t('Needs attention') if tone == 'error' else t('Synchronization status'))
        self.update()

    def paintEvent(self, event):
        colors = DARK if self.palette().color(QPalette.ColorRole.Window).lightness() < 128 else LIGHT
        key = {'success': 'success', 'warning': 'warning', 'error': 'error', 'running': 'accent'}.get(self.tone, 'muted')
        color = QColor(colors[key])
        if getattr(getattr(QApplication.instance(), 'theme', None), 'high_contrast', False):
            color = self.palette().color(QPalette.ColorRole.Text)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width() / 42, self.height() / 42)
        if self.tone == 'error':
            high_contrast = getattr(getattr(QApplication.instance(), 'theme', None), 'high_contrast', False)
            fill = self.palette().color(QPalette.ColorRole.Highlight) if high_contrast else QColor(
                '#d63832' if colors is DARK else '#b42318')
            foreground = self.palette().color(QPalette.ColorRole.HighlightedText) if high_contrast else QColor('#ffffff')
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawEllipse(1, 1, 40, 40)
            p.setBrush(foreground)
            p.drawRoundedRect(QRect(19, 9, 4, 17), 2, 2)
            p.drawEllipse(19, 30, 4, 4)
            return
        fill = QColor(color)
        fill.setAlpha(22)
        p.setBrush(fill)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRect(0, 0, 42, 42), 12, 12)
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
    resized = Signal()

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
        self.resized.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Menu or (event.key() == Qt.Key.Key_F10 and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            item = self.item(self.currentRow(), 0)
            if item and not self.isRowHidden(item.row()):
                self.customContextMenuRequested.emit(self.visualItemRect(item).center())
        else:
            super().keyPressEvent(event)


class SyncPanel(QFrame):
    def __init__(self, parent=None, *, compact=False):
        super().__init__(parent)
        self.compact = compact
        self.external_report = False
        self.tone = 'neutral'
        self.setObjectName('compactSync' if compact else 'syncPanel')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 6, 0, 6) if compact else outer.setContentsMargins(18, 17, 18, 15)
        outer.setSpacing(5 if compact else 10)
        row = QHBoxLayout()
        row.setSpacing(8 if compact else 14)
        self.mark = StatusMark(compact=compact)
        row.addWidget(self.mark, alignment=Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(4)
        self.title = ElidedLabel() if compact else QLabel()
        self.title.setObjectName('compactStatusTitle' if compact else 'statusTitle')
        self.title.setWordWrap(not compact)
        self.detail = QLabel()
        self.detail.setObjectName('subtitle')
        self.detail.setWordWrap(True)
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setTextFormat(Qt.TextFormat.PlainText)
        self.detail.setAccessibleName(t('Synchronization status'))
        text.addWidget(self.title)
        if not compact:
            text.addWidget(self.detail)
        row.addLayout(text, 1)
        self.recovery_layout = row
        self.disclosure = QPushButton(t('Details'))
        self.disclosure.setObjectName('compactControl')
        self.disclosure.setCheckable(True)
        self.disclosure.setAccessibleName(t('Show synchronization details'))
        self.disclosure.setToolTip(t('Show synchronization details'))
        self.disclosure.setVisible(compact)
        self.disclosure.toggled.connect(self.set_expanded)
        if compact:
            row.addWidget(self.disclosure)
        outer.addLayout(row)
        if compact:
            outer.addWidget(self.detail)
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
        self.schedule = ElidedLabel()
        self.schedule.setObjectName('statusMeta')
        self.schedule.setVisible(compact)
        outer.addWidget(self.schedule)
        self.report_host = QScrollArea()
        self.report_host.setWidgetResizable(True)
        self.report_host.setFrameShape(QFrame.Shape.NoFrame)
        self.report_host.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.report_host.setMinimumHeight(100)
        self.report_host.setMaximumHeight(200)
        self.report_body = QWidget()
        self.report_layout = QVBoxLayout(self.report_body)
        self.report_layout.setContentsMargins(0, 0, 0, 0)
        self.report_host.setWidget(self.report_body)
        self.report_host.hide()
        outer.addWidget(self.report_host)
        self.set_expanded(False)

    def set_expanded(self, expanded):
        self.detail.setVisible(not self.compact or (expanded and not self.external_report) or self.tone == 'error')
        self.meta.setVisible(True)
        if not self.external_report:
            self.report_host.setVisible(self.compact and expanded)
        self.disclosure.setText(t('Hide details') if expanded else t('Details'))
        self.disclosure.setAccessibleName(t('Hide synchronization details') if expanded else t('Show synchronization details'))
        self.update_minimum_height()

    def set_state(self, title, detail, tone, *, busy=False):
        self.title.setText(title)
        self.detail.setText(detail)
        self.detail.setAccessibleName(detail)
        tone_changed = self.property('tone') != tone
        self.tone = tone
        if tone_changed:
            self.setProperty('tone', tone)
            if self.compact:
                self.layout().setContentsMargins(10, 8, 10, 8) if tone == 'error' else self.layout().setContentsMargins(0, 6, 0, 6)
                self.layout().setSpacing(8 if tone == 'error' else 5)
            for widget in (self, self.title):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
        self.mark.set_tone(tone)
        self.progress.setVisible(busy)
        self.set_expanded(self.disclosure.isChecked())
        self.update_minimum_height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_minimum_height()

    def update_minimum_height(self):
        if self.compact:
            self.setMinimumHeight(0)
            return
        title_height = max(self.title.fontMetrics().height() + 2, self.title.heightForWidth(max(120, self.title.width())))
        detail_height = max(self.detail.fontMetrics().height() + 2, self.detail.heightForWidth(max(120, self.detail.width())))
        meta_height = max(self.meta.fontMetrics().height() + 2, self.meta.heightForWidth(max(120, self.width() - 36)))
        minimum = 32 + max(42, title_height + detail_height + 4) + meta_height + 10
        if not self.progress.isHidden():
            minimum += 13
        if self.minimumHeight() != minimum:
            self.setMinimumHeight(minimum)
