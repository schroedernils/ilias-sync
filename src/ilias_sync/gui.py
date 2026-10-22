"""A small Qt Widgets interface. Work happens in one disposable headless subprocess."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QFileSystemWatcher, QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget, QSizePolicy, QFrame, QStackedWidget,
)

from . import __version__
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
        self.resize(640, 650)
        self.setMinimumSize(560, 580)
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
        self.mode = QComboBox()
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
            self.show_error(str(exc) if isinstance(exc, (ValueError, RuntimeError)) else "The credential vault or folder is unavailable.")


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
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("dialogBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        self.language = QComboBox()
        self.language.addItem("Deutsch", "de")
        self.language.addItem("English", "en")
        self.language.setCurrentIndex(self.language.findData(settings.value.get("language", "de")))
        self.appearance = QComboBox()
        for title, value in [("Follow system", "system"), ("Light", "light"), ("Dark", "dark")]:
            self.appearance.addItem(t(title), value)
        self.appearance.setCurrentIndex(self.appearance.findData(settings.value.get("appearance", "system")))
        self.enabled = QCheckBox(t("Automatic sync"))
        self.enabled.setChecked(settings.value["scheduled"])
        self.hours = QComboBox()
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
        outer.addWidget(scroll, 1)
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
        self.sync_button = button("Sync now", self.sync_or_pause, True)
        self.stop_button = button("Stop", self.stop_sync)
        self.stop_button.hide()
        self.courses_button = button("Choose courses", lambda: self.start("discover"))
        self.edit_button = button("Edit source", self.edit)
        self.open_button = button("Open folder", self.open_folder)
        for item in (self.sync_button, self.stop_button, self.courses_button, self.edit_button, self.open_button):
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
        if self.process or self.run_info:
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
        self.sync_button.setText(t("Pause"))
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
        for item in (self.edit_button, self.courses_button):
            item.setEnabled(not busy and self.selected() is not None)
        self.sync_button.setEnabled(self.selected() is not None)
        self.sync_button.setText(t("Resume" if self.run_info and self.run_info["state"] == "paused" else "Pause" if busy else "Sync now"))
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
    application = QApplication(sys.argv[:1])
    application.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    application.setApplicationName("IliasSync")
    application.setOrganizationName("IliasSync")
    application.setApplicationVersion(__version__)
    application.setWindowIcon(app_icon())
    application.theme = Theme(application, Settings().value.get("appearance", "system"))
    window = MainWindow()
    application.main_window = window
    window.show()
    if args.render:
        QTimer.singleShot(200, lambda: (window.grab().save(args.render), application.quit()))
    return application.exec()
