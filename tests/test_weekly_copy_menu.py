"""Copy one weekday into another while retaining all unrelated days and draft safety."""
from unittest.mock import patch

import pytest


@pytest.mark.parametrize('source_day', [0, 2, 6])
def test_copy_to_one_day_only(source_day):
    from PySide6.QtWidgets import QApplication
    from ilias_sync.i18n import set_language, t
    from ilias_sync.schedule_widgets import WeeklySchedule, WEEKDAYS
    app = QApplication.instance() or QApplication([])
    set_language('de')
    values = {str(day): [f'{day + 8:02d}:00'] for day in range(7)}
    plan = WeeklySchedule(values)
    with patch('ilias_sync.schedule_widgets.popup') as popup:
        plan.copy_menu()
    menu = popup.call_args.args[0]
    day_menu = menu.actions()[source_day].menu()
    targets = day_menu.actions()[-1].menu()
    assert targets.title() == 'Anderer Tag'
    assert len(targets.actions()) == 6
    target_day = (source_day + 1) % 7
    next(action for action in targets.actions() if action.text() == t(WEEKDAYS[target_day])).trigger()
    expected = {**values, str(target_day): values[str(source_day)]}
    assert plan.values() == expected
    assert app is not None


def test_copy_button_is_next_to_battery_and_stays_in_draft():
    from PySide6.QtWidgets import QApplication
    from ilias_sync.gui import SettingsDialog
    from ilias_sync.storage import Settings
    app = QApplication.instance() or QApplication([])
    settings = Settings()
    settings.value.update(scheduled=True, schedule_mode='weekly', weekly_times={'0':['09:00','15:00'],'1':['11:00']})
    dialog = SettingsDialog(settings)
    dialog.tabs.setCurrentIndex(1)
    dialog.show()
    app.processEvents()
    copy = dialog.week_plan.copy_button
    assert copy.text() == 'Zeiten kopieren'
    assert copy.isVisible() and copy.isEnabled()
    assert copy.parentWidget() is dialog.battery.parentWidget()
    assert copy.x() > dialog.battery.x()
    dialog.week_plan.copy_day(0, [1])
    dialog.enabled.setChecked(False)
    assert not copy.isEnabled()
    dialog.reject()
    assert settings.value['weekly_times']['1'] == ['11:00']
    assert not settings.path.exists()


@pytest.mark.parametrize('action_index,targets', [(0, range(5)), (1, range(7))])
def test_bulk_copy_actions_still_work(action_index, targets):
    from PySide6.QtWidgets import QApplication
    from ilias_sync.schedule_widgets import WeeklySchedule
    app = QApplication.instance() or QApplication([])
    plan = WeeklySchedule({'0':['09:00','15:00']})
    with patch('ilias_sync.schedule_widgets.popup') as popup:
        plan.copy_menu()
    popup.call_args.args[0].actions()[0].menu().actions()[action_index].trigger()
    assert all(plan.values()[str(day)] == ['09:00','15:00'] for day in targets)
    assert app is not None
