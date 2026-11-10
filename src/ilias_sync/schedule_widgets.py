"""Direct weekly schedule editing; all changes remain a settings draft."""
from PySide6.QtCore import Qt, QTime, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QTimeEdit, QAbstractSpinBox, QSizePolicy,
)

from .i18n import t
from .hints import set_hint
from .motion import FadeButton, MotionMenu, popup
from .policy import normalize_weekly

WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


class WeeklySchedule(QWidget):
    changed = Signal()

    def __init__(self, values, parent=None):
        super().__init__(parent)
        self.setObjectName('weeklySchedule')
        self.setAccessibleName(t('Weekly sync schedule'))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.rows = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        heading = QHBoxLayout()
        title = QLabel(t('Your week'))
        title.setObjectName('sectionTitle')
        heading.addWidget(title, 1)
        self.copy_button = FadeButton(t('Copy times'), self)
        self.copy_button.setObjectName('toolbarControl')
        self.copy_button.hide()
        self.copy_button.clicked.connect(self.copy_menu)
        layout.addLayout(heading)
        note = QLabel(t('Add times with +. Days without times stay free.'))
        note.setObjectName('subtitle')
        note.setWordWrap(True)
        layout.addWidget(note)
        for day, name in enumerate(WEEKDAYS):
            row = QWidget()
            row.setObjectName('weekDay')
            row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 7, 0, 7)
            line.setSpacing(10)
            title = QLabel(t(name))
            title.setFixedWidth(86)
            title.setObjectName('weekDayName')
            line.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop)
            slots = QWidget()
            grid = QGridLayout(slots)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(5)
            line.addWidget(slots, 1)
            empty = QLabel(t('No sync'))
            empty.setObjectName('subtitle')
            grid.addWidget(empty, 0, 0)
            add = FadeButton('+')
            add.setObjectName('weekAdd')
            add.setFixedSize(30, 30)
            add.setAccessibleName(t('Add time on {day}', day=t(name)))
            set_hint(add, add.accessibleName())
            add.clicked.connect(lambda _, day=day: self.add_time(day))
            line.addWidget(add, alignment=Qt.AlignmentFlag.AlignTop)
            self.rows[day] = {'widget': row, 'grid': grid, 'slots': [], 'empty': empty, 'add': add}
            layout.addWidget(row)
            self.reflow(day)
        normalized = normalize_weekly(values, require_times=False)
        for day, times in normalized.items():
            for value in times:
                self.add_time(int(day), value, focus=False)
        self.update_copy_button()

    def values(self):
        return {str(day): sorted({slot['edit'].time().toString('HH:mm') for slot in row['slots']})
                for day, row in self.rows.items()}

    def add_time(self, day, value=None, *, focus=True):
        used = self.values()[str(day)]
        if value is None:
            value = next((f'{hour:02d}:00' for hour in [9, 12, 15, 18, 21, 8, 10, 11, 13, 14, 16, 17, 19, 20, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7]
                          if f'{hour:02d}:00' not in used), '09:00')
        row = self.rows[day]
        widget = QWidget()
        widget.setObjectName('weekTime')
        line = QHBoxLayout(widget)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(0)
        edit = QTimeEdit(QTime.fromString(value, 'HH:mm'))
        edit.setObjectName('weekTimeEdit')
        edit.setDisplayFormat('HH:mm')
        edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        edit.setFixedWidth(65)
        edit.setFixedHeight(max(30, self.fontMetrics().height() + 12))
        edit.setAccessibleName(t('Sync time on {day}', day=t(WEEKDAYS[day])))
        edit.timeChanged.connect(self.edited)
        line.addWidget(edit)
        remove = FadeButton('×')
        remove.setObjectName('weekRemove')
        remove.setFixedSize(25, 30)
        remove.setAccessibleName(t('Remove time on {day}', day=t(WEEKDAYS[day])))
        set_hint(remove, remove.accessibleName())
        line.addWidget(remove)
        slot = {'widget': widget, 'edit': edit, 'remove': remove}
        row['slots'].append(slot)
        remove.clicked.connect(lambda: self.remove_time(day, slot))
        self.reflow(day)
        self.edited()
        if focus:
            edit.setFocus()
            edit.setSelectedSection(QTimeEdit.Section.HourSection)

    def remove_time(self, day, slot):
        row = self.rows[day]
        row['slots'].remove(slot)
        row['grid'].removeWidget(slot['widget'])
        slot['widget'].hide()
        slot['widget'].deleteLater()
        self.reflow(day)
        self.edited()
        row['add'].setFocus()

    def reflow(self, day):
        row = self.rows[day]
        row['empty'].setVisible(not row['slots'])
        lines = max(1, (len(row['slots']) + 2) // 3)
        row['widget'].setFixedHeight(14 + lines * max(30, self.fontMetrics().height() + 12) + (lines - 1) * 5)
        for index, slot in enumerate(row['slots']):
            row['grid'].addWidget(slot['widget'], index // 3, index % 3, alignment=Qt.AlignmentFlag.AlignLeft)
        row['grid'].setColumnStretch(3, 1)

    def edited(self, *_):
        self.update_copy_button()
        self.changed.emit()

    def update_copy_button(self):
        self.copy_button.setEnabled(any(self.values().values()))

    def copy_menu(self):
        menu = MotionMenu(self)
        for day, times in self.values().items():
            if times:
                submenu = menu.addMenu(t(WEEKDAYS[int(day)]) + ' · ' + ', '.join(times))
                submenu.addAction(t('Apply to Monday–Friday'), lambda _=False, day=int(day): self.copy_day(day, range(5)))
                submenu.addAction(t('Apply to all days'), lambda _=False, day=int(day): self.copy_day(day, range(7)))
                submenu.addSeparator()
                target_menu = submenu.addMenu(t('Another day'))
                for target, name in enumerate(WEEKDAYS):
                    if target != int(day):
                        target_menu.addAction(t(name), lambda _=False, day=int(day), target=target: self.copy_day(day, [target]))
        popup(menu, self.copy_button)

    def copy_day(self, source, targets):
        times = self.values()[str(source)]
        for day in targets:
            if day == source:
                continue
            for slot in list(self.rows[day]['slots']):
                self.remove_time(day, slot)
            for value in times:
                self.add_time(day, value, focus=False)
        self.edited()
