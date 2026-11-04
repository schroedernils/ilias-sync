"""Use native OS scheduling; do not keep a polling process alive between syncs."""
import os
import plistlib
import subprocess
import sys
import tempfile
import getpass
import re
from datetime import date
from xml.etree import ElementTree as ET
from pathlib import Path

from .storage import atomic_write

LABEL = "org.iliassync.desktop"


def saved_schedule(value):
    """Preserve the chosen calendar; never silently fall back to an interval."""
    mode = value.get('schedule_mode', 'interval')
    if mode not in {'interval', 'times', 'weekly'}:
        raise ValueError('Choose a valid schedule mode.')
    options = ({'weekly': value.get('weekly_times', {})} if mode == 'weekly' else
               {'times': value.get('sync_times', [])} if mode == 'times' else {})
    hours = value['interval_hours']
    if hours not in (1, 3, 6, 12, 24):
        raise ValueError('Choose 1, 3, 6, 12 or 24 hours.')
    return hours, options


def ensure_schedule(value):
    """Repair only an enabled saved schedule, once at startup, without changing it."""
    if not value.get('scheduled') or registration_matches(value):
        return False
    hours, options = saved_schedule(value)
    install(hours, **options)
    return True


def command(*args):
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "ilias_sync", *args]


def _mac_job(cmd, hours, times, weekly):
    data = {'Label': LABEL, 'ProgramArguments': cmd, 'StartInterval': hours * 3600,
            'RunAtLoad': True, 'ProcessType': 'Background', 'LowPriorityIO': True, 'Nice': 10,
            'ThrottleInterval': 300}
    if times or weekly:
        data.pop('StartInterval')
        data['RunAtLoad'] = False
        data['ThrottleInterval'] = 10
        data['StartCalendarInterval'] = ([{'Weekday': (int(day) + 1) % 7, 'Hour': int(value[:2]), 'Minute': int(value[3:])}
            for day, values in weekly.items() for value in values] if weekly else
            [{'Hour': int(value[:2]), 'Minute': int(value[3:])} for value in times])
    return data


def _linux_units(cmd, hours, times, weekly):
    escaped = ' '.join('"' + c.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"' for c in cmd)
    service = f'[Unit]\nDescription=IliasSync downloads\n[Service]\nType=oneshot\nExecStart={escaped}\nNice=10\n'
    calendars = ([f'{("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[int(day)]} *-*-* {value}:00'
                  for day, values in weekly.items() for value in values] if weekly else
                 [f'*-*-* {value}:00' for value in times or []])
    triggers = (''.join(f'OnCalendar={value}\n' for value in calendars) + 'AccuracySec=1s\nRandomizedDelaySec=0\n'
                if times or weekly else f'OnBootSec=2min\nOnUnitActiveSec={hours}h\nRandomizedDelaySec=5min\n')
    timer = f'[Unit]\nDescription=IliasSync schedule\n[Timer]\n{triggers}[Install]\nWantedBy=timers.target\n'
    return service, timer


def _query(args):
    return subprocess.run(args, capture_output=True, timeout=10)


def registration_matches(value):
    """Inspect this user's job and current executable, rather than a version marker."""
    if not value.get('scheduled'):
        return True
    hours, options = saved_schedule(value)
    from .policy import normalize_times, normalize_weekly
    times = normalize_times(options['times']) if 'times' in options else None
    weekly = normalize_weekly(options['weekly']) if 'weekly' in options else None
    cmd = command('--sync', *(['--scheduled-time'] if times or weekly else []))
    try:
        if sys.platform == 'darwin':
            target = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
            if not target.exists() or plistlib.loads(target.read_bytes()) != _mac_job(cmd, hours, times, weekly):
                return False
            return _query(['launchctl', 'print', f'gui/{os.getuid()}/{LABEL}']).returncode == 0
        if sys.platform == 'win32':
            result = _query(['schtasks', '/Query', '/TN', 'IliasSync', '/XML'])
            return result.returncode == 0 and _windows_matches(result.stdout, cmd, hours, times, weekly)
        unit = Path.home() / '.config/systemd/user'
        for suffix, expected in zip(('.service', '.timer'), _linux_units(cmd, hours, times, weekly)):
            target = unit / (LABEL + suffix)
            if not target.exists() or target.read_text() != expected:
                return False
        return all(_query(['systemctl', '--user', action, '--quiet', LABEL + '.timer']).returncode == 0
                   for action in ('is-enabled', 'is-active'))
    except (OSError, ValueError, ET.ParseError, subprocess.SubprocessError):
        return False


def _windows_matches(xml, cmd, hours, times, weekly):
    task = ET.fromstring(xml)
    ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    action = task.find('t:Actions/t:Exec', ns)
    if (action is None or (action.findtext('t:Command', '', ns)).casefold() != cmd[0].casefold() or
            action.findtext('t:Arguments', '', ns) != subprocess.list2cmdline(cmd[1:])):
        return False
    if task.findtext('t:Settings/t:Enabled', 'true', ns) == 'false':
        return False
    trigger_host = task.find('t:Triggers', ns)
    triggers = list(trigger_host) if trigger_host is not None else []
    if not triggers or any(trigger.findtext('t:Enabled', 'true', ns) == 'false' for trigger in triggers):
        return False
    if not times and not weekly:
        if len(triggers) != 1:
            return False
        interval = triggers[0].findtext('t:Repetition/t:Interval', '', ns)
        match = re.fullmatch(r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', interval)
        return bool(match and sum(int(n or 0) * factor for n, factor in zip(match.groups(), (86400, 3600, 60, 1))) == hours * 3600)
    desired = windows_calendar_xml(cmd, times, weekly=weekly)
    expected = ET.fromstring(desired).findall('t:Triggers/t:CalendarTrigger', ns)
    def calendar(trigger):
        boundary = trigger.findtext('t:StartBoundary', '', ns)
        schedule = trigger.find('t:ScheduleByWeek' if weekly else 't:ScheduleByDay', ns)
        if schedule is None:
            return ('', '', ())
        period = schedule.findtext('t:WeeksInterval' if weekly else 't:DaysInterval', '', ns)
        days = schedule.find('t:DaysOfWeek', ns)
        return (boundary.partition('T')[2][:8], period,
                tuple(sorted(day.tag.rpartition('}')[2] for day in days)) if days is not None else ())
    return sorted(calendar(trigger) for trigger in triggers) == sorted(calendar(trigger) for trigger in expected)


def install(hours: int, *, times=None, weekly=None):
    if times is not None and weekly is not None:
        raise ValueError('Choose one schedule mode.')
    if times is not None:
        from .policy import normalize_times
        times = normalize_times(times)
    if weekly is not None:
        from .policy import normalize_weekly
        weekly = normalize_weekly(weekly)
    if hours not in (1, 3, 6, 12, 24):
        raise ValueError("Choose 1, 3, 6, 12 or 24 hours.")
    calendar = bool(times or weekly)
    cmd = command("--sync", *(['--scheduled-time'] if calendar else []))
    if sys.platform == "darwin":
        target = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
        data = _mac_job(cmd, hours, times, weekly)
        domain = f"gui/{os.getuid()}"
        previous = target.read_bytes() if target.exists() else None
        subprocess.run(["launchctl", "bootout", domain + "/" + LABEL], capture_output=True)
        atomic_write(target, plistlib.dumps(data))
        try:
            subprocess.run(["launchctl", "bootstrap", domain, str(target)], check=True, capture_output=True)
        except Exception:
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                atomic_write(target, previous)
                subprocess.run(["launchctl", "bootstrap", domain, str(target)], capture_output=True)
            raise
        return str(target)
    if sys.platform == "win32":
        if calendar:
            xml = windows_calendar_xml(cmd, times, weekly=weekly)
            with tempfile.TemporaryDirectory(prefix='iliassync-schedule-') as temporary:
                path = Path(temporary) / 'schedule.xml'
                path.write_bytes(xml)
                subprocess.run(['schtasks', '/Create', '/TN', 'IliasSync', '/XML', str(path), '/F'],
                               check=True, capture_output=True)
            return 'Windows Task Scheduler / IliasSync (current user)'
        subprocess.run(["schtasks", "/Create", "/TN", "IliasSync", "/SC", "HOURLY", "/MO", str(hours),
                        "/TR", subprocess.list2cmdline(cmd), "/F"], check=True, capture_output=True)
        return "Windows Task Scheduler / IliasSync (current user)"
    unit = Path.home() / ".config/systemd/user"
    unit.mkdir(parents=True, exist_ok=True)
    for suffix, text in zip(('.service', '.timer'), _linux_units(cmd, hours, times, weekly)):
        atomic_write(unit / (LABEL + suffix), text.encode())
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", LABEL + ".timer"], check=True, capture_output=True)
    return str(unit / (LABEL + ".timer"))


def windows_calendar_xml(cmd, times=None, *, weekly=None):
    task = ET.Element('Task', {'xmlns': 'http://schemas.microsoft.com/windows/2004/02/mit/task', 'version': '1.2'})
    triggers = ET.SubElement(task, 'Triggers')
    entries = [(day, value) for day, values in weekly.items() for value in values] if weekly else [(None, value) for value in times]
    for day, value in entries:
        trigger = ET.SubElement(triggers, 'CalendarTrigger')
        ET.SubElement(trigger, 'StartBoundary').text = f'{date.today().isoformat()}T{value}:00'
        if day is None:
            ET.SubElement(ET.SubElement(trigger, 'ScheduleByDay'), 'DaysInterval').text = '1'
        else:
            schedule = ET.SubElement(trigger, 'ScheduleByWeek')
            ET.SubElement(schedule, 'WeeksInterval').text = '1'
            ET.SubElement(ET.SubElement(schedule, 'DaysOfWeek'),
                          ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')[int(day)])
    principal = ET.SubElement(ET.SubElement(task, 'Principals'), 'Principal', {'id': 'CurrentUser'})
    user = getpass.getuser()
    domain = os.environ.get('USERDOMAIN', '')
    ET.SubElement(principal, 'UserId').text = domain + '\\' + user if domain else user
    ET.SubElement(principal, 'LogonType').text = 'InteractiveToken'
    ET.SubElement(principal, 'RunLevel').text = 'LeastPrivilege'
    settings = ET.SubElement(task, 'Settings')
    ET.SubElement(settings, 'MultipleInstancesPolicy').text = 'IgnoreNew'
    ET.SubElement(settings, 'DisallowStartIfOnBatteries').text = 'false'
    ET.SubElement(settings, 'StopIfGoingOnBatteries').text = 'false'
    ET.SubElement(settings, 'ExecutionTimeLimit').text = 'PT0S'
    action = ET.SubElement(ET.SubElement(task, 'Actions', {'Context': 'CurrentUser'}), 'Exec')
    ET.SubElement(action, 'Command').text = cmd[0]
    ET.SubElement(action, 'Arguments').text = subprocess.list2cmdline(cmd[1:])
    return ET.tostring(task, encoding='utf-16', xml_declaration=True)


def uninstall():
    if sys.platform == "darwin":
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
        (Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")).unlink(missing_ok=True)
    elif sys.platform == "win32":
        subprocess.run(["schtasks", "/Delete", "/TN", "IliasSync", "/F"], capture_output=True, check=True)
    else:
        subprocess.run(["systemctl", "--user", "disable", "--now", LABEL + ".timer"], capture_output=True, check=True)
        for suffix in (".timer", ".service"):
            (Path.home() / ".config/systemd/user" / (LABEL + suffix)).unlink(missing_ok=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
