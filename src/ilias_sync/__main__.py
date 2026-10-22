"""The headless worker exits after a run; importing it does not import Qt."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

from filelock import FileLock, Timeout

from . import __version__
from .policy import due, next_run, on_battery
from .security import LoginRequired
from .storage import Settings, data_dir, read_json, write_json


EVENT_FILE = None


def emit(event):
    line = json.dumps(event, ensure_ascii=False) + "\n"
    if EVENT_FILE:
        with Path(EVENT_FILE).open("a", encoding="utf-8") as f:
            f.write(line)
    if sys.stdout is not None:
        sys.stdout.write(line)
        sys.stdout.flush()


async def worker(args):
    from .engine import probe, synchronize
    if args.probe:
        emit({"event": "result", "result": await probe(args.probe)})
        return 0
    settings = Settings()
    lock = FileLock(data_dir() / "sync.lock", timeout=0)
    try:
        lock.acquire()
    except Timeout:
        emit({"event": "busy", "message": "Another synchronization is already running."})
        return 3
    errors = 0
    batch_started = time.time()
    try:
        for source in settings.sources():
            if not source.enabled or (args.profile and source.id != args.profile):
                continue
            path = data_dir() / "sources" / source.id / "status.json"
            previous = read_json(path, {})
            manual = bool(args.profile)
            if not manual and not due(previous):
                continue
            if args.sync and not manual and settings.value["battery_saver"] and on_battery():
                emit({"event": "power", "message": "Scheduled run deferred while on battery."})
                continue
            interval = settings.value["interval_hours"]
            started = time.time()
            write_json(path, {**previous, "state": "Checking courses", "started": started, "login_required": False})
            try:
                result = await synchronize(source, emit, discover=args.discover)
                if args.discover:
                    write_json(path, previous)
                    emit({"event": "result", "result": result})
                    continue
                partial = result["partial"] or result["warnings"] or result["errors"]
                failures = previous.get("failures", 0) + 1 if partial else 0
                status = {"state": "Completed with warnings" if partial else "Up to date", "finished": time.time(),
                          "next_run": next_run(interval, failures, clock=batch_started), "failures": failures,
                          "login_required": False, "result": result}
                write_json(path, status)
                emit({"event": "result", "profile": source.id, "result": status})
                errors += int(bool(partial))
            except Exception as exc:
                # Never print traceback, credential values, form data or server response bodies.
                from PFERD.auth import AuthError
                login = isinstance(exc, (LoginRequired, AuthError))
                failures = previous.get("failures", 0) + 1
                message = str(exc) if login else f"{type(exc).__name__}: sync could not complete. Existing files were retained."
                status = {"state": "Sign in again" if login else "Needs attention", "finished": time.time(),
                          "next_run": next_run(interval, failures), "failures": failures,
                          "login_required": login, "message": message}
                write_json(path, status)
                emit({"event": "error", "profile": source.id, "message": message})
                errors += 1
    finally:
        lock.release()
    return 1 if errors else 0


def self_test():
    import tempfile
    from pathlib import Path
    from .storage import Archive
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        raw = root / "file.pdf"
        raw.write_bytes(b"%PDF-1.4 self-test")
        archive = Archive(root / "state", root / "out")
        assert archive.publish("test:1", raw, "Course/File.pdf") == "added"
        assert archive.publish("test:1", raw, "Course/File.pdf") == "unchanged"
    from PySide6.QtCore import qVersion
    from PySide6.QtWidgets import QApplication
    # Exercise frozen Qt plugins and GUI imports without touching the user's profiles.
    previous_root = os.environ.get("ILIAS_SYNC_DATA_DIR")
    with tempfile.TemporaryDirectory() as gui_tmp:
        os.environ["ILIAS_SYNC_DATA_DIR"] = gui_tmp
        try:
            from .gui import MainWindow
            app = QApplication.instance() or QApplication([])
            window = MainWindow()
            window.show()
            app.processEvents()
            assert not window.progress_timer.isActive()
            assert window.sync_button.text() == "Jetzt synchronisieren"
            window.close()
        finally:
            if previous_root is None:
                os.environ.pop("ILIAS_SYNC_DATA_DIR", None)
            else:
                os.environ["ILIAS_SYNC_DATA_DIR"] = previous_root
    emit({"event": "self-test", "ok": True, "version": __version__, "qt": qVersion()})
    return 0


def main():
    global EVENT_FILE
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="IliasSync — quiet course-file synchronization")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--sync", action="store_true", help="Synchronize due sources, then exit (no GUI).")
    parser.add_argument("--discover", action="store_true", help="List joined courses for --profile.")
    parser.add_argument("--profile", help="Source UUID; a manual run bypasses the due-time and battery policy.")
    parser.add_argument("--probe", help="Detect the client ID at an HTTPS installation URL.")
    parser.add_argument("--self-test", action="store_true", help="Offline packaged-runtime smoke test.")
    parser.add_argument("--render", help=argparse.SUPPRESS)
    parser.add_argument("--event-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    EVENT_FILE = args.event_file
    if args.self_test:
        return self_test()
    if args.sync or args.discover or args.probe:
        try:
            return asyncio.run(worker(args))
        except Exception:
            emit({"event": "error", "message": "The job could not start. Check configuration and OS permissions."})
            return 1
    from .gui import run
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
