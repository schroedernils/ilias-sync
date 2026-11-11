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
from .control import RunControl
from .policy import due, next_scheduled_run, on_battery
from .security import LoginRequired
from .storage import Settings, data_dir, read_json, write_json, record_attempt, source_scope


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
            from .recovery import needs_signin
            if not manual and (needs_signin(previous) or
                               (not getattr(args, 'scheduled_time', False) and not due(previous))):
                continue
            if args.sync and not manual and settings.value["battery_saver"] and on_battery():
                write_json(path, {**previous, 'deferred': 'battery', 'deferred_at': time.time()})
                emit({"event": "power", "message": "Scheduled run deferred while on battery."})
                continue
            started = time.time()
            write_json(path, {**previous, "state": "Checking courses", "started": started, "login_required": False})
            control = RunControl(source, emit)
            try:
                result = await control.run(synchronize(source, control.report, discover=args.discover),
                                           deadline=90 if args.discover else 5400)
                if args.discover:
                    write_json(path, previous)
                    emit({"event": "result", "result": result})
                    continue
                incomplete = result["partial"] or result["warnings"] or result["errors"]
                partial = incomplete or result.get('unavailable', 0) or result.get('course_link_issues')
                failures = previous.get("failures", 0) + 1 if incomplete else 0
                status = {"state": "Completed with warnings" if partial else "Up to date", "finished": time.time(),
                          "next_run": next_scheduled_run(settings.value, failures, clock=batch_started), "failures": failures,
                          "login_required": False, "result": result}
                if result.get('course_link_issues'):
                    status['failure_kind'] = 'course_links'
                status['next_run'] = max(status['next_run'], result.get('http', {}).get('retry_at', 0))
                record_attempt(path.parent, {**status, 'started': started, 'scope': source_scope(source)}, previous)
                emit({"event": "result", "profile": source.id, "result": status})
                errors += int(bool(incomplete))
            except asyncio.CancelledError as exc:
                if not control.stopped:
                    raise
                if args.discover:
                    write_json(path, previous)
                else:
                    record_attempt(path.parent, {"state": "Stopped", 'started': started, "finished": time.time(),
                                      "next_run": next_scheduled_run(settings.value), "login_required": False, 'scope': source_scope(source),
                                      'evidence': getattr(exc, 'sync_evidence', {})}, previous)
                emit({"event": "stopped", "profile": source.id})
                break
            except Exception as exc:
                if args.discover:
                    write_json(path, previous)
                    emit({'event': 'error', 'profile': source.id, 'message': 'Course list could not be loaded. Check your connection or sign-in and try again.'})
                    errors += 1
                    continue
                # Never print traceback, credential values, form data or server response bodies.
                from PFERD.auth import AuthError
                login = isinstance(exc, (LoginRequired, AuthError))
                failures = previous.get("failures", 0) + 1
                from .storage import FolderCollisionError
                collision = isinstance(exc, FolderCollisionError)
                from .http_policy import HostDeferred
                server_deferred = isinstance(exc, HostDeferred)
                if server_deferred:
                    failures = previous.get('failures', 0)
                message = str(exc) if login or collision or isinstance(exc, HostDeferred) else f"{type(exc).__name__}: sync could not complete. Existing files were retained."
                status = {"state": "Sign in again" if login else "Needs attention", "finished": time.time(),
                          "next_run": next_scheduled_run(settings.value, failures), "failures": failures,
                          "login_required": login, "message": message}
                status['evidence'] = getattr(exc, 'sync_evidence', {})
                # Only persist causes established by exception type/errno.
                # Unknown failures retain their existing generic recovery.
                from .recovery import failure_kind
                if known_kind := failure_kind(exc):
                    status['failure_kind'] = known_kind
                if server_deferred:
                    status['server_deferred'] = True
                    status['server_retry_at'] = exc.retry_at
                status['next_run'] = max(status['next_run'], status['evidence'].get('http', {}).get('retry_at', 0),
                                         getattr(exc, 'retry_at', 0))
                if collision:
                    status['recovery'] = 'folders'
                record_attempt(path.parent, {**status, 'started': started, 'scope': source_scope(source)}, previous)
                emit({"event": "error", "profile": source.id, "message": message,
                      'status': {key: status[key] for key in ('state', 'login_required', 'failure_kind', 'recovery',
                                                             'server_deferred', 'server_retry_at') if key in status}})
                errors += 1
    finally:
        lock.release()
    return 1 if errors else 0


def self_test():
    import tempfile
    previous_root = os.environ.get("ILIAS_SYNC_DATA_DIR")
    with tempfile.TemporaryDirectory() as isolated_root:
        os.environ["ILIAS_SYNC_DATA_DIR"] = isolated_root
        try:
            return _isolated_self_test()
        finally:
            if previous_root is None:
                os.environ.pop("ILIAS_SYNC_DATA_DIR", None)
            else:
                os.environ["ILIAS_SYNC_DATA_DIR"] = previous_root


def _isolated_self_test():
    import tempfile
    from pathlib import Path
    from .storage import Archive, Source
    from .engine import make_crawler
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        raw = root / "file.pdf"
        raw.write_bytes(b"%PDF-1.4 self-test")
        archive = Archive(root / "state", root / "out")
        assert archive.publish("test:1", raw, "Course/File.pdf") == "added"
        assert archive.publish("test:1", raw, "Course/File.pdf") == "unchanged"
        crawler = make_crawler(Source("Test", "https://ilias.example.edu", str(root / "downloads"), client_id="test"))
        from .page_index import PageData
        sample = PageData(b'<div class="il-maincontrols-metabar"></div><div id="ilContentContainer">Files</div>',
                          'https://ilias.example.edu')
        assert sample.logged_in() and sample.fingerprint()
        assert crawler._parse_page(sample).soup.select_one('#ilContentContainer').get_text() == 'Files'
    from PySide6.QtCore import qVersion
    from PySide6.QtWidgets import QApplication
    # Exercise frozen Qt plugins and GUI imports without touching the user's profiles.
    previous_root = os.environ.get("ILIAS_SYNC_DATA_DIR")
    with tempfile.TemporaryDirectory() as gui_tmp:
        os.environ["ILIAS_SYNC_DATA_DIR"] = gui_tmp
        try:
            from .gui import MainWindow
            from .branding import app_icon
            app = QApplication.instance() or QApplication([])
            from .native_compat import protect_accessibility
            protect_accessibility(app)
            icon = app_icon()
            assert not icon.isNull(), "Packaged application icon is missing"
            assert not icon.pixmap(32, 32).isNull(), "Packaged icon cannot be decoded"
            app.setWindowIcon(icon)
            window = MainWindow()
            window.show()
            app.processEvents()
            assert not window.progress_timer.isActive()
            assert window.sync_button.text() == "Jetzt synchronisieren"
            window.close()
            if getattr(sys, 'frozen', False):
                config = json.loads((Path(__file__).parent / 'assets/update-config.json').read_text())
                if sys.platform in {'darwin', 'win32'}:
                    from .native_updates import NativeUpdates
                    # Load the real frozen libraries without starting the updater:
                    # no network request, consent prompt or native preference write.
                    target = 'windows-x64.xml' if sys.platform == 'win32' else 'macOS-arm64.xml'
                    native = NativeUpdates(config['public_key'], config['releases'] + '/latest/download/' + target,
                                           __version__)
                    assert native.supported, 'Packaged native updater could not be loaded: ' + native.last_error
                    assert not native.can_check
                    native.close()
                elif sys.platform == 'linux':
                    import base64
                    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                    Ed25519PublicKey.from_public_bytes(base64.b64decode(config['public_key'], validate=True))
        finally:
            if previous_root is None:
                os.environ.pop("ILIAS_SYNC_DATA_DIR", None)
            else:
                os.environ["ILIAS_SYNC_DATA_DIR"] = previous_root
    from .build_info import build_info
    emit({"event": "self-test", "ok": True, "version": __version__, "qt": qVersion(), 'build':build_info()['id']})
    return 0


def main():
    global EVENT_FILE
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="IliasSync — quiet course-file synchronization")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--sync", action="store_true", help="Synchronize due sources, then exit (no GUI).")
    parser.add_argument('--scheduled-time', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument("--discover", action="store_true", help="List joined courses for --profile.")
    parser.add_argument("--profile", help="Source UUID; a manual run bypasses the due-time and battery policy.")
    parser.add_argument("--probe", help="Detect the client ID at an HTTPS installation URL.")
    parser.add_argument("--self-test", action="store_true", help="Offline packaged-runtime smoke test.")
    parser.add_argument('--repair-schedule', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument("--render", help=argparse.SUPPRESS)
    parser.add_argument("--event-file", help=argparse.SUPPRESS)
    args = parser.parse_args()
    EVENT_FILE = args.event_file
    if args.self_test:
        return self_test()
    if args.repair_schedule:
        from .scheduler import ensure_schedule
        try:
            repaired = ensure_schedule(Settings().value)
            emit({'event': 'schedule', 'ok': True, 'repaired': repaired})
            return 0
        except Exception:
            emit({'event': 'schedule', 'ok': False, 'message': 'The saved schedule could not be restored. Your times are kept.'})
            return 1
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
