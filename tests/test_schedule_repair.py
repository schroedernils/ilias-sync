"""An update may change the executable or remove its job, never the saved calendar."""
from copy import deepcopy
from pathlib import Path
import plistlib
import subprocess
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

import pytest

from ilias_sync import scheduler
from ilias_sync.storage import Settings


@pytest.fixture
def settings():
    value = Settings()
    value.value.update(scheduled=True, schedule_mode='weekly',
                       weekly_times={'0': ['10:30'], '1': ['13:50', '17:00'], '6': []})
    value.save()
    return value


@pytest.mark.parametrize('platform', ['darwin', 'linux'])
@pytest.mark.parametrize('mode', ['interval', 'times', 'weekly'])
def test_update_reinstall_and_missing_job_preserve_calendar(settings, tmp_path, monkeypatch, platform, mode):
    monkeypatch.setattr(scheduler.sys, 'platform', platform)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setattr(scheduler.os, 'getuid', lambda: 501, raising=False)
    settings.value.update(schedule_mode=mode, sync_times=['09:00', '16:30'])
    settings.save()
    original = settings.path.read_bytes()
    executable = ['/old installation/IliasSync']
    monkeypatch.setattr(scheduler, 'command', lambda *args: [executable[0], *args])
    monkeypatch.setattr(scheduler, '_query', lambda args: subprocess.CompletedProcess(args, 0, b''))
    with patch.object(scheduler.subprocess, 'run'):
        hours, options = scheduler.saved_schedule(settings.value)
        scheduler.install(hours, **options)
        assert scheduler.registration_matches(settings.value)
        # Launching the app repeatedly must not reset an intact OS timer.
        with patch.object(scheduler, 'install', wraps=scheduler.install) as install:
            assert not scheduler.ensure_schedule(settings.value)
            install.assert_not_called()
            executable[0] = '/new installation/IliasSync'
            assert scheduler.ensure_schedule(settings.value)
            assert scheduler.registration_matches(settings.value)
            assert install.call_count == 1
            assert not scheduler.ensure_schedule(settings.value)
            if platform == 'darwin':
                target = tmp_path / 'Library/LaunchAgents/org.iliassync.desktop.plist'
                assert plistlib.loads(target.read_bytes())['ProgramArguments'][0] == executable[0]
            else:
                target = tmp_path / '.config/systemd/user/org.iliassync.desktop.timer'
            target.unlink()
            assert scheduler.ensure_schedule(settings.value)
            assert install.call_count == 2
        # A job file alone is insufficient when the OS registration was removed.
        monkeypatch.setattr(scheduler, '_query', lambda args: subprocess.CompletedProcess(args, 1, b''))
        with patch.object(scheduler, 'install') as install:
            assert scheduler.ensure_schedule(settings.value)
            install.assert_called_once_with(hours, **options)
    assert settings.path.read_bytes() == original


def windows_task(cmd, mode):
    if mode == 'weekly':
        raw = scheduler.windows_calendar_xml(cmd, weekly={'0': ['10:30'], '6': ['12:00']})
    else:
        raw = scheduler.windows_calendar_xml(cmd, ['09:00', '16:30'] if mode == 'times' else ['08:00'])
    tree = ET.fromstring(raw)
    ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    if mode == 'interval':
        trigger = tree.find('t:Triggers/t:CalendarTrigger', ns)
        repetition = ET.SubElement(trigger, '{' + ns['t'] + '}Repetition')
        ET.SubElement(repetition, '{' + ns['t'] + '}Interval').text = 'PT360M'
    for boundary in tree.findall('t:Triggers/t:CalendarTrigger/t:StartBoundary', ns):
        boundary.text = '2020-01-01T' + boundary.text.partition('T')[2]
    ET.indent(tree)
    return tree, ns


@pytest.mark.parametrize('mode', ['interval', 'times', 'weekly'])
def test_windows_reads_native_task_xml_and_repairs_only_stale_registration(settings, monkeypatch, mode):
    monkeypatch.setattr(scheduler.sys, 'platform', 'win32')
    settings.value.update(schedule_mode=mode, sync_times=['09:00', '16:30'],
                          weekly_times={'0': ['10:30'], '6': ['12:00']})
    before = deepcopy(settings.value)
    cmd = [r'C:\New App\IliasSync.exe', '--sync', *([] if mode == 'interval' else ['--scheduled-time'])]
    monkeypatch.setattr(scheduler, 'command', lambda *args: [cmd[0], *args])
    task, ns = windows_task(cmd, mode)
    monkeypatch.setattr(scheduler, '_query', lambda args: subprocess.CompletedProcess(args, 0, ET.tostring(task)))
    with patch.object(scheduler, 'install') as install:
        assert not scheduler.ensure_schedule(settings.value)
        install.assert_not_called()
        task.find('t:Actions/t:Exec/t:Command', ns).text = r'C:\Old App\IliasSync.exe'
        assert scheduler.ensure_schedule(settings.value)
        hours, options = scheduler.saved_schedule(settings.value)
        install.assert_called_once_with(hours, **options)
    assert settings.value == before
    task.find('t:Actions/t:Exec/t:Command', ns).text = cmd[0]
    ET.SubElement(task.find('t:Settings', ns), '{' + ns['t'] + '}Enabled').text = 'false'
    assert not scheduler.registration_matches(settings.value)


def test_disabled_automation_is_never_reenabled(settings):
    settings.value['scheduled'] = False
    with patch.object(scheduler, 'registration_matches') as inspect, patch.object(scheduler, 'install') as install:
        assert not scheduler.ensure_schedule(settings.value)
    inspect.assert_not_called()
    install.assert_not_called()


def test_unchanged_settings_save_reinstalls_missing_schedule_and_keeps_times(settings):
    from ilias_sync.settings_service import apply_settings
    original = settings.path.read_bytes()
    install = Mock()
    apply_settings(settings, deepcopy(settings.value), install=install, uninstall=Mock(),
                   schedule_is_current=lambda value: False)
    install.assert_called_once_with(6, weekly=settings.value['weekly_times'])
    assert settings.path.read_bytes() == original


def test_failed_repair_keeps_saved_policy_and_rolls_back(settings):
    from ilias_sync.settings_service import apply_settings
    before = settings.path.read_bytes()
    install = Mock(side_effect=[OSError('system unavailable'), None])
    with pytest.raises(OSError):
        apply_settings(settings, deepcopy(settings.value), install=install, uninstall=Mock(),
                       schedule_is_current=lambda value: False)
    assert settings.path.read_bytes() == before
    assert all(call.kwargs == {'weekly': settings.value['weekly_times']} for call in install.call_args_list)


def test_invalid_calendar_never_falls_back_to_six_hour_sync(settings):
    settings.value['weekly_times'] = {}
    with patch.object(scheduler, 'install') as install, pytest.raises(ValueError):
        scheduler.ensure_schedule(settings.value)
    install.assert_not_called()


def test_schedule_repair_failure_guides_to_settings_without_discarding_calendar(settings, source):
    from PySide6.QtWidgets import QApplication
    from ilias_sync.gui import MainWindow
    app = QApplication.instance() or QApplication([])
    settings.save_source(source)
    window = MainWindow()
    before = settings.path.read_bytes()
    window.show()
    with patch('ilias_sync.gui.ensure_schedule', side_effect=OSError('unavailable')):
        window.restore_schedule()
    app.processEvents()
    assert window.ui_error_kind == 'schedule'
    assert window.recovery_button.text() == 'Zeitplan prüfen'
    with patch.object(window, 'background') as open_settings:
        window.recover()
        open_settings.assert_called_once_with(1)
    window.ui_error = ''
    window.ui_error_kind = ''
    window.refresh()
    assert window.ui_error_kind == 'schedule'
    assert settings.path.read_bytes() == before
    window.close()
