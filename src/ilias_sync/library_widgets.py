"""Small native widgets for readable materials and non-modal synchronization feedback."""
from pathlib import PurePosixPath

from PySide6.QtCore import QEvent, QRect, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPalette, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QBoxLayout, QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QStyle,
                              QStyledItemDelegate, QStyleOptionViewItem, QTableWidget, QVBoxLayout, QWidget,
                              QTreeWidget, QTreeWidgetItem, QToolTip)
from PySide6.QtWidgets import QScrollArea

from .branding import action_pixmap
from .i18n import t
from .hints import hint_text, set_hint
from .motion import FadeButton, QuietDelegate, RowHover
from .theme import CARD_INSET, DARK, LIGHT, is_dark


class ElidedLabel(QLabel):
    """Keep complete text accessible; hover only reveals otherwise clipped text."""
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
        self.setAccessibleName(text)
        self._fit_text()

    def _fit_text(self):
        shown = self.fontMetrics().elidedText(self.full_text, Qt.TextElideMode.ElideRight, max(1, self.width()))
        super().setText(shown)
        if not self.property('helpHint'):
            self.setToolTip(hint_text(self.full_text) if shown != self.full_text else '')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_text()


class MaterialDelegate(QStyledItemDelegate):
    def needs_hint(self, option, index):
        entry = index.data(Qt.ItemDataRole.UserRole + 1) or {}
        if index.column() != 0 or not entry:
            return option.fontMetrics.horizontalAdvance(str(index.data() or '')) > option.rect.width() - 8
        width = max(0, option.rect.width() - 56)
        font = QFont(option.font)
        font.setWeight(QFont.Weight.Medium)
        if QFontMetrics(font).horizontalAdvance(PurePosixPath(entry['path']).name) > width:
            return True
        font.setPixelSize(max(11, round(option.fontMetrics.height() * 0.78)))
        font.setWeight(QFont.Weight.Normal)
        context = material_context(entry, getattr(option.widget, 'library_scope', 'source'))
        return QFontMetrics(font).horizontalAdvance(context) > width

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.Type.ToolTip and not self.needs_hint(option, index):
            QToolTip.hideText()
            return True
        return super().helpEvent(event, view, option, index)

    def paint(self, painter, option, index):
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        self._row_chip(painter, option, index, selected)
        if index.column() != 0:
            self._paint_quiet(painter, option, index)
            return
        entry = index.data(Qt.ItemDataRole.UserRole + 1) or {}
        if not entry:
            self._paint_quiet(painter, option, index)
            return
        styled = self._quiet_option(option, index)
        styled.text = ''
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, option.widget)
        color = option.palette.color(QPalette.ColorRole.Text)
        colors = DARK if is_dark(option.palette) else LIGHT
        high_contrast = getattr(getattr(QApplication.instance(), 'theme', None), 'high_contrast', False)
        muted = color if high_contrast else QColor(colors['muted'])
        painter.save()
        paint_file_icon(painter, QRect(option.rect.left() + 10, option.rect.center().y() - 12, 26, 26), entry, muted)
        text_rect = option.rect.adjusted(46, 3, -10, -3)
        font = QFont(option.font)
        font.setWeight(QFont.Weight.Medium)
        context_font = QFont(font)
        context_font.setPixelSize(max(11, round(option.fontMetrics.height() * 0.78)))
        context_font.setWeight(QFont.Weight.Normal)
        context = material_context(entry, getattr(option.widget, 'library_scope', 'source'))
        line_height = QFontMetrics(font).height() + 1
        context_height = QFontMetrics(context_font).height() + 2 if context else 0
        top = text_rect.top() + max(0, (text_rect.height() - line_height - context_height) // 2)
        painter.setFont(font)
        painter.setPen(color)
        title = PurePosixPath(entry['path']).name
        painter.drawText(QRect(text_rect.left(), top, text_rect.width(), line_height),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(title, Qt.TextElideMode.ElideMiddle, text_rect.width()))
        painter.setFont(context_font)
        painter.setPen(muted)
        painter.drawText(QRect(text_rect.left(), top + line_height, text_rect.width(), context_height),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(context, Qt.TextElideMode.ElideRight, text_rect.width()))
        painter.restore()

    def _quiet_option(self, option, index):
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.state &= ~(QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus)
        styled.backgroundBrush = QBrush(Qt.BrushStyle.NoBrush)
        styled.palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 0, 0, 0))
        return styled

    def _paint_quiet(self, painter, option, index):
        styled = self._quiet_option(option, index)
        widget = option.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, widget)

    def _row_chip(self, painter, option, index, selected):
        widget = option.widget
        hover = getattr(widget, '_row_hover', None)
        amount = 1.0 if selected else (hover.amount if hover is not None and hover.matches(index) else 0.0)
        if amount <= 0 or widget is None:
            return
        from .theme import DARK, LIGHT
        dark = is_dark(option.palette)
        color = QColor((DARK if dark else LIGHT)['selection' if selected else 'hover'])
        color.setAlphaF(amount)
        rect = QRectF(6, option.rect.top() + 3, max(0, widget.viewport().width() - 12), option.rect.height() - 6)
        painter.save()
        painter.setClipRect(option.rect)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 12, 12)
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
        painter.setPen(QPen(color, 1.25))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        page = rect.adjusted(6, 2, -6, -2)
        painter.drawRoundedRect(page, 2, 2)
        painter.drawLine(page.left() + 3, page.top() + 6, page.right() - 3, page.top() + 6)
        font = QFont(painter.font())
        font.setPixelSize(7)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(page.adjusted(0, 4, 0, 0), Qt.AlignmentFlag.AlignCenter, file_family(entry['path']))
        painter.restore()


class LibraryNavigation(QTreeWidget):
    """Two-level, read-only university/course navigation with stable identities."""
    scopeChanged = Signal()
    manageRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('libraryNavigation')
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setItemDelegate(QuietDelegate(self))
        self._row_hover = RowHover(self)
        self._quieting = False
        self.quiet_selection()
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setAccessibleName(t('Library navigation'))
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setIndentation(22)
        self.setUniformRowHeights(True)
        self.setItemsExpandable(True)
        self.setRootIsDecorated(True)
        self.setExpandsOnDoubleClick(False)
        self.currentItemChanged.connect(lambda *_: self.scopeChanged.emit())

    def quiet_selection(self):
        if self._quieting:
            return
        self._quieting = True
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.HighlightedText, palette.color(QPalette.ColorRole.Text))
        self.setPalette(palette)
        self._quieting = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self.quiet_selection()

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
        colors = DARK if is_dark(self.palette()) else LIGHT
        for identity, library in libraries.items():
            source = library['source']
            parent = QTreeWidgetItem(self, [source.name])
            parent.setData(0, Qt.ItemDataRole.UserRole, (identity, ''))
            parent.setToolTip(0, hint_text(source.name))
            parent.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, source.url)
            from .library import source_summary
            summary = source_summary(library)
            if summary.tone in {'error', 'warning'}:
                parent.setForeground(0, QColor(colors['error' if summary.tone == 'error' else 'warning']))
                parent.setToolTip(0, hint_text(source.name, summary.title))
                parent.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, summary.title + '\n' + summary.detail)
            font = parent.font(0)
            font.setWeight(QFont.Weight.DemiBold)
            parent.setFont(0, font)
            for course, name in sorted(library['courses'].items(), key=lambda row: row[1].casefold()):
                child = QTreeWidgetItem(parent, [name])
                child.setData(0, Qt.ItemDataRole.UserRole, (identity, course))
                child.setToolTip(0, hint_text(name))
            parent.setExpanded(expanded.get(identity, True))
        if not self.select_scope(*scope):
            self.select_scope(scope[0]) or self.select_scope()
        self.verticalScrollBar().setValue(scroll)
        self.blockSignals(False)

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.ToolTip:
            item = self.itemAt(event.pos())
            if item is not None:
                width = self.visualItemRect(item).width() - 20
                if QFontMetrics(item.font(0).resolve(self.font())).horizontalAdvance(item.text(0)) <= width:
                    QToolTip.hideText()
                    return True
        return super().viewportEvent(event)

    def drawRow(self, painter, option, index):
        item = self.itemFromIndex(index)
        content = self.visualItemRect(item) if item is not None else QRect()
        if item is not None and content.left() > option.rect.left():
            painter.save()
            painter.setClipRect(QRect(content.left(), option.rect.top(), max(1, option.rect.right() - content.left() + 1), option.rect.height()),
                                Qt.ClipOperation.IntersectClip)
            super().drawRow(painter, option, index)
            painter.restore()
            branch = QRect(content.left() - self.indentation(), option.rect.top(), self.indentation(), option.rect.height())
            self.drawBranches(painter, branch, index)
            return
        super().drawRow(painter, option, index)

    def drawBranches(self, painter, rect, index):
        item = self.itemFromIndex(index)
        if item is None or item.childCount() == 0:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.palette().color(QPalette.ColorRole.Text)
        color.setAlpha(170)
        painter.setPen(QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        center = rect.center()
        if item.isExpanded():
            painter.drawLine(center.x() - 4, center.y() - 1, center.x(), center.y() + 3)
            painter.drawLine(center.x(), center.y() + 3, center.x() + 4, center.y() - 1)
        else:
            painter.drawLine(center.x() - 2, center.y() - 4, center.x() + 2, center.y())
            painter.drawLine(center.x() + 2, center.y(), center.x() - 2, center.y() + 4)
        painter.restore()

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        if item is not None and item.childCount():
            row = self.visualItemRect(item)
            chevron = QRect(row.left() - self.indentation(), row.top(), self.indentation(), row.height())
            if chevron.contains(pos):
                item.setExpanded(not item.isExpanded())
                return
        super().mousePressEvent(event)

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
        self._angle = 0.0
        self._spin = QVariantAnimation(self)
        self._spin.setDuration(1400)
        self._spin.setStartValue(0.0)
        self._spin.setEndValue(360.0)
        self._spin.setLoopCount(-1)
        self._spin.valueChanged.connect(self._turn)
        size = 32 if compact else 28
        self.setFixedSize(size, size)
        self.setAccessibleName(t('Synchronization status'))

    def _turn(self, value):
        self._angle = float(value)
        self.update()

    def set_tone(self, tone):
        self.tone = tone
        if tone == 'running':
            if self._spin.state() != self._spin.State.Running:
                self._spin.start()
        else:
            self._spin.stop()
            self._angle = 0.0
        name = t('Needs attention') if tone == 'error' else t('Synchronized') if tone == 'success' else t('Synchronization status')
        self.setAccessibleName(name)
        self.update()

    def paintEvent(self, event):
        if self.compact:
            self._paint_compact()
            return
        colors = DARK if self.palette().color(QPalette.ColorRole.Text).lightness() > 128 else LIGHT
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

    def _paint_compact(self):
        colors = DARK if self.palette().color(QPalette.ColorRole.Text).lightness() > 128 else LIGHT
        high_contrast = getattr(getattr(QApplication.instance(), '_ilias_theme_manager', None), 'high_contrast', False)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        key = {'success': 'success', 'warning': 'warning', 'running': 'accent', 'error': 'error'}.get(self.tone, 'muted')
        color = self.palette().color(QPalette.ColorRole.Text) if high_contrast else QColor(colors[key])
        fill = QColor(color)
        fill.setAlpha(34 if colors is DARK else 22)
        if self.tone == 'error':
            fill = self.palette().color(QPalette.ColorRole.Highlight) if high_contrast else QColor(colors['error_fill'])
            color = self.palette().color(QPalette.ColorRole.HighlightedText) if high_contrast else QColor('#ffffff')
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(self.rect()), 10, 10)
        if self.tone == 'success':
            self._paint_check(p, color)
            return
        if self.tone == 'running':
            self._paint_sync(p, color, self._angle)
            return
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self.tone in {'warning', 'error'}:
            p.drawLine(16, 9, 16, 17)
            p.drawPoint(16, 22)
        else:
            p.drawEllipse(9, 9, 14, 14)
            p.drawLine(16, 12, 16, 16)
            p.drawLine(16, 16, 19, 17)

    def _paint_check(self, painter, color):
        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        side = min(self.width(), self.height())
        painter.drawLine(int(side * 0.29), int(side * 0.51), int(side * 0.44), int(side * 0.66))
        painter.drawLine(int(side * 0.44), int(side * 0.66), int(side * 0.72), int(side * 0.36))

    def _paint_sync(self, painter, color, angle):
        size = 18
        pixmap = action_pixmap('rotate-cw', color.name(), size, self.devicePixelRatioF())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(angle)
        painter.drawPixmap(-size // 2, -size // 2, pixmap)
        painter.restore()


class MaterialTable(QTableWidget):
    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(0, 3, parent)
        self.empty = QWidget(self.viewport())
        self.empty.setObjectName('libraryEmpty')
        self.empty.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self.empty)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(6)
        self.empty_title = QLabel()
        self.empty_title.setObjectName('sectionTitle')
        self.empty_body = QLabel()
        self.empty_body.setObjectName('subtitle')
        for item in (self.empty_title, self.empty_body):
            item.setWordWrap(True)
            item.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            layout.addWidget(item)
        self._fitting_empty = False
        self.empty.hide()
        self._row_hover = RowHover(self)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self._quieting = False
        self._quiet_highlight()

    def _quiet_highlight(self):
        if self._quieting:
            return
        self._quieting = True
        colors = DARK if self.palette().color(QPalette.ColorRole.Text).lightness() > 128 else LIGHT
        palette = self.palette()
        # The style paints Highlight as a sharp rectangle. The delegate draws the rounded chip.
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors['text']))
        self.setPalette(palette)
        self._quieting = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self._quiet_highlight()

    def set_empty(self, title, detail):
        self.empty_title.setText(title)
        self.empty_body.setText(detail)
        self.empty.setVisible(bool(title))
        self._place_empty()

    def _place_empty(self):
        if self._fitting_empty:
            return
        self.empty.setGeometry(self.viewport().rect())
        if not self.empty.isVisible() or self.rowCount():
            return
        width = self.viewport().width()
        if width < 40:
            return
        margins = self.empty.layout().contentsMargins()
        inner = max(40, width - margins.left() - margins.right())
        self.empty_title.setMaximumWidth(inner)
        self.empty_body.setMaximumWidth(inner)
        flags = int(Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap)
        title_h = self.empty_title.fontMetrics().boundingRect(0, 0, inner, 2000, flags, self.empty_title.text()).height()
        body_h = self.empty_body.fontMetrics().boundingRect(0, 0, inner, 2000, flags, self.empty_body.text()).height()
        self.empty_title.setMinimumHeight(title_h)
        self.empty_body.setMinimumHeight(body_h)
        height = margins.top() + margins.bottom() + self.empty.layout().spacing() + title_h + body_h
        if height > 0 and self.height() != height:
            self._fitting_empty = True
            self.setFixedHeight(height)
            self.empty.setGeometry(self.viewport().rect())
            self._fitting_empty = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_empty()
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
        self.mark = StatusMark(compact=compact)
        self.title = QLabel()
        self.title.setObjectName('compactStatusTitle' if compact else 'statusTitle')
        self.detail = QLabel()
        self.detail.setObjectName('compactStatusDetail' if compact else 'subtitle')
        self.detail.setAccessibleName(t('Synchronization status'))
        self.meta = QLabel()
        self.meta.setObjectName('statusMeta')
        self.schedule = QLabel()
        self.schedule.setObjectName('statusMeta')
        self.schedule.setVisible(compact)
        self.disclosure = FadeButton(t('Details'))
        self.disclosure.setObjectName('compactControl')
        self.disclosure.setCheckable(True)
        self.disclosure.setAccessibleName(t('Show synchronization details'))
        self.disclosure.setVisible(compact)
        self.disclosure.toggled.connect(self.set_expanded)
        self.exception_host = QWidget()
        exception_row = QHBoxLayout(self.exception_host)
        exception_row.setContentsMargins(0, 0, 0, 0)
        exception_row.setSpacing(8)
        self.exception = QLabel()
        self.exception.setObjectName('compactStatusDetail' if compact else 'subtitle')
        self.exception_dismiss = FadeButton(t('Ignore'))
        self.exception_dismiss.setObjectName('exceptionDismiss')
        set_hint(self.exception_dismiss, t('Ignore'), t('Skip these unavailable files in future syncs. Existing local copies stay.'))
        self.exception_dismiss.setAccessibleName(t('Skip these unavailable files in future syncs. Existing local copies stay.'))
        exception_row.addWidget(self.exception, 1)
        exception_row.addWidget(self.exception_dismiss, 0)
        self.exception_host.hide()
        for label in (self.title, self.detail, self.meta, self.schedule, self.exception):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            policy = label.sizePolicy()
            policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored if compact else QSizePolicy.Policy.Preferred)
            policy.setVerticalPolicy(QSizePolicy.Policy.Maximum)
            label.setSizePolicy(policy)
        if compact:
            self._compose_card(outer)
        else:
            outer.setContentsMargins(0, 14, 0, 12)
            outer.setSpacing(10)
            row = QHBoxLayout()
            row.setSpacing(14)
            row.addWidget(self.mark, alignment=Qt.AlignmentFlag.AlignVCenter)
            text = QVBoxLayout()
            text.addWidget(self.title)
            text.addWidget(self.detail)
            row.addLayout(text, 1)
            outer.addLayout(row)
            outer.addWidget(self.exception_host)
        self.progress = QProgressBar()
        self.progress.setAccessibleName(t('Synchronization progress'))
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        outer.addWidget(self.progress)
        if not compact:
            outer.addWidget(self.meta)
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

    def _compose_card(self, outer):
        outer.setContentsMargins(CARD_INSET, 12, CARD_INSET, 12)
        outer.setSpacing(0)
        self._card_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._card_row.setSpacing(12)
        status = QHBoxLayout()
        status.setSpacing(12)
        status.addWidget(self.mark, alignment=Qt.AlignmentFlag.AlignVCenter)
        self._summary = QVBoxLayout()
        self._summary.setSpacing(3)
        self._summary.addWidget(self.title)
        self._summary.addWidget(self.meta)
        self._summary.addWidget(self.schedule)
        status.addLayout(self._summary, 1)
        self._card_row.addLayout(status, 1)
        self.action_layout = QHBoxLayout()
        self.action_layout.setSpacing(0)
        self.action_layout.addStretch(1)
        self.action_layout.addWidget(self.disclosure, alignment=Qt.AlignmentFlag.AlignVCenter)
        self._card_row.addLayout(self.action_layout)
        outer.addLayout(self._card_row)
        self._detail_body = QWidget()
        self._body_layout = QVBoxLayout(self._detail_body)
        self._body_layout.setContentsMargins(self.mark.width() + status.spacing(), 8, 0, 22)
        self._body_layout.setSpacing(6)
        self._body_layout.addWidget(self.detail)
        self._body_layout.addWidget(self.exception_host)
        self._detail_body.hide()
        self._body_open = False
        outer.addWidget(self._detail_body)

    def adapt_actions(self):
        if not self.compact:
            return
        # Give text a comfortable reading column; stack only when both sides
        # cannot fit. The same action slot is shared by sync, pause and stop.
        available = self.width() - 2 * CARD_INSET
        actions = self.action_layout.minimumSize().width()
        beside = self.mark.width() + 12 + 192 + self._card_row.spacing() + actions
        direction = (QBoxLayout.Direction.TopToBottom if actions and available < beside
                     else QBoxLayout.Direction.LeftToRight)
        if self._card_row.direction() != direction:
            self._card_row.setDirection(direction)
        margins = self._body_layout.contentsMargins()
        top = 22 if direction == QBoxLayout.Direction.TopToBottom else 8
        if margins.top() != top:
            self._body_layout.setContentsMargins(margins.left(), top, margins.right(), 22)

    def set_expanded(self, expanded):
        self._update_detail(expanded)
        self.meta.setVisible(True)
        if not self.external_report:
            self.report_host.setVisible(self.compact and expanded)
        self.disclosure.setText(t('Hide details') if expanded else t('Details'))
        self.disclosure.setAccessibleName(t('Hide synchronization details') if expanded else t('Show synchronization details'))
        self.update_minimum_height()

    def _update_detail(self, expanded):
        has_detail = bool(self.detail.text() and self.detail.text() != self.title.text())
        if self.compact:
            has_exception = not self.exception_host.isHidden()
            has_detail &= not has_exception and (self.tone != 'success' or (expanded and not self.external_report))
            body_open = has_detail or has_exception
            if body_open != self._body_open:
                self._body_open = body_open
                old, new = (self._summary, self._body_layout) if body_open else (self._body_layout, self._summary)
                for fact in (self.meta, self.schedule):
                    old.removeWidget(fact)
                    new.addWidget(fact)
                self._detail_body.setVisible(body_open)
        self.detail.setVisible(has_detail)

    def set_state(self, title, detail, tone, *, busy=False):
        self.title.setText(title)
        self.detail.setText(detail)
        self.detail.setAccessibleName(detail)
        tone_changed = self.property('tone') != tone
        self.tone = tone
        if tone_changed:
            self.setProperty('tone', tone)
            for widget in (self, self.title):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
        self.mark.set_tone(tone)
        if not busy:
            self.progress.setRange(0, 0)
            self.progress.setValue(0)
        self.progress.setVisible(busy)
        self.set_expanded(self.disclosure.isChecked())
        self.update_minimum_height()

    def set_exception(self, text, *, dismiss=False):
        self.exception.setText(text)
        self.exception_dismiss.setVisible(bool(dismiss))
        self.exception_host.setVisible(bool(text))
        self._update_detail(self.disclosure.isChecked())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adapt_actions()
        self.update_minimum_height()

    def event(self, event):
        handled = super().event(event)
        if event.type() == QEvent.Type.LayoutRequest and getattr(self, 'compact', False):
            self.update_minimum_height()
        return handled

    def update_minimum_height(self):
        if self.compact:
            self.adapt_actions()
            layout = self.layout()
            minimum = layout.totalHeightForWidth(self.width())
            if minimum < 0:
                minimum = layout.totalSizeHint().height()
            if self.minimumHeight() != minimum:
                self.setMinimumHeight(minimum)
            return
        title_height = max(self.title.fontMetrics().height() + 2, self.title.heightForWidth(max(120, self.title.width())))
        detail_height = max(self.detail.fontMetrics().height() + 2, self.detail.heightForWidth(max(120, self.detail.width())))
        meta_height = max(self.meta.fontMetrics().height() + 2, self.meta.heightForWidth(max(120, self.width() - 36)))
        minimum = 32 + max(42, title_height + detail_height + 4) + meta_height + 10
        if not self.progress.isHidden():
            minimum += 13
        if self.minimumHeight() != minimum:
            self.setMinimumHeight(minimum)
