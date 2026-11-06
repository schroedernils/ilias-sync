from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import plistlib
import time
from datetime import datetime
from xml.etree import ElementTree as ET

import pytest

from ilias_sync.naming import course_folders
from ilias_sync.policy import next_scheduled_run, normalize_times
from ilias_sync.storage import Archive, Settings, data_dir, write_json


async def test_existing_course_folder_names_change_without_losing_annotations(source, monkeypatch):
    from ilias_sync.engine import synchronize
    from test_engine import FixtureSession
    monkeypatch.setattr('aiohttp.ClientSession', FixtureSession)
    source.include_course_ids = True
    await synchronize(source)
    old = Path(source.destination) / 'Algorithms [crs-123]'
    (old / 'my notes.txt').write_text('personal notes')
    (old / 'Lecture.pdf').write_bytes(b'ANNOTATED PDF')
    source.include_course_ids = False
    result = await synchronize(source)
    new = Path(source.destination) / 'Algorithms'
    assert not old.exists()
    assert (new / 'my notes.txt').read_text() == 'personal notes'
    assert (new / 'Lecture.pdf').read_bytes() == b'ANNOTATED PDF'
    assert result['counts'] == {'conflict': 1}
    assert result['pages']['parsed'] == 0
    source.folder_names = {'course/crs-123': 'Meine Vorlesung'}
    source.include_course_ids = True
    await synchronize(source)
    renamed = Path(source.destination) / 'Meine Vorlesung [crs-123]'
    assert (renamed / 'my notes.txt').read_text() == 'personal notes'
    assert (renamed / 'Lecture.pdf').read_bytes() == b'ANNOTATED PDF'


def test_colliding_course_names_are_stable_without_exposing_server_ids(source):
    rows = [{'id': 'crs-1', 'name': 'Vorlesung'}, {'id': 'crs-2', 'name': 'Vorlesung'}]
    names = course_folders(source, rows)
    assert len(set(names.values())) == 2
    assert all('crs-' not in name for name in names.values())
    assert names == course_folders(source, list(reversed(rows)))
    assert names == {'crs-1': 'Vorlesung', 'crs-2': 'Vorlesung (2)'}


def test_numbered_course_names_do_not_collide_with_real_titles(source):
    rows = [{'id': 'crs-1', 'name': 'Vorlesung'}, {'id': 'crs-2', 'name': 'Vorlesung'},
            {'id': 'crs-3', 'name': 'Vorlesung (2)'}]
    assert course_folders(source, rows) == {'crs-1': 'Vorlesung', 'crs-2': 'Vorlesung (3)',
                                          'crs-3': 'Vorlesung (2)'}


def test_namesake_joined_later_does_not_take_an_established_course_folder(source):
    initial = [{'id': 'crs-2', 'name': 'Vorlesung'}, {'id': 'crs-3', 'name': 'Vorlesung'}]
    names = course_folders(source, initial, persist=True)
    added = {'id': 'crs-1', 'name': 'Vorlesung'}
    assert course_folders(source, [added, *initial]) == {**names, 'crs-1': 'Vorlesung (3)'}
    assert course_folders(source, [added], persist=True) == {'crs-1': 'Vorlesung (3)'}
    assert course_folders(source, initial) == names


def test_naming_preview_is_read_only_and_alias_changes_are_not_blocked_by_saved_numbers(source):
    rows = [{'id': 'crs-1', 'name': 'Vorlesung'}]
    saved = data_dir() / 'sources' / source.id / 'course-folder-names.json'
    assert course_folders(source, rows) == {'crs-1': 'Vorlesung'}
    assert not saved.exists()
    course_folders(source, rows, persist=True)
    source.folder_names['course/crs-1'] = 'Mein Kurs'
    before = saved.read_bytes()
    assert course_folders(source, rows) == {'crs-1': 'Mein Kurs'}
    assert saved.read_bytes() == before


def test_multiple_remote_links_keep_established_folder_and_allow_alias_reset(source, tmp_path):
    from ilias_sync.naming import align_folders
    raw = tmp_path / 'raw.pdf'
    raw.write_bytes(b'local document')
    archive = Archive(tmp_path / 'state', Path(source.destination))
    courses = [{'id': 'crs-1', 'name': 'Vorlesung'}]
    for identity, logical in [('1', 'Material'), ('2', 'Termin 1'), ('3', 'Termin 2')]:
        archive.publish(identity, raw, f'Vorlesung [crs-1]/Material/{identity}.pdf',
                        metadata={'course_id': 'crs-1', 'logical': f'crs-1/{logical}/{identity}.pdf'})
    archive.publish('submission', raw, 'Vorlesung [crs-1]/Abgabe/Submission/4.pdf',
                    metadata={'course_id': 'crs-1', 'logical': 'crs-1/Abgabe/4.pdf'})
    align_folders(archive, source, courses)
    assert archive.manifest['files'].pop('submission')['path'] == 'Vorlesung/Abgabe/Submission/4.pdf'
    assert all(e['path'] == f'Vorlesung/Material/{i}.pdf' for i, e in archive.manifest['files'].items())
    source.folder_names = {'path/crs-1/Material': 'Folien'}
    align_folders(archive, source, courses)
    assert all(e['path'] == f'Vorlesung/Folien/{i}.pdf' for i, e in archive.manifest['files'].items())
    for e in archive.manifest['files'].values():
        e['folder_names_applied'] = dict(source.folder_names)
    source.folder_names = {}
    align_folders(archive, source, courses)
    assert all(e['path'] == f'Vorlesung/Material/{i}.pdf' for i, e in archive.manifest['files'].items())


def test_folder_rename_recovers_after_directory_move_before_manifest_write(tmp_path, monkeypatch):
    from ilias_sync import storage
    raw = tmp_path / 'raw.pdf'
    raw.write_bytes(b'%PDF-1.4 cached')
    archive = Archive(tmp_path / 'state', tmp_path / 'out')
    archive.publish('file:1', raw, 'Old/Intro.pdf')
    original = storage.write_json

    def interrupted(path, value):
        if path.name == 'manifest.json':
            raise OSError('simulated interruption')
        original(path, value)

    monkeypatch.setattr(storage, 'write_json', interrupted)
    with pytest.raises(OSError):
        archive.rename_folder(tmp_path / 'out', 'Old', 'New')
    assert (tmp_path / 'out/New/Intro.pdf').read_bytes() == raw.read_bytes()
    monkeypatch.setattr(storage, 'write_json', original)
    recovered = Archive(tmp_path / 'state', tmp_path / 'out')
    assert recovered.manifest['files']['file:1']['path'] == 'New/Intro.pdf'
    assert not recovered.rename_path.exists()
    assert recovered.publish('file:1', raw, 'New/Intro.pdf') == 'unchanged'


def test_rename_never_merges_an_existing_unmanaged_folder(tmp_path):
    raw = tmp_path / 'raw.pdf'
    raw.write_bytes(b'%PDF-1.4 cached')
    archive = Archive(tmp_path / 'state', tmp_path / 'out')
    archive.publish('file:1', raw, 'Old/Intro.pdf')
    (tmp_path / 'out/New').mkdir()
    (tmp_path / 'out/New/keep.txt').write_text('unrelated')
    with pytest.raises(ValueError, match='already exists'):
        archive.rename_folder(tmp_path / 'out', 'Old', 'New')
    assert (tmp_path / 'out/New/keep.txt').read_text() == 'unrelated'
    assert (tmp_path / 'out/Old/Intro.pdf').exists()


def test_custom_names_are_portable_and_route_specific(source, tmp_path):
    from ilias_sync.routing import route_file
    source.folder_names = {'course/crs-1': 'Mein Kurs', 'path/crs-1/Folien': 'Skripte'}
    source.folder_rules = {'course/crs-1': str(tmp_path / 'Custom')}
    source.validate()
    root, relative, _ = route_file(source, 'file:1', 'crs-1', 'crs-1/Folien/Intro.pdf', 'Mein Kurs/Folien/Intro.pdf')
    assert root == tmp_path / 'Custom'
    assert relative == 'Skripte/Intro.pdf'
    source.folder_names['course/crs-1'] = '../Outside'
    with pytest.raises(ValueError):
        source.validate()


def test_daily_times_are_deduplicated_and_next_run_uses_local_clock():
    assert normalize_times(['18:30', '08:00', '08:00']) == ['08:00', '18:30']
    with pytest.raises(ValueError):
        normalize_times(['24:00'])
    with pytest.raises(ValueError):
        normalize_times([])
    settings = {'schedule_mode': 'times', 'sync_times': ['08:00', '18:30'], 'interval_hours': 6}
    stamp = datetime(2026, 10, 27, 9, 0).timestamp()
    assert datetime.fromtimestamp(next_scheduled_run(settings, clock=stamp)) == datetime(2026, 10, 27, 18, 30)
    stamp = datetime(2026, 10, 27, 19, 0).timestamp()
    assert datetime.fromtimestamp(next_scheduled_run(settings, clock=stamp)) == datetime(2026, 10, 28, 8, 0)


def test_mac_fixed_schedule_has_exact_daily_triggers_and_no_run_on_install(tmp_path, monkeypatch):
    import ilias_sync.scheduler as scheduler
    monkeypatch.setattr(scheduler.sys, 'platform', 'darwin')
    monkeypatch.setattr(scheduler.os, 'getuid', lambda: 501, raising=False)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    with patch.object(scheduler.subprocess, 'run'):
        scheduler.install(6, times=['18:30', '08:00'])
    row = plistlib.loads((tmp_path / 'Library/LaunchAgents/org.iliassync.desktop.plist').read_bytes())
    assert row['StartCalendarInterval'] == [{'Hour': 8, 'Minute': 0}, {'Hour': 18, 'Minute': 30}]
    assert 'StartInterval' not in row
    assert not row['RunAtLoad']
    assert row['ProgramArguments'][-1] == '--scheduled-time'


def test_linux_fixed_schedule_has_no_random_delay(tmp_path, monkeypatch):
    import ilias_sync.scheduler as scheduler
    monkeypatch.setattr(scheduler.sys, 'platform', 'linux')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    with patch.object(scheduler.subprocess, 'run'):
        scheduler.install(6, times=['08:00', '18:30'])
    unit = tmp_path / '.config/systemd/user'
    timer = (unit / 'org.iliassync.desktop.timer').read_text()
    assert 'OnCalendar=*-*-* 08:00:00' in timer and 'OnCalendar=*-*-* 18:30:00' in timer
    assert 'RandomizedDelaySec=0' in timer
    assert 'OnBootSec' not in timer and 'OnUnitActiveSec' not in timer
    assert '--scheduled-time' in (unit / 'org.iliassync.desktop.service').read_text()


def test_mac_failed_install_restores_previous_schedule(tmp_path, monkeypatch):
    import subprocess
    import ilias_sync.scheduler as scheduler
    monkeypatch.setattr(scheduler.sys, 'platform', 'darwin')
    monkeypatch.setattr(scheduler.os, 'getuid', lambda: 501, raising=False)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    target = tmp_path / 'Library/LaunchAgents/org.iliassync.desktop.plist'
    target.parent.mkdir(parents=True)
    previous = plistlib.dumps({'Label': scheduler.LABEL, 'StartInterval': 21600})
    target.write_bytes(previous)
    with patch.object(scheduler.subprocess, 'run', side_effect=[
        None, subprocess.CalledProcessError(5, 'launchctl'), None,
    ]) as run:
        with pytest.raises(subprocess.CalledProcessError):
            scheduler.install(6, times=['08:00'])
    assert target.read_bytes() == previous
    assert run.call_count == 3


def test_windows_fixed_schedule_uses_one_task_with_two_daily_triggers():
    from ilias_sync.scheduler import windows_calendar_xml
    root = ET.fromstring(windows_calendar_xml(['C:/Program Files/IliasSync/IliasSync.exe', '--sync', '--scheduled-time'],
                                             ['08:00', '18:30']))
    ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    triggers = root.findall('t:Triggers/t:CalendarTrigger', ns)
    assert len(triggers) == 2
    assert all(t.find('t:ScheduleByDay/t:DaysInterval', ns).text == '1' for t in triggers)
    assert root.find('t:Principals/t:Principal/t:LogonType', ns).text == 'InteractiveToken'
    assert '--scheduled-time' in root.find('t:Actions/t:Exec/t:Arguments', ns).text


async def test_fixed_time_trigger_runs_after_manual_sync_without_ignoring_login_failure(source, monkeypatch):
    from ilias_sync.__main__ import worker
    from unittest.mock import AsyncMock
    settings = Settings()
    settings.save_source(source)
    settings.value.update(schedule_mode='times', sync_times=['08:00', '18:30'], scheduled=True, battery_saver=False)
    settings.save()
    status = data_dir() / 'sources' / source.id / 'status.json'
    write_json(status, {'next_run': time.time() + 99999, 'login_required': False})
    sync = AsyncMock(return_value={'partial': False, 'warnings': 0, 'errors': 0})
    monkeypatch.setattr('ilias_sync.engine.synchronize', sync)
    args = SimpleNamespace(probe=None, profile=None, sync=True, discover=False, scheduled_time=True)
    assert await worker(args) == 0
    sync.assert_awaited_once()
    sync.reset_mock()
    write_json(status, {'next_run': 0, 'login_required': True})
    assert await worker(args) == 0
    sync.assert_not_awaited()
