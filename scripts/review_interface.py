"""Render synthetic UX states and verify desktop geometry without account access."""
import json
import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_SCALE_FACTOR', '2')


def main():
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication, QPushButton, QScrollArea
    from ilias_sync.gui import MainWindow, SourceDialog, SettingsDialog, FolderMappingDialog, SyncReportDialog, HelpDialog
    from ilias_sync.storage import Settings, Source, data_dir, write_json, source_scope
    from ilias_sync.theme import Theme
    output = Path(__file__).resolve().parents[1] / '.local/redesign-review'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ilias-ux-review-') as temporary:
        os.environ['ILIAS_SYNC_DATA_DIR'] = str(Path(temporary) / 'state')
        app = QApplication([])
        app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        app.theme = Theme(app, 'light')
        geometry = []

        def capture(widget, name):
            widget.show()
            app.processEvents()
            surface = widget.centralWidget() if isinstance(widget, MainWindow) else widget
            assert surface.grab().save(str(output / (name + '.png')))
            for control in widget.findChildren(QPushButton):
                if control.isVisibleTo(widget):
                    origin = control.mapTo(widget, control.rect().topLeft())
                    assert origin.x() >= 0 and origin.y() >= 0, (name, control.text(), origin)
                    assert origin.x() + control.width() <= widget.width() + 1, (name, control.text())
                    parent = control.parentWidget()
                    scrollable = False
                    while parent and parent is not widget:
                        if isinstance(parent, QScrollArea) and parent.verticalScrollBar().maximum() > 0:
                            scrollable = True
                        parent = parent.parentWidget()
                    assert scrollable or origin.y() + control.height() <= widget.height() + 1, (name, control.text())
            geometry.append({'state': name, 'width': widget.width(), 'height': widget.height()})

        settings = Settings()
        empty = MainWindow()
        capture(empty, 'empty-light')
        empty.close()
        source = Source('Universität Stuttgart', 'https://campus.example.edu', str(Path(temporary) / 'Kursmaterialien'), client_id='campus')
        settings.save_source(source)
        state = data_dir() / 'sources' / source.id
        courses = [{'id': 'crs-1', 'name': 'Programmierung und Softwareentwicklung [Vorlesung]', 'url': source.url + '/go/crs/1'},
                   {'id': 'crs-2', 'name': 'Logik und Diskrete Strukturen [Vorlesung]', 'url': source.url + '/go/crs/2'}]
        write_json(state / 'courses.json', courses)
        files = [
            ('PSE/Folien/03 Datenrepräsentation.pdf', 'crs-1', 8_500_000, 'updated'),
            ('PSE/Übungen/Aufgabenblatt 02.pdf', 'crs-1', 240_000, 'added'),
            ('LDS/Vorlesungsskript.pdf', 'crs-2', 2_450_000, ''),
            ('LDS/Übungen/Aufgabenblatt 02.pdf', 'crs-2', 187_000, ''),
        ]
        entries = {}
        for index, (path, course, size, change) in enumerate(files):
            entry = {'path': path, 'logical': course + '/' + '/'.join(path.split('/')[1:]), 'target_stat': [size],
                     'course_id': course, 'course_name': next(c['name'] for c in courses if c['id'] == course)}
            if change:
                entry.update(changed_at=time.time() - index * 600, change=change)
            entries[f'file:{index}'] = entry
        entries['generated:crs-1/Description.html'] = {'path': 'Course info/PSE/Description.html', 'course_id': 'crs-1', 'target_stat': [600]}
        write_json(state / 'manifest.json', {'schema': 1, 'files': entries})
        success = {'scope': source_scope(source), 'state': 'Up to date', 'finished': time.time(), 'result': {'files': 5, 'counts': {'added': 1, 'updated': 1, 'unchanged': 3},
                                                                                 'material_counts': {'added': 1, 'updated': 1, 'unchanged': 2}}}
        for mode in ('light', 'dark'):
            app.theme.set_mode(mode)
            write_json(state / 'status.json', success)
            window = MainWindow()
            capture(window, 'library-' + mode)
            window.workspace_tabs.setCurrentIndex(1)
            capture(window, 'all-materials-' + mode)
            window.workspace_tabs.setCurrentIndex(0)
            window.resize(820, 560)
            capture(window, 'compact-' + mode)
            window.resize(980, 700)
            window.library_view.setCurrentIndex(window.library_view.findData('recent'))
            capture(window, 'recent-' + mode)
            window.library_view.setCurrentIndex(window.library_view.findData('materials'))
            window.file_search.setText('missing search')
            capture(window, 'no-results-' + mode)
            window.clear_file_filters()
            for name, status in [
                ('first-sync', {}),
                ('login', {'state': 'Sign in again', 'login_required': True}),
                ('error', {'state': 'Needs attention', 'message': 'OSError: sync could not complete. Existing files were retained.'}),
                ('partial', {'state': 'Completed with warnings', 'finished': time.time(), 'result': {'files': 5, 'unavailable': 2, 'unavailable_items': ['PSE/Folien/Beispiel.pdf', 'LDS/Literatur/Übersicht.pdf'], 'counts': {'conflict': 1}, 'skipped': {'forum': 3, 'test': 2, 'groups without membership': 1}}}),
            ]:
                write_json(state / 'status.json', status)
                window.refresh()
                capture(window, name + '-' + mode)
                if name == 'partial':
                    report = SyncReportDialog(status, 'Prüfe die Kursmaterialien …', window)
                    capture(report, 'report-' + mode)
                    report.close()
            for name, run_state in [('running', 'running'), ('paused', 'paused'), ('stopping', 'stopping')]:
                window.run_info = {'state': run_state}
                window.progress_message = 'Prüfe Programmierung und Softwareentwicklung / Material (Folien)'
                window.show_progress(window.progress_message)
                window.refresh_controls()
                capture(window, name + '-' + mode)
            window.run_info = None
            window.refresh_controls()
            window.close()
            setup = SourceDialog(settings, source)
            for step in range(3):
                setup.stack.setCurrentIndex(step)
                setup.update_step()
                capture(setup, f'setup-{step + 1}-{mode}')
            setup.close()
            preferences = SettingsDialog(settings)
            preferences.tabs.setCurrentIndex(1)
            preferences.enabled.setChecked(True)
            preferences.schedule_mode.setCurrentIndex(preferences.schedule_mode.findData('weekly'))
            preferences.week_plan.add_time(0, '09:00')
            preferences.week_plan.add_time(0, '15:00')
            preferences.week_plan.copy_day(0, range(5))
            preferences.week_plan.add_time(5, '11:00')
            capture(preferences, 'schedule-' + mode)
            preferences.resize(520, 640)
            capture(preferences, 'weekly-compact-' + mode)
            preferences.close()
            app.theme.set_mode(mode)
            mapping = FolderMappingDialog(source, settings)
            mapping.tree.setCurrentItem(mapping.tree.topLevelItem(0))
            capture(mapping, 'mapping-' + mode)
            mapping.close()
        settings.value['language'] = 'en'
        settings.save()
        for mode in ('light', 'dark'):
            app.theme.set_mode(mode)
            write_json(state / 'status.json', success)
            window = MainWindow()
            window.resize(820, 560)
            capture(window, 'english-compact-' + mode)
            window.close()
        for mode in ('light', 'dark'):
            app.theme.set_mode(mode)
            draft = SourceDialog(settings)
            draft.url.setText(source.url)
            for step in range(3):
                draft.stack.setCurrentIndex(step)
                draft.update_step()
                capture(draft, f'new-university-{step+1}-{mode}')
            draft.close()
            app.theme.set_mode(mode)
            help_window = HelpDialog()
            capture(help_window, 'help-' + mode)
            help_window.close()
            app.theme.set_mode(mode)
            preferences = SettingsDialog(settings)
            capture(preferences, 'general-' + mode)
            preferences.tabs.setCurrentIndex(1)
            preferences.enabled.setChecked(True)
            preferences.schedule_mode.setCurrentIndex(1)
            capture(preferences, 'empty-times-' + mode)
            preferences.close()
            app.theme.set_mode(mode)
            window = MainWindow()
            window.filter_files()
            capture(window, 'inline-filters-' + mode)
            window.close()
        # Shared-library and recovery scenarios use synthetic accounts only.
        second = Source('Hochschule der Medien', 'https://second.example.edu', str(Path(temporary) / 'HdM'), client_id='fixture')
        settings.save_source(second)
        second_state = data_dir() / 'sources' / second.id
        write_json(second_state / 'courses.json', [{'id': 'crs-1', 'name': 'Medieninformatik [Übung]', 'url': second.url + '/go/crs/1'}])
        many = {f'file:{i}': {'path': f'Medieninformatik/Woche {i // 4 + 1}/Material {i:02}.{ext}',
                'course_id': 'crs-1', 'course_name': 'Medieninformatik [Übung]',
                'logical': f'crs-1/Woche {i // 4 + 1}/Material {i:02}.{ext}', 'target_stat': [1024 * (i + 1)]}
                for i, ext in enumerate(['pdf', 'zip', 'png', 'java', 'xlsx', 'mp4', 'docx', 'txt'] * 5)}
        write_json(second_state / 'manifest.json', {'files': many})
        second_success = {'state': 'Up to date', 'scope': source_scope(second),
            'finished': time.time(), 'result': {'counts': {'unchanged': 40}}}
        write_json(second_state / 'status.json', second_success)
        settings.value['language'] = 'de'
        settings.save()
        for mode in ('light', 'dark'):
            app.theme.set_mode(mode)
            write_json(second_state / 'status.json', second_success)
            window = MainWindow()
            window.sources.select_scope()
            for width, height in [(820, 560), (980, 700), (1280, 800)]:
                window.resize(width, height)
                capture(window, f'global-{width}-{mode}')
                window.workspace_tabs.setCurrentIndex(1)
                capture(window, f'materials-{width}-{mode}')
                window.workspace_tabs.setCurrentIndex(0)
            window.resize(980, 700)
            window.sources.select_scope(second.id, 'crs-1')
            capture(window, 'course-' + mode)
            window.filter_files()
            capture(window, 'course-filters-' + mode)
            window.filter_panel.hide()
            for name, failure in [
                ('signin', {'state': 'Needs attention', 'message': 'Sign-in expired or was rejected by ILIAS.'}),
                ('network', {'state': 'Needs attention', 'failure_kind': 'network'}),
                ('server', {'state': 'Needs attention', 'server_deferred': True, 'server_retry_at': time.time() + 1800}),
            ]:
                write_json(second_state / 'status.json', failure)
                window.refresh()
                capture(window, 'recovery-' + name + '-' + mode)
                window.report()
                capture(window, 'recovery-' + name + '-expanded-' + mode)
                window.resize(820, 560)
                capture(window, 'recovery-' + name + '-compact-' + mode)
                window.resize(980, 700)
                window.details_button.setChecked(False)
            window.sources.select_scope()
            capture(window, 'global-attention-' + mode)
            window.run_info = {'state': 'running', 'source': second.id, 'token': 'fixture'}
            window.refresh_controls()
            window.show_progress('Synthetic sync progress')
            capture(window, 'workspace-running-' + mode)
            window.run_info['state'] = 'paused'
            window.refresh_controls()
            window.show_progress('Synthetic sync paused')
            capture(window, 'workspace-paused-' + mode)
            window.run_info = None
            window.refresh()
            window.report()
            capture(window, 'global-attention-expanded-' + mode)
            window.close()
            recovery = SourceDialog(settings, second, signin_recovery=True)
            capture(recovery, 'renew-signin-' + mode)
            recovery.close()
        app.theme.set_mode('light')
        from PySide6.QtGui import QFont
        enlarged_font = QFont(app.font())
        enlarged_font.setPointSizeF(18)
        app.setFont(enlarged_font)
        app.theme.apply()
        window = MainWindow()
        window.resize(1024, 720)
        capture(window, 'enlarged-text-library')
        window.close()
        preferences = SettingsDialog(settings)
        preferences.tabs.setCurrentIndex(1)
        preferences.enabled.setChecked(True)
        preferences.schedule_mode.setCurrentIndex(1)
        capture(preferences, 'enlarged-text-schedule')
        preferences.close()
        (output / 'geometry.json').write_text(json.dumps(geometry, indent=2))
        print(f'{len(geometry)} states rendered and button bounds verified: {output}')


if __name__ == '__main__':
    main()
