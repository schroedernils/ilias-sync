"""Reproducible Qt screenshots using synthetic courses only. No account access."""
import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")


def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase
    from ilias_sync.branding import app_icon
    from ilias_sync.gui import MainWindow, FolderMappingDialog, SourceDialog, HelpDialog, SettingsDialog
    from ilias_sync.storage import Settings, Source, data_dir, write_json, source_scope
    from ilias_sync.theme import Theme
    output = Path(__file__).resolve().parents[1] / "docs/images"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ilias-product-") as temporary:
        os.environ["ILIAS_SYNC_DATA_DIR"] = str(Path(temporary) / "state")
        settings = Settings()
        source = Source("Beispiel-Universität", "https://ilias.example.edu", "/Studium/WS26-27",
                        username="beispiel", client_id="campus")
        settings.save_source(source)
        state = data_dir() / "sources" / source.id
        courses = [{"id": "crs-1", "name": "Programmierung und Softwareentwicklung", "url": source.url + "/go/crs/1"},
                   {"id": "crs-2", "name": "Technische Grundlagen der Informatik", "url": source.url + "/go/crs/2"},
                   {"id": "crs-3", "name": "Logik und diskrete Strukturen", "url": source.url + "/go/crs/3"}]
        write_json(state / "courses.json", courses)
        names = [("PSE/Skripte/01 Einführung.pdf", "crs-1/Material/01 Einführung.pdf", "crs-1", 3440000),
                 ("PSE/Skripte/02 Datenrepräsentation.pdf", "crs-1/Material/02 Datenrepräsentation.pdf", "crs-1", 8520000),
                 ("PSE/Übungen/Blatt 01.pdf", "crs-1/Übungen/Blatt 01.pdf", "crs-1", 285000),
                 ("TGI/Skripte/01 Zahlensysteme.pdf", "crs-2/Material/01 Zahlensysteme.pdf", "crs-2", 2160000),
                 ("LDS/Übungen/Blatt 01.pdf", "crs-3/Übungen/Blatt 01.pdf", "crs-3", 180000)]
        write_json(state / "manifest.json", {"schema": 1, "files": {
            f"file:{index}": {"path": path, "logical": logical, "course_id": course,
                              "target_stat": [size], "size": size, "changed_at": time.time() - index * 3600, "change": "added",
                              "course_name": next(c["name"] for c in courses if c["id"] == course)}
            for index, (path, logical, course, size) in enumerate(names)}})
        write_json(state / "status.json", {"state": "Up to date", "scope": source_scope(source), "finished": time.time(), "result": {
            "files": 5, "counts": {"added": 5}, "material_counts": {"added": 5}, "skipped": {}, "warnings": 0, "errors": 0, "unavailable": 0}})
        app = QApplication([])
        app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        app.setWindowIcon(app_icon())
        app.theme = Theme(app, "light")
        window = MainWindow()
        window.show()

        def capture(widget, name):
            widget.show()
            app.processEvents()
            surface = widget.centralWidget() if isinstance(widget, MainWindow) else widget
            assert surface.grab().save(str(output / name))

        capture(window, "app-light.png")
        app.theme.set_mode("dark")
        capture(window, "app-dark.png")
        window.workspace_tabs.setCurrentIndex(1)
        capture(window, "materials.png")
        window.workspace_tabs.setCurrentIndex(0)
        settings.value.update(scheduled=True, schedule_mode="weekly", weekly_times={"0":["09:00","16:30"],"1":["13:00"],"2":["09:00","16:30"],"3":["13:00"],"4":["10:00"],"5":[],"6":[]})
        schedule = SettingsDialog(settings)
        schedule.tabs.setCurrentIndex(1)
        capture(schedule, "schedule.png")
        schedule.reject()
        app.theme.set_mode("light")
        mapping = FolderMappingDialog(source, settings)
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
    print("Synthetic product screenshots written to", output)


if __name__ == "__main__":
    main()
