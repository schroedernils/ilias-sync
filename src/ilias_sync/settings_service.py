"""Commit settings with scheduler rollback; edits remain a draft until Save."""
from copy import deepcopy


class ScheduleRestoreError(RuntimeError):
    pass


class SettingsStorageError(RuntimeError):
    pass


def apply_settings(settings, candidate, *, install, uninstall, schedule_is_current=None):
    from .storage import atomic_write
    previous = deepcopy(settings.value)
    try:
        previous_config = settings.path.read_bytes() if settings.path.exists() else None
    except OSError:
        raise SettingsStorageError('Existing settings could not be read. Check access to the application data folder and try again.') from None
    def schedule(value):
        if value['scheduled']:
            if value.get('schedule_mode') == 'weekly':
                install(value['interval_hours'], weekly=value.get('weekly_times', {}))
            else:
                install(value['interval_hours'], times=value.get('sync_times', []) if value.get('schedule_mode') == 'times' else None)
        else:
            uninstall()
    keys = ('scheduled', 'interval_hours', 'schedule_mode', 'sync_times', 'weekly_times')
    changed = any(candidate.get(key) != previous.get(key) for key in keys)
    changed = changed and (candidate['scheduled'] or previous['scheduled'])
    # Persist first so a RunAtLoad worker sees the new policy. Roll back both
    # configuration and native scheduling if installation or the write fails.
    settings.value = deepcopy(candidate)
    native_attempted = False
    try:
        settings.save()
        repair = candidate['scheduled'] and not changed and schedule_is_current is not None and not schedule_is_current(candidate)
        if changed or repair:
            native_attempted = True
            schedule(candidate)
    except Exception:
        settings.value = previous
        restore_failed = False
        try:
            if previous_config is None:
                settings.path.unlink(missing_ok=True)
            elif not settings.path.exists() or settings.path.read_bytes() != previous_config:
                atomic_write(settings.path, previous_config)
        except Exception:
            restore_failed = True
        if native_attempted:
            try:
                schedule(previous)
            except Exception:
                raise ScheduleRestoreError('The previous system schedule could not be restored. Reapply the schedule before relying on automatic sync.') from None
        if restore_failed:
            raise ScheduleRestoreError('The previous settings could not be restored. Check settings and reapply the schedule before relying on automatic sync.') from None
        if not native_attempted:
            raise SettingsStorageError('Settings could not be saved. Check available space and folder permissions, then try again. Your changes are still shown.') from None
        raise
