import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setenv("ILIAS_SYNC_DATA_DIR", str(tmp_path / "app-data"))


@pytest.fixture
def source(tmp_path):
    from ilias_sync.storage import Source
    return Source("Example University", "https://campus.example.edu/ilias", str(tmp_path / "Downloads"),
                  username="test-user", client_id="test-client")
