"""Filter placement and scope checks without screenshots or visual tests."""
from PySide6.QtWidgets import QApplication

from ilias_sync.gui import MainWindow
from ilias_sync.storage import Settings


def test_filters_belong_to_materials_and_keep_their_values_between_tabs(source):
    app = QApplication.instance() or QApplication([])
    Settings().save_source(source)
    window = MainWindow()
    window.show()
    app.processEvents()
    try:
        window.filter_files()
        app.processEvents()
        panel = window.filter_panel
        materials = window.materials_page.layout()
        assert window.workspace_tabs.currentIndex() == 1
        assert panel.parentWidget() is window.materials_page
        assert materials.indexOf(window.library_widget) < materials.indexOf(panel)
        assert materials.indexOf(panel) + 1 == materials.indexOf(window.files)
        assert window.content_layout.indexOf(panel) == -1
        assert panel.isVisible()
        panel.size.setCurrentIndex(panel.size.findData('small'))
        for tab in [0, 2, 1]:
            window.workspace_tabs.setCurrentIndex(tab)
            app.processEvents()
            assert panel.isVisible() == (tab == 1)
            assert window.file_filters['size'] == 'small'
        window.filter_files()
        assert panel.isHidden()
        window.filter_files()
        assert panel.isVisible()
        assert window.filter_panel is panel
        assert window.file_filters['size'] == 'small'
    finally:
        window.close()
