"""Build platform icon containers from the original IliasSync artwork."""
from pathlib import Path
import struct
import subprocess
import tempfile


def macos_icon(icons: Path, output: Path):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter

    # Our original tile occupies 928 of 1024 pixels. Apple's classic system
    # tiles occupy 824. Preserve the original color and aspect ratio.
    scale = 824 / 928
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        iconset = Path(directory) / 'IliasSync.iconset'
        iconset.mkdir()
        for path in sorted((icons / 'macOS/IliasSync-Dark.iconset').glob('icon_*.png')):
            original = QImage(str(path))
            if original.isNull() or original.width() != original.height():
                raise ValueError(f'Invalid icon image: {path.name}')
            size = original.width()
            inset = (1 - scale) * size / 2
            canvas = QImage(original.size(), QImage.Format.Format_ARGB32_Premultiplied)
            canvas.fill(Qt.GlobalColor.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(QRectF(inset, inset, size * scale, size * scale), original)
            painter.end()
            if not canvas.save(str(iconset / path.name)):
                raise OSError(f'Could not write {path.name}')
        subprocess.run(['iconutil', '-c', 'icns', str(iconset), '-o', str(output)], check=True)
    return output


def windows_icon(icons: Path, output: Path):
    entries = [(n, (icons / f"PNG/Dark/IliasSync-Dark-{n}.png").read_bytes())
               for n in (16, 32, 64, 128, 256)]
    offset = 6 + 16 * len(entries)
    directory = []
    for size, data in entries:
        directory.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(struct.pack("<HHH", 0, 1, len(entries)) + b"".join(directory)
                       + b"".join(data for _, data in entries))
    return output
