"""A small Qt Widgets interface. Work happens in one disposable headless subprocess."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from . import __version__
from .scheduler import command, install, uninstall
from .security import import_session, store_password
from .storage import Settings, Source, data_dir, read_json

STYLE = """
QWidget { font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 13px; }
QMainWindow, QDialog { background: #f7f9f8; color: #182b26; }
QLabel#eyebrow { color: #527267; font-size: 11px; font-weight: 700; }
QLabel#title { font-size: 27px; font-weight: 650; }
QLabel#subtitle { color: #5c7069; font-size: 13px; }
QLabel#status { padding: 12px 16px; border-radius: 8px; background: #e5f0eb; color: #175841; }
QPushButton { background: #fff; border: 1px solid #cbd8d1; border-radius: 6px; padding: 9px 15px; }
QPushButton:hover { background: #edf4f0; border-color: #6b9985; }
QPushButton:pressed { background: #d8e9df; }
QPushButton:focus { border: 2px solid #167357; }
QPushButton:disabled { color: #8a9891; background: #f1f4f2; }
QPushButton#primary { background: #176a50; color: #fff; border-color: #176a50; font-weight: 600; }
QPushButton#primary:hover { background: #10563f; }
QPushButton#primary:disabled { background: #9eaea5; border-color: #9eaea5; }
QLineEdit, QTextEdit, QComboBox { background: #fff; padding: 8px; border: 1px solid #cbd8d1; border-radius: 5px; }
QLineEdit:focus, QTextEdit:focus { border: 2px solid #167357; }
QListWidget { background: #edf2ee; border: 0; padding: 8px; }
QListWidget::item { padding: 14px 12px; margin-bottom: 4px; border-radius: 6px; }
QListWidget::item:selected { background: #d7e7de; color: #153b2d; }
QTableWidget { background: white; border: 1px solid #dbe3de; border-radius: 7px; gridline-color: #edf2ee; }
QHeaderView::section { background: #edf2ee; padding: 10px; border: 0; font-weight: 600; text-align: left; }
QTextEdit#activity { font-family: 'SFMono-Regular', 'Consolas', monospace; font-size: 11px; color: #456054; }
QCheckBox { spacing: 8px; padding: 5px 0; }
QSplitter::handle { background: #dce5df; width: 1px; }
"""


def label(text, name=None):
    item = QLabel(text)
    item.setWordWrap(True)
    if name:
        item.setObjectName(name)
    return item


def button(text, callback, primary=False):
    item = QPushButton(text)
    item.clicked.connect(callback)
    if primary:
        item.setObjectName("primary")
    return item


def app_icon():
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#176a50"))
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
        self.setWindowTitle("Edit ILIAS source" if existing else "Add an ILIAS source")
        self.resize(620, 740)
        outer = QVBoxLayout(self)
        outer.addWidget(label("CONNECT YOUR CAMPUS", "eyebrow"))
        outer.addWidget(label("Your ILIAS, your files.", "title"))
        outer.addWidget(label("Use your university's HTTPS address. Downloads stay on your computer.", "subtitle"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        pane = QWidget()
        form = QFormLayout(pane)
        form.setSpacing(12)
        self.name = QLineEdit(existing.name if existing else "")
        self.name.setPlaceholderText("University / campus name")
        self.url = QLineEdit(existing.url if existing else "")
        self.url.setPlaceholderText("https://ilias.example.edu")
        self.client = QLineEdit(existing.client_id if existing else "")
        self.client.setPlaceholderText("Detected automatically when possible")
        self.detect = button("Detect installation", self.probe)
        self.mode = QComboBox()
        for text, value in [("University username & password", "local"), ("Shibboleth SSO (advanced)", "shibboleth"),
                            ("Browser session / MFA", "session")]:
            self.mode.addItem(text, value)
        if existing:
            self.mode.setCurrentIndex(self.mode.findData(existing.login))
        self.user = QLineEdit(existing.username if existing else "")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Leave blank to keep the saved password" if existing else "Stored only in your OS credential vault")
        self.idp = QLineEdit(existing.idp_host if existing else "")
        self.idp.setPlaceholderText("idp.example.edu — explicitly trusted SSO host")
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
        self.automatic = QCheckBox("Discover all joined courses and groups, including new ones")
        self.automatic.setChecked(existing.automatic_courses if existing else True)
        self.targets = QTextEdit()
        self.targets.setMaximumHeight(90)
        self.targets.setPlaceholderText("Optional direct course / folder URLs, one per line")
        if existing:
            self.targets.setPlainText("\n".join(existing.targets))
        self.videos = QCheckBox("Include supported video downloads (more storage and data)")
        self.videos.setChecked(existing.videos if existing else False)
        for title, widget in [("Source name", self.name), ("ILIAS address", self.url), ("", self.detect),
                              ("Sign-in method", self.mode), ("Client ID", self.client), ("Username", self.user),
                              ("Password", self.password), ("Trusted SSO host", self.idp), ("Session import", session_row),
                              ("Download folder", destination_row), ("Courses", self.automatic),
                              ("Specific links", self.targets), ("Media", self.videos)]:
            form.addRow(title, widget)
        self.note = label("Standard ILIAS login is supported. For MFA or custom SSO, import a Netscape cookies.txt "
                          "export from your own browser. Sessions expire and may need to be imported again.", "subtitle")
        form.addRow(self.note)
        scroll.setWidget(pane)
        outer.addWidget(scroll)
        self.error = label("")
        self.error.setStyleSheet("color: #a02e28")
        outer.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a dedicated download folder")
        if folder:
            self.destination.setText(folder)

    def choose_session(self):
        file, _ = QFileDialog.getOpenFileName(self, "Import your own browser session", filter="Netscape cookies (*.txt);;All files (*)")
        if file:
            self.session.setText(file)
            self.mode.setCurrentIndex(self.mode.findData("session"))

    def probe(self):
        from .storage import server_url
        try:
            url = server_url(self.url.text())
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        self.detect.setEnabled(False)
        self.process = QProcess(self)
        self.event_file.write_text("", encoding="utf-8")
        cmd = command("--probe", url, "--event-file", str(self.event_file))
        self.process.setProgram(cmd[0])
        self.process.setArguments(cmd[1:])
        self.process.finished.connect(self.probed)
        self.process.start()

    def probed(self):
        self.detect.setEnabled(True)
        output = self.event_file.read_text(encoding="utf-8") if self.event_file.exists() else ""
        for line in output.splitlines():
            try:
                event = json.loads(line)
                if event["event"] == "result":
                    self.client.setText(event["result"]["client_id"])
                    if not self.name.text():
                        self.name.setText(event["result"]["title"][:70])
                    self.error.setText("Installation detected." if self.client.text() else "Enter the client ID or use a browser session.")
                elif event["event"] == "error":
                    self.error.setText(event["message"])
            except (ValueError, KeyError):
                pass

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
            self.error.setText(str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "The credential vault or folder is unavailable.")


class CoursesDialog(QDialog):
    def __init__(self, courses, source, settings, parent):
        super().__init__(parent)
        self.setWindowTitle("Choose courses")
        self.resize(620, 440)
        layout = QVBoxLayout(self)
        layout.addWidget(label("Follow your semester.", "title"))
        auto = QCheckBox("Keep all joined courses in sync, including future courses")
        auto.setChecked(source.automatic_courses)
        layout.addWidget(auto)
        listing = QListWidget()
        for course in courses:
            item = QListWidgetItem(course["name"])
            item.setData(Qt.ItemDataRole.UserRole, course["url"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if source.automatic_courses or course["url"] in source.targets else Qt.CheckState.Unchecked)
            listing.addItem(item)
        layout.addWidget(listing)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        def save():
            source.automatic_courses = auto.isChecked()
            source.targets = [listing.item(i).data(Qt.ItemDataRole.UserRole) for i in range(listing.count())
                              if listing.item(i).checkState() == Qt.CheckState.Checked]
            try:
                settings.save_source(source)
                self.accept()
            except ValueError as exc:
                QMessageBox.warning(self, "Select courses", str(exc))
        buttons.accepted.connect(save)
        buttons.rejected.connect(self.reject)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.process = None
        self.buffer = ""
        self.job = None
        self.event_path = data_dir() / ("job-" + str(uuid4()) + ".jsonl")
        self.event_offset = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.read_output)
        self.setWindowTitle("IliasSync")
        self.resize(1080, 740)
        self.setMinimumSize(760, 540)
        container = QWidget()
        page = QVBoxLayout(container)
        page.setContentsMargins(26, 26, 26, 20)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("ILIAS SYNC", "eyebrow"))
        titles.addWidget(label("Your courses. On your computer.", "title"))
        titles.addWidget(label("Quiet downloads, readable folders, and earlier versions kept safe.", "subtitle"))
        header.addLayout(titles, 1)
        header.addWidget(button("Background sync…", self.background))
        page.addLayout(header)
        page.addSpacing(18)
        split = QSplitter()
        left = QWidget()
        sidebar = QVBoxLayout(left)
        sidebar.setContentsMargins(0, 0, 8, 0)
        sidebar.addWidget(label("SOURCES", "eyebrow"))
        self.sources = QListWidget()
        self.sources.setAccessibleName("ILIAS sources")
        self.sources.currentRowChanged.connect(self.refresh)
        sidebar.addWidget(self.sources, 1)
        sidebar.addWidget(button("+  Add ILIAS", self.add, True))
        split.addWidget(left)
        right = QWidget()
        content = QVBoxLayout(right)
        content.setContentsMargins(16, 0, 0, 0)
        self.source_title = label("A home for your course files.", "title")
        content.addWidget(self.source_title)
        self.destination = label("Add your university to get started. No account with us, no server in between.", "subtitle")
        self.destination.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content.addWidget(self.destination)
        actions = QHBoxLayout()
        self.sync_button = button("Sync now", lambda: self.start("sync"), True)
        self.courses_button = button("Choose courses", lambda: self.start("discover"))
        self.edit_button = button("Edit source", self.edit)
        self.open_button = button("Open folder", self.open_folder)
        for item in (self.sync_button, self.courses_button, self.edit_button, self.open_button):
            actions.addWidget(item)
        content.addLayout(actions)
        self.status = label("Ready when you are.", "status")
        self.status.setAccessibleName("Synchronization status")
        content.addWidget(self.status)
        self.files = QTableWidget(0, 2)
        self.files.setAccessibleName("Downloaded files")
        self.files.setHorizontalHeaderLabels(["LOCAL FILE", "SIZE"])
        self.files.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files.verticalHeader().hide()
        self.files.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        content.addWidget(self.files, 1)
        self.activity = QTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setObjectName("activity")
        self.activity.setAccessibleName("Activity for this session")
        self.activity.setMaximumHeight(110)
        self.activity.document().setMaximumBlockCount(150)
        self.activity.setPlaceholderText("Activity appears here during a sync. Closing this window leaves OS-scheduled runs enabled.")
        content.addWidget(self.activity)
        split.addWidget(right)
        split.setSizes([235, 790])
        page.addWidget(split, 1)
        footer = QHBoxLayout()
        footer.addWidget(label("Local first · No telemetry · No automatic deletions", "subtitle"), 1)
        footer.addWidget(label("Preview " + __version__, "subtitle"))
        page.addLayout(footer)
        self.setCentralWidget(container)
        about = QAction("About IliasSync", self)
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
        for item in (self.sync_button, self.edit_button, self.courses_button, self.open_button):
            item.setEnabled(source is not None and not busy)
        if not source:
            return
        self.source_title.setText(source.name)
        self.destination.setText(source.destination)
        state = data_dir() / "sources" / source.id
        status = read_json(state / "status.json", {})
        result = status.get("result", {})
        text = status.get("state", "Not synchronized yet")
        if result:
            text += f" · {result['files']} files · {result.get('unavailable', 0)} not released / unavailable"
        self.status.setText(status.get("message", text))
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
        self.process.errorOccurred.connect(lambda: self.status.setText("The worker could not start."))
        self.process.start()
        self.progress_timer.start()
        self.timeout.start((120 if action == "discover" else 5500) * 1000)
        self.status.setText("Checking your ILIAS…")
        self.refresh_controls()

    def refresh_controls(self):
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
                self.status.setText(event["message"])
                self.activity.append(event["message"])
            elif event["event"] in {"error", "busy"}:
                self.activity.append(event["message"])
                self.status.setText(event["message"])
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
            self.activity.append("Some items need attention. Existing files were kept.")
        self.refresh_controls()

    def timeout_job(self):
        if self.process:
            self.process.kill()
            self.activity.append("The job exceeded its time limit and was stopped. It can be retried safely.")

    def open_folder(self):
        source = self.selected()
        if source:
            QDesktopServices.openUrl(QUrl.fromLocalFile(source.destination))

    def background(self):
        if self.process:
            QMessageBox.information(self, "Sync is running", "Let the current job finish before changing its schedule.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Background synchronization")
        layout = QVBoxLayout(dialog)
        layout.addWidget(label("Work quietly. Then switch off.", "title"))
        layout.addWidget(label("Uses your operating system's scheduler. No polling process or browser stays running "
                               "between jobs. Your computer must be awake and signed in. Keep the app at its installed location.", "subtitle"))
        enabled = QCheckBox("Enable scheduled synchronization")
        enabled.setChecked(self.settings.value["scheduled"])
        hours = QComboBox()
        for n in (1, 3, 6, 12, 24):
            hours.addItem(f"Every {n} hour{'s' if n != 1 else ''}", n)
        hours.setCurrentIndex(hours.findData(self.settings.value["interval_hours"]))
        battery = QCheckBox("Defer scheduled downloads while on battery power")
        battery.setChecked(self.settings.value["battery_saver"])
        layout.addWidget(enabled)
        layout.addWidget(hours)
        layout.addWidget(battery)
        error = label("")
        layout.addWidget(error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        def save():
            try:
                # Save policy before RunAtLoad can start a new process.
                previous = dict(self.settings.value)
                self.settings.value.update(interval_hours=hours.currentData(), battery_saver=battery.isChecked())
                self.settings.save()
                try:
                    if enabled.isChecked():
                        install(hours.currentData())
                    elif previous["scheduled"]:
                        uninstall()
                except Exception:
                    self.settings.value = previous
                    self.settings.save()
                    raise
                self.settings.value["scheduled"] = enabled.isChecked()
                self.settings.save()
                dialog.accept()
            except Exception:
                error.setText("The OS scheduler could not be updated. On Linux, a systemd user session is required.")
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def about(self):
        QMessageBox.about(self, "About IliasSync", "IliasSync " + __version__ + "\nGPL-3.0-or-later · Powered by PFERD and Qt\n\n"
                          "Standard ILIAS files and supported media are synchronized. Tests, forums, SCORM and custom plugins "
                          "may not be downloadable. This preview has no vendor signing or automatic updater.\n\n"
                          "Source and license notices: github.com/schroedernils/ilias-sync")

    def closeEvent(self, event):
        if self.process:
            QMessageBox.information(self, "A download is running", "Let this job finish before closing the window. "
                                    "You can minimize it in the meantime.")
            event.ignore()
        else:
            self.event_path.unlink(missing_ok=True)
            event.accept()


def run(args):
    application = QApplication(sys.argv[:1])
    application.setApplicationName("IliasSync")
    application.setOrganizationName("IliasSync")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(app_icon())
    application.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    if args.render:
        QTimer.singleShot(200, lambda: (window.grab().save(args.render), application.quit()))
    return application.exec()
