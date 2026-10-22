"""No busy loop, one worker, persisted backoff and explicit power/network failure states."""
import random
import time


def next_run(interval_hours, failures=0, *, clock=None, jitter=True):
    delay = min(48 * 3600, interval_hours * 3600 * 2 ** min(failures, 4))
    return (time.time() if clock is None else clock) + delay + (random.uniform(0, 300) if jitter else 0)


def due(status, *, clock=None):
    if status.get("login_required"):
        return False
    return status.get("next_run", 0) <= (time.time() if clock is None else clock)


def on_battery():
    import psutil
    battery = psutil.sensors_battery()
    return bool(battery and not battery.power_plugged)
