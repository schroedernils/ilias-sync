"""Check tooltip eligibility through text metrics; no screenshots or visual tests."""
from PySide6.QtCore import Qt, QRect
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem, QTableWidget, QTableWidgetItem

from ilias_sync.hints import set_hint
from ilias_sync.library_widgets import ElidedLabel, MaterialDelegate


def test_labels_only_reveal_complete_names_when_clipped():
    app = QApplication.instance() or QApplication([])
    title = 'Programmierung und Softwareentwicklung [Vorlesung]'
    label = ElidedLabel(title)
    label.resize(800, 30)
    label.show()
    app.processEvents()
    assert not label.toolTip()
    label.resize(90, 30)
    app.processEvents()
    assert label.toolTip() and label.accessibleName() == title
    label.resize(800, 30)
    app.processEvents()
    assert not label.toolTip()
    label.close()


def test_important_explicit_help_survives_label_resizing():
    app = QApplication.instance() or QApplication([])
    label = ElidedLabel('Tomorrow')
    set_hint(label, 'Next sync', 'Tomorrow at 13:50, while your Mac is awake.')
    saved = label.toolTip()
    label.resize(800, 30)
    label.show()
    app.processEvents()
    assert label.toolTip() == saved
    label.resize(30, 30)
    app.processEvents()
    assert label.toolTip() == saved
    label.close()


def test_file_hint_only_appears_for_truncated_title_or_context():
    app = QApplication.instance() or QApplication([])
    table = QTableWidget(1, 1)
    table.library_scope = 'source'
    item = QTableWidgetItem('Lecture.pdf')
    item.setData(Qt.ItemDataRole.UserRole + 1,
                 {'path':'Course/Lecture.pdf', 'course_name':'Programmierung und Softwareentwicklung [Vorlesung]'})
    table.setItem(0, 0, item)
    delegate = MaterialDelegate(table)
    option = QStyleOptionViewItem()
    option.initFrom(table)
    option.widget = table
    option.rect = QRect(0, 0, 1000, 58)
    index = table.model().index(0, 0)
    assert not delegate.needs_hint(option, index)
    option.rect.setWidth(75)
    assert delegate.needs_hint(option, index)
    option.rect.setWidth(220)
    assert delegate.needs_hint(option, index)  # Context is clipped although the filename fits.
    table.close()
    assert app is not None
