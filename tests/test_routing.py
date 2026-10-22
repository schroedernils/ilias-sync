import pytest

from ilias_sync.routing import route_file
from ilias_sync.storage import Archive, Settings, data_dir


def test_file_rule_beats_folder_and_course_and_keeps_extension(source, tmp_path):
    source.folder_rules = {'course/crs-1':str(tmp_path/'PSE'),
                           'path/crs-1/Folien':str(tmp_path/'Skripte'),
                           'file/file:7':str(tmp_path/'Intro')}
    args = (source, 'file:7', 'crs-1', 'crs-1/Folien/01 Intro.pdf', 'Course/Folien/01 Intro.pdf')
    root, relative, fingerprint = route_file(*args)
    assert root == tmp_path/'Intro'
    assert relative == '01 Intro.pdf'
    assert fingerprint
    del source.folder_rules['file/file:7']
    root, relative, _ = route_file(*args)
    assert root == tmp_path/'Skripte'
    assert relative == '01 Intro.pdf'
    del source.folder_rules['path/crs-1/Folien']
    root, relative, _ = route_file(*args)
    assert root == tmp_path/'PSE'
    assert relative == 'Folien/01 Intro.pdf'


def test_rerouting_keeps_annotations_and_publishes_to_new_folder(tmp_path):
    raw = tmp_path/'raw.pdf'
    raw.write_bytes(b'%PDF-1.4 remote')
    archive = Archive(tmp_path/'state', tmp_path/'default')
    archive.publish('file:7', raw, 'Course/Intro.pdf')
    old = tmp_path/'default/Course/Intro.pdf'
    old.write_bytes(b'MY NOTES')
    destination = tmp_path/'Semester/PSE'
    assert archive.publish('file:7', raw, 'Intro.pdf', destination=destination, route='course-rule') == 'added'
    assert old.read_bytes() == b'MY NOTES'
    assert (destination/'Intro.pdf').read_bytes() == raw.read_bytes()
    assert archive.publish('file:7', raw, 'Intro.pdf', destination=destination, route='course-rule') == 'unchanged'
    entry = archive.manifest['files']['file:7']
    assert entry['root'] == str(destination)
    assert entry['prior_locations'][0]['path'] == 'Course/Intro.pdf'


def test_rule_update_does_not_adopt_identical_unmanaged_target(tmp_path):
    raw = tmp_path/'raw.pdf'
    raw.write_bytes(b'%PDF-1.4 remote')
    archive = Archive(tmp_path/'state', tmp_path/'default')
    archive.publish('file:7', raw, 'Intro.pdf')
    destination = tmp_path/'new'
    destination.mkdir()
    unmanaged = destination/'Intro.pdf'
    unmanaged.write_bytes(raw.read_bytes())
    assert archive.publish('file:7', raw, 'Intro.pdf', destination=destination, route='new-rule') == 'conflict'
    raw.write_bytes(b'%PDF-1.4 changed')
    archive.publish('file:7', raw, 'Intro.pdf', destination=destination, route='new-rule')
    assert unmanaged.read_bytes() == b'%PDF-1.4 remote'


def test_rules_survive_profile_edits_and_reject_application_state(source):
    source.folder_rules = {'course/crs-1':source.destination+'/PSE'}
    settings = Settings()
    settings.save_source(source)
    assert settings.sources()[0].folder_rules == source.folder_rules
    source.folder_rules = {'course/crs-1':str(data_dir()/'private')}
    with pytest.raises(ValueError):
        source.validate()


def test_membership_navigation_does_not_follow_actions_or_news():
    from bs4 import BeautifulSoup
    from ilias_sync.engine import membership_navigation
    html = '''<a href="/ilias.php?baseClass=ilMembershipOverviewGUI">Courses</a>
    <a href="/ilias.php?cmdClass=ilMembershipBlockGUI&amp;cmd=show&amp;offset=10">Next</a>
    <a href="/ilias.php?cmdClass=ilMembershipBlockGUI&amp;cmd=addToDesk&amp;offset=10">Add</a>
    <a href="/ilias.php?cmdClass=ilPDNewsBlockGUI&amp;cmd=show&amp;page=2">News</a>
    <a href="https://other.example/ilias.php?baseClass=ilMembershipOverviewGUI">Other</a>'''
    urls = membership_navigation(BeautifulSoup(html,'html.parser'),'https://ilias.example.edu')
    assert len(urls) == 2
    assert all('addToDesk' not in u for u in urls)


async def test_discovery_follows_membership_overview_and_pagination(source, monkeypatch):
    from test_engine import FixtureSession, Response, page
    from ilias_sync.engine import synchronize

    class Session(FixtureSession):
        def get(self, url, **kwargs):
            if 'Dashboard' in str(url):
                body = page('<a href="/go/crs/1">First</a><a href="/ilias.php?baseClass=ilMembershipOverviewGUI">All courses</a>')
            elif 'offset=10' in str(url):
                body = page('<a href="/go/crs/3">Third</a>')
            else:
                body = page('<a href="/go/crs/2">Second</a><a href="/ilias.php?cmdClass=ilMembershipBlockGUI&amp;cmd=show&amp;offset=10">Next</a>')
            return Response(url, body)
    monkeypatch.setattr('aiohttp.ClientSession', Session)
    result = await synchronize(source, discover=True)
    assert {r['id'] for r in result['courses']} == {'crs-1','crs-2','crs-3'}
