"""Help must stay readable, offline and consistent when navigating real topics."""
import pytest
from html import escape

from ilias_sync import i18n
from ilias_sync.info import info_html, info_links, info_sections, topic_html


@pytest.fixture(autouse=True)
def restore_language():
    previous = i18n.LANGUAGE
    yield
    i18n.set_language(previous)


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_help_formats_paragraphs_without_executing_or_dropping_text(app):
    from PySide6.QtGui import QTextDocument

    title = 'A <script> & B'
    body = 'Open <filename>.pdf & keep edits.\n\nNext: "Sync".\n\n'
    html = topic_html(title, body)
    assert '<script>' not in html and '&lt;filename&gt;.pdf' in html
    assert html.count('<p>') == 2
    document = QTextDocument()
    document.setHtml(html)
    assert document.toPlainText().splitlines() == [title, *body.strip().split('\n\n')]


@pytest.mark.parametrize('language', ['de', 'en'])
def test_each_help_topic_is_reachable_readable_and_exposed_to_accessibility(language, app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ilias_sync.gui import HelpDialog

    i18n.set_language(language)
    dialog = HelpDialog()
    dialog.resize(480, 370)
    dialog.show()
    app.processEvents()
    try:
        sections = info_sections()
        assert dialog.topics.count() == len(sections) + 1
        dialog.topics.setFocus()
        QTest.keyClick(dialog.topics, Qt.Key.Key_Down)
        assert dialog.topics.currentRow() == 1
        QTest.keyClick(dialog.topics, Qt.Key.Key_Home)
        assert dialog.topics.currentRow() == 0
        for index, (title, body) in enumerate(sections):
            dialog.topics.setCurrentRow(index)
            app.processEvents()
            displayed = dialog.info.toPlainText()
            assert displayed.startswith(title + '\n')
            for paragraph in body.split('\n\n'):
                assert paragraph in displayed
            assert dialog.info.document().blockCount() == 1 + len(body.split('\n\n'))
            assert dialog.info.accessibleDescription() == displayed
            assert dialog.info.isReadOnly()
            assert not dialog.info.document().isEmpty()
            assert dialog.topics.horizontalScrollBar().maximum() == 0
            dialog.info.moveCursor(dialog.info.textCursor().MoveOperation.End)
            dialog.info.ensureCursorVisible()
            assert dialog.info.viewport().rect().contains(dialog.info.cursorRect().center())
        dialog.topics.setCurrentRow(len(sections))
        app.processEvents()
        assert 'GitHub' in dialog.info.toPlainText()
        assert '404' in dialog.info.toPlainText()
    finally:
        dialog.close()


@pytest.mark.parametrize('language', ['de', 'en'])
def test_full_help_and_support_links_remain_available_in_both_languages(language):
    i18n.set_language(language)
    html = info_html()
    for title, _ in info_sections():
        assert '<h3>' + escape(title) + '</h3>' in html
    links = info_links()
    assert '/docs/INSTALLATION.md' in links
    assert '/docs/RECOVERY.md' in links
    assert '/issues/new/choose' in links
    assert ('Passwörter' if language == 'de' else 'passwords') in links
    assert ('GitHub-Zugriff' if language == 'de' else 'GitHub access') in links
