"""Reproducible Qt screenshots using synthetic courses only. No account access."""
import os
import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='Capture real macOS compositor output.')
    parser.add_argument('--preview', action='store_true', help='Keep the isolated sample app open for review.')
    parser.add_argument('--language', choices=('en', 'de'), default='en')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/images')
    args = parser.parse_args()
    if args.preview and not args.native:
        parser.error('--preview requires --native')
    if args.native:
        if sys.platform != 'darwin':
            parser.error('--native requires macOS')
        os.environ['QT_QPA_PLATFORM'] = 'cocoa'
        os.environ.pop('QT_SCALE_FACTOR', None)
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
    from PySide6.QtGui import QFontDatabase
    from ilias_sync.branding import app_icon
    from ilias_sync.gui import MainWindow, FolderMappingDialog, SourceDialog, HelpDialog, SettingsDialog
    from ilias_sync.storage import Settings, Source, data_dir, write_json, source_scope
    from ilias_sync.theme import Theme
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ilias-product-") as temporary:
        os.environ["ILIAS_SYNC_DATA_DIR"] = str(Path(temporary) / "state")
        settings = Settings()
        settings.value.update(language=args.language, appearance='dark', scheduled=True, schedule_mode='weekly',
                              weekly_times={"0":["09:00","16:30"],"1":["13:00"],"2":["09:00","16:30"],
                                            "3":["13:00"],"4":["10:00"],"5":[],"6":[]})
        source = Source("Example University", "https://ilias.example.edu", str(Path(temporary) / 'Materials'),
                        username="beispiel", client_id="campus")
        settings.save_source(source)
        state = data_dir() / "sources" / source.id
        names_by_language = (['Programming and Software Engineering', 'Computer Architecture', 'Discrete Mathematics']
                             if args.language == 'en' else ['Programmierung und Softwareentwicklung',
                             'Technische Grundlagen der Informatik', 'Logik und diskrete Strukturen'])
        courses = [{"id": f"crs-{index}", "name": name, "url": source.url + f"/go/crs/{index}"}
                   for index, name in enumerate(names_by_language, 1)]
        write_json(state / "courses.json", courses)
        names = [("Programming/Lectures/01 Introduction.pdf", "crs-1/Lectures/01 Introduction.pdf", "crs-1", 3440000),
                 ("Programming/Lectures/02 Data Representation.pdf", "crs-1/Lectures/02 Data Representation.pdf", "crs-1", 8520000),
                 ("Programming/Exercises/Exercise Sheet 01.pdf", "crs-1/Exercises/Exercise Sheet 01.pdf", "crs-1", 285000),
                 ("Architecture/Lectures/01 Number Systems.pdf", "crs-2/Lectures/01 Number Systems.pdf", "crs-2", 2160000),
                 ("Mathematics/Exercises/Exercise Sheet 01.pdf", "crs-3/Exercises/Exercise Sheet 01.pdf", "crs-3", 180000)]
        write_json(state / "manifest.json", {"schema": 1, "files": {
            f"file:{index}": {"path": path, "logical": logical, "course_id": course,
                              "target_stat": [size], "size": size, "changed_at": time.time() - index * 3600, "change": "added",
                              "course_name": next(c["name"] for c in courses if c["id"] == course)}
            for index, (path, logical, course, size) in enumerate(names)}})
        write_json(state / "status.json", {"state": "Up to date", "scope": source_scope(source), "finished": time.time(), "result": {
            "files": 5, "counts": {"added": 5}, "material_counts": {"added": 5}, "skipped": {}, "warnings": 0, "errors": 0, "unavailable": 0}})
        app = QApplication([])
        from ilias_sync.native_compat import protect_accessibility
        protect_accessibility(app)
        app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        app.setWindowIcon(app_icon())
        app.theme = Theme(app, "dark")
        backdrop = None
        if args.native and not args.preview:
            # Keep private desktop contents out of public compositor captures.
            backdrop = QWidget(None, Qt.WindowType.FramelessWindowHint)
            backdrop.setStyleSheet('background: qlineargradient(x1:0,y1:0,x2:1,y2:1,'
                                  'stop:0 #26373b, stop:0.5 #22272e, stop:1 #37303b);')
            backdrop.setGeometry(app.primaryScreen().availableGeometry().adjusted(2, 2, -2, -2))
            backdrop.show()
        window = MainWindow()
        window.resize(980, 700)
        available = app.primaryScreen().availableGeometry()
        window.move(available.center() - window.rect().center())
        window.show()
        if args.preview:
            app.setApplicationName('IliasSync Preview')
            def preview_sync(view, *_):
                QMessageBox.information(view, 'IliasSync Preview',
                    'Lokale Vorschau mit Beispieldaten. Es wird keine Synchronisierung gestartet.'
                    if args.language == 'de' else 'Local preview with sample data. No synchronization is started.')
            # Review the settings draft without touching the installed scheduler.
            with patch('ilias_sync.gui.install'), patch('ilias_sync.gui.uninstall'), \
                    patch('ilias_sync.gui.registration_matches', return_value=True), \
                    patch.object(MainWindow, 'start', preview_sync):
                window.raise_()
                window.activateWindow()
                print('Native sample preview opened. No installed app or user schedule is changed.', flush=True)
                app.exec()
            return

        def capture(widget, name):
            widget.show()
            if args.native:
                widget.move(app.primaryScreen().availableGeometry().center() - widget.rect().center())
            widget.raise_()
            widget.activateWindow()
            QTest.qWait(180)
            if args.native:
                point = widget.mapToGlobal(QPoint())
                region = f'{point.x()},{point.y()},{widget.width()},{widget.height()}'
                subprocess.run(['/usr/sbin/screencapture', '-x', '-R' + region, str(output / name)], check=True)
                return
            surface = widget.centralWidget() if isinstance(widget, MainWindow) else widget
            assert surface.grab().save(str(output / name))

        capture(window, "app-dark.png")
        app.theme.set_mode("light")
        capture(window, "app-light.png")
        app.theme.set_mode("dark")
        window.workspace_tabs.setCurrentIndex(1)
        capture(window, "materials.png")
        window.workspace_tabs.setCurrentIndex(0)
        settings.value.update(scheduled=True, schedule_mode="weekly", weekly_times={"0":["09:00","16:30"],"1":["13:00"],"2":["09:00","16:30"],"3":["13:00"],"4":["10:00"],"5":[],"6":[]})
        schedule = SettingsDialog(settings, window)
        schedule.tabs.setCurrentIndex(1)
        capture(schedule, "schedule.png")
        schedule.reject()
        app.theme.set_mode("light")
        mapping_source = replace(source, destination='/Study/Materials')
        mapping = FolderMappingDialog(mapping_source, settings)
        mapping.tree.expandAll()
        capture(mapping, "folders.png")
        mapping.close()
        setup = SourceDialog(settings, source)
        capture(setup, "setup.png")
        setup.close()
        preferences = HelpDialog()
        capture(preferences, "info.png")
        preferences.close()
        window.close()
        if backdrop:
            backdrop.close()
    print("Synthetic product screenshots written to", output)


if __name__ == "__main__":
    main()
