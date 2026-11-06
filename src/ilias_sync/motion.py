"""Short hover fades measured from the Cursor and Grok Bot interfaces.

Those surfaces fade a wash in 140ms and settle a press in about 120ms.
Qt stylesheets cannot interpolate those states, so the widgets animate them.
"""
from PySide6.QtCore import QEasingCurve, QEvent, QModelIndex, QObject, QPersistentModelIndex, QRectF, QVariantAnimation, Qt
from PySide6.QtGui import QBitmap, QColor, QFont, QPainter, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QGraphicsOpacityEffect, QMenu, QPushButton,
                              QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget)

from .i18n import t
from .control_colors import pause_colors
from .theme import popup_color, uses_native_backdrop

def popup(menu, anchor):
    """Open a menu from a control without replaying that control's hover."""
    if isinstance(anchor, FadeButton):
        anchor.dismiss_hover()
    menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
    if isinstance(anchor, FadeButton):
        anchor.release_popup()


def clip_round(widget, radius=12):
    """Drop the square window that otherwise frames a rounded popup."""
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    width, height = max(1, widget.width()), max(1, widget.height())
    bitmap = QBitmap(width, height)
    bitmap.fill(Qt.GlobalColor.color0)
    painter = QPainter(bitmap)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(Qt.GlobalColor.color1)
    painter.drawRoundedRect(0, 0, width, height, radius, radius)
    painter.end()
    widget.setMask(bitmap)


class PopupChipDelegate(QStyledItemDelegate):
    """A light rounded row. The style's own highlight is a blue rectangle."""

    def paint(self, painter, option, index):
        hot = bool(option.state & (QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_MouseOver))
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.state &= ~(QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus)
        if hot:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            dark = option.palette.color(QPalette.ColorRole.Text).lightness() > 128
            painter.setBrush(wash(dark))
            painter.drawRoundedRect(QRectF(option.rect.adjusted(4, 2, -4, -2)), 8, 8)
            painter.restore()
        widget = option.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, widget)


class RowHover(QObject):
    """Fades the row under the pointer instead of snapping the fill on."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.index = QPersistentModelIndex()
        self.amount = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(90)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._apply)
        view.setMouseTracking(True)
        view.viewport().setMouseTracking(True)
        view.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind == QEvent.Type.MouseMove:
            pos = event.position().toPoint()
            index = self.view.indexAt(pos)
            label = self._label_rect(index)
            if label is not None and not label.contains(pos):
                index = QModelIndex()
            self._aim(index)
        elif kind == QEvent.Type.Leave:
            self._aim(QPersistentModelIndex())
        return False

    def _aim(self, index):
        if QPersistentModelIndex(index) == self.index:
            return
        self.index = QPersistentModelIndex(index)
        self.animation.stop()
        self.animation.setStartValue(0.0 if self.index.isValid() else self.amount)
        self.animation.setEndValue(1.0 if self.index.isValid() else 0.0)
        self.animation.start()

    def _apply(self, value):
        self.amount = float(value)
        self.view.viewport().update()

    def _label_rect(self, index):
        """Sidebar rows include an empty gutter. Hover belongs on the name, not left of it."""
        view = self.view
        if not index.isValid() or view.objectName() != 'libraryNavigation':
            return None
        item = view.itemFromIndex(index)
        return view.visualItemRect(item) if item is not None else None

    def matches(self, index):
        current = self.index
        return (current.isValid() and self.amount > 0 and index.row() == current.row()
                and index.parent().internalId() == current.parent().internalId())


def wash(dark, amount=1.0):
    """One light chip for rows, menus and ghost controls. Strength, not a darker fill."""
    amount = max(0.0, min(1.0, float(amount)))
    if dark:
        return QColor(255, 255, 255, round(78 * amount))
    return QColor(20, 20, 20, round(28 * amount))


def paint_row_wash(painter, option, index):
    """A 7% white wash, the same step as Cursor's list hover, faded over 140ms."""
    hover = getattr(option.widget, '_row_hover', None)
    selected = bool(option.state & QStyle.StateFlag.State_Selected)
    if selected or hover is None or not hover.matches(index):
        return
    dark = option.palette.color(QPalette.ColorRole.Text).lightness() > 128
    color = QColor(240, 240, 240, round(17 * hover.amount)) if dark else QColor(20, 20, 20, round(20 * hover.amount))
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRect(option.rect)
    painter.restore()


class QuietDelegate(QStyledItemDelegate):
    """Lets the animated wash own the hover, so the style does not flash a second fill."""

    def paint(self, painter, option, index):
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        selected = bool(styled.state & QStyle.StateFlag.State_Selected)
        styled.state &= ~(QStyle.StateFlag.State_MouseOver | QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus)
        self._chip(painter, option, index, False)
        if selected:
            font = styled.font
            font.setWeight(QFont.Weight.DemiBold)
            styled.font = font
        widget = option.widget
        style = widget.style() if widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, widget)

    def _chip(self, painter, option, index, selected):
        hover = getattr(option.widget, '_row_hover', None)
        amount = 1.0 if selected else (hover.amount if hover is not None and hover.matches(index) else 0.0)
        if amount <= 0:
            return
        dark = option.palette.color(QPalette.ColorRole.Text).lightness() > 128
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(wash(dark, amount))
        view = option.widget
        rect = QRectF(option.rect.adjusted(4, 2, -4, -2))
        if view is not None and view.objectName() == 'libraryNavigation':
            item = view.itemFromIndex(index)
            if item is not None:
                rect = QRectF(view.visualItemRect(item).adjusted(2, 2, -4, -2))
        painter.drawRoundedRect(rect, 10, 10)
        painter.restore()


class FadeButton(QPushButton):
    """A control whose hover wash eases in and whose press settles a step darker."""

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._hover = 0.0
        self._pressed = False
        self._inside = False
        self._hold_hover = False
        self._popup_lock = False
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(90)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.valueChanged.connect(self._set_hover)

    def _set_hover(self, value):
        self._hover = float(value)
        self.update()

    def _fade(self, target, duration):
        target = float(target)
        if self._hover_animation.state() == self._hover_animation.State.Running and float(self._hover_animation.endValue()) == target:
            return
        if abs(self._hover - target) < 0.02:
            self._hover = target
            self.update()
            return
        self._hover_animation.stop()
        self._hover_animation.setDuration(duration)
        self._hover_animation.setStartValue(self._hover)
        self._hover_animation.setEndValue(target)
        self._hover_animation.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        if self._hold_hover:
            return
        self._inside = True
        self._fade(1.0, 90)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._inside = False
        self._pressed = False
        if not self._popup_lock:
            self._hold_hover = False
        self._fade(0.0, 110)

    def mousePressEvent(self, event):
        # A click must not replay the wash that is already showing.
        self._hold_hover = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        super().mouseReleaseEvent(event)

    def dismiss_hover(self):
        """Drop the wash while a menu is open, and ignore the click's extra enter."""
        self._popup_lock = True
        self._hold_hover = True
        self._inside = False
        self._pressed = False
        self._hover_animation.stop()
        self._hover = 0.0
        self.update()

    def release_popup(self):
        self._popup_lock = False
        self._hold_hover = False
        if self.underMouse():
            self._inside = True
            self._fade(1.0, 90)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.objectName() in {'primary', 'syncAction', 'quiet', 'commit', 'pauseControl', 'stopControl'}:
            return
        if self._hover <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        dark = self.palette().color(QPalette.ColorRole.Text).lightness() > 128
        painter.setBrush(wash(dark, self._hover))
        if self.objectName() == 'sidebarAction':
            radius = 10
        elif self.objectName() == 'iconControl':
            radius = self.height() / 2
        else:
            radius = 10
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)


class MotionMenu(QMenu):
    """Fade in without moving Qt's screen-constrained popup geometry."""

    def __init__(self, *args):
        super().__init__(*args)
        self._use_frost = uses_native_backdrop(QApplication.instance())
        if self._use_frost:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)
        self._showing = False
        self._motion = None

    def addMenu(self, *args):
        if len(args) == 1 and isinstance(args[0], str):
            child = MotionMenu(args[0], self)
            super().addMenu(child)
            return child
        return super().addMenu(*args)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._use_frost or self._showing:
            return
        self._showing = True
        self.setWindowOpacity(0)
        clip_round(self, 12)
        self._run(0.0, 1.0, 160)
        self._showing = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Cocoa can finalize a menu's size after Show. A mask from the small
        # initial window would otherwise clip the actions that appear later.
        if self._use_frost:
            clip_round(self, 12)

    def paintEvent(self, event):
        if not self._use_frost:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = popup_color(QApplication.palette())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        painter.end()
        super().paintEvent(event)

    def hideEvent(self, event):
        if self._motion:
            self._motion.stop()
            self.setWindowOpacity(1)
        super().hideEvent(event)

    def _run(self, start, end, duration, done=None):
        if self._motion:
            self._motion.stop()
        motion = QVariantAnimation(self)
        motion.setDuration(duration)
        motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        motion.setStartValue(float(start))
        motion.setEndValue(float(end))
        def step(value):
            amount = float(value)
            self.setWindowOpacity(amount)

        motion.valueChanged.connect(step)
        if done:
            motion.finished.connect(done)
        self._motion = motion
        motion.start()


class Switch(QCheckBox):
    """A 36×22 pill. The knob travels in 140ms; the track uses the measured green."""

    def __init__(self, name=''):
        super().__init__()
        self.setAccessibleName(name)
        self.setFixedSize(36, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._knob = 0.0
        self._motion = QVariantAnimation(self)
        self._motion.setDuration(140)
        self._motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._motion.valueChanged.connect(self._set_knob)
        self.toggled.connect(self._travel)

    def _set_knob(self, value):
        self._knob = float(value)
        self.update()

    def _travel(self, checked):
        self._motion.stop()
        self._motion.setStartValue(self._knob)
        self._motion.setEndValue(1.0 if checked else 0.0)
        self._motion.start()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        dark = self.palette().color(QPalette.ColorRole.Text).lightness() > 128
        painter.setBrush(QColor('#3fa266') if self.isChecked() else QColor('#3a3a3a' if dark else '#d4d4d4'))
        painter.drawRoundedRect(self.rect(), 11, 11)
        painter.setBrush(QColor('#f4f4f4') if dark else QColor('#ffffff'))
        painter.drawEllipse(QRectF(2 + self._knob * 14, 2, 18, 18))


class SyncCluster(QWidget):
    """Morphs the labeled sync action into pause and stop without moving either."""

    ROW = 36
    GAP = 8

    def __init__(self, sync, pause, stop):
        super().__init__()
        self.sync = sync
        self.pause = pause
        self.stop = stop
        self.setAutoFillBackground(False)
        self._effects = {}
        for button in (sync, pause, stop):
            button.setParent(self)
            effect = QGraphicsOpacityEffect(button)
            effect.setOpacity(1 if button is sync else 0)
            button.setGraphicsEffect(effect)
            self._effects[button] = effect
        self.pause.hide()
        self.stop.hide()
        self._mode = None
        self._motion = None
        self._span = 0.0
        self._shaped = False
        self._rest_width = 0
        self._width_key = None
        self.setFixedHeight(self.ROW)

    def set_mode(self, mode):
        if mode == 'hidden':
            self._stop_motion()
            self._mode = mode
            self.setFixedSize(0, self.ROW)
            for button in (self.sync, self.pause, self.stop):
                button.hide()
            return
        self._ensure_size()
        self._place()
        if mode == self._mode:
            return
        opening = self._mode is not None
        self._mode = mode
        self.sync.show()
        self.sync.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, mode == 'running')
        if mode == 'running':
            self.pause.show()
            self.stop.show()
            self.pause.raise_()
            self.stop.raise_()
        if not opening:
            self._span = 1.0 if mode == 'running' else 0.0
            self._settle()
            return
        self._set_shaped(True)
        self._animate_to(1.0 if mode == 'running' else 0.0)

    def _ensure_size(self):
        button = self.sync
        labels = (t('Sync now'), t('Sync all'))
        key = (button.font().family(), button.font().pixelSize(), button.font().pointSize(), labels)
        if key != self._width_key or not self._rest_width:
            current = button.text()
            minimum, maximum = button.minimumWidth(), button.maximumWidth()
            button.setUpdatesEnabled(False)
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            width = 120
            for label in labels:
                button.setText(label)
                width = max(width, button.sizeHint().width())
            button.setText(current)
            button.setMinimumWidth(minimum)
            button.setMaximumWidth(maximum)
            button.setUpdatesEnabled(True)
            self._width_key = key
            self._rest_width = width
        if self.width() != self._rest_width or self.height() != self.ROW:
            self.setFixedSize(self._rest_width, self.ROW)

    def _place(self):
        width = self._rest_width or self.width()
        icon = self.ROW
        self.sync.setFixedSize(width, self.ROW)
        self.sync.move(0, 0)
        self.pause.setFixedSize(icon, icon)
        self.stop.setFixedSize(icon, icon)
        self.stop.move(width - icon, 0)
        self.pause.move(width - icon - self.GAP - icon, 0)

    def _animate_to(self, target):
        self._stop_motion()
        motion = QVariantAnimation(self)
        motion.setDuration(640)
        motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        motion.setStartValue(float(self._span))
        motion.setEndValue(float(target))
        motion.valueChanged.connect(self._apply)
        motion.finished.connect(self._settle)
        self._motion = motion
        motion.start()

    def _apply(self, value):
        self._span = float(value)
        # The label leaves in place, then the pill splits, then the symbols arrive.
        text = 1.0 if self._span <= 0.02 else max(0.0, 1.0 - (self._span - 0.02) / 0.20)
        icons = 0.0 if self._span <= 0.46 else min(1.0, (self._span - 0.46) / 0.38)
        self._effects[self.sync].setOpacity(text)
        self._effects[self.pause].setOpacity(icons)
        self._effects[self.stop].setOpacity(icons)
        self.update()

    def _split(self):
        if self._span <= 0.14:
            return 0.0
        raw = min(1.0, (self._span - 0.14) / 0.86)
        return raw * raw * (3 - 2 * raw)

    def _settle(self):
        if self._mode not in {'sync', 'running'}:
            return
        running = self._mode == 'running'
        self._span = 1.0 if running else 0.0
        self._set_shaped(False)
        self._effects[self.sync].setOpacity(0.0 if running else 1.0)
        self._effects[self.pause].setOpacity(1.0 if running else 0.0)
        self._effects[self.stop].setOpacity(1.0 if running else 0.0)
        self.sync.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, running)
        self.sync.show()
        self.pause.setVisible(running)
        self.stop.setVisible(running)
        if running:
            self.pause.raise_()
            self.stop.raise_()
        else:
            self.sync.raise_()
        self.update()

    def _set_shaped(self, shaped):
        self._shaped = shaped
        for button in (self.sync, self.pause, self.stop):
            if bool(button.property('shaped')) == shaped:
                continue
            button.setProperty('shaped', shaped)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _stop_motion(self):
        if self._motion is None:
            return
        self._motion.finished.disconnect(self._settle)
        self._motion.stop()
        self._motion = None

    def paintEvent(self, _event):
        if not self._shaped:
            return
        split = self._split()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        dark = self.palette().color(QPalette.ColorRole.Text).lightness() > 128
        accent = QColor(self.palette().color(QPalette.ColorRole.Highlight))
        pause = QColor(pause_colors(dark).fill)
        stop = QColor('#6e1c34' if dark else '#8d1234')
        right = float(self.width())
        height = float(self.ROW)
        icon = height
        radius = 10.0
        if split < 0.004:
            painter.setBrush(accent)
            painter.drawRoundedRect(QRectF(0, 0, right, height), radius, radius)
            painter.end()
            return
        gap = self.GAP * split
        left = (right - icon - self.GAP - icon) * split
        painter.setBrush(self._mix(accent, pause, split))
        painter.drawRoundedRect(QRectF(left, 0, max(0.0, right - icon - gap - left), height), radius, radius)
        painter.setBrush(self._mix(accent, stop, split))
        painter.drawRoundedRect(QRectF(right - icon, 0, icon, height), radius, radius)
        painter.end()

    @staticmethod
    def _mix(start, end, amount):
        return QColor(
            round(start.red() + (end.red() - start.red()) * amount),
            round(start.green() + (end.green() - start.green()) * amount),
            round(start.blue() + (end.blue() - start.blue()) * amount),
        )
