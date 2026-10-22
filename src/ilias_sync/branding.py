"""One supplied identity, with native application and compact UI representations."""
from pathlib import Path
import sys

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import QLabel

ICONS = Path(__file__).resolve().parent / "assets" / "icons"


def app_icon():
    # Keep the OS identity independent of the in-app appearance preference.
    # In particular, don't replace macOS's Dock icon when a settings pane changes.
    if sys.platform == "darwin":
        return QIcon(str(ICONS / "macOS/IliasSync.icns"))
    icon = QIcon()
    for size in (16, 32, 64, 128, 256, 512, 1024):
        icon.addFile(str(ICONS / f"PNG/Default/IliasSync-Default-{size}.png"))
    return icon


class BrandMark(QLabel):
    """Small, non-interactive identity mark; adjacent text provides its name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_icon()

    def update_icon(self):
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        name = "IliasSync-Legacy-Dark.svg" if dark else "IliasSync-Legacy.svg"
        self.setPixmap(QIcon(str(ICONS / "SVG" / name)).pixmap(QSize(44, 44), self.devicePixelRatioF()))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self.update_icon()
