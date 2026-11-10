"""Regressions for resizable translucent panes and live appearance changes."""
import pytest


@pytest.fixture
def workspace(source):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase
    from ilias_sync.gui import MainWindow
    from ilias_sync.storage import Settings, data_dir, write_json
    from ilias_sync.theme import Theme
    app = QApplication.instance() or QApplication([])
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    app.theme = Theme(app, 'dark')
    Settings().save_source(source)
    state = data_dir() / 'sources' / source.id
    write_json(state / 'courses.json', [{'id': 'crs-1', 'name': 'Programmierung und Softwareentwicklung [Vorlesung]'}])
    write_json(state / 'manifest.json', {'files': {
        'file:1': {'path': 'Vorlesung/Kapitel 1.pdf', 'course_id': 'crs-1',
                   'course_name': 'Programmierung und Softwareentwicklung [Vorlesung]',
                   'target_stat': [2048], 'changed_at': 1000},
    }})
    window = MainWindow()
    window.show()
    app.processEvents()
    yield app, window
    window.close()


@pytest.mark.parametrize('size', [(820, 560), (980, 700), (1280, 800)])
def test_dragging_sidebar_keeps_content_inside_window(workspace, size):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    app, window = workspace
    window.resize(*size)
    app.processEvents()
    recent = window.recent_files
    assert recent.y() + recent.height() <= recent.parentWidget().height()
    for tab in [0, 1, 2, 0]:
        window.workspace_tabs.setCurrentIndex(tab)
        for delta in [150, -250, 350, -170]:
            handle = window.split.handle(1)
            origin = handle.rect().center()
            QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=origin)
            QTest.mouseMove(handle, origin + QPoint(delta, 0))
            QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=origin + QPoint(delta, 0))
            app.processEvents()
            assert window.size().width() == size[0]
            assert 200 <= window.sidebar.width() <= 480
            right = window.split.widget(1)
            assert right.width() >= 500
            assert right.x() == window.sidebar.geometry().right() + 1 + window.split.handleWidth()
            assert right.geometry().right() + 1 == window.split.width()
            assert window.split.sizes() == [window.sidebar.width(), right.width()]
            for control in [window.file_search, window.sync_button, window.management_button, window.workspace]:
                point = control.mapTo(window, control.rect().topLeft())
                assert 0 <= point.x() < window.width()
                assert point.x() + control.width() <= window.width()
    assert window.view_state['sidebar_width'] == window.sidebar.width()
    saved = window.sidebar.width()
    window.close()
    from ilias_sync.gui import MainWindow
    reopened = MainWindow()
    reopened.show()
    app.processEvents()
    assert reopened.sidebar.width() == saved
    reopened.close()


def test_light_rows_keep_soft_readable_colors_after_theme_switches(workspace):
    from ilias_sync.theme import LIGHT, is_dark
    app, window = workspace
    for mode in ['light', 'dark', 'light']:
        app.theme.set_mode(mode)
        app.processEvents()
        table = window.recent_files
        assert is_dark(table.palette()) == (mode == 'dark')
        if mode != 'light':
            continue
        table.selectRow(0)
        image = table.viewport().grab().toImage()
        # The selected chip must remain light with dark ink, including a transparent table Base.
        assert image.pixelColor(20, 5).lightness() > 170
        assert image.pixelColor(20, 5).name() == LIGHT['selection']
        # Secondary text should use the light palette, not washed-out dark-mode gray.
        colors = {image.pixelColor(x, y).name()
                  for y in range(24, 40) for x in range(46, min(image.width(), 250))}
        assert LIGHT['muted'] in colors


def test_popups_use_a_readable_surface_in_both_themes(workspace):
    from ilias_sync.theme import DARK, LIGHT, popup_color
    app, _ = workspace
    for mode, colors in [('dark', DARK), ('light', LIGHT)]:
        app.theme.set_mode(mode)
        app.processEvents()
        color = popup_color(app.palette())
        assert color.alphaF() >= 0.96
        assert color.name() == colors['elevated']


@pytest.mark.parametrize('state,exit_code', [
    ('Up to date', 0), ('Completed with warnings', 0), ('Needs attention', 1), ('Stopped', 0),
])
def test_sync_completion_keeps_chosen_sidebar_width(workspace, source, state, exit_code):
    from unittest.mock import Mock, patch
    from ilias_sync.storage import data_dir, source_scope, write_json
    app, window = workspace
    window.split.moveSplitter(420, 1)
    app.processEvents()
    assert window.sidebar.width() == 420
    window.job = ('sync', source)
    window.process = Mock()
    write_json(data_dir()/'sources'/source.id/'status.json', {
        'state': state, 'started': 100, 'finished': 101, 'scope': source_scope(source),
        'result': {'counts': {'unchanged': 1}, 'errors': int(bool(exit_code))},
    })
    with patch.object(window, 'read_output'):
        window.finished(exit_code, None)
    app.processEvents()
    assert window.sidebar.width() == 420
    assert window.view_state['sidebar_width'] == 420
    window.refresh()
    window.populate(source.id)
    app.processEvents()
    assert window.sidebar.width() == 420
    window.resize(820, 560)
    app.processEvents()
    assert window.sidebar.width() < 420
    window.resize(1280, 800)
    app.processEvents()
    assert window.sidebar.width() == 420
    window.toggle_sidebar()
    window.toggle_sidebar()
    app.processEvents()
    assert window.sidebar.width() == 420


def test_sidebar_animates_and_reverses_without_saving_intermediate_width(workspace):
    from PySide6.QtCore import QAbstractAnimation

    _, window = workspace
    window.split.moveSplitter(300, 1)
    window.toggle_sidebar()
    motion = window.sidebar_animation
    assert motion.state() == QAbstractAnimation.State.Running
    motion.setCurrentTime(motion.duration() // 2)
    width = window.sidebar.width()
    assert 1 < width < 300
    assert window.view_state['sidebar_width'] == 300
    window.toggle_sidebar()
    assert window.sidebar.width() == width
    motion.setCurrentTime(motion.duration())
    assert window.sidebar.width() == 300
    assert window.sidebar.minimumWidth() == 200
    assert window.split.handleWidth() == 10


def test_language_change_keeps_sidebar_width_in_replacement_window(workspace):
    from unittest.mock import patch
    app, window = workspace
    window.split.moveSplitter(420, 1)
    app.processEvents()

    def save_language():
        window.settings.value['language'] = 'en'
        return True

    with patch('ilias_sync.gui.SettingsDialog') as dialog:
        dialog.return_value.exec.side_effect = save_language
        window.background()
    app.processEvents()
    replacement = app.main_window
    try:
        assert replacement is not window
        assert replacement.sidebar.width() == 420
        assert replacement.view_state['sidebar_width'] == 420
    finally:
        replacement.close()
