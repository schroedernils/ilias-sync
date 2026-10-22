"""A small Qt Widgets interface. Work happens in one disposable headless subprocess."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QFileSystemWatcher, QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QPainter, QFontDatabase, QPalette
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QTextBrowser, QTabWidget, QVBoxLayout, QWidget, QSizePolicy, QFrame, QStackedWidget, QTreeWidget, QTreeWidgetItem,
)

from . import __version__
from .branding import BrandMark, app_icon, paint_action
from .info import info_html
from .control import active_run, send_command
from .theme import LIGHT, Theme, stylesheet
from .i18n import message, set_language, t
from .scheduler import command, install, uninstall
from .security import import_session, store_password
from .storage import Settings, Source, data_dir, read_json

STYLE = stylesheet(LIGHT)


def label(text, name=None):
    item = QLabel(t(text))
    item.setWordWrap(True)
    item.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    if name:
        item.setObjectName(name)
    return item


def button(text, callback, primary=False):
    item = QPushButton(t(text))
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
    def __init__(self, text, callback, primary=False):
        super().__init__(t(text))
        self.action = None
        self.clicked.connect(callback)
        if primary:
            self.setObjectName('primary')

    def set_action(self, action=None):
        self.action = action
        name = t({'pause':'Pause', 'resume':'Resume', 'stop':'Stop'}.get(action, 'Sync now'))
        self.setAccessibleName(name)
        self.setToolTip(name)
        self.setText('' if action else name)
        if action:
            self.setFixedSize(42, 36)
        else:
            self.setMinimumSize(0, 36)
            self.setMaximumSize(16777215, 36)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.action:
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
    def __init__(self, settings, existing=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.existing = existing
        self.process = None
        self.event_file = data_dir() / ("probe-" + str(uuid4()) + ".jsonl")
        self.source = None
        self.setWindowTitle(t("Edit ILIAS source" if existing else "Add an ILIAS source"))
        self.resize(620, 580)
        self.setMinimumSize(560, 540)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 22)
        outer.setSpacing(16)
        self.step_label = label("", "step")
        outer.addWidget(self.step_label)
        self.heading = label("", "title")
        outer.addWidget(self.heading)
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
        outer.addWidget(self.stack, 1)
        self.name = QLineEdit(existing.name if existing else "")
        self.name.setPlaceholderText(t("University / campus"))
        self.url = QLineEdit(existing.url if existing else "")
        self.url.setPlaceholderText("https://ilias.example.edu")
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
        self.password.setPlaceholderText(t("Leave blank to keep saved password") if existing else "")
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
        self.forms[0].addWidget(label("Use the start address of your university's ILIAS.", "subtitle"))
        self.note = label("Import a cookies.txt export from your browser. When the session expires, import a new export.", "subtitle")
        self.forms[1].addWidget(self.note)
        self.advanced = button("Client ID…", self.toggle_client)
        self.advanced.setObjectName("quiet")
        self.forms[1].addWidget(self.advanced, alignment=Qt.AlignmentFlag.AlignLeft)
        self.vault_note = label("Saved in the system credential vault", "subtitle")
        self.forms[1].addWidget(self.vault_note)
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

    def update_step(self):
        index = self.stack.currentIndex()
        self.step_label.setText(t("Step {step} of 3", step=index + 1))
        self.heading.setText(t(["Your university", "Sign in to ILIAS", "Choose your files"][index]))
        self.back_button.setEnabled(index > 0)
        self.next_button.setText(t("Save" if index == 2 else "Continue"))
        self.error.hide()

    def back(self):
        self.stack.setCurrentIndex(max(0, self.stack.currentIndex() - 1))
        self.update_step()

    def advance(self):
        from .storage import server_url
        try:
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
        for line in output.splitlines():
            try:
                event = json.loads(line)
                if event["event"] == "result":
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
                    self.stack.setCurrentIndex(1)
                    self.update_step()
                    self.show_error(event["message"])
            except (ValueError, KeyError):
                pass

    def done(self, result):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        self.event_file.unlink(missing_ok=True)
        super().done(result)

    def save(self):
        try:
            kwargs = {"id": self.existing.id} if self.existing else {}
            source = Source(name=self.name.text().strip(), url=self.url.text(), destination=self.destination.text(),
                            username=self.user.text().strip(), client_id=self.client.text().strip(),
                            login=self.mode.currentData(), idp_host=self.idp.text().strip(),
                            automatic_courses=self.automatic.isChecked(),
                            targets=[s.strip() for s in self.targets.toPlainText().splitlines() if s.strip()],
                            videos=self.videos.isChecked(), folder_rules=self.existing.folder_rules if self.existing else {}, **kwargs)
            source.validate()
            if source.login != "session":
                if not source.username:
                    raise ValueError("Enter your university username.")
                if self.password.text():
                    store_password(source.id, self.password.text())
                elif not self.existing:
                    raise ValueError("Enter a password, or choose browser-session sign-in.")
            elif self.session.text():
                import_session(Path(self.session.text()), source.url, data_dir() / "sources" / source.id / "cache/.cookies")
            elif not self.existing:
                raise ValueError("Choose a browser session file.")
            self.settings.save_source(source)
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
        buttons = save_buttons()
        layout.addWidget(buttons)

        def save():
            source.automatic_courses = auto.isChecked()
            source.targets = [listing.item(i).data(Qt.ItemDataRole.UserRole) for i in range(listing.count())
                              if listing.item(i).checkState() == Qt.CheckState.Checked]
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
        self.setWindowTitle(t("Folder mapping"))
        self.resize(880, 620)
        self.setMinimumSize(720, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        layout.addWidget(label("Folder mapping", "title"))
        layout.addWidget(label("Choose destinations for courses, folders or individual files.", "subtitle"))
        search = QLineEdit()
        search.setPlaceholderText(t("Search courses and files…"))
        layout.addWidget(search)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([t("Course / content"), t("Download folder")])
        self.tree.setColumnWidth(0, 400)
        self.tree.setAccessibleName(t("Course folder assignments"))
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        layout.addWidget(self.tree, 1)
        state = data_dir() / 'sources' / source.id
        courses = read_json(state / 'courses.json', [])
        entries = read_json(state / 'manifest.json', {'files':{}})['files']
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
        self.selected_label = label("Select a course or file.", "subtitle")
        layout.addWidget(self.selected_label)
        row = QHBoxLayout()
        self.target = QLineEdit()
        self.target.setPlaceholderText(t("Inherit parent destination"))
        self.target.setReadOnly(True)
        row.addWidget(self.target, 1)
        self.choose_button = button("Choose folder…", self.choose)
        self.reset_button = button("Reset", self.reset_rule)
        row.addWidget(self.choose_button)
        row.addWidget(self.reset_button)
        layout.addLayout(row)
        layout.addWidget(label("Changes apply on the next sync. Existing copies at previous destinations are kept.", "subtitle"))
        if not entries:
            layout.addWidget(label("Course contents appear after the first sync.", "subtitle"))
        self.error = label("", "error")
        self.error.hide()
        layout.addWidget(self.error)
        buttons = save_buttons()
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.choose_button.setEnabled(False)
        self.reset_button.setEnabled(False)

        def filter_tree(text):
            def visit(item):
                children = [visit(item.child(i)) for i in range(item.childCount())]
                visible = text.casefold() in item.text(0).casefold() or any(children)
                item.setHidden(not visible)
                if text and visible:
                    item.setExpanded(True)
                return visible
            for i in range(self.tree.topLevelItemCount()):
                visit(self.tree.topLevelItem(i))
        search.textChanged.connect(filter_tree)

    def update_targets(self):
        def visit(item):
            key = item.data(0, Qt.ItemDataRole.UserRole)
            item.setText(1, self.rules.get(key, t("Inherited")))
            item.setToolTip(1, self.rules.get(key, self.source.destination))
            for i in range(item.childCount()):
                visit(item.child(i))
        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    def selected(self, item, previous=None):
        self.choose_button.setEnabled(item is not None)
        self.reset_button.setEnabled(item is not None)
        if item:
            self.selected_label.setText(item.text(0))
            self.target.setText(self.rules.get(item.data(0, Qt.ItemDataRole.UserRole), ''))

    def choose(self):
        item = self.tree.currentItem()
        if not item:
            return
        folder = QFileDialog.getExistingDirectory(self, t("Choose folder…"), self.target.text() or self.source.destination)
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

    def save(self):
        previous = self.source.folder_rules
        try:
            self.source.folder_rules = self.rules
            self.settings.save_source(self.source)
            self.accept()
        except ValueError as exc:
            self.source.folder_rules = previous
            self.error.setText(message(str(exc)))
            self.error.show()


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(t("Settings"))
        self.resize(590, 550)
        self.setMinimumWidth(550)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(26, 24, 26, 22)
        outer.setSpacing(16)
        outer.addWidget(label("Settings", "title"))
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("dialogBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        self.language = Dropdown()
        self.language.addItem("Deutsch", "de")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(self.language.findData(settings.value.get("language", "de")))
        self.appearance = Dropdown()
        for title, value in [("Follow system", "system"), ("Light", "light"), ("Dark", "dark")]:
            self.appearance.addItem(t(title), value)
        self.appearance.setCurrentIndex(self.appearance.findData(settings.value.get("appearance", "system")))
        self.enabled = QCheckBox(t("Automatic sync"))
        self.enabled.setChecked(settings.value["scheduled"])
        self.hours = Dropdown()
        for n in (1, 3, 6, 12, 24):
            self.hours.addItem(t("Every hour") if n == 1 else t("Every {n} hours", n=n), n)
        self.hours.setCurrentIndex(self.hours.findData(settings.value["interval_hours"]))
        self.battery = QCheckBox(t("Pause on battery power"))
        self.battery.setChecked(settings.value["battery_saver"])
        self.enabled.toggled.connect(self.hours.setEnabled)
        self.enabled.toggled.connect(self.battery.setEnabled)
        self.hours.setEnabled(self.enabled.isChecked())
        self.battery.setEnabled(self.enabled.isChecked())
        for title, rows in [("Appearance", [("Language", self.language), ("Theme", self.appearance)]),
                            ("Synchronization", [("", self.enabled), ("Interval", self.hours), ("", self.battery)])]:
            layout.addWidget(label(title, "sectionTitle"))
            panel = QFrame()
            panel.setObjectName("surface")
            form = QFormLayout(panel)
            form.setContentsMargins(18, 14, 18, 14)
            form.setVerticalSpacing(14)
            form.setHorizontalSpacing(24)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            for caption, widget in rows:
                widget.setAccessibleName(t(caption) if caption else widget.text())
                if caption:
                    form.addRow(t(caption), widget)
                else:
                    form.addRow(widget)
            layout.addWidget(panel)
        layout.addWidget(label("Automatic runs continue when this window is closed. Your computer must be awake and signed in.", "subtitle"))
        layout.addStretch(1)
        scroll.setWidget(body)
        self.tabs.addTab(scroll, t("General"))
        self.info = QTextBrowser()
        self.info.setOpenExternalLinks(True)
        self.info.setHtml(info_html())
        self.info.setAccessibleName(t("About & usage"))
        self.tabs.addTab(self.info, t("Info"))
        self.error = label("", "error")
        self.error.hide()
        outer.addWidget(self.error)
        buttons = save_buttons()
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("primary")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.appearance.currentIndexChanged.connect(self.preview_theme)

    def preview_theme(self):
        app = QApplication.instance()
        if hasattr(app, "theme"):
            app.theme.set_mode(self.appearance.currentData())

    def reject(self):
        app = QApplication.instance()
        if hasattr(app, "theme"):
            app.theme.set_mode(self.settings.value.get("appearance", "system"))
        super().reject()

    def save(self):
        previous = dict(self.settings.value)
        try:
            self.settings.value.update(interval_hours=self.hours.currentData(), battery_saver=self.battery.isChecked(),
                                       language=self.language.currentData(), appearance=self.appearance.currentData())
            self.settings.save()
            if self.enabled.isChecked() and (not previous["scheduled"] or self.hours.currentData() != previous["interval_hours"]):
                install(self.hours.currentData())
            elif not self.enabled.isChecked() and previous["scheduled"]:
                uninstall()
            self.settings.value["scheduled"] = self.enabled.isChecked()
            self.settings.save()
            self.accept()
        except Exception:
            self.settings.value = previous
            self.settings.save()
            self.error.setText(t("The OS scheduler could not be updated. On Linux, a systemd user session is required."))
            self.error.show()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        set_language(self.settings.value.get("language", "de"))
        self.process = None
        self.run_info = None
        self.buffer = ""
        self.job = None
        self.event_path = data_dir() / ("job-" + str(uuid4()) + ".jsonl")
        self.event_offset = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.read_output)
        self.setWindowTitle(t("IliasSync"))
        self.resize(940, 640)
        self.setMinimumSize(800, 500)
        container = QWidget()
        page = QVBoxLayout(container)
        page.setContentsMargins(22, 20, 22, 18)
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(BrandMark())
        titles = QVBoxLayout()
        titles.addWidget(label("IliasSync", "title"))
        self.schedule_label = label(self.schedule_text(), "subtitle")
        titles.addWidget(self.schedule_label)
        header.addLayout(titles, 1)
        self.settings_button = IconButton("Settings", "settings", self.background)
        header.addWidget(self.settings_button)
        page.addLayout(header)
        page.addSpacing(12)
        split = QSplitter()
        left = QWidget()
        self.sidebar = left
        sidebar = QVBoxLayout(left)
        sidebar.setContentsMargins(0, 0, 8, 0)
        sidebar.addWidget(label("Sources", "eyebrow"))
        self.sources = QListWidget()
        self.sources.setAccessibleName(t("ILIAS sources"))
        self.sources.currentRowChanged.connect(self.refresh)
        sidebar.addWidget(self.sources, 1)
        sidebar.addWidget(button("Add ILIAS", self.add))
        split.addWidget(left)
        right = QWidget()
        content = QVBoxLayout(right)
        content.setContentsMargins(16, 0, 0, 0)
        content.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.setSpacing(10)
        self.source_title = label("Connect ILIAS", "title")
        source_heading = QHBoxLayout()
        source_heading.addWidget(self.source_title)
        self.routing_button = IconButton("Folder mapping", "folder-tree", self.folder_mapping)
        self.edit_button = IconButton("Edit source", "pencil", self.edit)
        self.open_button = IconButton("Open folder", "folder-open", self.open_folder)
        source_heading.setSpacing(6)
        source_heading.addWidget(self.edit_button)
        source_heading.addStretch(1)
        content.addLayout(source_heading)
        self.destination = label("Add your university to download course files.", "subtitle")
        self.destination.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        destination_row = QHBoxLayout()
        destination_row.setSpacing(6)
        destination_row.addWidget(self.destination, 1)
        destination_row.addWidget(self.routing_button)
        destination_row.addWidget(self.open_button)
        content.addLayout(destination_row)
        self.onboard_button = button("Add ILIAS", self.add, True)
        content.addWidget(self.onboard_button, alignment=Qt.AlignmentFlag.AlignLeft)
        actions = QHBoxLayout()
        self.sync_button = RunButton("Sync now", self.sync_or_pause, True)
        self.stop_button = RunButton("Stop", self.stop_sync)
        self.stop_button.setObjectName("stopControl")
        self.stop_button.set_action("stop")
        self.stop_button.hide()
        self.courses_button = button("Choose courses", lambda: self.start("discover"))
        for item in (self.sync_button, self.stop_button, self.courses_button):
            actions.addWidget(item)
        actions.addStretch(1)
        self.empty_spacer = QWidget()
        content.addWidget(self.empty_spacer, 1)
        self.actions_widget = QWidget()
        self.actions_widget.setLayout(actions)
        content.addWidget(self.actions_widget)
        self.status = label("Not synchronized yet", "status")
        self.status.setAccessibleName(t("Synchronization status"))
        content.addWidget(self.status)
        self.files = QTableWidget(0, 2)
        self.files.setAccessibleName(t("Downloaded files"))
        self.files.setHorizontalHeaderLabels([t("File"), t("Size")])
        self.files.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files.verticalHeader().hide()
        self.files.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        content.addWidget(self.files, 1)
        self.activity = QTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setObjectName("activity")
        self.activity.setAccessibleName(t("Activity"))
        self.activity.setMaximumHeight(110)
        self.activity.document().setMaximumBlockCount(150)
        self.details_button = button("Details", lambda: self.activity.setVisible(not self.activity.isVisible()))
        content.addWidget(self.details_button, alignment=Qt.AlignmentFlag.AlignLeft)
        content.addWidget(self.activity)
        self.activity.hide()
        split.addWidget(right)
        split.setSizes([200, 700])
        page.addWidget(split, 1)
        self.setCentralWidget(container)
        about = QAction(t("About IliasSync"), self)
        about.triggered.connect(self.about)
        self.menuBar().addAction(about)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.timeout_job)
        self.populate()
        if not self.settings.sources():
            self.setMinimumSize(620, 390)
            self.resize(660, 420)
        self.run_watch = QFileSystemWatcher([str(data_dir())], self)
        self.run_watch.directoryChanged.connect(self.check_active_run)
        self.check_active_run()

    def selected(self):
        row = self.sources.currentRow()
        sources = self.settings.sources()
        return sources[row] if 0 <= row < len(sources) else None

    def populate(self, selected_id=None):
        self.sources.clear()
        for source in self.settings.sources():
            item = QListWidgetItem(source.name + "\n" + QUrl(source.url).host())
            self.sources.addItem(item)
        row = next((i for i, s in enumerate(self.settings.sources()) if s.id == selected_id), 0)
        self.sources.setCurrentRow(row)
        self.refresh()

    def refresh(self):
        source = self.selected()
        busy = self.process is not None or self.run_info is not None
        self.sidebar.setVisible(bool(self.settings.sources()))
        self.onboard_button.setVisible(source is None)
        self.empty_spacer.setVisible(source is None)
        self.schedule_label.setVisible(source is not None)
        for item in (self.sync_button, self.edit_button, self.courses_button, self.routing_button, self.open_button):
            item.setEnabled(source is not None and not busy)
        for widget in (self.actions_widget, self.status, self.files, self.details_button, self.routing_button, self.edit_button, self.open_button):
            widget.setVisible(source is not None)
        if not source:
            return
        self.source_title.setText(source.name)
        self.destination.setText(source.destination)
        state = data_dir() / "sources" / source.id
        status = read_json(state / "status.json", {})
        result = status.get("result", {})
        text = t(status.get("state", "Not synchronized yet"))
        if result:
            text += " · " + t("{count} files", count=result['files'])
            for key, template in [("unavailable", "{count} unavailable"), ("skipped", "{count} skipped"),
                                  ("warnings", "{count} warnings"), ("errors", "{count} errors")]:
                count = result.get(key, 0)
                if isinstance(count, dict):
                    count = sum(count.values())
                if count:
                    text += " · " + t(template, count=count)
        self.status.setText(message(status["message"]) if status.get("message") else text)
        entries = read_json(state / "manifest.json", {"files": {}})["files"]
        self.files.setRowCount(len(entries))
        for row, entry in enumerate(sorted(entries.values(), key=lambda e: e["path"].casefold())):
            item = QTableWidgetItem(entry["path"])
            item.setToolTip(str(Path(entry.get("root", source.destination)) / entry["path"]))
            self.files.setItem(row, 0, item)
            self.files.setItem(row, 1, QTableWidgetItem(f"{entry.get('target_stat', [0])[0] / 1024:.0f} KB"))

    def add(self):
        if self.process or self.run_info:
            return
        dialog = SourceDialog(self.settings, parent=self)
        if dialog.exec():
            self.setMinimumSize(800, 500)
            self.resize(940, 640)
            self.populate(dialog.source.id)

    def edit(self):
        dialog = SourceDialog(self.settings, self.selected(), self)
        if dialog.exec():
            self.populate(dialog.source.id)

    def start(self, action):
        source = self.selected()
        if not source or self.process or self.run_info:
            return
        self.job = (action, source)
        self.process = QProcess(self)
        self.event_path.write_text("", encoding="utf-8")
        self.event_offset = 0
        cmd = command("--" + action, "--profile", source.id, "--event-file", str(self.event_path))
        self.process.setProgram(cmd[0])
        self.process.setArguments(cmd[1:])
        self.buffer = ""
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.worker_error)
        self.process.start()
        self.sync_button.set_action("pause")
        self.stop_button.show()
        self.progress_timer.start()
        self.timeout.start((120 if action == "discover" else 5500) * 1000)
        self.status.setText(t("Checking ILIAS…"))
        self.refresh_controls()

    def worker_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.timeout.stop()
            self.progress_timer.stop()
            self.process.deleteLater()
            self.process = None
            self.status.setText(t("The worker could not start."))
            self.refresh_controls()

    def check_active_run(self, *_):
        run = active_run()
        self.run_info = run if run and run.get("state") in {"running", "paused", "stopping"} else None
        if self.run_info and (not self.selected() or self.selected().id != self.run_info["source"]):
            for index, source in enumerate(self.settings.sources()):
                if source.id == self.run_info["source"]:
                    self.sources.setCurrentRow(index)
                    break
        self.refresh_controls()
        if self.run_info:
            paused = self.run_info["state"] == "paused"
            if paused:
                self.timeout.stop()
            elif self.process and not self.timeout.isActive():
                self.timeout.start((120 if self.job[0] == "discover" else 5500) * 1000)
            self.status.setText(t("Paused" if paused else "Stopping…" if self.run_info["state"] == "stopping" else "Checking ILIAS…"))
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
            self.start("sync")

    def stop_sync(self):
        run = self.run_info or active_run()
        if run and run.get("state") in {"running", "paused"}:
            send_command(run, "stop")
            self.status.setText(t("Stopping…"))
            self.stop_button.setEnabled(False)

    def refresh_controls(self):
        busy = self.process is not None or self.run_info is not None
        self.sources.setEnabled(not busy)
        for item in (self.edit_button, self.courses_button, self.routing_button):
            item.setEnabled(not busy and self.selected() is not None)
        self.sync_button.setEnabled(self.selected() is not None)
        self.sync_button.set_action("resume" if self.run_info and self.run_info["state"] == "paused" else "pause" if busy else None)
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
                if not self.run_info or self.run_info["state"] == "running":
                    self.status.setText(message(event["message"]))
                self.activity.append(message(event["message"]))
            elif event["event"] in {"error", "busy"}:
                self.activity.append(message(event["message"]))
                self.status.setText(message(event["message"]))
            elif event["event"] == "result" and self.job[0] == "discover":
                self.pending_courses = event["result"]["courses"]

    def finished(self, exit_code, exit_status):
        self.read_output()
        self.timeout.stop()
        self.progress_timer.stop()
        self.process.deleteLater()
        self.process = None
        self.run_info = None
        self.refresh()
        if self.job[0] == "discover" and hasattr(self, "pending_courses"):
            courses = self.pending_courses
            del self.pending_courses
            CoursesDialog(courses, self.job[1], self.settings, self).exec()
        elif exit_code and self.selected():
            self.activity.append(t("Some items need attention. Existing files were kept."))
        self.refresh_controls()

    def timeout_job(self):
        if self.process:
            self.stop_sync()
            self.activity.append(t("The job exceeded its time limit and was stopped. It can be retried safely."))

    def folder_mapping(self):
        source = self.selected()
        if source and not self.process and not self.run_info:
            FolderMappingDialog(source, self.settings, self).exec()
            self.refresh()

    def open_folder(self):
        source = self.selected()
        if source:
            QDesktopServices.openUrl(QUrl.fromLocalFile(source.destination))

    def background(self):
        if self.process or self.run_info:
            QMessageBox.information(self, t("Sync is running"), t("Let the current sync finish before changing settings."))
            return
        previous_language = self.settings.value.get("language", "de")
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.schedule_label.setText(self.schedule_text())
            if previous_language != self.settings.value.get("language", "de"):
                replacement = MainWindow()
                replacement.resize(self.size())
                replacement.populate(self.selected().id if self.selected() else None)
                QApplication.instance().main_window = replacement
                replacement.show()
                self.close()

    def schedule_text(self):
        if not self.settings.value["scheduled"]:
            return t("Automatic sync: off")
        n = self.settings.value["interval_hours"]
        return t("Automatic sync: hourly") if n == 1 else t("Automatic sync: every {n} hours", n=n)

    def about(self):
        QMessageBox.about(self, t("About IliasSync"), "IliasSync " + __version__ + "\nGPL-3.0-or-later · PFERD · Qt\n\n"
                          + t("Preview. Files and supported videos are downloaded; forums, tests, SCORM and custom plugins may be excluded. No automatic updates or verified publisher signature.")
                          + "\n\ngithub.com/schroedernils/ilias-sync")

    def closeEvent(self, event):
        if self.process:
            QMessageBox.information(self, t("A download is running"), t("Wait for the download to finish before closing. You can minimize this window."))
            event.ignore()
        else:
            self.event_path.unlink(missing_ok=True)
            event.accept()


def run(args):
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("org.iliassync.desktop")
    application = QApplication(sys.argv[:1])
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
