"""Hover brightness changes continuously, including when leaving mid-fade."""
import pytest

from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import QApplication, QWidget

from ilias_sync.motion import FadeButton
from ilias_sync.theme import Theme


@pytest.mark.parametrize('mode', ['dark', 'light'])
@pytest.mark.parametrize('name', ['secondary', 'sidebarAction', 'syncAction', 'syncRecovery',
                                  'commit', 'primary', 'pauseControl', 'stopControl', 'weekRemove'])
def test_button_wash_fades_and_reverses_without_a_style_flash(mode, name):
    app = QApplication.instance() or QApplication([])
    app.theme = Theme(app, mode)
    host = QWidget()
    host.setAutoFillBackground(True)
    button = FadeButton('', host)
    button.setObjectName(name)
    button.setGeometry(20, 20, 160, 40)
    host.resize(220, 80)
    host.show()
    app.processEvents()

    def sample():
        return host.grab().toImage().pixelColor(100, 40).lightness()

    try:
        button._hover_animation.stop()
        button._set_hover(0)
        idle = sample()
        QApplication.sendEvent(button, QEnterEvent(QPointF(80, 20), QPointF(100, 40), QPointF(100, 40)))
        motion = button._hover_animation
        motion.setCurrentTime(0)
        assert sample() == idle
        motion.setCurrentTime(motion.duration() // 2)
        half = sample()
        motion.setCurrentTime(motion.duration())
        full = sample()
        assert min(idle, full) < half < max(idle, full), (idle, half, full)
        QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
        assert sample() == full
        motion.setCurrentTime(motion.duration() // 2)
        midway = button._hover
        QApplication.sendEvent(button, QEnterEvent(QPointF(), QPointF(), QPointF()))
        assert button._hover == midway
        motion.setCurrentTime(motion.duration())
        assert sample() == full
        button.setEnabled(False)
        disabled = sample()
        motion.setCurrentTime(0)
        assert sample() == disabled
    finally:
        host.close()
