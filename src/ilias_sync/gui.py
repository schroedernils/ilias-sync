"""A small Qt Widgets interface. Work happens in one disposable headless subprocess."""
from __future__ import annotations

import json
import sys
import time
from html import escape
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QFileSystemWatcher, QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QPainter, QFontDatabase, QPalette, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QTextBrowser, QTabWidget, QVBoxLayout, QWidget, QSizePolicy, QFrame, QStackedWidget, QTreeWidget, QTreeWidgetItem,
    QTabBar,
)

from . import __version__
from .branding import BrandMark, app_icon, paint_action
from .control import active_run, send_command
from .theme import LIGHT, Theme, stylesheet
from .i18n import message, set_language, t
from .scheduler import command, install, uninstall
from .security import import_session, store_password
from .storage import Settings, Source, data_dir, read_json, write_json, source_scope
from .library_widgets import MaterialDelegate, MaterialTable, SyncPanel, ElidedLabel, LibraryNavigation
from .library import load_library, course_key, source_summary, library_summary
from .recovery import recovery_plan
from .presentation import file_size, is_course_info, local_time, sync_summary, schedule_expectation, progress_copy, file_context

STYLE = stylesheet(LIGHT)


def label(text, name=None):
    item = QLabel(t(text))
    item.setTextFormat(Qt.TextFormat.PlainText)
    item.setWordWrap(True)
    item.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    if name:
        item.setObjectName(name)
    return item


def button(text, callback, primary=False):
    item = QPushButton(t(text).replace('&', '&&'))
    item.clicked.connect(callback)
    if primary:
        item.setObjectName("primary")
    return item


def save_buttons():
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Save).setText(t("Save"))
    buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("Cancel"))
    return buttons


class RunButton(QPushButton):
    def __init__(self, text, callback, primary=False, *, icon_only=False):
        super().__init__(t(text))
        self.icon_only = icon_only
        self.action = None
        self.clicked.connect(callback)
        if primary:
            self.setObjectName('primary')

    def set_action(self, action=None):
        self.action = action
        name = t({'pause':'Pause', 'resume':'Resume', 'stop':'Stop'}.get(action, 'Sync now'))
        self.setAccessibleName(name)
        self.setToolTip(name)
        self.setText('' if self.icon_only else t('Stop this sync') if action == 'stop' else name)
        height = max(42 if self.objectName() == 'syncAction' else 36, self.fontMetrics().height() + 18)
        if action:
            self.setMinimumSize(70, height)
            self.setMaximumSize(16777215, height)
        else:
            self.setMinimumSize(0, height)
            self.setMaximumSize(16777215, height)
        self.update()
        if self.icon_only:
            self.setFixedSize(42, 42)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.action or self.text():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        app = QApplication.instance()
        dark = getattr(getattr(app, 'theme', None), 'dark', False)
        color = QColor('#ffffff' if self.action == 'stop' or not dark else '#132b4c')
        if not self.isEnabled():
            color.setAlpha(120)
        symbol = {'pause': 'pause', 'resume': 'play', 'stop': 'square'}[self.action]
        paint_action(painter, self, symbol, color, 18)



class IconButton(QPushButton):
    def __init__(self, name, symbol, callback):
        super().__init__('')
        self.symbol = symbol
        self.setObjectName('iconControl')
        self.setAccessibleName(t(name))
        self.setToolTip(t(name))
        self.setFixedSize(34, 34)
        self.clicked.connect(callback)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.palette().color(QPalette.ColorRole.WindowText)
        if not self.isEnabled():
            color.setAlpha(90)
        paint_action(p, self, self.symbol, color, 18)


class FileCell(QTableWidgetItem):
    def __lt__(self, other):
        return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)


class FileHeader(QHeaderView):
    def __init__(self, table, callback):
        super().__init__(Qt.Orientation.Horizontal, table)
        self.setSectionsClickable(True)
        self.filter_button = IconButton('Filter files', 'filter', callback)
        self.filter_button.setParent(self.viewport())
        self.filter_button.setFixedSize(26, 26)
        self.filter_button.setCheckable(True)
        self.sectionResized.connect(self.place_filter)
        self.geometriesChanged.connect(self.place_filter)

    def place_filter(self, *_):
        x = self.sectionViewportPosition(0) + self.fontMetrics().horizontalAdvance(t('File')) + 22
        self.filter_button.move(x, max(0, (self.height() - 26) // 2))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.place_filter()


class FileFilterDialog(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.setWindowTitle(t('Filter files'))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        form = QHBoxLayout()
        self.search = window.file_search
        self.course = Dropdown()
        self.kind = Dropdown()
        self.size = Dropdown()
        self.window = window
        self.reload_options()
        for title, value in [('Any size', ''), ('Up to 1 MB', 'small'), ('1–10 MB', 'medium'), ('Over 10 MB', 'large')]:
            self.size.addItem(t(title), value)
        for key, widget in [('course', self.course), ('kind', self.kind), ('size', self.size)]:
            widget.setCurrentIndex(max(0, widget.findData(window.file_filters[key])))
        for name, widget in [('Course', self.course), ('File type', self.kind), ('Size', self.size)]:
            widget.setAccessibleName(t(name))
            form.addWidget(widget, 1)
        layout.addLayout(form)
        self.count = label('', 'subtitle')
        self.count.hide()
        form.addWidget(button('Hide filters', self.hide), alignment=Qt.AlignmentFlag.AlignBottom)
        for widget in (self.course, self.kind, self.size):
            widget.currentIndexChanged.connect(self.apply)
        self.apply()

    def reload_options(self):
        window = self.window
        previous = {key: (widget.currentData(), widget.currentText()) for key, widget in [('course', self.course), ('kind', self.kind)]}
        for widget in (self.course, self.kind):
            widget.blockSignals(True)
            widget.clear()
        self.course.addItem(t('All courses'), '')
        self.kind.addItem(t('All file types'), '')
        courses, kinds = {}, set()
        for row in range(window.files.rowCount()):
            entry = window.files.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
            key = course_key(entry, global_scope=not window.selected())
            if key:
                courses.setdefault(key, entry['course_id'])
                if entry.get('course_name'):
                    courses[key] = (entry['_source_name'] + ' · ' if not window.selected() else '') + entry['course_name']
            kinds.add(Path(entry['path']).suffix.casefold())
        for identity, name in sorted(courses.items(), key=lambda value: value[1].casefold()):
            self.course.addItem(name, identity)
        for suffix in sorted(kinds):
            self.kind.addItem(suffix.upper().lstrip('.') or t('No extension'), suffix or '<none>')
        for key, widget in [('course', self.course), ('kind', self.kind)]:
            value, text = previous[key]
            if value and widget.findData(value) < 0:
                widget.addItem(text, value)
            widget.setCurrentIndex(max(0, widget.findData(value)))
            widget.blockSignals(False)

    def apply(self, *_):
        self.window.file_filters.update(search=self.search.text(), course=self.course.currentData(),
                                        kind=self.kind.currentData(), size=self.size.currentData())
        self.window.apply_file_filters()
        self.count.setText(self.window.file_count.text())

    def reset(self):
        self.search.clear()
        for widget in (self.course, self.kind, self.size):
            widget.setCurrentIndex(0)


class SyncReportDialog(QDialog):
    def __init__(self, status, activity, parent=None, history=None, *, embedded=False):
        super().__init__(parent)
        self.status = status
        self.activity_text = activity
        self.history = history or [status]
        self.setWindowTitle(t('Sync report'))
        if embedded:
            self.setWindowFlags(Qt.WindowType.Widget)
            self.setObjectName('inlineReport')
        else:
            self.resize(720, 560)
            self.setMinimumSize(520, 410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) if embedded else layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(6 if embedded else 12)
        heading = QHBoxLayout()
        if not embedded:
            heading.addWidget(label('Sync report', 'title'), 1)
        self.attempts = Dropdown()
        self.attempts.setAccessibleName(t('Synchronization history'))
        for index, attempt in enumerate(self.history):
            self.attempts.addItem((t('Latest attempt') + ' · ' if index == 0 else '') + local_time(attempt.get('finished')))
        heading.addWidget(self.attempts)
        layout.addLayout(heading)
        self.outcome = SyncPanel()
        layout.addWidget(self.outcome)
        self.outcome.setVisible(not embedded)
        self.summary = label('', 'subtitle')
        self.summary.setAccessibleName(t('Synchronization result'))
        layout.addWidget(self.summary)
        self.sections = QTabWidget()
        self.issues = QTreeWidget()
        self.issues.setHeaderLabels([t('Affected material'), t('What is known')])
        self.issues.setColumnWidth(0, 370)
        self.issues.setRootIsDecorated(False)
        self.issues.setAccessibleName(t('Affected materials'))
        self.sections.addTab(self.issues, t('Needs attention'))
        self.exclusions = QTreeWidget()
        self.exclusions.setHeaderLabels([t('Content not included'), t('Count')])
        self.exclusions.setRootIsDecorated(False)
        self.exclusions.setColumnWidth(0, 420)
        self.sections.addTab(self.exclusions, t('Excluded content'))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setAccessibleName(t('Technical activity'))
        self.sections.addTab(self.log, t('Technical activity'))
        layout.addWidget(self.sections, 1)
        if embedded:
            self.sections.setMinimumHeight(100)
            self.sections.setMaximumHeight(160)
        self.issue_path = label('', 'pathPreview')
        self.issue_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        layout.addWidget(self.issue_path)
        self.issues.currentItemChanged.connect(lambda item, _: self.issue_path.setText(item.toolTip(0) if item else ''))
        if not embedded:
            close = button('Close', self.accept)
            close.setDefault(True)
            layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.attempts.currentIndexChanged.connect(self.render_attempt)
        self.render_attempt(0)

    def render_attempt(self, index):
        from .presentation import report_html
        status = self.history[index]
        result = status.get('result') or {}
        counts = result.get('material_counts', result.get('counts', {}))
        summary = sync_summary(status, None)
        self.outcome.set_state(summary.title, summary.detail, summary.tone)
        self.outcome.meta.setText(t('Attempt: {time}', time=local_time(status.get('finished'))))
        text = t('{added} new · {updated} updated', added=counts.get('added', 0), updated=counts.get('updated', 0))
        if result and not any(key in result for key in ('counts', 'material_counts')):
            text = t('No per-file counts recorded in this older result.')
        elif result:
            text += ' · ' + t('{count} unchanged', count=counts.get('unchanged', 0))
            if 'material_counts' in result:
                text += '\n' + t('Material files processed: {count}', count=sum(counts.values()))
                generated = max(0, sum(result.get('counts', {}).values()) - sum(counts.values()))
                if generated:
                    text += ' · ' + t('Course information: {count}', count=generated)
            else:
                text += '\n' + t('Legacy result: file totals may include course information.')
        else:
            text = t('No completed result yet')
        self.summary.setText(text)
        self.summary.setAccessibleDescription(QTextDocument_text(report_html(status)))
        self.issues.clear()
        reasons = {'server_missing': t('Server returned not found'), 'access_denied': t('Server denied access'),
                   'check_failed': t('This item could not be checked'),
                   'transfer_failed': t('Transfer failed'), 'invalid_content': t('Invalid file content returned'), 'not_confirmed': t('Not confirmed for publication in this run')}
        details = result.get('unavailable_details') or [{'path': path, 'reason': 'not_confirmed'} for path in result.get('unavailable_items', [])]
        known = {row['path'] for row in details}
        details = [*details, *[row for row in result.get('transfer_issues', []) if row['path'] not in known]]
        for detail in details:
            path = detail['path']
            row = QTreeWidgetItem(self.issues, [Path(path).name, reasons.get(detail.get('reason'), reasons['not_confirmed'])])
            row.setToolTip(0, path)
            row.setToolTip(1, reasons.get(detail.get('reason'), reasons['not_confirmed']))
        facts = result or status.get('evidence') or {}
        for detail in facts.get('check_issues', []):
            path = t('Course list') if detail['path'] == 'Course list' else detail['path']
            row = QTreeWidgetItem(self.issues, [path, reasons.get(detail.get('reason'), reasons['check_failed'])])
            row.setToolTip(0, path)
        if not details and result.get('unavailable'):
            QTreeWidgetItem(self.issues, [t('{count} files unavailable', count=result['unavailable']), t('No filenames recorded in this older result.')])
        if counts.get('conflict'):
            QTreeWidgetItem(self.issues, [t('Local edits preserved'), t('Your edited files were kept. A separate ILIAS copy was saved beside them.')])
        if result.get('errors') or result.get('warnings'):
            QTreeWidgetItem(self.issues, [t('Checks requiring attention'), t('{count} errors', count=result.get('errors', 0)) + ' · ' + t('{count} warnings', count=result.get('warnings', 0))])
        has_issues = bool(self.issues.topLevelItemCount())
        if not has_issues:
            QTreeWidgetItem(self.issues, [t('No file details recorded') if not result else t('No file issues recorded'), t('See the outcome above for the status of this attempt.')])
        self.exclusions.clear()
        names = {'forum': t('Forums'), 'test': t('Tests'), 'groups without membership': t('Groups you have not joined')}
        for kind, count in result.get('skipped', {}).items():
            QTreeWidgetItem(self.exclusions, [names.get(kind.casefold(), kind), str(count)])
        if not self.exclusions.topLevelItemCount():
            QTreeWidgetItem(self.exclusions, [t('No excluded content recorded'), ''])
        self.exclusions.setToolTip(t('Excluded types and groups are not failed file downloads.'))
        self.sections.setTabText(0, t('Needs attention') if has_issues or summary.tone in {'error','warning'} else t('Files'))
        if self.sections.currentIndex() != 2:
            self.sections.setCurrentIndex(1 if not has_issues and result.get('skipped') else 0)
        scope = facts.get('course_scope', [])
        scope_text = t('Courses included in this check') + ':\n' + '\n'.join(row['name'] + ' [' + row['id'] + ']' for row in scope) + '\n\n' if scope else ''
        intended = facts.get('intended_scope', [])
        if intended and intended != scope:
            scope_text += t('Planned courses') + ':\n' + '\n'.join(row['name'] + ' [' + row['id'] + ']' for row in intended) + '\n\n'
        if facts.get('enumeration_complete') is False:
            scope_text += t('The course list could not be fully checked.') + '\n\n'
        if facts.get('http'):
            scope_text += t('HTTP request measurements') + ':\n' + json.dumps(facts['http'], ensure_ascii=False, indent=2) + '\n\n'
        self.log.setPlainText(scope_text + (self.activity_text if index == 0 and self.activity_text else t('No technical activity recorded in this window.')))
        if self.issues.topLevelItemCount():
            self.issues.setCurrentItem(self.issues.topLevelItem(0))


def QTextDocument_text(html):
    from PySide6.QtGui import QTextDocument
    document = QTextDocument()
    document.setHtml(html)
    return document.toPlainText()


class Dropdown(QComboBox):
    """Keep a visible disclosure affordance with either native or custom palettes."""
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.palette().color(QPalette.ColorRole.Text if self.isEnabled() else QPalette.ColorRole.PlaceholderText)
        painter.setPen(color)
        x, y = self.width() - 16, self.height() // 2
        painter.drawLine(x-4, y-2, x, y+2)
        painter.drawLine(x, y+2, x+4, y-2)


class SourceDialog(QDialog):
    def __init__(self, settings, existing=None, parent=None, *, signin_recovery=False, verify_on_save=False):
        super().__init__(parent)
        self.settings = settings
        self.existing = existing
        self.signin_recovery = signin_recovery
        self.verify_on_save = signin_recovery or verify_on_save
        self.process = None
        self.event_file = data_dir() / ("probe-" + str(uuid4()) + ".jsonl")
        self.source = None
        self.probed_url = existing.url if existing else None
        self.probe_url = None
        self.setWindowTitle(t("Edit ILIAS source" if existing else "Add an ILIAS source"))
        self.resize(620, 460 if not existing else 510)
        self.setMinimumSize(520, 390)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 22)
        outer.setSpacing(16)
        self.step_label = label("", "step")
        outer.addWidget(self.step_label)
        self.heading = label("", "title")
        outer.addWidget(self.heading)
        self.sections = QTabBar()
        for title in ('Your university', 'Sign-in', 'Download folder'):
            self.sections.addTab(t(title))
        self.sections.setExpanding(False)
        self.sections.setVisible(existing is not None and not signin_recovery)
        outer.addWidget(self.sections)
        self.stack = QStackedWidget()
        self.pages = []
        self.forms = []
        for _ in range(3):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            pane = QWidget()
            pane.setObjectName("page")
            form = QVBoxLayout(pane)
            form.setContentsMargins(0, 6, 0, 6)
            form.setSpacing(16)
            scroll.setWidget(pane)
            self.stack.addWidget(scroll)
            self.pages.append(pane)
            self.forms.append(form)
        self.sections.currentChanged.connect(self.stack.setCurrentIndex)
        self.sections.currentChanged.connect(self.update_step)
        outer.addWidget(self.stack, 1)
        self.name = QLineEdit(existing.name if existing else "")
        self.name.setPlaceholderText(t("University / campus"))
        self.url = QLineEdit(existing.url if existing else "")
        self.url.setPlaceholderText("https://ilias.example.edu")
        self.url.textEdited.connect(self.address_changed)
        self.client = QLineEdit(existing.client_id if existing else "")
        self.client.setPlaceholderText(t("Detected when checking the address"))
        self.detect = button("Check address", self.probe)
        self.detect.setObjectName("quiet")
        self.mode = Dropdown()
        for text, value in [("Username & password", "local"), ("Shibboleth SSO", "shibboleth"),
                            ("Browser session (MFA)", "session")]:
            self.mode.addItem(t(text), value)
        if existing:
            self.mode.setCurrentIndex(self.mode.findData(existing.login))
        self.user = QLineEdit(existing.username if existing else "")
        self.user.setAccessibleName(t("Username"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText(t('Current university password') if signin_recovery else t("Leave blank to keep saved password") if existing else "")
        self.idp = QLineEdit(existing.idp_host if existing else "")
        self.idp.setPlaceholderText("idp.example.edu")
        self.session = QLineEdit()
        self.session.setReadOnly(True)
        self.session.setPlaceholderText(t("No file selected"))
        session_row = QWidget()
        session_layout = QHBoxLayout(session_row)
        session_layout.setContentsMargins(0, 0, 0, 0)
        session_layout.addWidget(self.session, 1)
        session_layout.addWidget(button("Choose…", self.choose_session))
        self.destination = QLineEdit(existing.destination if existing else "")
        self.destination.setPlaceholderText(t("Choose a dedicated download folder"))
        destination_row = QWidget()
        destination_layout = QHBoxLayout(destination_row)
        destination_layout.setContentsMargins(0, 0, 0, 0)
        destination_layout.addWidget(self.destination, 1)
        destination_layout.addWidget(button("Choose…", self.choose_folder))
        self.automatic = QCheckBox(t("All joined courses, including new ones"))
        self.automatic.setChecked(existing.automatic_courses if existing else True)
        self.targets = QTextEdit()
        self.targets.setMaximumHeight(110)
        self.targets.setPlaceholderText(t("One course or folder URL per line"))
        if existing:
            self.targets.setPlainText("\n".join(existing.targets))
        self.videos = QCheckBox(t("Download videos"))
        self.videos.setChecked(existing.videos if existing else False)
        self.field_rows = {}
        for page, title, widget in [(0, "ILIAS address", self.url), (0, "Name", self.name),
                                   (1, "Sign-in", self.mode), (1, "Username", self.user),
                                   (1, "Password", self.password), (1, "Trusted SSO host", self.idp),
                                   (1, "Browser session", session_row), (1, "Client ID", self.client),
                                   (2, "Download folder", destination_row), (2, "Course links", self.targets)]:
            row = QWidget()
            layout = QVBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(7)
            caption = label(title)
            caption.setBuddy(widget)
            layout.addWidget(caption)
            layout.addWidget(widget)
            widget.setAccessibleName(t(title))
            self.forms[page].addWidget(row)
            self.field_rows[widget] = row
        self.forms[0].addWidget(self.detect, alignment=Qt.AlignmentFlag.AlignLeft)
        self.probe_status = label('', 'success')
        self.probe_status.hide()
        self.forms[0].addWidget(self.probe_status)
        self.forms[0].addWidget(label("Use the start address of your university's ILIAS.", "subtitle"))
        self.note = label("Import a cookies.txt export from your browser. When the session expires, import a new export.", "subtitle")
        self.forms[1].addWidget(self.note)
        self.advanced = button("Client ID…", self.toggle_client)
        self.advanced.setObjectName("quiet")
        self.forms[1].addWidget(self.advanced, alignment=Qt.AlignmentFlag.AlignLeft)
        self.vault_note = label("Saved in the system credential vault", "subtitle")
        self.forms[1].addWidget(self.vault_note)
        self.recovery_note = label('', 'subtitle')
        self.forms[1].insertWidget(0, self.recovery_note)
        self.browser_button = button('Open ILIAS in browser', self.open_ilias)
        self.forms[1].insertWidget(1, self.browser_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.forms[2].insertWidget(1, self.automatic)
        self.forms[2].addWidget(self.videos)
        self.forms[2].addWidget(label("A folder in Google Drive or OneDrive works too.", "subtitle"))
        for form in self.forms:
            form.addStretch(1)
        self.client_expanded = False
        self.mode.currentIndexChanged.connect(self.fields_for_login)
        self.automatic.toggled.connect(self.fields_for_login)
        self.fields_for_login()
        self.error = label("", "error")
        self.error.hide()
        outer.addWidget(self.error)
        footer = QHBoxLayout()
        self.back_button = button("Back", self.back)
        footer.addWidget(self.back_button)
        footer.addStretch(1)
        footer.addWidget(button("Cancel", self.reject))
        self.next_button = button("Continue", self.advance, True)
        self.next_button.setDefault(True)
        footer.addWidget(self.next_button)
        outer.addLayout(footer)
        self.update_step()
        if signin_recovery:
            self.resize(620, 600)
            self.stack.setCurrentIndex(1)
            self.update_step()
            (self.session if self.mode.currentData() == 'session' else self.password).setFocus()

    def address_changed(self, *_):
        bound_url = self.probed_url or (self.probe_url if getattr(self, 'probe_attempted', False) else None)
        if bound_url and self.url.text().rstrip('/') != bound_url.rstrip('/'):
            self.client.clear()
            self.probe_attempted = False
            self.probed_url = None
            self.probe_status.hide()
            self.show_error('The address changed. Check it again or enter its client ID manually.')

    def update_step(self):
        index = self.stack.currentIndex()
        self.step_label.setVisible(self.existing is None or self.signin_recovery)
        self.step_label.setText(self.existing.name if self.signin_recovery else t("Step {step} of 3", step=index + 1))
        self.heading.setText(t('Renew sign-in') if self.signin_recovery else t('University settings') if self.existing else t(["Your university", "Sign in to ILIAS", "Choose your files"][index]))
        self.back_button.setEnabled(index > 0)
        self.back_button.setVisible(self.existing is None)
        self.next_button.setText(t('Save and check') if self.verify_on_save else t("Save" if index == 2 or self.existing else "Continue"))
        self.error.hide()
        if not self.existing:
            self.resize(self.width(), [460, 550, 500][index])
        elif self.sections.currentIndex() != index:
            self.sections.setCurrentIndex(index)

    def back(self):
        self.stack.setCurrentIndex(max(0, self.stack.currentIndex() - 1))
        self.update_step()

    def advance(self):
        from .storage import server_url
        try:
            self.address_changed()
            if self.existing:
                self.save()
                return
            index = self.stack.currentIndex()
            if index == 0:
                server_url(self.url.text())
                if not self.name.text().strip():
                    from urllib.parse import urlparse
                    self.name.setText(urlparse(self.url.text()).hostname)
                if not self.client.text() and not getattr(self, "probe_attempted", False):
                    self.probe_attempted = True
                    self.probe()
                    return
            elif index == 1:
                if self.mode.currentData() == "local" and not self.client.text().strip():
                    self.client_expanded = True
                    self.fields_for_login()
                    raise ValueError("Detect or enter the ILIAS client ID first.")
                if self.mode.currentData() != "session" and not self.user.text().strip():
                    raise ValueError("Enter your university username.")
                if self.mode.currentData() != "session" and not self.password.text() and not self.existing:
                    raise ValueError("Enter a password, or choose browser-session sign-in.")
                if self.mode.currentData() == "session" and not self.session.text() and not self.existing:
                    raise ValueError("Choose a browser session file.")
            else:
                self.save()
                return
            self.stack.setCurrentIndex(index + 1)
            self.update_step()
        except ValueError as exc:
            self.show_error(str(exc))

    def show_error(self, text):
        self.error.setText(message(text))
        self.error.setObjectName("error")
        self.error.show()

    def toggle_client(self):
        self.client_expanded = not self.client_expanded
        self.fields_for_login()

    def fields_for_login(self, *_):
        mode = self.mode.currentData()
        for widget, visible in [(self.client, mode == "local" and self.client_expanded),
                                (self.user, mode != "session"), (self.password, mode != "session"),
                                (self.idp, mode == "shibboleth"), (self.session.parentWidget(), mode == "session"),
                                (self.targets, not self.automatic.isChecked())]:
            self.field_rows[widget].setVisible(visible)
        self.note.setVisible(mode == "session")
        self.vault_note.setVisible(mode != "session") if hasattr(self, "vault_note") else None
        self.advanced.setVisible(mode == "local") if hasattr(self, "advanced") else None
        if hasattr(self, 'recovery_note'):
            self.recovery_note.setVisible(self.signin_recovery)
            self.browser_button.setVisible(self.signin_recovery)
            self.recovery_note.setText(t('Sign in to ILIAS in your browser, export a fresh cookies.txt session with your browser tool, then choose that file here. Signing in in the browser alone does not renew IliasSync’s session.')
                                      if mode == 'session' else t('Enter the current university password. Save and check starts a new check to confirm the sign-in. If your university requires MFA, use Browser session instead.'))

    def open_ilias(self):
        from .storage import server_url
        try:
            QDesktopServices.openUrl(QUrl(server_url(self.url.text())))
        except ValueError as exc:
            self.show_error(str(exc))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, t("Choose a dedicated download folder"))
        if folder:
            self.destination.setText(folder)

    def choose_session(self):
        file, _ = QFileDialog.getOpenFileName(self, t("Import browser session"), filter=t("Cookie files (*.txt);;All files (*)"))
        if file:
            self.session.setText(file)
            self.mode.setCurrentIndex(self.mode.findData("session"))

    def probe(self):
        from .storage import server_url
        try:
            url = server_url(self.url.text())
        except ValueError as exc:
            self.show_error(str(exc))
            return
        self.error.hide()
        self.probe_url = url
        self.probe_attempted = True
        self.detect.setText(t("Checking ILIAS…"))
        self.next_button.setEnabled(False)
        self.detect.setEnabled(False)
        self.back_button.setEnabled(False)
        self.process = QProcess(self)
        self.event_file.write_text("", encoding="utf-8")
        cmd = command("--probe", url, "--event-file", str(self.event_file))
        self.process.setProgram(cmd[0])
        self.process.setArguments(cmd[1:])
        self.probe_timeout = QTimer(self)
        self.probe_timeout.setSingleShot(True)
        self.probe_timeout.timeout.connect(self.process.kill)
        self.probe_timeout.start(60000)
        self.process.finished.connect(self.probed)
        self.process.errorOccurred.connect(self.probe_failed)
        self.process.start()

    def probe_failed(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.probe_timeout.stop()
            self.detect.setEnabled(True)
            self.next_button.setEnabled(True)
            self.detect.setText(t("Check address"))
            self.stack.setCurrentIndex(1)
            self.update_step()
            self.show_error("The worker could not start.")

    def probed(self):
        self.probe_timeout.stop()
        self.detect.setEnabled(True)
        self.detect.setText(t("Check address"))
        self.next_button.setEnabled(True)
        self.back_button.setEnabled(self.stack.currentIndex() > 0)
        output = self.event_file.read_text(encoding="utf-8") if self.event_file.exists() else ""
        self.event_file.unlink(missing_ok=True)
        handled = False
        for line in output.splitlines():
            try:
                event = json.loads(line)
                if event["event"] == "result":
                    if self.url.text().rstrip('/') != self.probe_url.rstrip('/'):
                        self.address_changed()
                        return
                    handled = True
                    self.probed_url = self.probe_url
                    self.probe_status.setText(t('Address checked'))
                    self.probe_status.show()
                    self.client.setText(event["result"]["client_id"])
                    if not self.name.text():
                        self.name.setText(event["result"]["title"][:70])
                    self.stack.setCurrentIndex(1)
                    self.update_step()
                    if not self.client.text():
                        self.client_expanded = True
                        self.fields_for_login()
                        self.show_error("Enter the client ID or use a browser session.")
                elif event["event"] == "error":
                    handled = True
                    self.stack.setCurrentIndex(1)
                    self.update_step()
                    self.show_error(event["message"])
            except (ValueError, KeyError):
                pass
        if not handled:
            self.show_error('Address check returned no result. Try again or continue with manual sign-in details.')

    def done(self, result):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        self.event_file.unlink(missing_ok=True)
        super().done(result)

    def save(self):
        try:
            if self.signin_recovery:
                if self.mode.currentData() == 'session' and not self.session.text():
                    raise ValueError('Choose a fresh browser session file before checking again.')
                if self.mode.currentData() != 'session' and not self.password.text():
                    raise ValueError('Enter the current password before checking again.')
            kwargs = {"id": self.existing.id} if self.existing else {}
            source = Source(name=self.name.text().strip(), url=self.url.text(), destination=self.destination.text(),
                            username=self.user.text().strip(), client_id=self.client.text().strip(),
                            login=self.mode.currentData(), idp_host=self.idp.text().strip(),
                            automatic_courses=self.automatic.isChecked(),
                            targets=[s.strip() for s in self.targets.toPlainText().splitlines() if s.strip()],
                            videos=self.videos.isChecked(), folder_rules=self.existing.folder_rules if self.existing else {}, **kwargs)
            if self.existing:
                source.enabled = self.existing.enabled
                source.include_course_ids = self.existing.include_course_ids
                source.folder_names = dict(self.existing.folder_names)
            self.settings.validate_source(source)
            if source.login != 'session' and not source.username:
                raise ValueError('Enter your university username.')
            if source.login != 'session' and not self.password.text() and not self.existing:
                raise ValueError('Enter a password, or choose browser-session sign-in.')
            changed_auth = self.existing and (QUrl(self.existing.url).host(), self.existing.username, self.existing.login) != (QUrl(source.url).host(), source.username, source.login)
            if changed_auth and (source.login == 'session' and not self.session.text() or source.login != 'session' and not self.password.text()):
                raise ValueError('Sign-in changed. Enter the new password or import a new session before saving.')
            if source.login == 'session' and not self.session.text() and not self.existing:
                raise ValueError('Choose a browser session file.')
            from .profile_service import commit_profile
            commit_profile(self.settings, source,
                           password=self.password.text() if source.login != 'session' else '',
                           session=self.session.text() if source.login == 'session' else '',
                           store=store_password, import_cookies=import_session)
            self.source = source
            self.password.clear()
            self.accept()
        except Exception as exc:
            # Avoid arbitrary backend error text that might expose vault internals.
            self.show_error(str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "The credential vault or folder is unavailable.")


class CoursesDialog(QDialog):
    def __init__(self, courses, source, settings, parent):
        super().__init__(parent)
        self.setWindowTitle(t("Choose courses"))
        self.resize(700, 540)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(label("Choose courses", "title"))
        layout.addWidget(label(t("{count} courses and groups", count=len(courses)), "subtitle"))
        search = QLineEdit()
        search.setPlaceholderText(t("Search courses…"))
        layout.addWidget(search)
        auto = QCheckBox(t("All joined courses, including new ones"))
        auto.setChecked(source.automatic_courses)
        layout.addWidget(auto)
        listing = QListWidget()
        listing.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        listing.setUniformItemSizes(True)
        for course in sorted(courses, key=lambda c: c["name"].casefold()):
            item = QListWidgetItem(course["name"])
            item.setData(Qt.ItemDataRole.UserRole, course["url"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if source.automatic_courses or course["url"] in source.targets else Qt.CheckState.Unchecked)
            listing.addItem(item)
        listing.setEnabled(not auto.isChecked())
        auto.toggled.connect(lambda checked: listing.setEnabled(not checked))
        layout.addWidget(listing)
        search.textChanged.connect(lambda text: [listing.item(i).setHidden(text.casefold() not in listing.item(i).text().casefold())
                                                for i in range(listing.count())])
        self.listing = listing
        self.automatic = auto
        self.search = search
        extra = QLineEdit()
        extra.setPlaceholderText(t("Missing a course? Paste its ILIAS link here."))
        layout.addWidget(extra)
        known_urls = {course['url'] for course in courses}
        self.saved_links = QListWidget()
        self.saved_links.setAccessibleName(t('Additional saved links'))
        for url in source.targets:
            if url not in known_urls:
                item = QListWidgetItem(url)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setToolTip(url)
                self.saved_links.addItem(item)
        self.saved_links.setMaximumHeight(95)
        self.saved_links.setVisible(bool(self.saved_links.count()))
        layout.addWidget(self.saved_links)
        buttons = save_buttons()
        layout.addWidget(buttons)

        def save():
            source.automatic_courses = auto.isChecked()
            source.targets = [listing.item(i).data(Qt.ItemDataRole.UserRole) for i in range(listing.count())
                              if listing.item(i).checkState() == Qt.CheckState.Checked]
            source.targets += [self.saved_links.item(i).text() for i in range(self.saved_links.count())
                               if self.saved_links.item(i).checkState() == Qt.CheckState.Checked]
            if extra.text().strip():
                source.targets.append(extra.text().strip())
                source.automatic_courses = False
            try:
                settings.save_source(source)
                self.accept()
            except ValueError as exc:
                QMessageBox.warning(self, t("Select courses"), message(str(exc)))
        buttons.accepted.connect(save)
        buttons.rejected.connect(self.reject)


class FolderMappingDialog(QDialog):
    def __init__(self, source, settings, parent=None):
        super().__init__(parent)
        self.source = source
        self.settings = settings
        self.rules = dict(source.folder_rules)
        self.names = dict(source.folder_names)
        self.name_errors = {}
        self.name_drafts = {}
        self.setWindowTitle(t("Folder mapping"))
        self.resize(940, 640)
        self.setMinimumSize(720, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(label('Organize course folders', 'title'))
        layout.addWidget(label('Select a course, folder or file to see where it will be saved.', 'subtitle'))
        split = QSplitter()
        split.setChildrenCollapsible(False)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 12, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText(t('Search courses and files…'))
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName(t('Search courses and files…'))
        left_layout.addWidget(self.search)
        tree_actions = QHBoxLayout()
        tree_actions.addWidget(button('Expand all', lambda: self.tree.expandAll()))
        tree_actions.addWidget(button('Collapse all', lambda: self.tree.collapseAll()))
        left_layout.addLayout(tree_actions)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([t('Course / content'), t('Folder name'), t('Download folder')])
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnHidden(2, True)
        self.tree.header().hide()
        self.tree.setAccessibleName(t('Course folder assignments'))
        left_layout.addWidget(self.tree, 1)
        split.addWidget(left)
        editor = QScrollArea()
        editor.setWidgetResizable(True)
        body = QWidget()
        self.editor_layout = QVBoxLayout(body)
        self.editor_layout.setContentsMargins(16, 0, 0, 0)
        self.editor_layout.setSpacing(10)
        editor.setWidget(body)
        split.addWidget(editor)
        split.setSizes([380, 490])
        layout.addWidget(split, 1)
        self.show_ids = QCheckBox(t('Show course IDs in folder names'))
        self.show_ids.setChecked(source.include_course_ids)
        state = data_dir() / 'sources' / source.id
        courses = read_json(state / 'courses.json', [])
        entries = read_json(state / 'manifest.json', {'files':{}})['files']
        self.entries = entries
        self.courses = courses
        course_rows = {}
        nodes = {}
        for course in courses:
            item = QTreeWidgetItem(self.tree, [course['name'], ''])
            item.setData(0, Qt.ItemDataRole.UserRole, 'course/' + course['id'])
            course_rows[course['id']] = item
        import re
        for identity, entry in sorted(entries.items(), key=lambda row: row[1]['path']):
            logical = entry.get('logical')
            course_id = entry.get('course_id')
            if not logical:
                original = entry.get('original_path', entry['path'])
                parts = original.split('/')
                match = re.search(r'\[(crs-\d+|grp-\d+)\]', parts[0])
                if not match:
                    continue
                course_id = match[1]
                logical = '/'.join([course_id, *parts[1:]])
            if course_id not in course_rows:
                item = QTreeWidgetItem(self.tree, [entry.get('course_name', course_id), ''])
                item.setData(0, Qt.ItemDataRole.UserRole, 'course/' + course_id)
                course_rows[course_id] = item
            parent_item = course_rows[course_id]
            parts = logical.split('/')
            for index, name in enumerate(parts[1:-1], 1):
                key = 'path/' + '/'.join(parts[:index+1])
                if key not in nodes:
                    item = QTreeWidgetItem(parent_item, [name, ''])
                    item.setData(0, Qt.ItemDataRole.UserRole, key)
                    nodes[key] = item
                parent_item = nodes[key]
            item = QTreeWidgetItem(parent_item, [parts[-1], ''])
            item.setData(0, Qt.ItemDataRole.UserRole, 'file/' + identity)
        self.tree.expandToDepth(0)
        self.update_targets()
        self.tree.currentItemChanged.connect(self.selected)
        self.selected_label = label('Select a course or file.', 'sectionTitle')
        self.editor_layout.addWidget(self.selected_label)
        self.mapping_state = label('', 'subtitle')
        self.editor_layout.addWidget(self.mapping_state)
        self.editor_layout.addWidget(label('Folder name', 'eyebrow'))
        self.folder_name = QLineEdit()
        self.folder_name.setMaxLength(80)
        self.folder_name.setAccessibleName(t('Folder name'))
        self.folder_name.setEnabled(False)
        self.folder_name.textEdited.connect(self.rename_selected)
        self.editor_layout.addWidget(self.folder_name)
        self.reset_name_button = button('Use original name', self.reset_name)
        self.editor_layout.addWidget(self.reset_name_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.editor_layout.addSpacing(8)
        self.editor_layout.addWidget(label('Effective destination after the next sync', 'eyebrow'))
        self.target = QLineEdit()
        self.target.setReadOnly(True)
        self.target.setAccessibleName(t('Effective destination after the next sync'))
        self.target.hide()
        self.effective_path = label('', 'pathPreview')
        self.effective_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.editor_layout.addWidget(self.effective_path)
        self.choose_button = button('Choose a different destination…', self.choose)
        self.reset_button = button('Use parent destination', self.reset_rule)
        self.editor_layout.addWidget(self.choose_button)
        self.editor_layout.addWidget(self.reset_button)
        self.mapping_effect = label('', 'subtitle')
        self.editor_layout.addWidget(self.mapping_effect)
        self.editor_layout.addStretch()
        layout.addWidget(self.show_ids)
        if not entries:
            self.editor_layout.addWidget(label('Course contents appear after the first sync.', 'subtitle'))
        layout.addWidget(label('Destination changes create new copies at the next sync. Existing copies are kept. Name changes rename the managed folder and its local contents.', 'subtitle'))
        self.error = label("", "error")
        self.error.hide()
        layout.addWidget(self.error)
        buttons = save_buttons()
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.choose_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.show_ids.toggled.connect(self.update_targets)

        def filter_tree(text):
            def visit(item, parent_matches=False):
                matched = parent_matches or text.casefold() in item.text(0).casefold()
                children = [visit(item.child(i), matched) for i in range(item.childCount())]
                visible = matched or any(children)
                item.setHidden(not visible)
                if text and visible:
                    item.setExpanded(True)
                return visible
            for i in range(self.tree.topLevelItemCount()):
                visit(self.tree.topLevelItem(i))
            current = self.tree.currentItem()
            if current is None or current.isHidden():
                visible = next((self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())
                                if not self.tree.topLevelItem(i).isHidden()), None)
                self.tree.setCurrentItem(visible)
                if visible is None:
                    self.selected(None)
        self.search.textChanged.connect(filter_tree)
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def update_targets(self, *_):
        from .naming import course_folders
        preview = replace(self.source, folder_names=self.names, include_course_ids=self.show_ids.isChecked())
        courses = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            courses.append({'id': item.data(0, Qt.ItemDataRole.UserRole)[7:], 'name': item.text(0)})
        folder_names = course_folders(preview, courses)
        def visit(item):
            key = item.data(0, Qt.ItemDataRole.UserRole)
            folder = folder_names.get(key[7:], '') if key.startswith('course/') else self.names.get(key, item.text(0))
            item.setText(1, Path(self.rules[key]).name if key in self.rules and not key.startswith('file/') else folder)
            item.setText(2, self.rules.get(key, t("Inherited")))
            item.setToolTip(2, self.rules.get(key, self.source.destination))
            item.setToolTip(0, item.text(0))
            for i in range(item.childCount()):
                visit(item.child(i))
        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))
        self.courses = courses
        if hasattr(self, 'target') and self.tree.currentItem():
            self.show_effective_destination(self.tree.currentItem())

    def show_effective_destination(self, item):
        from .routing import mapping_preview
        key = item.data(0, Qt.ItemDataRole.UserRole)
        preview = replace(self.source, folder_rules=self.rules, folder_names=self.names,
                          include_course_ids=self.show_ids.isChecked())
        try:
            path, origin = mapping_preview(preview, self.courses, key, self.entries)
        except (KeyError, ValueError):
            self.effective_path.setText(t('The destination will be available after the next sync.'))
            return
        self.target.setText(str(path))
        self.target.setToolTip(str(path))
        self.effective_path.setText(str(path))
        custom = key in self.rules
        self.mapping_state.setText(t('Custom destination for this item') if custom else
                                   t('Uses the parent destination') if origin else t('Uses the university download folder'))
        self.reset_button.setEnabled(custom)
        self.reset_name_button.setEnabled(key in self.names)
        if custom and not key.startswith('file/'):
            self.reset_name_button.setEnabled(self.rules[key] != self.source.folder_rules.get(key))
            self.reset_name_button.setText(t('Restore saved destination'))
            self.mapping_effect.setText(t('Changing this name changes the custom destination. A new copy will be saved; existing files stay in the previous folder.'))
        else:
            self.reset_name_button.setText(t('Use original name'))
            self.mapping_effect.setText(t('Subfolders follow this destination unless they have their own destination.')
                                       if not key.startswith('file/') else t('Only this file is affected. Its filename stays unchanged.'))

    def selected(self, item, previous=None):
        self.choose_button.setEnabled(item is not None)
        self.reset_button.setEnabled(item is not None)
        self.folder_name.setEnabled(item is not None and not item.data(0, Qt.ItemDataRole.UserRole).startswith('file/'))
        if item is None:
            self.selected_label.setText(t('Select a course or file.'))
            self.mapping_state.clear()
            self.mapping_effect.clear()
            self.effective_path.clear()
            self.target.clear()
            self.folder_name.clear()
            self.folder_name.setPlaceholderText('')
            self.reset_name_button.setEnabled(False)
            return
        if item:
            ancestors = []
            current = item
            while current:
                ancestors.insert(0, current.text(0))
                current = current.parent()
            self.selected_label.setText(' / '.join(ancestors))
            key = item.data(0, Qt.ItemDataRole.UserRole)
            self.folder_name.setPlaceholderText(item.text(1))
            self.folder_name.setText(Path(self.rules[key]).name if key in self.rules and not key.startswith('file/')
                                     else self.names.get(key, ''))
            if key in self.name_drafts:
                self.folder_name.setText(self.name_drafts[key])
            self.show_effective_destination(item)

    def rename_selected(self, text):
        item = self.tree.currentItem()
        if not item:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key.startswith('file/'):
            return
        self.name_drafts[key] = text
        from .naming import validate_names
        try:
            if text.strip():
                validate_names({key: text.strip()})
            self.name_errors.pop(key, None)
            self.error.hide()
        except ValueError as exc:
            self.name_errors[key] = str(exc)
            self.error.setText(message(str(exc)))
            self.error.show()
            return
        if key in self.rules:
            if text.strip():
                self.rules[key] = str(Path(self.rules[key]).parent / text.strip())
                self.target.setText(self.rules[key])
        elif text.strip():
            self.names[key] = text.strip()
        else:
            self.names.pop(key, None)
        self.update_targets()

    def choose(self):
        item = self.tree.currentItem()
        if not item:
            return
        initial = self.target.text() or self.source.destination
        if item.data(0, Qt.ItemDataRole.UserRole).startswith('file/'):
            initial = str(Path(initial).parent)
        folder = QFileDialog.getExistingDirectory(self, t("Choose folder…"), initial)
        if folder:
            self.rules[item.data(0, Qt.ItemDataRole.UserRole)] = folder
            self.update_targets()
            self.selected(item)

    def reset_rule(self):
        item = self.tree.currentItem()
        if item:
            self.rules.pop(item.data(0, Qt.ItemDataRole.UserRole), None)
            self.update_targets()
            self.selected(item)

    def reset_name(self):
        item = self.tree.currentItem()
        if item:
            key = item.data(0, Qt.ItemDataRole.UserRole)
            if key in self.rules:
                if key in self.source.folder_rules:
                    self.rules[key] = self.source.folder_rules[key]
                else:
                    self.rules.pop(key)
            self.names.pop(key, None)
            self.name_errors.pop(key, None)
            self.name_drafts.pop(key, None)
            self.update_targets()
            self.selected(item)

    def save(self):
        previous = (self.source.folder_rules, self.source.folder_names, self.source.include_course_ids)
        try:
            if self.name_errors:
                raise ValueError(next(iter(self.name_errors.values())))
            from .naming import validate_folder_changes
            candidate = replace(self.source, folder_rules=self.rules, folder_names=self.names,
                                include_course_ids=self.show_ids.isChecked())
            validate_folder_changes(self.source, candidate, self.courses, self.entries)
            self.source.folder_rules = self.rules
            self.source.folder_names = self.names
            self.source.include_course_ids = self.show_ids.isChecked()
            self.settings.save_source(self.source)
            self.accept()
        except ValueError as exc:
            self.source.folder_rules, self.source.folder_names, self.source.include_course_ids = previous
            self.error.setText(message(str(exc)))
            self.error.show()


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(t('Settings'))
        self.resize(590, 350)
        self.setMinimumSize(480, 310)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 22, 24, 20)
        outer.setSpacing(12)
        outer.addWidget(label('Settings', 'title'))
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        self.language = Dropdown()
        for title, value in [('Deutsch', 'de'), ('English', 'en')]:
            self.language.addItem(title, value)
        self.language.setCurrentIndex(self.language.findData(settings.value.get('language', 'de')))
        self.appearance = Dropdown()
        for title, value in [('Follow system', 'system'), ('Light', 'light'), ('Dark', 'dark')]:
            self.appearance.addItem(t(title), value)
        self.appearance.setCurrentIndex(self.appearance.findData(settings.value.get('appearance', 'system')))
        general, form = self.page()
        form.addRow(t('Language'), self.language)
        form.addRow(t('Theme'), self.appearance)
        self.tabs.addTab(general, t('General'))
        schedule, form = self.page()
        self.enabled = QCheckBox(t('Automatic sync'))
        self.enabled.setChecked(settings.value['scheduled'])
        form.addRow(self.enabled)
        self.schedule_mode = Dropdown()
        self.schedule_mode.addItem(t('At intervals'), 'interval')
        self.schedule_mode.addItem(t('Weekly schedule'), 'weekly')
        mode = settings.value.get('schedule_mode', 'interval')
        self.schedule_mode.setCurrentIndex(1 if mode in {'times', 'weekly'} else 0)
        form.addRow(t('Schedule'), self.schedule_mode)
        self.hours = Dropdown()
        for n in (1, 3, 6, 12, 24):
            self.hours.addItem(t('Every hour') if n == 1 else t('Every {n} hours', n=n), n)
        self.hours.setCurrentIndex(self.hours.findData(settings.value['interval_hours']))
        form.addRow(t('Interval'), self.hours)
        from .policy import weekly_draft
        from .schedule_widgets import WeeklySchedule
        self.week_plan = WeeklySchedule(weekly_draft(settings.value))
        form.addRow(self.week_plan)
        self.battery = QCheckBox(t('Pause on battery power'))
        self.battery.setChecked(settings.value['battery_saver'])
        form.addRow(self.battery)
        self.schedule_preview = label('', 'subtitle')
        timing_note = label('Local time · your Mac must be awake, signed in and online.', 'statusMeta')
        timing_note.setToolTip(t('Schedules use the computer’s local time, including daylight saving changes. The OS decides when missed runs can resume; the computer must be awake, signed in and online.'))
        form.addRow(timing_note)
        self.tabs.addTab(schedule, t('Schedule'))
        outer.addWidget(self.schedule_preview)
        self.error = label('', 'error')
        self.error.hide()
        outer.addWidget(self.error)
        footer = QHBoxLayout()
        footer.addWidget(button('Help & about', lambda: HelpDialog(self).exec()))
        footer.addStretch()
        self.buttons = save_buttons()
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName('primary')
        self.buttons.accepted.connect(self.save)
        self.buttons.rejected.connect(self.reject)
        footer.addWidget(self.buttons)
        self.draft_note = label('Changes apply when you save. Appearance is previewed until then.', 'subtitle')
        outer.addWidget(self.draft_note)
        outer.addLayout(footer)
        self.appearance.currentIndexChanged.connect(self.preview_theme)
        self.tabs.currentChanged.connect(self.update_schedule_fields)
        self.enabled.toggled.connect(self.update_schedule_fields)
        self.schedule_mode.currentIndexChanged.connect(self.update_schedule_fields)
        self.hours.currentIndexChanged.connect(self.update_schedule_fields)
        self.week_plan.changed.connect(self.update_schedule_fields)
        for widget, name in [(self.language, 'Language'), (self.appearance, 'Theme'), (self.hours, 'Interval'), (self.schedule_mode, 'Schedule')]:
            widget.setAccessibleName(t(name))
        self.update_schedule_fields()

    def page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName('dialogBody')
        form = QFormLayout(body)
        form.setContentsMargins(0, 12, 0, 4)
        form.setSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        scroll.setWidget(body)
        return scroll, form

    def update_schedule_fields(self, *_):
        from .presentation import schedule_expectation
        weekly = self.schedule_mode.currentData() == 'weekly'
        enabled = self.enabled.isChecked()
        self.schedule_mode.setEnabled(enabled)
        self.hours.setEnabled(enabled)
        self.battery.setEnabled(enabled)
        self.week_plan.setEnabled(enabled)
        self.week_plan.setVisible(weekly)
        self.hours.setVisible(not weekly)
        self.hours.parentWidget().layout().labelForField(self.hours).setVisible(not weekly)
        values = self.week_plan.values()
        draft = {**self.settings.value, 'scheduled': enabled, 'schedule_mode': self.schedule_mode.currentData(),
                 'weekly_times': values, 'interval_hours': self.hours.currentData()}
        self.schedule_preview.setText(t('Add a time to at least one weekday.') if enabled and weekly and not any(values.values())
                                      else schedule_expectation(draft, {}))
        self.schedule_preview.setVisible(self.tabs.currentIndex() == 1)
        self.draft_note.setText(t('Your plan applies when you save.') if self.tabs.currentIndex() == 1 else
                               t('Changes apply when you save. Appearance is previewed until then.'))
        layout_mode = (self.tabs.currentIndex(), weekly)
        if getattr(self, '_schedule_layout', None) != layout_mode:
            self._schedule_layout = layout_mode
            self.resize(max(self.width(), 620) if weekly else self.width(),
                        350 if self.tabs.currentIndex() == 0 else 730 if weekly else 460)

    def preview_theme(self):
        app = QApplication.instance()
        if hasattr(app, 'theme'):
            app.theme.set_mode(self.appearance.currentData())

    def reject(self):
        app = QApplication.instance()
        if hasattr(app, 'theme'):
            app.theme.set_mode(self.settings.value.get('appearance', 'system'))
        super().reject()

    def save(self):
        from .policy import normalize_weekly
        from .settings_service import apply_settings, ScheduleRestoreError, SettingsStorageError
        week = self.week_plan.values()
        mode = self.schedule_mode.currentData()
        try:
            week = normalize_weekly(week, require_times=self.enabled.isChecked() and mode == 'weekly')
            candidate = {**self.settings.value, 'interval_hours': self.hours.currentData(), 'battery_saver': self.battery.isChecked(),
                         'language': self.language.currentData(), 'appearance': self.appearance.currentData(),
                         'schedule_mode': mode, 'weekly_times': week, 'scheduled': self.enabled.isChecked()}
            apply_settings(self.settings, candidate, install=install, uninstall=uninstall)
            self.accept()
        except ValueError as exc:
            self.error.setText(message(str(exc)))
            self.error.show()
            self.tabs.setCurrentIndex(1)
            self.week_plan.rows[0]['add'].setFocus()
        except ScheduleRestoreError as exc:
            self.error.setText(message(str(exc)))
            self.error.show()
            self.tabs.setCurrentIndex(1)
        except SettingsStorageError as exc:
            self.error.setText(message(str(exc)))
            self.error.show()
        except Exception:
            self.error.setText(t('The OS scheduler could not be updated. On Linux, a systemd user session is required.'))
            self.error.show()
            self.tabs.setCurrentIndex(1)


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('Help & about'))
        self.resize(670, 550)
        self.setMinimumSize(480, 370)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.addWidget(label('Help & about', 'title'))
        layout.addWidget(label('IliasSync ' + __version__ + ' · GPL-3.0-or-later', 'subtitle'))
        from .build_info import build_info
        layout.addWidget(label(t('Build: {id}', id=build_info()['id']), 'subtitle'))
        from .info import info_sections, info_links, topic_html
        self.topics_data = info_sections()
        split = QSplitter()
        self.topics = QListWidget()
        self.topics.setAccessibleName(t('Help topics'))
        self.topics.setWordWrap(True)
        self.topics.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.topics.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.topics.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.topics.setStyleSheet('QListWidget::item { padding: 6px 4px; margin: 2px 0; }')
        self.topics.setMinimumWidth(150)
        self.topics.setMaximumWidth(210)
        self.topics.addItems([title for title, _ in self.topics_data] + [t('Info')])
        split.addWidget(self.topics)
        self.info = QTextBrowser()
        self.info.setOpenExternalLinks(True)
        self.info.setAccessibleName(t('About & usage'))
        split.addWidget(self.info)
        split.setSizes([180, 440])
        layout.addWidget(split, 1)
        def show_topic(index):
            if index < len(self.topics_data):
                title, body = self.topics_data[index]
                self.info.setHtml(topic_html(title, body))
            else:
                self.info.setHtml(info_links())
            self.info.setAccessibleDescription(self.info.toPlainText())
        self.topics.currentRowChanged.connect(show_topic)
        self.topics.setCurrentRow(0)
        layout.addWidget(button('Close', self.accept), alignment=Qt.AlignmentFlag.AlignRight)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.view_state = read_json(data_dir() / 'view-state.json', {})
        set_language(self.settings.value.get("language", "de"))
        self.process = None
        self.run_info = None
        self.file_filters = {'search': '', 'course': '', 'kind': '', 'size': ''}
        self.progress_message = ""
        self.progress_token = None
        self.buffer = ""
        self.job = None
        self.sync_queue = []
        self.libraries = {}
        self.report_widget = None
        self.event_path = data_dir() / ("job-" + str(uuid4()) + ".jsonl")
        self.event_offset = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.read_output)
        self.setWindowTitle(t("IliasSync"))
        saved_size = self.view_state.get('size', [980, 700])
        self.resize(max(820, min(saved_size[0], 1400)), max(560, min(saved_size[1], 1000)))
        self.setMinimumSize(820, 560)
        self.library_source = None
        self.filter_panel = None
        self.ui_error = ''
        self.ui_error_kind = ''
        self.ui_error_source = None
        self.ui_error_entry = None
        self.ui_error_status = None
        self.repair_checks = {}
        container = QWidget()
        page = QVBoxLayout(container)
        page.setContentsMargins(0, 0, 0, 0)
        split = QSplitter()
        split.setChildrenCollapsible(False)
        left = QFrame()
        left.setObjectName('sidebar')
        left.setMinimumWidth(190)
        left.setMaximumWidth(360)
        self.sidebar = left
        sidebar = QVBoxLayout(left)
        sidebar.setContentsMargins(12, 16, 12, 12)
        sidebar.setSpacing(8)
        brand = QHBoxLayout()
        brand.setSpacing(9)
        mark = BrandMark()
        brand.addWidget(mark)
        brand.addWidget(label('IliasSync', 'appTitle'), 1)
        sidebar.addLayout(brand)
        sidebar.addSpacing(8)
        sidebar.addWidget(label('Library', 'eyebrow'))
        self.sources = LibraryNavigation()
        self.sources.scopeChanged.connect(self.navigate)
        self.sources.manageRequested.connect(lambda identity: self.edit_source(identity))
        self.sources.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sources.customContextMenuRequested.connect(self.navigation_menu)
        sidebar.addWidget(self.sources, 1)
        self.add_button = button('Add ILIAS', self.add)
        self.add_button.setObjectName('sidebarAction')
        sidebar.addWidget(self.add_button)
        self.settings_button = button('Settings', self.background)
        self.settings_button.setAccessibleName(t('Settings'))
        sidebar.addWidget(self.settings_button)
        split.addWidget(left)
        right = QWidget()
        content = QVBoxLayout(right)
        self.content_layout = content
        content.setContentsMargins(20, 14, 20, 10)
        content.setSpacing(8)
        self.welcome_brand = BrandMark()
        content.addWidget(self.welcome_brand)
        source_heading = QHBoxLayout()
        self.sidebar_button = IconButton('Hide sidebar', 'sidebar', self.toggle_sidebar)
        source_heading.addWidget(self.sidebar_button, alignment=Qt.AlignmentFlag.AlignTop)
        title_group = QVBoxLayout()
        title_group.setSpacing(2)
        self.source_title = ElidedLabel(t('Connect ILIAS'))
        self.source_title.setObjectName('title')
        self.source_host = ElidedLabel()
        self.source_host.setObjectName('subtitle')
        self.destination = label('Connect your university. Choose your courses. We will take it from there.', 'subtitle')
        self.destination.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.destination.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_group.addWidget(self.source_title)
        source_meta = QHBoxLayout()
        source_meta.setSpacing(12)
        source_meta.addWidget(self.source_host)
        source_meta.addWidget(self.destination, 1)
        title_group.addLayout(source_meta)
        source_heading.addLayout(title_group, 1)
        self.sync_button = RunButton('Sync now', self.request_sync)
        self.sync_button.setObjectName('syncAction')
        self.pause_button = RunButton('Pause', self.sync_or_pause, icon_only=True)
        self.pause_button.setObjectName('primary')
        self.pause_button.hide()
        self.stop_button = RunButton('Stop', self.stop_sync, icon_only=True)
        self.stop_button.setObjectName('stopControl')
        self.stop_button.setToolTip(t('Stops this run. Completed files and the schedule are kept.'))
        self.stop_button.set_action('stop')
        self.stop_button.hide()
        self.management_button = IconButton('University actions', 'more', self.management_menu)
        source_heading.addWidget(self.management_button, alignment=Qt.AlignmentFlag.AlignTop)
        content.addLayout(source_heading)
        self.onboard_button = button('Connect ILIAS', self.add, True)
        content.addWidget(self.onboard_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.empty_spacer = QWidget()
        content.addWidget(self.empty_spacer, 1)
        self.sync_panel = SyncPanel(compact=True)
        self.status = self.sync_panel.detail
        self.recovery_button = button('View report', self.recover)
        self.sync_panel.recovery_layout.addWidget(self.recovery_button, alignment=Qt.AlignmentFlag.AlignTop)
        self.recovery_button.hide()
        self.recovery_button.setObjectName('primary')
        self.sync_panel.disclosure.toggled.connect(self.toggle_report)
        self.details_button = self.sync_panel.disclosure
        self.details_button.hide()
        library = QVBoxLayout()
        library.setSpacing(9)
        heading = QHBoxLayout()
        self.file_search = QLineEdit()
        self.file_search.setObjectName('materialSearch')
        self.file_search.setPlaceholderText(t('Search materials…'))
        self.file_search.setAccessibleName(t('Search materials'))
        self.file_search.setClearButtonEnabled(True)
        self.file_search.textChanged.connect(self.search_files)
        heading.addWidget(self.file_search, 1)
        self.library_view = Dropdown()
        self.library_view.setAccessibleName(t('Library view'))
        for title, value in [('Materials', 'materials'), ('Recent changes', 'recent'), ('Course information', 'info'), ('All files', 'all')]:
            self.library_view.addItem(t(title), value)
        self.library_view.currentIndexChanged.connect(self.change_library_view)
        heading.addWidget(self.library_view)
        library.addLayout(heading)
        self.library_widget = QWidget()
        self.library_widget.setLayout(library)
        self.library_widget.layout().setContentsMargins(0, 0, 0, 0)
        content.addWidget(self.library_widget)
        self.files = MaterialTable()
        self.files.resized.connect(self.adapt_columns)
        self.files.setAccessibleName(t('Downloaded files'))
        self.files.setColumnCount(4)
        self.files.setHorizontalHeaderLabels([t('File'), t('Size'), t('Changed'), t('Course')])
        self.files_header = FileHeader(self.files, self.filter_files)
        self.files.setHorizontalHeader(self.files_header)
        self.files.setItemDelegate(MaterialDelegate(self.files))
        self.files.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.files.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.files.setColumnWidth(3, 210)
        self.files.verticalHeader().hide()
        self.files.verticalHeader().setDefaultSectionSize(max(44, self.files.fontMetrics().height() * 2 + 10))
        self.files.setShowGrid(False)
        self.files.setTabKeyNavigation(False)
        self.files.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.files.setSortingEnabled(True)
        self.files.sortItems(2, Qt.SortOrder.DescendingOrder)
        self.files.horizontalHeader().sortIndicatorChanged.connect(lambda *_: QTimer.singleShot(0, self.apply_file_filters))
        self.files.horizontalHeader().sortIndicatorChanged.connect(lambda *_: self.adapt_columns())
        self.files.itemDoubleClicked.connect(lambda *_: self.open_file())
        self.files.itemSelectionChanged.connect(self.update_file_actions)
        self.files.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.files.customContextMenuRequested.connect(self.file_menu)
        content.addWidget(self.files, 1)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        self.file_count = label('', 'subtitle')
        footer.addWidget(self.file_count)
        self.clear_filters_button = button('Clear filters', self.clear_file_filters)
        self.clear_filters_button.setObjectName('compactControl')
        self.clear_filters_button.hide()
        footer.addWidget(self.clear_filters_button)
        footer.addStretch()
        self.file_open_button = button('Open file', self.open_file)
        self.file_open_button.setObjectName('compactControl')
        footer.addWidget(self.file_open_button)
        self.library_footer = QWidget()
        self.library_footer.setLayout(footer)
        content.addWidget(self.library_footer)
        # One workspace: overview first, full library and reports on demand.
        self.workspace_tabs = QTabBar()
        self.workspace_tabs.setObjectName('workspaceTabs')
        self.workspace_tabs.setAccessibleName(t('Workspace view'))
        self.workspace_tabs.setExpanding(False)
        for name in ('Overview', 'Materials', 'Notifications', 'Details'):
            self.workspace_tabs.addTab(t(name))
        content.insertWidget(3, self.workspace_tabs)
        self.workspace = QStackedWidget()
        content.addWidget(self.workspace, 1)
        self.overview = QWidget()
        overview = QVBoxLayout(self.overview)
        overview.setContentsMargins(0, 14, 0, 0)
        overview.setSpacing(12)
        self.recent_title = label('Recently updated', 'sectionTitle')
        overview.addWidget(self.recent_title)
        self.recent_files = MaterialTable()
        self.recent_files.setAccessibleName(t('Three recent materials'))
        self.recent_files.setColumnCount(2)
        self.recent_files.setHorizontalHeaderLabels([t('File'), t('Changed')])
        self.recent_files.setItemDelegate(MaterialDelegate(self.recent_files))
        self.recent_files.library_scope = 'global'
        self.recent_files.horizontalHeader().hide()
        self.recent_files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recent_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.recent_files.verticalHeader().hide()
        self.recent_files.verticalHeader().setDefaultSectionSize(58)
        self.recent_files.setShowGrid(False)
        self.recent_files.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_files.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.recent_files.setMaximumHeight(180)
        self.recent_files.setMinimumHeight(120)
        self.recent_files.itemDoubleClicked.connect(lambda *_: self.open_recent())
        self.recent_files.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_files.customContextMenuRequested.connect(self.recent_menu)
        overview.addWidget(self.recent_files)
        self.all_files_button = button('View all materials', lambda: self.workspace_tabs.setCurrentIndex(1))
        overview.addWidget(self.all_files_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.overview_notes = label('', 'subtitle')
        overview.addWidget(self.overview_notes)
        overview.addStretch()
        self.workspace.addWidget(self.overview)
        self.materials_page = QWidget()
        materials = QVBoxLayout(self.materials_page)
        materials.setContentsMargins(0, 8, 0, 0)
        for widget in (self.library_widget, self.files, self.library_footer):
            content.removeWidget(widget)
            materials.addWidget(widget, 1 if widget is self.files else 0)
        self.workspace.addWidget(self.materials_page)
        self.notices_page = QScrollArea()
        self.notices_page.setWidgetResizable(True)
        self.notices_body = QWidget()
        self.notices_layout = QVBoxLayout(self.notices_body)
        self.notices_layout.setContentsMargins(0, 12, 0, 0)
        self.notices_page.setWidget(self.notices_body)
        self.workspace.addWidget(self.notices_page)
        self.sync_panel.layout().removeWidget(self.sync_panel.report_host)
        self.sync_panel.external_report = True
        self.sync_panel.report_host.setMaximumHeight(16777215)
        self.workspace.addWidget(self.sync_panel.report_host)
        self.workspace_tabs.currentChanged.connect(self.change_workspace)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(label('Synchronization', 'eyebrow'))
        controls.addStretch()
        controls.addWidget(self.sync_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.stop_button)
        self.sync_panel.layout().insertLayout(0, controls)
        content.addWidget(self.sync_panel)
        self.activity = QTextEdit(self)
        self.activity.setReadOnly(True)
        self.activity.setAccessibleName(t('Activity'))
        self.activity.document().setMaximumBlockCount(150)
        self.activity.hide()
        split.addWidget(right)
        self.split = split
        split.setSizes([240, 740])
        page.addWidget(split, 1)
        self.setCentralWidget(container)
        self.shortcuts = []
        for key, callback, target in [('Return', self.open_file, self.files),
                                      ('Return', self.open_recent, self.recent_files),
                                      (QKeySequence.StandardKey.Refresh, self.request_sync, self),
                                      ('Ctrl+Shift+S', self.toggle_sidebar, self),
                                      (QKeySequence.StandardKey.Preferences, self.background, self)]:
            shortcut = QShortcut(QKeySequence(key), target)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut if target is self.files else Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        about = QAction(t("About IliasSync"), self)
        about.triggered.connect(self.about)
        file_menu = self.menuBar().addMenu(t('File'))
        file_menu.addAction(t('Open file'), self.open_current_file, QKeySequence(QKeySequence.StandardKey.Open))
        file_menu.addAction(t('Open containing folder'), self.reveal_file)
        file_menu.addSeparator()
        file_menu.addAction(t('Add ILIAS'), self.add)
        view_menu = self.menuBar().addMenu(t('View'))
        self.sidebar_action = view_menu.addAction(t('Hide sidebar'), self.toggle_sidebar)
        view_menu.addAction(t('Search materials'), self.focus_search, QKeySequence(QKeySequence.StandardKey.Find))
        self.menuBar().addAction(about)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.timeout_job)
        self.populate()
        self.sidebar.setVisible(bool(self.settings.sources()) and not self.view_state.get('sidebar_hidden', False))
        if not self.settings.sources():
            self.setMinimumSize(620, 390)
            self.resize(660, 420)
        self.run_watch = QFileSystemWatcher([str(data_dir())], self)
        self.run_watch.directoryChanged.connect(self.check_active_run)
        self.library_refresh = QTimer(self)
        self.library_refresh.setSingleShot(True)
        self.library_refresh.setInterval(120)
        self.library_refresh.timeout.connect(self.refresh)
        self.library_watch = QFileSystemWatcher(self)
        self.library_watch.directoryChanged.connect(lambda *_: self.library_refresh.start())
        self.watch_library()
        self.check_active_run()
        self.age_timer = QTimer(self)
        self.age_timer.setInterval(60000)
        self.age_timer.timeout.connect(self.update_sync_age)
        self.age_timer.start()

    def selected(self):
        identity = self.sources.scope()[0]
        return next((source for source in self.settings.sources() if source.id == identity), None)

    def change_workspace(self, index):
        self.workspace.setCurrentIndex(index)
        self.details_button.blockSignals(True)
        self.details_button.setChecked(index == 3)
        self.details_button.blockSignals(False)
        if index == 3:
            self.build_report()
        elif index == 2:
            self.render_notices()
        elif index == 1:
            self.adapt_columns()

    def update_sync_age(self):
        from .notifications import relative_time
        rows = []
        source = self.selected()
        relevant = [self.libraries[source.id]] if source else list(self.libraries.values())
        for library in relevant:
            status = library['status']
            stamp = status.get('finished')
            current_scope = status.get('scope') == source_scope(library['source'])
            successful = current_scope and status.get('state') in {'Up to date', 'Completed with warnings'} and bool(status.get('result'))
            title = 'Last synchronization: {time} ({age})' if successful else 'Last attempt: {time} ({age})'
            text = t(title, time=local_time(stamp), age=relative_time(stamp)) if stamp else t('Not yet synchronized')
            if current_scope and not successful and status.get('last_success'):
                previous = status['last_success']
                text += '\n' + t('Last complete synchronization: {time} ({age})', time=local_time(previous), age=relative_time(previous))
            rows.append((library['source'].name + ': ' if len(relevant) > 1 else '') + text)
        self.sync_panel.meta.setText('\n'.join(rows))

    def render_overview(self, entries):
        from .notifications import observe_attempt
        materials = [entry for entry in entries if not is_course_info(entry)]
        recent = sorted((entry for entry in materials if entry.get('changed_at')), key=lambda entry: entry['changed_at'], reverse=True)[:3]
        self.recent_title.setText(t('Recently updated') if recent else t('Your materials'))
        # Older archives have no timestamp. Fill unused slots without inventing
        # a date or promoting those files above recorded changes.
        if len(recent) < 3:
            recent += [entry for entry in materials if not entry.get('changed_at')][:3 - len(recent)]
        self.recent_files.library_scope = self.files.library_scope
        self.recent_files.setRowCount(len(recent))
        for row, entry in enumerate(recent):
            item = QTableWidgetItem(Path(entry['path']).name)
            item.setData(Qt.ItemDataRole.UserRole + 1, entry)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, Path(entry['path']).name + ' · ' + file_context(entry))
            item.setToolTip(entry['_source_name'] + '\n' + entry['path'])
            self.recent_files.setItem(row, 0, item)
            self.recent_files.setItem(row, 1, QTableWidgetItem(local_time(entry.get('changed_at')) if entry.get('changed_at') else '—'))
        self.recent_files.set_empty('' if recent else t('No materials yet'),
                                    '' if recent else t('Start a sync to download your course materials.'))
        self.all_files_button.setText(t('View all materials ({count})', count=len(materials)))
        for library in self.libraries.values():
            observe_attempt(data_dir() / 'sources' / library['source'].id, library['status'])
        self.render_notices()

    def open_recent(self):
        item = self.recent_files.item(self.recent_files.currentRow(), 0)
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole + 1)
        # Resolve by identity, never by a possibly duplicated display name.
        self.library_view.setCurrentIndex(self.library_view.findData('materials'))
        self.clear_file_filters()
        for row in range(self.files.rowCount()):
            candidate = self.files.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
            if (candidate['_source_id'], candidate['_identity']) == (entry['_source_id'], entry['_identity']):
                self.files.selectRow(row)
                self.open_file()
                return

    def open_current_file(self):
        if self.workspace.currentIndex() == 0:
            self.open_recent()
        elif self.workspace.currentIndex() == 1:
            self.open_file()

    def recent_menu(self, point):
        item = self.recent_files.itemAt(point)
        if item:
            self.recent_files.selectRow(item.row())
            menu = QMenu(self)
            menu.addAction(t('Open file'), self.open_recent)
            menu.addAction(t('View all materials'), lambda: self.workspace_tabs.setCurrentIndex(1))
            menu.exec(self.recent_files.viewport().mapToGlobal(point))

    def render_notices(self):
        from .notifications import notices, preferences
        source = self.selected()
        rows = [(identity, row) for identity in self.libraries if not source or identity == source.id
                for row in notices(identity) if not row.get('resolved')]
        active = sum(row['count'] for _, row in rows)
        hidden = sum(row['count'] for _, row in rows if row.get('dismissed'))
        errors = sum(row['count'] for _, row in rows if row['severity'] == 'error')
        summary = t('{errors} errors · {notes} notes', errors=errors, notes=active - errors) if active else t('No current problems')
        if not rows and any(source_summary(library).tone == 'error' for identity, library in self.libraries.items()
                            if not source or identity == source.id):
            summary = t('Action required — see Details')
        if hidden:
            summary += ' · ' + t('{count} hidden', count=hidden)
        self.overview_notes.setText(summary)
        self.workspace_tabs.setTabText(2, t('Notifications') + (f' ({active - hidden})' if active > hidden else ''))
        while self.notices_layout.count():
            widget = self.notices_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self.notices_layout.addWidget(label(summary, 'sectionTitle'))
        setting = QCheckBox(t('Notify me about new sync problems on this Mac'))
        setting.setChecked(preferences().get('enabled', False))
        setting.toggled.connect(self.configure_notifications)
        self.notices_layout.addWidget(setting)
        self.notices_layout.addWidget(button('Test notification', self.test_notification), alignment=Qt.AlignmentFlag.AlignLeft)
        self.notification_permission_note = label(getattr(self, 'notification_feedback', '') or
            t('Hidden notices stay in Details. Repeated problems do not trigger another notification.'), 'subtitle')
        self.notices_layout.addWidget(self.notification_permission_note)
        for identity, row in rows:
            if not row.get('dismissed'):
                self.notices_layout.addWidget(self.notice_widget(identity, row))
        if not rows:
            self.notices_layout.addWidget(label('New sync problems appear here. Your existing materials remain available.', 'subtitle'))
        self.notices_layout.addStretch()

    def notice_widget(self, identity, row, *, details=False):
        from .notifications import relative_time
        widget = QFrame()
        widget.setObjectName('noticeRow')
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 10, 12, 10)
        line = QHBoxLayout()
        titles = {'signin': 'Sign-in required', 'unavailable': 'Download unavailable', 'network': 'Connection unavailable',
                  'errors': 'Sync errors', 'warnings': 'Sync notes', 'incomplete': 'Check incomplete'}
        title = t(titles.get(row['kind'], 'Check incomplete'))
        line.addWidget(label(title, 'sectionTitle'), 1)
        action = button('Show again' if row.get('dismissed') else 'Dismiss notice',
                        lambda: self.dismiss_notice(identity, row['id'], not row.get('dismissed')))
        action.setObjectName('compactControl')
        action.setToolTip(t('Hides this notice only. The sync result and recovery steps are kept.'))
        line.addWidget(action)
        layout.addLayout(line)
        text = self.libraries[identity]['source'].name + ' · ' + relative_time(row['last_seen'])
        if row['occurrences'] > 1:
            text += ' · ' + t('{count} attempts', count=row['occurrences'])
        layout.addWidget(label(text, 'subtitle'))
        if row['path']:
            layout.addWidget(label(row['path'], 'subtitle'))
        if not details:
            layout.addWidget(button('View details', lambda: self.open_notice_details(identity)), alignment=Qt.AlignmentFlag.AlignLeft)
        return widget

    def dismiss_notice(self, identity, notice_id, dismissed):
        from .notifications import dismiss
        dismiss(identity, notice_id, dismissed)
        self.render_notices()
        if self.workspace_tabs.currentIndex() == 3:
            self.build_report(identity)

    def open_notice_details(self, identity):
        self.workspace_tabs.setCurrentIndex(3)
        self.build_report(identity)

    def configure_notifications(self, enabled):
        from .notifications import set_enabled, permission
        set_enabled(enabled)
        if enabled:
            result = permission(request=True)
            self.notification_feedback = (t('Allow notifications in macOS when prompted. If denied, enable IliasSync in System Settings → Notifications.')
                if result != -1 else t('System notifications are available in the installed macOS app. Notices here always work.'))
        else:
            self.notification_feedback = ''
        self.render_notices()

    def test_notification(self):
        from .notifications import native_notify, permission, preferences
        authorization = permission()
        if authorization == -1:
            self.notification_feedback = t('macOS notification access is unavailable. In-app notices remain available.')
            self.notification_permission_note.setText(self.notification_feedback)
            return
        if authorization == 1:
            self.notification_feedback = t('macOS has denied notifications. Enable IliasSync in System Settings → Notifications.')
            self.notification_permission_note.setText(self.notification_feedback)
            return
        if not preferences().get('enabled') or authorization != 2:
            self.notification_feedback = t('Enable notifications above and allow IliasSync in macOS first.')
            self.notification_permission_note.setText(self.notification_feedback)
            return
        accepted = native_notify('IliasSync', t('Notifications for new sync problems are enabled.'), 'ilias-sync-test')
        self.notification_feedback = t('Test notification handed to macOS.') if accepted else t('macOS could not accept the test notification. Check System Settings → Notifications.')
        self.notification_permission_note.setText(self.notification_feedback)

    def request_sync(self):
        if self.process or self.run_info:
            return
        if active_run():
            self.check_active_run()
            return
        plan = getattr(self, 'recovery_plan', None)
        if plan and plan.action in {'signin', 'folders', 'storage'}:
            self.recover()
        else:
            if self.selected():
                self.start('sync')
            else:
                self.sync_queue = [source for source in self.settings.sources() if source.enabled]
                if self.sync_queue:
                    self.start('sync', self.sync_queue.pop(0))

    def navigate(self):
        if not hasattr(self, 'files'):
            return
        # Search/filter state belongs to a browsing scope, never to sync targets.
        self.clear_file_filters()
        self.ui_error = ''
        self.ui_error_kind = ''
        self.ui_error_source = None
        self.ui_error_entry = None
        self.ui_error_status = None
        self.sync_panel.disclosure.setChecked(False)
        self.render_library()

    def populate(self, selected_id=None):
        self.libraries = load_library(self.settings.sources())
        saved = self.view_state.get('navigation')
        if selected_id:
            scope = (selected_id, '')
        elif self.sources.topLevelItemCount():
            scope = self.sources.scope()
        elif isinstance(saved, list) and len(saved) == 2:
            scope = tuple(saved)
        else:
            # Keep the previous single-university starting point; several
            # universities start at the shared library unless a scope was saved.
            identity = self.view_state.get('source')
            if not identity and len(self.libraries) == 1:
                identity = next(iter(self.libraries))
            scope = (identity or '', '')
        self.sources.populate(self.libraries, scope)
        self.render_library()
        if hasattr(self, 'library_watch'):
            self.watch_library()

    def watch_library(self):
        paths = [str(data_dir() / 'sources')]
        paths += [str(data_dir() / 'sources' / identity) for identity in self.libraries]
        existing = set(self.library_watch.directories())
        wanted = {path for path in paths if Path(path).is_dir()}
        if existing - wanted:
            self.library_watch.removePaths(list(existing - wanted))
        if wanted - existing:
            self.library_watch.addPaths(list(wanted - existing))

    def refresh(self):
        scope = self.sources.scope()
        self.libraries = load_library(self.settings.sources())
        self.sources.populate(self.libraries)
        if self.sources.scope() != scope:
            self.clear_file_filters()
        self.render_library()
        if hasattr(self, 'library_watch'):
            self.watch_library()

    def render_library(self):
        source = self.selected()
        scope = self.sources.scope()
        has_sources = bool(self.libraries)
        busy = self.process is not None or self.run_info is not None
        self.onboard_button.setVisible(not has_sources)
        self.welcome_brand.setVisible(not has_sources)
        self.empty_spacer.setVisible(not has_sources)
        self.source_host.setVisible(has_sources)
        self.destination.hide()
        self.sidebar_button.setVisible(has_sources)
        self.management_button.setVisible(has_sources)
        for widget in (self.sync_panel, self.files, self.library_widget, self.library_footer, self.sync_button):
            widget.setVisible(has_sources)
        self.workspace_tabs.setVisible(has_sources)
        self.workspace.setVisible(has_sources)
        if not has_sources:
            self.sources.blockSignals(True)
            self.sources.clear()
            self.sources.blockSignals(False)
            self.source_title.setText(t('Connect ILIAS'))
            self.source_host.setVisible(True)
            self.source_host.setText(t('Add your university to download course files.'))
            self.refresh_controls()
            return
        scope_key = '/'.join(scope)
        scope_changed = self.library_source != scope_key
        if scope_changed:
            if self.library_source:
                self.view_state.setdefault('views', {})[self.library_source] = self.library_view.currentData()
            self.library_source = scope_key
            saved_view = self.view_state.get('views', {}).get(scope_key,
                         self.view_state.get('views', {}).get(scope[0], 'materials'))
            self.library_view.blockSignals(True)
            self.library_view.setCurrentIndex(max(0, self.library_view.findData(saved_view)))
            self.library_view.blockSignals(False)
            self.files.clearSelection()
            self.files.setCurrentCell(-1, -1)
        if scope[1] and source:
            self.source_title.setText(self.libraries[source.id]['courses'].get(scope[1], scope[1]))
            self.source_host.setText(source.name)
        elif source:
            self.source_title.setText(source.name)
            self.source_host.setText(t('All course materials'))
        else:
            self.source_title.setText(t('All materials'))
            self.source_host.setText(t('From one university') if len(self.libraries) == 1 else t('Across {count} universities', count=len(self.libraries)))
        self.file_search.setPlaceholderText(t('Search in this course…') if scope[1] else
                                            t('Search this university…') if source else t('Search all universities…'))
        self.file_search.setToolTip(self.file_search.placeholderText())
        entries = [entry for identity, library in self.libraries.items() if not source or identity == source.id
                   for entry in library['entries'] if not scope[1] or entry.get('course_id') == scope[1]]
        column, order = self.files_header.sortIndicatorSection(), self.files_header.sortIndicatorOrder()
        if scope_changed:
            column, order = 2, Qt.SortOrder.DescendingOrder
        selected = self.selected_entry()
        selected_key = (selected['_source_id'], selected['_identity']) if selected else None
        self.files.setUpdatesEnabled(False)
        self.files.setSortingEnabled(False)
        self.files.setRowCount(len(entries))
        self.files.library_scope = 'course' if scope[1] else 'source' if source else 'global'
        for row, entry in enumerate(entries):
            item = FileCell(entry['path'])
            item.setData(Qt.ItemDataRole.UserRole, (Path(entry['path']).name.casefold(), entry['path'].casefold()))
            item.setData(Qt.ItemDataRole.UserRole + 1, entry)
            item.setData(Qt.ItemDataRole.AccessibleTextRole,
                         entry['path'] + ' · ' + entry['_source_name'] + ' · ' + file_context(entry))
            item.setToolTip(entry['_source_name'] + '\n' + entry.get('course_name', '') + '\n' +
                            str(Path(entry.get('root', entry['_destination'])) / entry['path']))
            self.files.setItem(row, 0, item)
            size = entry.get('target_stat', [0])[0]
            size_item = FileCell(file_size(size))
            size_item.setData(Qt.ItemDataRole.UserRole, size)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.files.setItem(row, 1, size_item)
            changed = entry.get('changed_at', 0)
            date_item = FileCell(local_time(changed) if changed else '—')
            date_item.setData(Qt.ItemDataRole.UserRole, changed)
            date_item.setToolTip(t('No recorded change') if not changed else local_time(changed))
            self.files.setItem(row, 2, date_item)
            course_item = FileCell(entry.get('course_name', ''))
            course_item.setData(Qt.ItemDataRole.UserRole, entry.get('course_name', '').casefold())
            course_item.setToolTip(entry.get('course_name', ''))
            self.files.setItem(row, 3, course_item)
        self.files.setSortingEnabled(True)
        self.files.sortItems(max(0, column), order)
        self.files.setUpdatesEnabled(True)
        self.adapt_columns()
        if self.filter_panel:
            self.filter_panel.reload_options()
        self.apply_file_filters()
        if selected_key:
            for row in range(self.files.rowCount()):
                entry = self.files.item(row, 0).data(Qt.ItemDataRole.UserRole + 1)
                if (entry['_source_id'], entry['_identity']) == selected_key and not self.files.isRowHidden(row):
                    self.files.selectRow(row)
                    break
        self.update_file_actions()
        self.render_overview(entries)
        self.render_status()
        self.refresh_controls()
        if busy:
            self.show_progress(progress_copy(self.progress_message) if self.progress_message else t('Checking ILIAS…'))
        elif self.ui_error:
            self.show_local_error(self.ui_error, kind=self.ui_error_kind, source_id=self.ui_error_source,
                                  error_status=self.ui_error_status)

    def render_status(self):
        from .storage import source_scope
        source = self.selected()
        relevant = {source.id: self.libraries[source.id]} if source else self.libraries
        summary = source_summary(relevant[source.id]) if source else library_summary(relevant)
        problem_sources = [identity for identity, library in relevant.items() if recovery_plan(library['status'])]
        self.recovery_source = source.id if source else next((identity for identity in problem_sources
            if source_summary(relevant[identity]).tone == 'error'), next(iter(problem_sources), None))
        plan = recovery_plan(relevant[self.recovery_source]['status']) if self.recovery_source else None
        title = summary.title
        status = relevant[source.id]['status'] if source else {}
        unavailable = (status.get('result') or {}).get('unavailable', 0)
        if unavailable and summary.tone == 'warning':
            title += ' · ' + t('{count} files unavailable', count=unavailable)
        repair_id = source.id if source else getattr(self, 'last_repair_source', None)
        repair = self.repair_checks.get(repair_id)
        if repair and repair_id in self.libraries and repair.get('phase') != 'checking':
            if self.libraries[repair_id]['status'].get('finished') != repair.get('finished'):
                repair = None
        if repair and repair.get('phase') == 'verified':
            title = t('Sign-in confirmed') if repair['kind'] == 'signin' else t('Check successful again')
            if not source:
                title += ' · ' + self.libraries[repair_id]['source'].name
            if summary.tone in {'error', 'warning'}:
                title += ' · ' + summary.title
            summary = replace(summary, detail=t('The new check completed. You can continue using your materials.') + ' ' + summary.detail)
        elif repair and repair.get('phase') == 'failed':
            summary = replace(summary, detail=t('The problem is not resolved yet.') + ' ' + summary.detail)
            if summary.tone == 'success':
                summary = replace(summary, title=t('New check not confirmed'), tone='error', recovery='retry')
                title = summary.title
                plan = recovery_plan({'state': 'Needs attention'})
                self.recovery_source = repair_id
        self.sync_panel.set_state(title, summary.detail, summary.tone)
        self.recovery = summary.recovery
        self.recovery_plan = plan
        self.recovery_button.setText(plan.button if plan else '')
        self.recovery_button.setToolTip(relevant[self.recovery_source]['source'].name + '\n' + plan.explanation if plan else '')
        self.recovery_button.setVisible(bool(plan and summary.tone == 'error'))
        if plan and summary.tone == 'error':
            detail = plan.explanation
            if not source:
                detail = relevant[self.recovery_source]['source'].name + ': ' + detail
            if repair and repair.get('phase') == 'failed':
                detail = t('The problem is not resolved yet.') + ' ' + detail
            self.sync_panel.detail.setText(detail)
            self.sync_panel.detail.setAccessibleName(detail)
        checked = t('Last checked: {time}', time=local_time(status.get('finished'))) if status.get('finished') else t('Not yet checked')
        if source and status.get('scope') == source_scope(source):
            last_success = status.get('last_success')
            if last_success and last_success != status.get('finished'):
                checked += ' · ' + t('Last complete check: {time}', time=local_time(last_success))
        schedules = [library['source'].name + ': ' + schedule_expectation(self.settings.value, library['status'])
                     for library in relevant.values()]
        self.sync_panel.meta.setText(checked if source else '\n'.join(schedules))
        if source:
            next_check = schedule_expectation(self.settings.value, status)
        elif not self.settings.value.get('scheduled'):
            next_check = t('Automatic sync is off')
        elif len({schedule_expectation(self.settings.value, library['status']) for library in relevant.values()}) == 1:
            next_check = schedule_expectation(self.settings.value, next(iter(relevant.values()))['status'])
        else:
            next_check = t('Automatic checks follow each university’s schedule')
        self.sync_panel.schedule.setText(next_check)
        self.sync_panel.schedule.setToolTip('\n'.join(schedules) + '\n' + self.schedule_text())
        self.update_sync_age()
        if self.sync_panel.disclosure.isChecked():
            self.build_report()

    def adapt_columns(self):
        if not hasattr(self, 'files'):
            return
        self.files.setColumnHidden(3, bool(self.sources.scope()[1]) or self.files.viewport().width() < 850)
        # Keep the active date order visible even in compact windows.
        self.files.setColumnHidden(2, self.files.viewport().width() < 650 and
                                   self.library_view.currentData() != 'recent' and
                                   self.files_header.sortIndicatorSection() != 2)
        if hasattr(self, 'sync_panel') and not self.sync_panel.external_report:
            self.sync_panel.report_host.setMaximumHeight(max(100, min(260, self.height() - 500)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adapt_columns()

    def filter_files(self):
        if self.filter_panel is None:
            self.filter_panel = FileFilterDialog(self)
            self.content_layout.insertWidget(self.content_layout.indexOf(self.library_widget) + 1, self.filter_panel)
        self.filter_panel.setVisible(not self.filter_panel.isVisible())
        if self.filter_panel.isVisible():
            self.filter_panel.course.setFocus()

    def search_files(self, text):
        self.file_filters['search'] = text
        self.apply_file_filters()

    def focus_search(self):
        if self.libraries:
            self.workspace_tabs.setCurrentIndex(1)
            self.file_search.setFocus()
            self.file_search.selectAll()

    def change_library_view(self, *_):
        if not hasattr(self, 'files'):
            return
        self.apply_file_filters()
        self.adapt_columns()
        self.files.sortItems(2, Qt.SortOrder.DescendingOrder)

    def clear_file_filters(self):
        self.file_filters = {'search': '', 'course': '', 'kind': '', 'size': ''}
        if self.filter_panel:
            for widget in (self.filter_panel.course, self.filter_panel.kind, self.filter_panel.size):
                widget.blockSignals(True)
                widget.setCurrentIndex(0)
                widget.blockSignals(False)
        self.file_search.clear()
        self.apply_file_filters()

    def apply_file_filters(self):
        if not hasattr(self, 'files'):
            return 0
        filters = self.file_filters
        if self.file_search.text() != filters['search']:
            self.file_search.blockSignals(True)
            self.file_search.setText(filters['search'])
            self.file_search.blockSignals(False)
        view = self.library_view.currentData()
        visible, eligible = 0, 0
        for row in range(self.files.rowCount()):
            item = self.files.item(row, 0)
            if not item:
                continue
            entry = item.data(Qt.ItemDataRole.UserRole + 1)
            size = entry.get('target_stat', [0])[0]
            info = is_course_info(entry)
            in_view = (view == 'all' or view == 'materials' and not info or view == 'info' and info or
                       view == 'recent' and not info and bool(entry.get('changed_at')))
            eligible += bool(in_view)
            size_ok = (not filters['size'] or
                       filters['size'] == 'small' and size <= 1024 ** 2 or
                       filters['size'] == 'medium' and 1024 ** 2 < size <= 10 * 1024 ** 2 or
                       filters['size'] == 'large' and size > 10 * 1024 ** 2)
            searchable = ' '.join((entry['path'], entry.get('course_name', ''), entry.get('_source_name', ''))).casefold()
            matches = (in_view and filters['search'].casefold() in searchable and
                       (not filters['course'] or course_key(entry, global_scope=not self.selected()) == filters['course']) and
                       (not filters['kind'] or (Path(entry['path']).suffix.casefold() or '<none>') == filters['kind']) and size_ok)
            self.files.setRowHidden(row, not matches)
            visible += bool(matches)
        active = any(filters.values())
        self.files_header.filter_button.setChecked(active)
        self.files_header.filter_button.setToolTip(t('Filters active') if active else t('Filter files'))
        self.clear_filters_button.setVisible(active)
        self.file_count.setText(t('{visible} of {total} files', visible=visible, total=eligible) if active else
                                t('1 file') if visible == 1 else t('{count} files', count=visible))
        if visible:
            self.files.set_empty('', '')
        elif active:
            self.files.set_empty(t('No matching materials'), t('Try another search or clear the filters.'))
        elif view == 'recent':
            self.files.set_empty(t('No recent changes yet'), t('New and updated materials will appear here after a sync.'))
        elif view == 'info':
            self.files.set_empty(t('No course information yet'), t('Course descriptions and links appear here after a sync.'))
        else:
            self.files.set_empty(t('Your materials will appear here'), t('Start a sync to download files from your courses.'))
        self.update_file_actions()
        return visible

    def selected_entry(self):
        if not hasattr(self, 'files'):
            return None
        row = self.files.currentRow()
        if row < 0 or self.files.isRowHidden(row):
            return None
        item = self.files.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole + 1) if item else None

    def update_file_actions(self):
        if hasattr(self, 'file_open_button'):
            self.file_open_button.setEnabled(self.selected_entry() is not None)

    def file_target(self):
        entry = self.selected_entry()
        if not entry:
            return None
        from .storage import safe_path
        try:
            return safe_path(Path(entry.get('root', entry['_destination'])), entry['path'])
        except ValueError:
            self.show_local_error(t('This file path is unavailable. Try synchronizing again.'), kind='path',
                                  source_id=entry['_source_id'], entry=entry)
            return None

    def open_file(self):
        target = self.file_target()
        if target is None:
            return
        if not target.is_file():
            entry = self.selected_entry()
            self.show_local_error(t('This file is missing locally. Sync again to restore it.'),
                                  kind='missing', source_id=entry['_source_id'], entry=entry)
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
            self.show_local_error(t('The file could not be opened. Check its default application.'), kind='open',
                                  source_id=self.selected_entry()['_source_id'], entry=self.selected_entry())

    def reveal_file(self):
        target = self.file_target()
        if target:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.parent)))

    def file_menu(self, point):
        item = self.files.itemAt(point)
        if not item:
            return
        self.files.selectRow(item.row())
        menu = QMenu(self)
        menu.addAction(t('Open file'), self.open_file)
        menu.addAction(t('Open containing folder'), self.reveal_file)
        entry = self.selected_entry()
        if entry and entry.get('course_id') and self.sources.scope() != (entry['_source_id'], entry['course_id']):
            menu.addSeparator()
            menu.addAction(t('Show course'), lambda: self.sources.select_scope(entry['_source_id'], entry['course_id']))
        menu.exec(self.files.viewport().mapToGlobal(point))

    def show_progress(self, text):
        state = self.run_info.get('state', 'running') if self.run_info else 'running'
        loading = self.job and self.job[0] == 'discover'
        title = {'running': t('Loading your courses') if loading else t('Synchronizing your materials'), 'paused': t('Synchronization paused'),
                 'stopping': t('Finishing safely…')}[state]
        identity = self.run_info.get('source') if self.run_info else self.job[1].id if self.job else None
        library = self.libraries.get(identity)
        if library:
            title += ' · ' + library['source'].name
        self.sync_panel.set_state(title, text, 'running' if state == 'running' else 'neutral', busy=state != 'paused')
        self.recovery_button.hide()
        self.update_sync_age()
        self.sync_panel.schedule.setText(text)

    def show_local_error(self, text, *, kind=None, source_id=None, entry=None, error_status=None):
        self.ui_error = text
        self.ui_error_status = error_status or {'state': 'Needs attention', 'message': text, 'failure_kind': kind or 'local'}
        self.ui_error_kind = kind or 'local'
        if entry is not None:
            self.ui_error_entry = dict(entry)
        elif self.ui_error_kind not in {'missing', 'open', 'path'}:
            self.ui_error_entry = None
        self.ui_error_source = source_id or (self.job[1].id if self.job else self.selected().id if self.selected() else None)
        self.recovery_source = self.ui_error_source
        self.recovery_plan = recovery_plan(self.ui_error_status)
        summary = sync_summary(self.ui_error_status, None) if error_status else None
        self.sync_panel.set_state(summary.title if summary else t('Something needs attention'), message(text),
                                  summary.tone if summary else 'error')
        self.recovery_button.setVisible(bool(self.ui_error_source))
        if self.ui_error_kind == 'open':
            self.recovery_button.setText(t('Open containing folder'))
            self.recovery_button.setToolTip(t('The file was kept. Open its folder to choose another application.'))
        elif self.ui_error_kind == 'missing':
            self.recovery_button.setText(t('Restore file'))
            self.recovery_button.setToolTip(t('Checks this university and downloads missing materials again. Existing files are kept.'))
        elif self.recovery_plan:
            self.recovery_button.setText(self.recovery_plan.button)
            self.recovery_button.setToolTip(self.recovery_plan.explanation)
        self.refresh_controls()

    def recover(self):
        if self.ui_error and self.ui_error_kind == 'open':
            from .storage import safe_path
            entry = self.ui_error_entry
            if entry:
                target = safe_path(Path(entry.get('root', entry['_destination'])), entry['path'])
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.parent)))
            return
        if self.ui_error and self.ui_error_kind == 'missing':
            source = next((source for source in self.settings.sources() if source.id == self.ui_error_source), None)
            if source:
                self.begin_repair(source, 'missing')
            return
        self.run_recovery(self.recovery_source, self.recovery_plan)

    def run_recovery(self, identity, plan):
        source = next((source for source in self.settings.sources() if source.id == identity), None)
        if not source or not plan or self.process or self.run_info:
            return
        if plan.action == 'signin':
            self.edit(signin=True) if self.selected() and self.selected().id == identity else self.edit(signin=True, source=source)
        elif plan.action == 'folders':
            self.folder_mapping(verify=True) if self.selected() and self.selected().id == identity else self.folder_mapping(source, verify=True)
        elif plan.action == 'storage':
            self.edit(source=source, storage=True, verify=True)
        elif plan.action == 'browser':
            QDesktopServices.openUrl(QUrl(source.url))
        else:
            self.begin_repair(source, plan.kind)

    def begin_repair(self, source, kind):
        self.last_repair_source = source.id
        self.repair_checks[source.id] = {'kind': kind, 'phase': 'checking', 'started': time.time()}
        if kind == 'missing' and (self.ui_error_entry or self.selected_entry()):
            self.repair_checks[source.id]['identity'] = (self.ui_error_entry or self.selected_entry())['_identity']
        self.ui_error = ''
        self.ui_error_kind = ''
        self.start('sync', source)

    def report(self):
        self.sync_panel.disclosure.setChecked(True)

    def toggle_report(self, expanded):
        self.workspace_tabs.setCurrentIndex(3 if expanded else 0)

    def build_report(self, identity=None):
        previous = identity or (self.report_source.currentData() if hasattr(self, 'report_source') else None)
        host = self.sync_panel.report_layout
        while host.count():
            widget = host.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.report_source = Dropdown()
        self.report_source.setAccessibleName(t('University report'))
        source = self.selected()
        choices = [source] if source else [row['source'] for row in self.libraries.values()]
        for choice in choices:
            self.report_source.addItem(choice.name, choice.id)
        self.report_source.setCurrentIndex(max(0, self.report_source.findData(previous)))
        host.addWidget(self.report_source)
        self.report_source.setVisible(len(choices) > 1)
        source_id = self.report_source.currentData()
        if not source_id:
            return
        from .notifications import notices
        recorded_notices = notices(source_id)
        if recorded_notices:
            host.addWidget(label('Current notices', 'sectionTitle'))
            host.addWidget(label('Dismissal hides a notice; it does not fix the problem or remove the report.', 'subtitle'))
            for row in recorded_notices:
                if not row.get('resolved'):
                    host.addWidget(self.notice_widget(source_id, row, details=True))
        status = self.libraries[source_id]['status']
        if self.ui_error and (self.ui_error_source or (self.selected().id if self.selected() else None)) == source_id:
            status = self.ui_error_status or {'state': 'Needs attention', 'message': self.ui_error, 'failure_kind': self.ui_error_kind}
        plan = recovery_plan(status)
        if source_id == self.ui_error_source and self.ui_error_kind == 'missing':
            plan = recovery_plan({'failure_kind': 'missing'})
        if plan:
            guide = QWidget()
            guide_layout = QVBoxLayout(guide)
            guide_layout.setContentsMargins(0, 0, 0, 0)
            explain = source_id != getattr(self, 'recovery_source', None) or self.sync_panel.tone != 'error'
            steps = label((plan.explanation + '\n\n' if explain else '') + '\n'.join(plan.steps), 'subtitle')
            steps.setAccessibleName(t('Steps to recover'))
            guide_layout.addWidget(steps)
            actions = QHBoxLayout()
            if plan.action != 'retry' and (source_id != getattr(self, 'recovery_source', None) or self.recovery_button.isHidden()):
                action = button(plan.button, lambda: self.run_recovery(source_id, plan))
                action.setEnabled(not (self.process or self.run_info))
                actions.addWidget(action)
            if plan.action != 'browser':
                actions.addWidget(button('Open ILIAS', lambda: QDesktopServices.openUrl(QUrl(self.libraries[source_id]['source'].url))))
            actions.addStretch()
            guide_layout.addLayout(actions)
            host.addWidget(guide)
        active_id = self.run_info.get('source') if self.run_info else self.job[1].id if self.process and self.job else None
        if active_id == source_id:
            status = {'state': 'Running', 'started': status.get('started')}
        history = read_json(data_dir() / 'sources' / source_id / 'history.json', [])
        history = [status, *[row for row in history if (row.get('finished'), row.get('started')) != (status.get('finished'), status.get('started'))]]
        self.report_widget = SyncReportDialog(status, self.activity.toPlainText() if active_id == source_id else '',
                                              self.sync_panel.report_host, history=history, embedded=True)
        host.addWidget(self.report_widget)
        self.report_widget.show()
        self.report_source.currentIndexChanged.connect(lambda *_: self.build_report(self.report_source.currentData()))

    def toggle_sidebar(self):
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        self.view_state['sidebar_hidden'] = not visible
        name = t('Hide sidebar') if visible else t('Show sidebar')
        self.sidebar_button.setToolTip(name)
        self.sidebar_button.setAccessibleName(name)
        self.sidebar_action.setText(name)
        self.adapt_columns()

    def edit_source(self, identity):
        if self.process or self.run_info:
            return
        self.sources.select_scope(identity)
        self.edit()

    def source_menu(self, source, parent):
        menu = QMenu(source.name, parent)
        for name, callback in [('Choose sync courses…', lambda: self.start('discover', source)),
                               ('Folder mapping', lambda: self.folder_mapping(source)),
                               ('Open folder', lambda: self.open_folder(source)),
                               ('Edit source', lambda: self.edit_source(source.id))]:
            action = menu.addAction(t(name), callback)
            action.setEnabled(name == 'Open folder' or not (self.process or self.run_info))
        return menu

    def management_menu(self):
        source = self.selected()
        if source:
            menu = self.source_menu(source, self)
        else:
            menu = QMenu(self)
            for library in self.libraries.values():
                menu.addMenu(self.source_menu(library['source'], menu))
            menu.addSeparator()
            menu.addAction(t('Add ILIAS'), self.add).setEnabled(not (self.process or self.run_info))
        menu.exec(self.management_button.mapToGlobal(self.management_button.rect().bottomLeft()))

    def navigation_menu(self, point):
        item = self.sources.itemAt(point)
        if not item:
            return
        identity = item.data(0, Qt.ItemDataRole.UserRole)[0]
        if identity:
            menu = self.source_menu(self.libraries[identity]['source'], self)
            menu.exec(self.sources.viewport().mapToGlobal(point))

    def add(self):
        if self.process or self.run_info:
            return
        dialog = SourceDialog(self.settings, parent=self)
        if dialog.exec():
            self.setMinimumSize(820, 560)
            self.resize(980, 700)
            self.populate(dialog.source.id)

    def edit(self, *, signin=False, source=None, storage=False, verify=False):
        source = source or self.selected()
        if not source or self.process or self.run_info:
            return
        dialog = SourceDialog(self.settings, source, self, signin_recovery=signin, verify_on_save=verify)
        if storage:
            dialog.stack.setCurrentIndex(2)
            dialog.update_step()
            dialog.next_button.setText(t('Save and check'))
        if dialog.exec():
            self.populate()
            if signin or verify:
                self.begin_repair(dialog.source, 'signin' if signin else 'storage')

    def start(self, action, source=None):
        source = source or self.selected()
        if not source or self.process or self.run_info:
            return
        self.job = (action, source)
        self.job_started = time.time()
        self.ui_error = ''
        self.ui_error_kind = ''
        self.ui_error_status = None
        if source.id in self.repair_checks and self.repair_checks[source.id]['phase'] != 'checking':
            self.repair_checks.pop(source.id)
        self.progress_message = ""
        self.progress_token = None
        self.process = QProcess(self)
        self.event_path.write_text("", encoding="utf-8")
        self.event_offset = 0
        self.activity.clear()
        cmd = command("--" + action, "--profile", source.id, "--event-file", str(self.event_path))
        self.process.setProgram(cmd[0])
        self.process.setArguments(cmd[1:])
        self.buffer = ""
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.worker_error)
        self.process.start()
        self.pause_button.set_action("pause")
        self.stop_button.show()
        self.progress_timer.start()
        self.timeout.start((120 if action == "discover" else 5500) * 1000)
        self.show_progress(t("Checking ILIAS…"))
        self.refresh_controls()

    def worker_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.timeout.stop()
            self.progress_timer.stop()
            self.process.deleteLater()
            self.process = None
            self.sync_queue.clear()
            self.show_local_error(t("The worker could not start."))
            self.refresh_controls()

    def check_active_run(self, *_):
        run = active_run()
        self.run_info = run if run and run.get("state") in {"running", "paused", "stopping"} else None
        self.refresh_controls()
        if self.run_info:
            if self.run_info['state'] == 'stopping':
                self.sync_queue.clear()
            if self.progress_token != self.run_info['token']:
                self.progress_message = ""
                self.progress_token = self.run_info['token']
            self.progress_message = self.run_info.get('message', self.progress_message)
            paused = self.run_info["state"] == "paused"
            if paused:
                self.timeout.stop()
            elif self.process and not self.timeout.isActive():
                self.timeout.start((120 if self.job[0] == "discover" else 5500) * 1000)
            if paused or self.run_info["state"] == "stopping":
                self.show_progress(t("Paused" if paused else "Stopping…"))
            else:
                self.show_progress(progress_copy(self.progress_message) if self.progress_message else t("Checking ILIAS…"))
            if not self.progress_timer.isActive():
                self.progress_timer.start()
        elif not self.process:
            self.progress_timer.stop()
            self.refresh()

    def sync_or_pause(self):
        run = self.run_info or active_run()
        if run and run.get("state") in {"running", "paused"}:
            send_command(run, "resume" if run["state"] == "paused" else "pause")
        elif not self.process:
            if self.selected():
                self.start("sync")
            else:
                self.sync_queue = [source for source in self.settings.sources() if source.enabled]
                if self.sync_queue:
                    self.start('sync', self.sync_queue.pop(0))

    def stop_sync(self):
        self.sync_queue.clear()
        run = self.run_info or active_run()
        if run and run.get("state") in {"running", "paused"}:
            send_command(run, "stop")
            self.show_progress(t("Stopping…"))
            self.stop_button.setEnabled(False)

    def refresh_controls(self):
        busy = self.process is not None or self.run_info is not None
        self.sources.setEnabled(True)
        self.sync_button.setVisible(bool(self.libraries))
        self.sync_button.setEnabled(not busy and bool(self.selected() or any(source.enabled for source in self.settings.sources())))
        self.sync_button.set_action()
        self.pause_button.set_action("resume" if self.run_info and self.run_info["state"] == "paused" else "pause")
        self.pause_button.setVisible(busy)
        self.pause_button.setEnabled(busy and not (self.run_info and self.run_info['state'] == 'stopping'))
        if not self.selected() and self.libraries:
            self.sync_button.setText(t('Sync all'))
            self.sync_button.setAccessibleName(t('Sync all'))
        if not busy:
            self.sync_button.setToolTip(t('Checks all configured courses at this university; browsing a course does not change the sync selection.')
                                       if self.selected() else t('Checks all enabled universities one after another.'))
        self.add_button.setEnabled(not busy)
        self.settings_button.setEnabled(not busy)
        self.recovery_button.setEnabled(not busy)
        if getattr(self, 'recovery_plan', None) and self.recovery_plan.action == 'retry':
            self.recovery_button.hide()
        self.stop_button.setVisible(busy)
        self.stop_button.setEnabled(busy and not (self.run_info and self.run_info["state"] == "stopping"))

    def read_output(self):
        if self.process is None:
            self.check_active_run()
            return
        self.process.readAllStandardOutput()
        self.process.readAllStandardError()
        if self.event_path.exists():
            with self.event_path.open("r", encoding="utf-8") as events:
                events.seek(self.event_offset)
                self.buffer += events.read()
                self.event_offset = events.tell()
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event["event"] == "control":
                self.check_active_run()
            elif event["event"] == "progress":
                self.progress_message = event["message"]
                if not self.run_info or self.run_info["state"] == "running":
                    self.show_progress(progress_copy(event["message"]))
                self.activity.append(escape(message(event["message"])))
            elif event["event"] in {"error", "busy"}:
                self.activity.append(escape(message(event["message"])))
                status = {'state': 'Needs attention', 'message': event['message'], **event.get('status', {})}
                self.show_local_error(event['message'], source_id=event.get('profile'), error_status=status)
            elif event["event"] == "result" and self.job[0] == "discover":
                self.pending_courses = event["result"]["courses"]

    def finished(self, exit_code, exit_status):
        self.read_output()
        self.timeout.stop()
        self.progress_timer.stop()
        self.process.deleteLater()
        self.process = None
        self.run_info = None
        if self.job and self.job[0] == 'sync':
            latest = read_json(data_dir() / 'sources' / self.job[1].id / 'status.json', {})
            # Only the just-finished attempt may replace a transient worker
            # message. Busy/failed-to-start workers must not inherit old success.
            if (latest.get('finished') and latest.get('started', -1) >= getattr(self, 'job_started', time.time())
                    and latest.get('state') != 'Checking courses'):
                self.ui_error = ''
                self.ui_error_kind = ''
                self.ui_error_status = None
        if self.job and self.job[0] == 'sync' and self.job[1].id in self.repair_checks:
            repair = self.repair_checks[self.job[1].id]
            latest = read_json(data_dir() / 'sources' / self.job[1].id / 'status.json', {})
            result = latest.get('result')
            from .storage import source_scope
            verified = (not exit_code and latest.get('finished', 0) >= repair['started'] and
                        latest.get('state') in {'Up to date', 'Completed with warnings'} and
                        latest.get('scope') == source_scope(self.job[1]) and
                        result is not None and not result.get('errors'))
            repair['phase'] = 'verified' if verified else 'failed'
            repair['finished'] = latest.get('finished')
            if verified and repair['kind'] == 'missing':
                from .storage import safe_path
                entry = read_json(data_dir() / 'sources' / self.job[1].id / 'manifest.json', {'files': {}})['files'].get(repair.get('identity'))
                try:
                    present = entry and safe_path(Path(entry.get('root', self.job[1].destination)), entry['path']).is_file()
                except (ValueError, OSError):
                    present = False
                if not present:
                    repair['phase'] = 'failed'
                    self.ui_error = t('The file is still missing. Check whether it is available in ILIAS before trying again.')
                    self.ui_error_kind = 'missing'
                    self.ui_error_source = self.job[1].id
        self.refresh()
        if self.job[0] == "discover" and hasattr(self, "pending_courses"):
            courses = self.pending_courses
            del self.pending_courses
            CoursesDialog(courses, self.job[1], self.settings, self).exec()
            self.refresh()
        elif exit_code and self.selected():
            self.activity.append(t("Some items need attention. Existing files were kept."))
        self.refresh_controls()
        if self.sync_queue:
            next_source = self.sync_queue.pop(0)
            QTimer.singleShot(0, lambda: self.start('sync', next_source))

    def timeout_job(self):
        if self.process:
            self.stop_sync()
            self.activity.append(t("The job exceeded its time limit and was stopped. It can be retried safely."))

    def folder_mapping(self, source=None, *, verify=False):
        source = source if isinstance(source, Source) else self.selected()
        if source and not self.process and not self.run_info:
            dialog = FolderMappingDialog(source, self.settings, self)
            if verify:
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).setText(t('Save and check'))
            saved = dialog.exec()
            self.refresh()
            if saved and verify:
                updated = next(row for row in self.settings.sources() if row.id == source.id)
                self.begin_repair(updated, 'folders')

    def open_folder(self, source=None):
        source = source if isinstance(source, Source) else self.selected()
        if source:
            QDesktopServices.openUrl(QUrl.fromLocalFile(source.destination))

    def background(self, tab=0):
        if self.process or self.run_info:
            QMessageBox.information(self, t("Sync is running"), t("Let the current sync finish before changing settings."))
            return
        previous_language = self.settings.value.get("language", "de")
        dialog = SettingsDialog(self.settings, self)
        dialog.tabs.setCurrentIndex(tab if isinstance(tab, int) else 0)
        if dialog.exec():
            self.refresh()
            if previous_language != self.settings.value.get("language", "de"):
                replacement = MainWindow()
                replacement.resize(self.size())
                replacement.populate(self.selected().id if self.selected() else None)
                replacement.sources.select_scope(*self.sources.scope())
                QApplication.instance().main_window = replacement
                replacement.show()
                self.close()

    def schedule_text(self):
        if not self.settings.value["scheduled"]:
            return t("Automatic sync: off")
        if self.settings.value.get('schedule_mode') == 'weekly':
            return t('Automatic sync: weekly schedule')
        if self.settings.value.get('schedule_mode') == 'times':
            return t('Automatic sync: daily at {times}', times=', '.join(self.settings.value.get('sync_times', [])))
        n = self.settings.value["interval_hours"]
        return t("Automatic sync: hourly") if n == 1 else t("Automatic sync: every {n} hours", n=n)

    def about(self):
        HelpDialog(self).exec()

    def closeEvent(self, event):
        if self.process:
            QMessageBox.information(self, t("A download is running"), t("Wait for the download to finish before closing. You can minimize this window."))
            event.ignore()
        else:
            source = self.selected()
            self.view_state.update(size=[self.width(), self.height()], source=source.id if source else None,
                                   navigation=list(self.sources.scope()))
            if self.libraries:
                self.view_state.setdefault('views', {})['/'.join(self.sources.scope())] = self.library_view.currentData()
            write_json(data_dir() / 'view-state.json', self.view_state)
            self.event_path.unlink(missing_ok=True)
            event.accept()


def run(args):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("org.iliassync.desktop")
    application = QApplication(sys.argv[:1])
    from .native_compat import protect_accessibility
    protect_accessibility(application)
    application.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    application.setApplicationName("IliasSync")
    application.setOrganizationName("IliasSync")
    application.setDesktopFileName("org.iliassync.desktop")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(app_icon())
    application.theme = Theme(application, Settings().value.get("appearance", "system"))
    window = MainWindow()
    application.main_window = window
    window.show()
    if args.render:
        QTimer.singleShot(200, lambda: (window.grab().save(args.render), application.quit()))
    return application.exec()
