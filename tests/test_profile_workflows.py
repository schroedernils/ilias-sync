from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ilias_sync.storage import Settings, data_dir
from ilias_sync.i18n import set_language


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    set_language('de')
    return QApplication.instance() or QApplication([])


def test_setup_adds_source_and_edits_directly_without_losing_policy(app, source):
    from ilias_sync.gui import SourceDialog
    from PySide6.QtWidgets import QDialog
    settings = Settings()
    dialog = SourceDialog(settings)
    dialog.url.setText(source.url)
    dialog.name.setText(source.name)
    dialog.client.setText(source.client_id)
    dialog.advance()
    assert dialog.stack.currentIndex() == 1
    dialog.user.setText('student')
    dialog.password.setText('test-only-password')
    dialog.advance()
    assert dialog.stack.currentIndex() == 2
    dialog.destination.setText(source.destination)
    with patch('ilias_sync.gui.store_password') as vault:
        dialog.advance()
    assert dialog.result() == QDialog.DialogCode.Accepted
    saved = settings.sources()[0]
    vault.assert_called_once_with(saved.id, 'test-only-password')
    saved.folder_rules = {'course/crs-1': str(Path(source.destination) / 'PSE')}
    saved.folder_names = {'course/crs-1': 'Vorlesung'}
    saved.targets = [source.url + '/go/fold/99']
    saved.automatic_courses = False
    saved.enabled = False
    settings.save_source(saved)
    edit = SourceDialog(settings, saved)
    edit.sections.setCurrentIndex(2)
    assert edit.stack.currentIndex() == 2
    edit.name.setText('Renamed university')
    edit.advance()
    result = settings.sources()[0]
    assert result.id == saved.id and result.folder_rules == saved.folder_rules and result.folder_names == saved.folder_names
    assert result.targets == saved.targets and not result.enabled
    edit.close()

def test_address_change_invalidates_detection_and_empty_probe_is_actionable(app, source):
    from ilias_sync.gui import SourceDialog
    from PySide6.QtCore import QTimer
    dialog = SourceDialog(Settings(), source)
    dialog.url.setText('https://new-campus.example.edu')
    dialog.address_changed()
    assert not dialog.client.text()
    assert dialog.probed_url is None and not dialog.probe_attempted
    dialog.probe_timeout = QTimer(dialog)
    dialog.probe_url = dialog.url.text()
    dialog.event_file.write_text('')
    dialog.probed()
    assert 'kein Ergebnis' in dialog.error.text()
    assert dialog.next_button.isEnabled()
    dialog.close()

def test_course_save_keeps_non_discovered_manual_links_and_allows_explicit_removal(app, source):
    from ilias_sync.gui import CoursesDialog
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialogButtonBox
    courses = [{'id':'crs-1','name':'PSE','url':source.url+'/go/crs/1'}]
    manual = source.url + '/goto.php?target=fold_99'
    source.targets = [courses[0]['url'], manual]
    source.automatic_courses = False
    settings = Settings()
    settings.save_source(source)
    dialog = CoursesDialog(courses, source, settings, None)
    assert dialog.saved_links.count() == 1
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
    assert manual in settings.sources()[0].targets
    dialog = CoursesDialog(courses, settings.sources()[0], settings, None)
    dialog.saved_links.item(0).setCheckState(Qt.CheckState.Unchecked)
    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save).click()
    assert settings.sources()[0].targets == [courses[0]['url']]

def test_profile_validation_precedes_vault_and_write_failures_restore_config(app, source, tmp_path):
    from ilias_sync.gui import SourceDialog
    from ilias_sync.profile_service import commit_profile
    settings = Settings()
    settings.save_source(source)
    other = type(source)('Other', 'https://other.example.edu', str(tmp_path/'Other'), client_id='other')
    settings.save_source(other)
    dialog = SourceDialog(settings, source)
    dialog.destination.setText(other.destination)
    dialog.password.setText('new-secret-test-only')
    with patch('ilias_sync.gui.store_password') as store, patch('ilias_sync.security.vault') as vault:
        dialog.save()
    store.assert_not_called()
    vault.assert_not_called()
    assert settings.sources()[0].destination == source.destination
    dialog.reject()
    previous = settings.path.read_bytes()
    candidate = type(source)(**{**vars(source), 'name':'Changed'})
    backend = Mock()
    backend.get_password.return_value = 'old-secret-test-only'
    stored = []
    def store(identity, password):
        stored.append(password)
        if password == 'new-secret-test-only':
            raise OSError('simulated vault failure')
    with patch('ilias_sync.security.vault', return_value=backend):
        with pytest.raises(OSError):
            commit_profile(settings, candidate, password='new-secret-test-only', store=store, import_cookies=Mock())
    assert settings.path.read_bytes() == previous
    assert stored == ['new-secret-test-only','old-secret-test-only']
    store = Mock()
    with patch.object(settings,'save',side_effect=OSError('disk failure')), patch('ilias_sync.security.vault', return_value=backend):
        with pytest.raises(OSError):
            commit_profile(settings, candidate, password='new-secret-test-only', store=store, import_cookies=Mock())
    store.assert_not_called()
    assert settings.value['sources'][0]['name'] == source.name

def test_cookie_draft_failure_keeps_original_session_and_settings(source, tmp_path):
    from ilias_sync.profile_service import commit_profile
    settings = Settings()
    source.login = 'session'
    settings.save_source(source)
    previous = settings.path.read_bytes()
    cookies = data_dir()/'sources'/source.id/'cache/.cookies'
    cookies.parent.mkdir(parents=True)
    cookies.write_bytes(b'old-session-test-only')
    def invalid_import(*_):
        raise ValueError('No unexpired cookies for this ILIAS host were found.')
    with pytest.raises(ValueError):
        commit_profile(settings, source, session=str(tmp_path/'test.txt'), store=Mock(), import_cookies=invalid_import)
    assert settings.path.read_bytes() == previous
    assert cookies.read_bytes() == b'old-session-test-only'


def test_rollback_continues_when_config_restore_itself_fails(source):
    from ilias_sync.profile_service import commit_profile
    settings=Settings()
    settings.save_source(source)
    source.username='new-user'
    backend=Mock()
    backend.get_password.return_value='old-secret'
    state={'password':'old-secret'}
    def store(_,secret):
        state['password']=secret
        if secret=='new-secret':
            raise OSError('injected after vault mutation')
    with patch('ilias_sync.profile_service.atomic_write',side_effect=OSError('injected config rollback failure')), patch('ilias_sync.security.vault',return_value=backend):
        with pytest.raises(RuntimeError,match='fully restored'):
            commit_profile(settings,source,password='new-secret',store=store,import_cookies=Mock())
    assert state['password']=='old-secret'
    assert settings.value['sources'][0]['username']=='test-user'
