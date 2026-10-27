"""No busy loop, one worker, persisted backoff and explicit power/network failure states."""
import time
from datetime import datetime, timedelta
import re


def normalize_times(values):
    if not isinstance(values, list) or not values or any(not isinstance(v, str) or
            not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', v) for v in values):
        raise ValueError('Add at least one valid time (HH:MM).')
    return sorted(set(values))


def next_scheduled_run(settings, failures=0, *, clock=None):
    if settings.get('schedule_mode', 'interval') != 'times' or not settings.get('sync_times'):
        return next_run(settings['interval_hours'], failures, clock=clock)
    times = normalize_times(settings.get('sync_times', []))
    now = time.time() if clock is None else clock
    today = datetime.fromtimestamp(now)
    candidates = []
    for days in range(3):
        date = today.date() + timedelta(days=days)
        for value in times:
            hour, minute = map(int, value.split(':'))
            # mktime can silently turn a missing spring-forward hour into a
            # different wall-clock time. Only preview actual matching local times.
            requested = datetime(date.year, date.month, date.day, hour, minute)
            valid = []
            for dst in (-1, 0, 1):
                stamp = time.mktime((date.year, date.month, date.day, hour, minute, 0, -1, -1, dst))
                if datetime.fromtimestamp(stamp) == requested:
                    valid.append(stamp)
            if valid and min(valid) > now:
                candidates.append(min(valid))
    return min(candidates)


def next_run(interval_hours, failures=0, *, clock=None):
    delay = min(48 * 3600, interval_hours * 3600 * 2 ** min(failures, 4))
    return (time.time() if clock is None else clock) + delay


def due(status, *, clock=None):
    if status.get("login_required"):
        return False
    return status.get("next_run", 0) <= (time.time() if clock is None else clock)


def on_battery():
    import psutil
    battery = psutil.sensors_battery()
    return bool(battery and not battery.power_plugged)
