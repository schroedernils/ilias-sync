"""Hidden Cocoa state regression; never sends input or shows an OS window."""
import os
from pathlib import Path
import tempfile

os.environ['QT_QPA_PLATFORM'] = 'cocoa'

with tempfile.TemporaryDirectory(prefix='ilias-sidebar-state-') as temporary:
    root = Path(temporary)
    os.environ['ILIAS_SYNC_DATA_DIR'] = str(root/'state')

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from ilias_sync.gui import MainWindow, SettingsDialog, SourceDialog
    from ilias_sync.native_compat import protect_accessibility
    from ilias_sync.native_compat import titlebar_controls_right
    from ilias_sync.storage import Settings, Source, data_dir, write_json
    from ilias_sync.theme import Theme

    app = QApplication([])
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    protect_accessibility(app)
    app.theme = Theme(app, 'dark')
    source = Source('Example', 'https://campus.example.edu', str(root/'Downloads'),
                    username='example', client_id='example')
    Settings().save_source(source)
    state = data_dir()/'sources'/source.id
    write_json(state/'courses.json', [{'id': 'crs-1', 'name': 'Example course'}])
    write_json(state/'manifest.json', {'files': {f'file:{i}': {
        'path': f'Example/Kapitel {i}.pdf', 'course_id': 'crs-1',
        'course_name': 'Example course', 'target_stat': [2048], 'changed_at': 1000+i,
    } for i in range(3)}})
    window = MainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    app.processEvents()
    hints = Qt.WindowType.ExpandedClientAreaHint | Qt.WindowType.NoTitleBarBackgroundHint
    assert window.windowFlags() & hints == hints
    toggle = window.sidebar_button
    assert toggle.parentWidget() is window
    assert titlebar_controls_right(int(window.winId())) < toggle.x()
    assert toggle.geometry().bottom() < window.windowHandle().safeAreaMargins().top()
    for sidebar_visible in (False, True):
        QTest.mouseClick(window.windowHandle(), Qt.MouseButton.LeftButton, pos=toggle.geometry().center())
        assert window.view_state['sidebar_hidden'] != sidebar_visible
        window.sidebar_animation.setCurrentTime(window.sidebar_animation.duration())
        app.processEvents()
        assert window.sidebar.isVisible() == sidebar_visible

    def check_titlebar(widget):
        image = widget.grab().toImage()
        scale = image.devicePixelRatio()
        inset = widget.windowHandle().safeAreaMargins().top()
        assert inset > 0 and widget.contentsRect().top() == inset
        x, edge = image.width() - round(12 * scale), round(inset * scale)
        title = image.pixelColor(x, edge - 1).alpha()
        content = image.pixelColor(x, edge).alpha()
        assert 70 < title <= content - 40 and 210 < content < 235, (title, content)

    preferences = SettingsDialog(Settings(), window)
    setup = SourceDialog(Settings(), source)
    for dialog in (preferences, setup):
        dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dialog.show()
    app.processEvents()

    checked = 0
    for appearance in ('dark', 'light', 'dark'):
        app.theme.set_mode(appearance)
        for dialog in (preferences, setup):
            check_titlebar(dialog)
        for size in ((820, 560), (980, 700), (1280, 800)):
            window.resize(*size)
            app.processEvents()
            check_titlebar(window)
            for tab in (0, 1, 2):
                window.workspace_tabs.setCurrentIndex(tab)
                for position in (200, 480, 272, 400):
                    window.split.moveSplitter(position, 1)
                    app.processEvents()
                    left, right = window.split.widget(0), window.split.widget(1)
                    assert left.x() == 0
                    assert right.x() == left.width() + window.split.handleWidth()
                    assert right.geometry().right() + 1 == window.split.width()
                    assert window.split.sizes() == [left.width(), right.width()]
                    if tab == 0:
                        table = window.recent_files
                        assert table.horizontalHeader().length() <= table.viewport().width(), (
                            table.horizontalHeader().length(), table.viewport().width())
                    chosen_width = left.width()
                    window.refresh()
                    app.processEvents()
                    assert left.width() == chosen_width
                    for control in (window.file_search, window.management_button, window.sync_cluster):
                        top_left = control.mapTo(window, control.rect().topLeft())
                        assert top_left.x() >= right.mapTo(window, right.rect().topLeft()).x()
                        assert top_left.x() + control.width() <= window.width()
                    checked += 1
    for widget in (setup, preferences, window):
        widget.close()
    print(f'{checked} hidden Cocoa pane transitions passed')
