"""Use native OS scheduling; do not keep a polling process alive between syncs."""
import os
import plistlib
import subprocess
import sys
import tempfile
import getpass
from datetime import date
from xml.etree import ElementTree as ET
from pathlib import Path

from .storage import atomic_write

LABEL = "org.iliassync.desktop"


def command(*args):
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "ilias_sync", *args]


def install(hours: int, *, times=None):
    if times is not None:
        from .policy import normalize_times
        times = normalize_times(times)
    if hours not in (1, 3, 6, 12, 24):
        raise ValueError("Choose 1, 3, 6, 12 or 24 hours.")
    cmd = command("--sync", *(['--scheduled-time'] if times else []))
    if sys.platform == "darwin":
        target = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
        data = {"Label": LABEL, "ProgramArguments": cmd, "StartInterval": hours * 3600,
                "RunAtLoad": True, "ProcessType": "Background", "LowPriorityIO": True, "Nice": 10,
                "ThrottleInterval": 300}
        if times:
            data.pop('StartInterval')
            data['RunAtLoad'] = False
            data['ThrottleInterval'] = 10
            data['StartCalendarInterval'] = [{'Hour': int(value[:2]), 'Minute': int(value[3:])} for value in times]
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
        if times:
            xml = windows_calendar_xml(cmd, times)
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
    # systemd ExecStart has its own quoting rules; no shell evaluation or field-code expansion.
    escaped = " ".join('"' + c.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"' for c in cmd)
    atomic_write(unit / (LABEL + ".service"),
                 f"[Unit]\nDescription=IliasSync downloads\n[Service]\nType=oneshot\nExecStart={escaped}\nNice=10\n".encode())
    triggers = (''.join(f'OnCalendar=*-*-* {value}:00\n' for value in times) + 'AccuracySec=1s\nRandomizedDelaySec=0\n'
                if times else f'OnBootSec=2min\nOnUnitActiveSec={hours}h\nRandomizedDelaySec=5min\n')
    atomic_write(unit / (LABEL + ".timer"),
                 f"[Unit]\nDescription=IliasSync schedule\n[Timer]\n{triggers}[Install]\nWantedBy=timers.target\n".encode())
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", LABEL + ".timer"], check=True, capture_output=True)
    return str(unit / (LABEL + ".timer"))


def windows_calendar_xml(cmd, times):
    task = ET.Element('Task', {'xmlns': 'http://schemas.microsoft.com/windows/2004/02/mit/task', 'version': '1.2'})
    triggers = ET.SubElement(task, 'Triggers')
    for value in times:
        trigger = ET.SubElement(triggers, 'CalendarTrigger')
        ET.SubElement(trigger, 'StartBoundary').text = f'{date.today().isoformat()}T{value}:00'
        ET.SubElement(ET.SubElement(trigger, 'ScheduleByDay'), 'DaysInterval').text = '1'
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
