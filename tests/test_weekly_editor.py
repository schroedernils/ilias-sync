def test_weekly_widgets_edit_copy_and_cancel_without_changing_saved_plan():
    from PySide6.QtCore import QTime
    from PySide6.QtWidgets import QApplication
    from ilias_sync.gui import SettingsDialog
    from ilias_sync.storage import Settings
    app = QApplication.instance() or QApplication([])
    settings = Settings()
    settings.value.update(scheduled=True, schedule_mode='times', sync_times=['08:00', '17:00'])
    settings.save()
    before = settings.path.read_bytes()
    dialog = SettingsDialog(settings)
    assert dialog.schedule_mode.currentData() == 'weekly'
    plan = dialog.week_plan
    assert all(times == ['08:00', '17:00'] for times in plan.values().values())
    plan.rows[0]['slots'][0]['edit'].setTime(QTime(9, 30))
    plan.copy_day(0, range(5))
    assert plan.values()['4'] == ['09:30', '17:00']
    assert plan.values()['6'] == ['08:00', '17:00']
    for slot in list(plan.rows[6]['slots']):
        slot['remove'].click()
    assert plan.values()['6'] == []
    dialog.reject()
    app.processEvents()
    assert settings.path.read_bytes() == before and settings.value['schedule_mode'] == 'times'


def test_editing_a_time_preserves_user_window_size_and_preview_stays_outside_scroll():
    from PySide6.QtCore import QTime
    from PySide6.QtWidgets import QApplication, QScrollArea
    from ilias_sync.gui import SettingsDialog
    from ilias_sync.storage import Settings
    app = QApplication.instance() or QApplication([])
    dialog = SettingsDialog(Settings())
    dialog.tabs.setCurrentIndex(1)
    dialog.enabled.setChecked(True)
    dialog.schedule_mode.setCurrentIndex(1)
    dialog.resize(540, 640)
    dialog.week_plan.add_time(2, '12:00')
    dialog.week_plan.rows[2]['slots'][0]['edit'].setTime(QTime(13, 30))
    app.processEvents()
    assert dialog.size().width() == 540 and dialog.size().height() == 640
    assert not isinstance(dialog.schedule_preview.parentWidget(), QScrollArea)
    assert '13:30' in dialog.schedule_preview.text()
    dialog.reject()
