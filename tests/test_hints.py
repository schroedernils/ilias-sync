"""Hover help stays short, safe and separate from accessibility labels."""
from PySide6.QtWidgets import QApplication, QPushButton

from ilias_sync.hints import hint_text, set_hint


def test_names_and_explanations_are_not_interpreted_as_html():
    text = hint_text('Lecture <03> & notes', 'Keep <local> files.\nContinue later.')
    assert 'Lecture &lt;03&gt; &amp; notes' in text
    assert 'Keep &lt;local&gt; files.<br>Continue later.' in text
    assert 'width="280"' in text
    assert '<table' not in hint_text('Pause')


def test_help_does_not_replace_the_accessible_control_name():
    app = QApplication.instance() or QApplication([])
    control = QPushButton('')
    control.setAccessibleName('Pause synchronization')
    set_hint(control, 'Pause', 'Continue this run later.')
    assert control.accessibleName() == 'Pause synchronization'
    assert control.accessibleDescription() == 'Continue this run later.'
    assert control.toolTip().startswith('<qt>')
    assert app is not None


def test_hover_details_do_not_repeat_the_same_accessible_name():
    app = QApplication.instance() or QApplication([])
    control = QPushButton('18:36')
    detail = 'Last synchronization: Today at 18:36'
    control.setAccessibleName(detail)
    set_hint(control, 'Synchronization status', detail)
    assert control.accessibleName() == detail
    assert not control.accessibleDescription()
    assert detail in control.toolTip()
    assert app is not None
