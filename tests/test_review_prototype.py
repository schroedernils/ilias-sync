from pathlib import Path
from unittest.mock import patch

from experiments.review_state import ReviewState, local_read_check


def item(digest='same', path='Course/File.pdf', generated=False):
    return {'digest':digest,'path':path,'generated':generated,'course':'Course'}


def test_baseline_unchanged_route_copy_and_repair_do_not_create_events(tmp_path):
    ledger = ReviewState(tmp_path/'review.sqlite')
    ledger.baseline({'file:1':item()})
    ledger.observe('file:1',item())
    ledger.observe('file:1',item(path='Renamed/File.pdf'))
    ledger.observe('file:1',item(path='Restored/File.pdf'))
    ledger.observe('generated:1',item('new generated content',generated=True))
    assert ledger.boundary() == 0 and ledger.items(since_review=True) == []
    ledger.close()


def test_checkpoint_keeps_equal_time_updates_during_review_and_can_undo_after_restart(tmp_path):
    path = tmp_path/'review.sqlite'
    ledger = ReviewState(path)
    ledger.baseline({'file:1':item()})
    ledger.observe('file:1',item('revision-2'),stamp=100)
    captured = ledger.boundary()
    ledger.observe('file:2',item('revision-2'),stamp=100)
    ledger.acknowledge(captured)
    assert [row['identity'] for row in ledger.items(since_review=True)] == ['file:2']
    ledger.close()
    ledger = ReviewState(path)
    assert [row['identity'] for row in ledger.items(since_review=True)] == ['file:2']
    ledger.undo()
    assert {row['identity'] for row in ledger.items(since_review=True)} == {'file:1','file:2'}
    ledger.observe('file:3',item('revision-2'),stamp=1)  # wall-clock rollback cannot hide a new event
    assert len(ledger.items(since_review=True)) == 3
    assert len(ledger.items(since_time=50)) == 2
    ledger.close()


def test_same_bytes_with_distinct_object_ids_remain_distinct(tmp_path):
    ledger = ReviewState(tmp_path/'review.sqlite')
    ledger.baseline({'file:1':item()})
    ledger.observe('file:2',item())
    assert ledger.items(since_review=True)[0]['identity'] == 'file:2'
    assert len(ledger.items()) == 2
    ledger.close()


def test_local_check_reads_whole_file_and_separates_links_missing_and_roots(tmp_path):
    file = tmp_path/'material.bin'
    contents = b'fixture'*(1024*1024)
    file.write_bytes(contents)
    assert local_read_check(file,local_root=tmp_path)['state'] == 'local_read_passed'
    assert not local_read_check(file,local_root=tmp_path)['offline_certified']
    assert file.read_bytes() == contents
    assert local_read_check(tmp_path/'missing.pdf',local_root=tmp_path)['state'] == 'missing'
    assert local_read_check(tmp_path/'material.url',local_root=tmp_path)['state'] == 'external_link'
    assert local_read_check(tmp_path/'unmounted/file.pdf',local_root=tmp_path/'unmounted')['state'] == 'root_unavailable'


def test_cloud_and_parent_symlinks_are_not_opened_or_hydrated(tmp_path):
    cloud = tmp_path/'CloudStorage'
    cloud.mkdir()
    placeholder = cloud/'Document.pdf'
    placeholder.write_bytes(b'fixture')
    with patch.object(Path,'open',side_effect=AssertionError('Must not open cloud contents')):
        assert local_read_check(placeholder,local_root=tmp_path)['state'] == 'residency_unverified'
    other = tmp_path/'other'
    other.mkdir()
    (other/'real.pdf').write_bytes(b'fixture')
    link = tmp_path/'selected'/'linked'
    link.parent.mkdir()
    link.symlink_to(other,target_is_directory=True)
    with patch.object(Path,'open',side_effect=AssertionError('Must not follow a parent symlink')):
        assert local_read_check(link/'real.pdf',local_root=link.parent)['state'] == 'residency_unverified'


def test_unreadable_file_has_no_success_claim(tmp_path):
    file = tmp_path/'file.pdf'
    file.write_bytes(b'fixture')
    with patch.object(Path,'open',side_effect=PermissionError('synthetic permission denial')):
        result = local_read_check(file,local_root=tmp_path)
    assert result['state'] == 'unreadable' and not result['offline_certified']


def test_selected_root_and_its_ancestors_cannot_escape_through_symlinks(tmp_path):
    actual = tmp_path/'actual'
    actual.mkdir()
    (actual/'file.pdf').write_bytes(b'fixture')
    alias = tmp_path/'alias'
    alias.symlink_to(actual, target_is_directory=True)
    nested = actual/'nested'
    nested.mkdir()
    (nested/'file.pdf').write_bytes(b'fixture')
    with patch.object(Path,'open',side_effect=AssertionError('Must not open through a root symlink')):
        assert local_read_check(alias/'file.pdf',local_root=alias)['state'] == 'residency_unverified'
        assert local_read_check(alias/'nested/file.pdf',local_root=alias/'nested')['state'] == 'residency_unverified'
        assert local_read_check(actual/'../actual/file.pdf',local_root=nested)['state'] == 'outside_local_fixture'
