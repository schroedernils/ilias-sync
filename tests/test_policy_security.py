import time
from types import SimpleNamespace

import pytest

from ilias_sync.policy import due, next_run, on_battery
from ilias_sync.security import LoginRequired, import_session, vault
from ilias_sync.storage import Settings, server_url


@pytest.mark.parametrize("url", ["http://example.edu", "https://user:secret@example.edu", "file:///tmp/a", "https://example.edu/?token=secret", "javascript:alert(1)"])
def test_reject_unsafe_server(url):
    with pytest.raises(ValueError):
        server_url(url)


def test_profiles_have_no_password_and_no_overlapping_destinations(source, tmp_path):
    settings = Settings()
    settings.save_source(source)
    assert all("password" not in s for s in settings.value["sources"])
    from dataclasses import replace
    from uuid import uuid4
    other = replace(source, id=str(uuid4()), destination=str(tmp_path / "Downloads/nested"))
    with pytest.raises(ValueError):
        settings.save_source(other)
    assert len(Settings().sources()) == 1


def test_unknown_schema_refused():
    settings = Settings()
    settings.value["schema"] = 999
    settings.save()
    with pytest.raises(ValueError):
        Settings()


def test_backoff_and_login_block():
    assert next_run(6, 0, clock=0) == 21600
    assert next_run(6, 8, clock=0) == 48 * 3600
    assert not due({"login_required": True, "next_run": 0}, clock=1e12)
    assert due({"next_run": 1}, clock=2)


def test_battery_sensor(monkeypatch):
    monkeypatch.setattr("psutil.sensors_battery", lambda: SimpleNamespace(power_plugged=False))
    assert on_battery()
    monkeypatch.setattr("psutil.sensors_battery", lambda: None)
    assert not on_battery()


def test_plaintext_keyring_refused(monkeypatch):
    class Plaintext:
        pass
    monkeypatch.setattr("keyring.get_keyring", lambda: Plaintext())
    with pytest.raises(LoginRequired):
        vault()


def test_cookie_import_filters_unrelated_hosts(tmp_path):
    file = tmp_path / "cookies.txt"
    future = int(time.time()) + 3600
    file.write_text(f"# Netscape HTTP Cookie File\ncampus.example.edu\tFALSE\t/\tTRUE\t{future}\tsession\tvalid\n"
                    f"unrelated.example.org\tFALSE\t/\tTRUE\t{future}\tsecret\tmust-not-import\n")
    target = tmp_path / "state/.cookies"
    assert import_session(file, "https://campus.example.edu", target) == 1
    assert "valid" in target.read_text()
    assert "must-not-import" not in target.read_text()


def test_expired_cookie_import_refused(tmp_path):
    file = tmp_path / "cookies.txt"
    file.write_text("# Netscape HTTP Cookie File\ncampus.example.edu\tFALSE\t/\tTRUE\t1\tsession\told\n")
    with pytest.raises(ValueError):
        import_session(file, "https://campus.example.edu", tmp_path / ".cookies")
