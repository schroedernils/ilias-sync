"""One supplied identity, with native application and compact UI representations."""
from pathlib import Path
from functools import lru_cache
import sys

from PySide6.QtCore import QEvent, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel

ICONS = Path(__file__).resolve().parent / "assets" / "icons"


@lru_cache(maxsize=128)
def action_pixmap(name, color, size, ratio):
    svg = (ICONS / "actions" / (name + ".svg")).read_text().replace("currentColor", color)
    renderer = QSvgRenderer(svg.encode())
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def paint_action(painter, widget, name, color, size):
    painter.setOpacity(color.alphaF())
    pixmap = action_pixmap(name, color.name(), size, widget.devicePixelRatioF())
    painter.drawPixmap((widget.width() - size) // 2, (widget.height() - size) // 2, pixmap)


def app_icon():
    # Keep the OS identity independent of the in-app appearance preference.
    # In particular, don't replace macOS's Dock icon when a settings pane changes.
    if sys.platform == "darwin":
        return QIcon(str(ICONS / "macOS/IliasSync-Dark.icns"))
    icon = QIcon()
    for size in (16, 32, 64, 128, 256, 512, 1024):
        icon.addFile(str(ICONS / f"PNG/Dark/IliasSync-Dark-{size}.png"))
    return icon


class BrandMark(QLabel):
    """Small, non-interactive identity mark; adjacent text provides its name."""

    def __init__(self, parent=None, size=28):
        super().__init__(parent)
        self.mark_size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_icon()

    def update_icon(self):
        name = "IliasSync-Dark.iconset"
        # The supplied raster retains the alpha mask with every Qt SVG backend.
        path = ICONS / "macOS" / name / "icon_128x128.png"
        self.setPixmap(QIcon(str(path)).pixmap(QSize(self.mark_size, self.mark_size), self.devicePixelRatioF()))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            self.update_icon()
