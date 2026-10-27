"""Commit settings with scheduler rollback; edits remain a draft until Save."""
from copy import deepcopy


class ScheduleRestoreError(RuntimeError):
    pass


def apply_settings(settings, candidate, *, install, uninstall):
    previous = deepcopy(settings.value)
    def schedule(value):
        if value['scheduled']:
            install(value['interval_hours'], times=value.get('sync_times', []) if value.get('schedule_mode') == 'times' else None)
        else:
            uninstall()
    keys = ('scheduled', 'interval_hours', 'schedule_mode', 'sync_times')
    changed = any(candidate.get(key) != previous.get(key) for key in keys)
    changed = changed and (candidate['scheduled'] or previous['scheduled'])
    # Persist first so a RunAtLoad worker sees the new policy. Roll back both
    # configuration and native scheduling if installation or the write fails.
    settings.value = deepcopy(candidate)
    native_attempted = False
    try:
        settings.save()
        if changed:
            native_attempted = True
            schedule(candidate)
    except Exception:
        settings.value = previous
        settings.save()
        if native_attempted:
            try:
                schedule(previous)
            except Exception:
                raise ScheduleRestoreError('The previous system schedule could not be restored. Reapply the schedule before relying on automatic sync.') from None
        raise
