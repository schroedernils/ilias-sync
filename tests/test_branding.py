from pathlib import Path
import importlib.util
import os
import struct
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_supplied_artwork_decodes_at_small_and_retina_sizes():
    from PySide6.QtWidgets import QApplication
    from ilias_sync.branding import BrandMark, app_icon
    app = QApplication.instance() or QApplication([])
    icon = app_icon()
    for size in (16, 32, 128, 512):
        assert not icon.pixmap(size, size).isNull()
    mark = BrandMark()
    assert not mark.pixmap().isNull()
    mark.close()
    app.processEvents()


def test_windows_ico_preserves_original_png_entries(tmp_path):
    spec = importlib.util.spec_from_file_location("icon_assets", ROOT / "scripts/icon_assets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    icons = ROOT / "src/ilias_sync/assets/icons"
    data = module.windows_icon(icons, tmp_path / "IliasSync.ico").read_bytes()
    assert struct.unpack_from("<HHH", data) == (0, 1, 5)
    for index, size in enumerate((16, 32, 64, 128, 256)):
        width, height, _, _, _, depth, length, offset = struct.unpack_from("<BBBBHHII", data, 6 + index * 16)
        assert width == height == size % 256
        assert depth == 32
        assert data[offset:offset + length] == (icons / f"PNG/Dark/IliasSync-Dark-{size}.png").read_bytes()


def test_linux_launcher_only_writes_to_selected_user_data(tmp_path):
    import shutil
    import sys
    if sys.platform == "win32":
        import pytest
        pytest.skip("POSIX launcher")
    app_dir = tmp_path / 'App space % " unicode ü'
    app_dir.mkdir()
    installer = app_dir / "install-desktop.sh"
    shutil.copy2(ROOT / "scripts/install-desktop.sh", installer)
    data = tmp_path / "xdg"
    subprocess.run(["sh", str(installer)], env={**os.environ, "XDG_DATA_HOME": str(data)}, check=True)
    entry = (data / "applications/org.iliassync.desktop.desktop").read_text()
    assert '%%' in entry
    assert '\\"' in entry
    assert f"Icon={app_dir}/IliasSync.png" in entry


def test_info_tab_is_local_and_translated():
    from ilias_sync.info import info_html
    from ilias_sync.i18n import set_language
    set_language("de")
    assert "Nutzung" in info_html()
    assert "<script" not in info_html()
    set_language("en")
    assert "Compatibility" in info_html()
    set_language("de")
