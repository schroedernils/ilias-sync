"""Use native OS scheduling; do not keep a polling process alive between syncs."""
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from .storage import atomic_write

LABEL = "org.iliassync.desktop"


def command(*args):
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, "-m", "ilias_sync", *args]


def install(hours: int):
    if hours not in (1, 3, 6, 12, 24):
        raise ValueError("Choose 1, 3, 6, 12 or 24 hours.")
    cmd = command("--sync")
    if sys.platform == "darwin":
        target = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
        data = {"Label": LABEL, "ProgramArguments": cmd, "StartInterval": hours * 3600,
                "RunAtLoad": True, "ProcessType": "Background", "LowPriorityIO": True, "Nice": 10,
                "ThrottleInterval": 300}
        domain = f"gui/{os.getuid()}"
        subprocess.run(["launchctl", "bootout", domain + "/" + LABEL], capture_output=True)
        atomic_write(target, plistlib.dumps(data))
        subprocess.run(["launchctl", "bootstrap", domain, str(target)], check=True, capture_output=True)
        return str(target)
    if sys.platform == "win32":
        subprocess.run(["schtasks", "/Create", "/TN", "IliasSync", "/SC", "HOURLY", "/MO", str(hours),
                        "/TR", subprocess.list2cmdline(cmd), "/F"], check=True, capture_output=True)
        return "Windows Task Scheduler / IliasSync (current user)"
    unit = Path.home() / ".config/systemd/user"
    unit.mkdir(parents=True, exist_ok=True)
    # systemd ExecStart has its own quoting rules; no shell evaluation or field-code expansion.
    escaped = " ".join('"' + c.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"' for c in cmd)
    atomic_write(unit / (LABEL + ".service"),
                 f"[Unit]\nDescription=IliasSync downloads\n[Service]\nType=oneshot\nExecStart={escaped}\nNice=10\n".encode())
    atomic_write(unit / (LABEL + ".timer"),
                 f"[Unit]\nDescription=IliasSync schedule\n[Timer]\nOnBootSec=2min\nOnUnitActiveSec={hours}h\nRandomizedDelaySec=5min\n[Install]\nWantedBy=timers.target\n".encode())
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", LABEL + ".timer"], check=True, capture_output=True)
    return str(unit / (LABEL + ".timer"))


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
