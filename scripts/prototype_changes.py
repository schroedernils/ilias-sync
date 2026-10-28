"""Run an isolated, synthetic issue-2 comparison. No account or production state."""
import hashlib
from pathlib import Path
import tempfile
import sys
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QVBoxLayout, QHeaderView

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.review_state import ReviewState, local_read_check  # noqa: E402
from ilias_sync.native_compat import protect_accessibility
from ilias_sync.theme import Theme
from ilias_sync.library_widgets import MaterialTable


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--render', type=Path)
    args = parser.parse_args()
    app = QApplication([])
    protect_accessibility(app)
    app.theme = Theme(app, 'system')
    with tempfile.TemporaryDirectory(prefix='ilias-changes-prototype-') as temporary:
        root = Path(temporary).resolve()
        ledger = ReviewState(root/'review.sqlite')
        def entry(name, data, *, course='Algorithmen', generated=False):
            return {'path':name, 'digest':hashlib.sha256(data).hexdigest(), 'course':course, 'generated':generated}
        (root/'Skript.pdf').write_bytes(b'%PDF-1.4 synthetic fixture')
        (root/'Material.url').write_text('[InternetShortcut]\nURL=https://example.edu\n')
        ledger.baseline({'file:1':entry('Skript.pdf',b'baseline')})
        ledger.observe('file:1',entry('Skript.pdf',b'new revision'))
        ledger.observe('file:2',entry('Material.url',b'link',course='Logik'))
        dialog = QDialog()
        dialog.setWindowTitle('IliasSync – isolierte Änderungsvorschau')
        dialog.resize(860,560)
        layout = QVBoxLayout(dialog)
        title = QLabel('Änderungen im Blick')
        title.setObjectName('title')
        layout.addWidget(title)
        layout.addWidget(QLabel('Synthetische Vorschau. Keine echten Kurse, Dateien oder Kontoeinstellungen werden verwendet.'))
        views = QComboBox()
        views.addItems(['Seit deinem Überblick','In den letzten 7 Tagen','Alle Materialien'])
        search = QLineEdit()
        search.setPlaceholderText('Datei oder Kurs suchen')
        search.setAccessibleName('Datei oder Kurs suchen')
        search.setClearButtonEnabled(True)
        find = QHBoxLayout()
        find.addWidget(views)
        find.addWidget(search,1)
        layout.addLayout(find)
        table = MaterialTable()
        table.setHorizontalHeaderLabels(['Datei','Kurs','Änderung'])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setTabKeyNavigation(False)
        table.verticalHeader().hide()
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setDefaultSectionSize(42)
        layout.addWidget(table,1)
        result = QLabel()
        result.setWordWrap(True)
        layout.addWidget(result)
        controls = [QHBoxLayout(), QHBoxLayout()]
        for row in controls:
            layout.addLayout(row)
        def refresh(*args):
            dialog.captured_boundary = ledger.boundary()
            rows = ledger.items(since_review=views.currentIndex()==0,
                                since_time=time.time()-7*86400 if views.currentIndex()==1 else None)
            query = search.text().casefold()
            rows = [row for row in rows if query in (row['path']+' '+row['course']).casefold()]
            table.setRowCount(len(rows))
            table.set_empty('Keine offenen Änderungen' if not rows else '', 'Neue Änderungen bleiben bis zu deinem Überblick sichtbar.')
            for row, item in enumerate(rows):
                for column, value in enumerate([item['path'],item['course'],{'added':'Neu entdeckt','updated':'Aktualisiert'}.get(item['change'],'Ausgangsbestand')]):
                    cell = QTableWidgetItem(value)
                    cell.setData(Qt.ItemDataRole.UserRole,item)
                    table.setItem(row,column,cell)
            table.resizeColumnsToContents()
            review_buttons[0].setEnabled(views.currentIndex()==0 and not query and bool(rows))
            review_buttons[1].setEnabled(ledger.reviewed()>0)
        def acknowledge():
            ledger.acknowledge(dialog.captured_boundary)
            refresh()
        def undo():
            ledger.undo()
            refresh()
        def simulate():
            ledger.observe('file:3',entry('Neues Blatt.pdf',str(time.time()).encode(),course='Logik'))
            refresh()
        def check():
            items = ledger.items()
            checks = [local_read_check(root/item['path'],local_root=root) for item in items]
            names = {'local_read_passed':'vollständig lokal lesbar','external_link':'Link benötigt eine Verbindung',
                     'missing':'fehlt lokal'}
            result.setText('\n'.join(Path(row['path']).name+': '+names.get(row['state'],row['state']) for row in checks)
                           +'\nZeitpunkt und Auswahl gelten nur für diese Prüfung. Keine bestätigte Offline- oder Cloud-Verfügbarkeit.')
        review_buttons = []
        for index, (text, callback) in enumerate([('Bis hier überblickt',acknowledge),('Rückgängig',undo),('Änderung simulieren',simulate),('Lokale Dateien prüfen',check),('Schließen',dialog.accept)]):
            button = QPushButton(text)
            button.clicked.connect(callback)
            controls[0 if index<3 else 1].addWidget(button)
            review_buttons.append(button)
        views.currentIndexChanged.connect(refresh)
        search.textChanged.connect(refresh)
        failures = []
        if args.render:
            def render():
                records = []
                args.render.mkdir(parents=True,exist_ok=True)
                def capture(name):
                    app.processEvents()
                    assert dialog.grab().save(str(args.render/(name+'.png')))
                    records.append({'state':name,'rows':table.rowCount(),'reviewed':ledger.reviewed()})
                try:
                    capture('changes')
                    acknowledge()
                    capture('reviewed')
                    simulate()
                    capture('new-after-review')
                    undo()
                    capture('undo')
                    check()
                    capture('local-read-check')
                    views.setCurrentIndex(1)
                    capture('date-range')
                    assert not review_buttons[0].isEnabled()
                    (args.render/'scenarios.json').write_text(json.dumps(records,indent=2))
                except Exception as exc:
                    failures.append(str(exc))
                finally:
                    dialog.accept()
            QTimer.singleShot(0,render)
        refresh()
        dialog.exec()
        if failures:
            raise RuntimeError(failures[0])
        ledger.close()


if __name__ == '__main__':
    main()
