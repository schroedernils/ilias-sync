from datetime import datetime
from pathlib import Path
import os
import plistlib
import time
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

import pytest

from ilias_sync.policy import next_scheduled_run, normalize_weekly, weekly_draft


def test_normalization_and_read_only_legacy_migration():
    legacy = {'schedule_mode': 'times', 'sync_times': ['09:00', '15:00']}
    converted = weekly_draft(legacy)
    assert len(converted) == 7 and all(times == ['09:00', '15:00'] for times in converted.values())
    converted['0'].append('17:00')
    assert legacy['sync_times'] == ['09:00', '15:00']
    week = normalize_weekly({'0': ['15:00', '09:00', '09:00'], '6': []})
    assert week['0'] == ['09:00', '15:00'] and week['6'] == []
    assert normalize_weekly({}, require_times=False) == {str(day): [] for day in range(7)}
    for invalid in [{}, {'7': ['09:00']}, {'0': ['25:00']}, {'1': '09:00'}, []]:
        with pytest.raises(ValueError):
            normalize_weekly(invalid)


def test_next_weekly_run_skips_free_days_and_crosses_week_boundary():
    settings = {'schedule_mode': 'weekly', 'weekly_times': {'0': ['09:00', '15:00'], '4': ['12:00']}}
    cases = [(datetime(2026, 11, 2, 8), datetime(2026, 11, 2, 9)),
             (datetime(2026, 11, 2, 9), datetime(2026, 11, 2, 15)),
             (datetime(2026, 11, 2, 16), datetime(2026, 11, 6, 12)),
             (datetime(2026, 11, 6, 12), datetime(2026, 11, 9, 9)),
             (datetime(2026, 11, 8, 23, 59), datetime(2026, 11, 9, 9))]
    for now, expected in cases:
        assert datetime.fromtimestamp(next_scheduled_run(settings, clock=now.timestamp())) == expected


def test_weekly_preview_respects_server_pause_and_login_wait():
    from ilias_sync.presentation import schedule_expectation
    from ilias_sync.i18n import set_language
    set_language('de')
    settings = {'scheduled': True, 'schedule_mode': 'weekly', 'weekly_times': {'0': ['09:00'], '4': ['17:00']}}
    now = datetime(2026, 11, 2, 8).timestamp()
    retry = datetime(2026, 11, 2, 10).timestamp()
    text = schedule_expectation(settings, {'server_retry_at': retry}, clock=now)
    assert '17:00' in text and '09:00' not in text
    assert 'Anmeldung' in schedule_expectation(settings, {'login_required': True}, clock=now)


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='Explicit POSIX timezone switching; Windows triggers are checked separately')
def test_weekly_dst_missing_hour_skips_to_next_real_matching_week(monkeypatch):
    previous = os.environ.get('TZ')
    try:
        monkeypatch.setenv('TZ', 'Europe/Berlin')
        time.tzset()
        settings = {'schedule_mode': 'weekly', 'weekly_times': {'6': ['02:30']}}
        stamp = next_scheduled_run(settings, clock=datetime(2027, 3, 27, 12).timestamp())
        assert datetime.fromtimestamp(stamp) == datetime(2027, 4, 4, 2, 30)
    finally:
        if previous is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = previous
        time.tzset()


def test_mac_weekly_triggers_use_correct_weekdays_and_no_install_run(tmp_path, monkeypatch):
    import ilias_sync.scheduler as scheduler
    monkeypatch.setattr(scheduler.sys, 'platform', 'darwin')
    monkeypatch.setattr(scheduler.os, 'getuid', lambda: 501, raising=False)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    with patch.object(scheduler.subprocess, 'run'):
        scheduler.install(6, weekly={'0': ['08:00', '18:30'], '6': ['12:15']})
    row = plistlib.loads((tmp_path / 'Library/LaunchAgents/org.iliassync.desktop.plist').read_bytes())
    assert row['StartCalendarInterval'] == [{'Weekday': 1, 'Hour': 8, 'Minute': 0},
        {'Weekday': 1, 'Hour': 18, 'Minute': 30}, {'Weekday': 0, 'Hour': 12, 'Minute': 15}]
    assert not row['RunAtLoad'] and 'StartInterval' not in row
    assert row['ProgramArguments'][-1] == '--scheduled-time'


def test_linux_and_windows_encode_weekly_days_without_daily_fallback(tmp_path, monkeypatch):
    import ilias_sync.scheduler as scheduler
    monkeypatch.setattr(scheduler.sys, 'platform', 'linux')
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    with patch.object(scheduler.subprocess, 'run'):
        scheduler.install(6, weekly={'1': ['08:00'], '5': ['17:30']})
    timer = (tmp_path / '.config/systemd/user/org.iliassync.desktop.timer').read_text()
    assert 'OnCalendar=Tue *-*-* 08:00:00' in timer and 'OnCalendar=Sat *-*-* 17:30:00' in timer
    assert 'RandomizedDelaySec=0' in timer and 'OnBootSec' not in timer
    xml = ET.fromstring(scheduler.windows_calendar_xml(['sync.exe', '--sync'], weekly={'1': ['08:00'], '5': ['17:30']}))
    ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    triggers = xml.findall('t:Triggers/t:CalendarTrigger', ns)
    assert len(triggers) == 2
    assert triggers[0].find('t:ScheduleByWeek/t:DaysOfWeek/t:Tuesday', ns) is not None
    assert triggers[1].find('t:ScheduleByWeek/t:DaysOfWeek/t:Saturday', ns) is not None
    assert all(trigger.find('t:ScheduleByDay', ns) is None for trigger in triggers)


def test_weekly_install_failure_restores_previous_daily_settings_and_job():
    from ilias_sync.settings_service import apply_settings
    from ilias_sync.storage import Settings, read_json
    settings = Settings()
    settings.value.update(scheduled=True, schedule_mode='times', sync_times=['10:00'])
    settings.save()
    before = settings.path.read_bytes()
    installer = Mock(side_effect=[OSError('install failed'), None])
    with pytest.raises(OSError):
        apply_settings(settings, {**settings.value, 'schedule_mode': 'weekly', 'weekly_times': {'4': ['17:00']}},
                       install=installer, uninstall=Mock())
    assert settings.path.read_bytes() == before
    assert read_json(settings.path, {})['schedule_mode'] == 'times'
    assert installer.call_args_list[1].kwargs == {'times': ['10:00']}




@pytest.mark.parametrize('error', [OverflowError, ValueError, OSError])
def test_runtime_rejecting_forced_dst_keeps_normal_calendar_preview(monkeypatch, error):
    mktime = time.mktime
    def reject_forced_dst(value):
        if value[-1] != -1:
            raise error('forced DST unsupported in this timezone')
        return mktime(value)
    monkeypatch.setattr(time, 'mktime', reject_forced_dst)
    settings = {'schedule_mode':'weekly', 'weekly_times':{'0':['09:00']}}
    result = next_scheduled_run(settings, clock=datetime(2026,11,2,8).timestamp())
    assert datetime.fromtimestamp(result) == datetime(2026,11,2,9)
