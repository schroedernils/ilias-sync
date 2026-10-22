"""A small Qt Widgets interface. Work happens in one disposable headless subprocess."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget, QSizePolicy,
)

from . import __version__
from .i18n import message, set_language, t
from .scheduler import command, install, uninstall
from .security import import_session, store_password
from .storage import Settings, Source, data_dir, read_json

STYLE = """
QWidget { font-size: 13px; color: #202124; }
QMainWindow, QDialog { background: #fafafa; }
QLabel#eyebrow { color: #60646b; font-size: 12px; font-weight: 600; }
QLabel#title { font-size: 25px; font-weight: 600; }
QLabel#subtitle { color: #60646b; }
QLabel#status { padding: 12px 14px; border-radius: 8px; background: #eef1f5; }
QPushButton { background: #fff; border: 1px solid #d2d6dc; border-radius: 7px; padding: 9px 14px; }
QPushButton:hover { background: #f0f2f5; border-color: #8a939e; }
QPushButton:pressed { background: #e4e8ed; }
QPushButton:focus { border: 2px solid #2463b5; }
QPushButton:disabled { color: #92969d; background: #f5f5f5; }
QPushButton#primary { background: #2463b5; color: #fff; border-color: #2463b5; font-weight: 600; }
QPushButton#primary:hover { background: #1b5197; }
QPushButton#primary:disabled { background: #a4b6ce; border-color: #a4b6ce; }
QLineEdit, QTextEdit, QComboBox { background: #fff; padding: 8px; border: 1px solid #d2d6dc; border-radius: 6px; }
QLineEdit:focus, QTextEdit:focus { border: 2px solid #2463b5; }
QListWidget { background: #f0f1f3; border: 0; padding: 8px; border-radius: 8px; }
QListWidget::item { padding: 14px 12px; margin-bottom: 4px; border-radius: 6px; }
QListWidget::item:selected { background: #dce7f6; color: #173f71; }
QTableWidget { background: white; border: 1px solid #dfe2e7; border-radius: 7px; gridline-color: #f0f1f3; }
QHeaderView::section { background: #f0f1f3; padding: 10px; border: 0; font-weight: 600; }
QTextEdit#activity { font-size: 12px; color: #60646b; }
QCheckBox { spacing: 8px; padding: 5px 0; }
QSplitter::handle { background: #e2e4e8; width: 1px; }
"""


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


def app_icon():
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2463b5"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 120, 120, 29, 29)
    painter.setPen(QColor("#ffffff"))
    font = QFont("Arial", 67, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "↓")
    painter.end()
    return QIcon(pixmap)


class SourceDialog(QDialog):
    def __init__(self, settings, existing=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.existing = existing
        self.process = None
        self.event_file = data_dir() / ("probe-" + str(uuid4()) + ".jsonl")
        self.source = None
        self.setWindowTitle(t("Edit ILIAS source" if existing else "Add an ILIAS source"))
        self.resize(620, 740)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        pane = QWidget()
        form = QFormLayout(pane)
        form.setSpacing(12)
        self.name = QLineEdit(existing.name if existing else "")
        self.name.setPlaceholderText(t("University / campus"))
        self.url = QLineEdit(existing.url if existing else "")
        self.url.setPlaceholderText(t("https://ilias.example.edu"))
        self.client = QLineEdit(existing.client_id if existing else "")
        self.client.setPlaceholderText(t("Detected when checking the address"))
        self.detect = button("Check address", self.probe)
        self.mode = QComboBox()
        for text, value in [("Username & password", "local"), ("Shibboleth SSO", "shibboleth"),
                            ("Browser session (MFA)", "session")]:
            self.mode.addItem(t(text), value)
        if existing:
            self.mode.setCurrentIndex(self.mode.findData(existing.login))
        self.user = QLineEdit(existing.username if existing else "")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText(t("Leave blank to keep saved password" if existing else "Saved in the system credential vault"))
        self.idp = QLineEdit(existing.idp_host if existing else "")
        self.idp.setPlaceholderText(t("idp.example.edu"))
        self.session = QLineEdit()
        self.session.setReadOnly(True)
        session_row = QWidget()
        session_layout = QHBoxLayout(session_row)
        session_layout.setContentsMargins(0, 0, 0, 0)
        session_layout.addWidget(self.session)
        session_layout.addWidget(button("Choose cookies.txt…", self.choose_session))
        self.destination = QLineEdit(existing.destination if existing else "")
        destination_row = QWidget()
        destination_layout = QHBoxLayout(destination_row)
        destination_layout.setContentsMargins(0, 0, 0, 0)
        destination_layout.addWidget(self.destination)
        destination_layout.addWidget(button("Choose…", self.choose_folder))
        self.automatic = QCheckBox(t("All joined courses, including new ones"))
        self.automatic.setChecked(existing.automatic_courses if existing else True)
        self.targets = QTextEdit()
        self.targets.setMaximumHeight(90)
        self.targets.setPlaceholderText(t("One course or folder URL per line"))
        if existing:
            self.targets.setPlainText("\n".join(existing.targets))
        self.videos = QCheckBox(t("Download videos"))
        self.videos.setChecked(existing.videos if existing else False)
        for title, widget in [("Name", self.name), ("ILIAS address", self.url), ("", self.detect),
                              ("Sign-in", self.mode), ("Client ID", self.client), ("Username", self.user),
                              ("Password", self.password), ("Trusted SSO host", self.idp), ("Browser session", session_row),
                              ("Download folder", destination_row), ("Courses", self.automatic),
                              ("Course links", self.targets), ("", self.videos)]:
            form.addRow(t(title), widget)
        self.note = label("Import a cookies.txt export from your browser. When the session expires, import a new export.", "subtitle")
        form.addRow(self.note)
        self.videos.setToolTip(t("Uses more storage and data."))
        self.mode.currentIndexChanged.connect(lambda: self.fields_for_login(form, session_row))
        self.automatic.toggled.connect(lambda: self.fields_for_login(form, session_row))
        self.fields_for_login(form, session_row)
        scroll.setWidget(pane)
        outer.addWidget(scroll)
        self.error = label("")
        self.error.setStyleSheet("color: #a02e28")
        outer.addWidget(self.error)
        buttons = save_buttons()
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def fields_for_login(self, form, session_row):
        mode = self.mode.currentData()
        for widget, visible in [(self.client, mode == "local"), (self.user, mode != "session"),
                                (self.password, mode != "session"), (self.idp, mode == "shibboleth"),
                                (session_row, mode == "session"), (self.targets, not self.automatic.isChecked())]:
            form.setRowVisible(widget, visible)
        self.note.setVisible(mode == "session")

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
            self.error.setText(message(str(exc)))
            return
        self.error.clear()
        self.error.setStyleSheet("color: #a02e28")
        self.detect.setEnabled(False)
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
        self.process.errorOccurred.connect(lambda: self.detect.setEnabled(True))
        self.process.start()

    def probed(self):
        self.probe_timeout.stop()
        self.detect.setEnabled(True)
        output = self.event_file.read_text(encoding="utf-8") if self.event_file.exists() else ""
        self.event_file.unlink(missing_ok=True)
        for line in output.splitlines():
            try:
                event = json.loads(line)
                if event["event"] == "result":
                    self.client.setText(event["result"]["client_id"])
                    if not self.name.text():
                        self.name.setText(event["result"]["title"][:70])
                    self.error.setStyleSheet("color: #175841" if self.client.text() else "color: #a02e28")
                    self.error.setText(t("Address checked" if self.client.text() else "Enter the client ID or use a browser session."))
                elif event["event"] == "error":
                    self.error.setText(message(event["message"]))
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
                            videos=self.videos.isChecked(), **kwargs)
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
            self.error.setText(message(str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "The credential vault or folder is unavailable."))


class CoursesDialog(QDialog):
    def __init__(self, courses, source, settings, parent):
        super().__init__(parent)
        self.setWindowTitle(t("Choose courses"))
        self.resize(620, 440)
        layout = QVBoxLayout(self)
        auto = QCheckBox(t("All joined courses, including new ones"))
        auto.setChecked(source.automatic_courses)
        layout.addWidget(auto)
        listing = QListWidget()
        for course in courses:
            item = QListWidgetItem(course["name"])
            item.setData(Qt.ItemDataRole.UserRole, course["url"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if source.automatic_courses or course["url"] in source.targets else Qt.CheckState.Unchecked)
            listing.addItem(item)
        listing.setEnabled(not auto.isChecked())
        auto.toggled.connect(lambda checked: listing.setEnabled(not checked))
        layout.addWidget(listing)
        buttons = save_buttons()
        layout.addWidget(buttons)

        def save():
            source.automatic_courses = auto.isChecked()
            source.targets = [listing.item(i).data(Qt.ItemDataRole.UserRole) for i in range(listing.count())
                              if listing.item(i).checkState() == Qt.CheckState.Checked]
            try:
                settings.save_source(source)
                self.accept()
            except ValueError as exc:
                QMessageBox.warning(self, t("Select courses"), message(str(exc)))
        buttons.accepted.connect(save)
        buttons.rejected.connect(self.reject)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        set_language(self.settings.value.get("language", "de"))
        self.process = None
        self.buffer = ""
        self.job = None
        self.event_path = data_dir() / ("job-" + str(uuid4()) + ".jsonl")
        self.event_offset = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.read_output)
        self.setWindowTitle(t("IliasSync"))
        self.resize(1080, 740)
        self.setMinimumSize(760, 540)
        container = QWidget()
        page = QVBoxLayout(container)
        page.setContentsMargins(26, 26, 26, 20)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("IliasSync", "title"))
        self.schedule_label = label(self.schedule_text(), "subtitle")
        titles.addWidget(self.schedule_label)
        header.addLayout(titles, 1)
        header.addWidget(button("Settings", self.background))
        page.addLayout(header)
        page.addSpacing(18)
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
        sidebar.addWidget(button("Add ILIAS", self.add, True))
        split.addWidget(left)
        right = QWidget()
        content = QVBoxLayout(right)
        content.setContentsMargins(16, 0, 0, 0)
        content.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.setSpacing(10)
        self.source_title = label("Connect ILIAS", "title")
        content.addWidget(self.source_title)
        self.destination = label("Add your university to download course files.", "subtitle")
        self.destination.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content.addWidget(self.destination)
        self.onboard_button = button("Add ILIAS", self.add, True)
        content.addWidget(self.onboard_button, alignment=Qt.AlignmentFlag.AlignLeft)
        actions = QHBoxLayout()
        self.sync_button = button("Sync now", lambda: self.start("sync"), True)
        self.courses_button = button("Choose courses", lambda: self.start("discover"))
        self.edit_button = button("Edit source", self.edit)
        self.open_button = button("Open folder", self.open_folder)
        for item in (self.sync_button, self.courses_button, self.edit_button, self.open_button):
            actions.addWidget(item)
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
        split.setSizes([235, 790])
        page.addWidget(split, 1)
        self.setCentralWidget(container)
        about = QAction(t("About IliasSync"), self)
        about.triggered.connect(self.about)
        self.menuBar().addAction(about)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.timeout.connect(self.timeout_job)
        self.populate()

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
        busy = self.process is not None
        self.sidebar.setVisible(bool(self.settings.sources()))
        self.onboard_button.setVisible(source is None)
        self.empty_spacer.setVisible(source is None)
        self.schedule_label.setVisible(source is not None)
        for item in (self.sync_button, self.edit_button, self.courses_button, self.open_button):
            item.setEnabled(source is not None and not busy)
        for widget in (self.actions_widget, self.status, self.files, self.details_button):
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
            self.files.setItem(row, 0, QTableWidgetItem(entry["path"]))
            self.files.setItem(row, 1, QTableWidgetItem(f"{entry.get('target_stat', [0])[0] / 1024:.0f} KB"))

    def add(self):
        if self.process:
            return
        dialog = SourceDialog(self.settings, parent=self)
        if dialog.exec():
            self.populate(dialog.source.id)

    def edit(self):
        dialog = SourceDialog(self.settings, self.selected(), self)
        if dialog.exec():
            self.populate(dialog.source.id)

    def start(self, action):
        source = self.selected()
        if not source or self.process:
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

    def refresh_controls(self):
        self.sources.setEnabled(self.process is None)
        for item in (self.sync_button, self.edit_button, self.courses_button):
            item.setEnabled(self.process is None and self.selected() is not None)

    def read_output(self):
        if self.process is None:
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
            if event["event"] == "progress":
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
            self.process.kill()
            self.activity.append(t("The job exceeded its time limit and was stopped. It can be retried safely."))

    def open_folder(self):
        source = self.selected()
        if source:
            QDesktopServices.openUrl(QUrl.fromLocalFile(source.destination))

    def background(self):
        if self.process:
            QMessageBox.information(self, t("Sync is running"), t("Let the current sync finish before changing settings."))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(t("Settings"))
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        language = QComboBox()
        language.addItem("Deutsch", "de")
        language.addItem("English", "en")
        language.setCurrentIndex(language.findData(self.settings.value.get("language", "de")))
        form.addRow(t("Language"), language)
        layout.addLayout(form)
        enabled = QCheckBox(t("Automatic sync"))
        enabled.setChecked(self.settings.value["scheduled"])
        hours = QComboBox()
        for n in (1, 3, 6, 12, 24):
            hours.addItem(t("Every hour") if n == 1 else t("Every {n} hours", n=n), n)
        hours.setCurrentIndex(hours.findData(self.settings.value["interval_hours"]))
        battery = QCheckBox(t("Pause on battery power"))
        battery.setChecked(self.settings.value["battery_saver"])
        layout.addWidget(enabled)
        layout.addWidget(hours)
        layout.addWidget(battery)
        enabled.toggled.connect(hours.setEnabled)
        enabled.toggled.connect(battery.setEnabled)
        hours.setEnabled(enabled.isChecked())
        battery.setEnabled(enabled.isChecked())
        layout.addWidget(label("Runs while you are signed in and the computer is awake. Keep the app at its installed location.", "subtitle"))
        error = label("")
        layout.addWidget(error)
        buttons = save_buttons()
        layout.addWidget(buttons)

        def save():
            try:
                # Save policy before RunAtLoad can start a new process.
                previous = dict(self.settings.value)
                self.settings.value.update(interval_hours=hours.currentData(), battery_saver=battery.isChecked(), language=language.currentData())
                self.settings.save()
                try:
                    if enabled.isChecked() and (not previous["scheduled"] or hours.currentData() != previous["interval_hours"]):
                        install(hours.currentData())
                    elif not enabled.isChecked() and previous["scheduled"]:
                        uninstall()
                except Exception:
                    self.settings.value = previous
                    self.settings.save()
                    raise
                self.settings.value["scheduled"] = enabled.isChecked()
                self.settings.save()
                dialog.accept()
                self.schedule_label.setText(self.schedule_text())
                if previous.get("language", "de") != language.currentData():
                    replacement = MainWindow()
                    replacement.resize(self.size())
                    replacement.populate(self.selected().id if self.selected() else None)
                    QApplication.instance().main_window = replacement
                    replacement.show()
                    self.close()
            except Exception:
                error.setText(t("The OS scheduler could not be updated. On Linux, a systemd user session is required."))
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

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
    application = QApplication(sys.argv[:1])
    application.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    application.setApplicationName("IliasSync")
    application.setOrganizationName("IliasSync")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(app_icon())
    application.setStyleSheet(STYLE)
    window = MainWindow()
    application.main_window = window
    window.show()
    if args.render:
        QTimer.singleShot(200, lambda: (window.grab().save(args.render), application.quit()))
    return application.exec()
