import asyncio
from types import SimpleNamespace

import pytest

from ilias_sync.control import RunControl, active_run, checkpoint, send_command
from ilias_sync.storage import Settings, data_dir, read_json, write_json


async def until(predicate):
    async with asyncio.timeout(4):
        while not predicate():
            await asyncio.sleep(0.02)


async def test_pause_resume_and_stop_at_safe_checkpoint(source):
    count = []
    control = RunControl(source, lambda event: None)

    async def operation():
        while True:
            await checkpoint()
            count.append(1)
            await asyncio.sleep(0.01)
    task = asyncio.create_task(control.run(operation()))
    await until(lambda: len(count) > 2)
    assert active_run()['source'] == source.id
    send_command(control.row, 'pause')
    await until(lambda: not control.gate.is_set())
    paused = len(count)
    await asyncio.sleep(0.15)
    assert len(count) == paused
    send_command(control.row, 'resume')
    await until(lambda: len(count) > paused)
    send_command(control.row, 'pause')
    await until(lambda: not control.gate.is_set())
    send_command(control.row, 'stop')
    with pytest.raises(asyncio.CancelledError):
        await task
    assert read_json(data_dir() / 'active-run.json', {})['state'] == 'stopped'


async def test_commands_are_scoped_to_current_run(source):
    control = RunControl(source, lambda event: None)
    released = asyncio.Event()

    async def operation():
        await asyncio.sleep(0.4)
        await checkpoint()
        released.set()
    task = asyncio.create_task(control.run(operation()))
    await asyncio.sleep(0.02)
    write_json(data_dir() / 'run-command.json', {'token':'old-run', 'action':'stop'})
    await task
    assert released.is_set()
    assert not control.stopped


async def test_pause_during_checkpoint_yield_blocks_the_next_operation(source):
    from ilias_sync.control import CURRENT
    control = RunControl(source, lambda event: None)
    token = CURRENT.set(control)
    try:
        passed = asyncio.Event()

        async def operation():
            await checkpoint()
            passed.set()

        task = asyncio.create_task(operation())
        await asyncio.sleep(0)
        control.gate.clear()
        await asyncio.sleep(0)
        assert not passed.is_set()
        control.gate.set()
        await task
        assert passed.is_set()
    finally:
        CURRENT.reset(token)


async def test_worker_stop_preserves_files_and_is_not_a_login_failure(source, monkeypatch):
    from pathlib import Path
    from ilias_sync.__main__ import worker
    settings = Settings()
    settings.save_source(source)
    folder = Path(source.destination)
    folder.mkdir()
    original = folder / 'lecture.pdf'
    original.write_bytes(b'%PDF-1.4 existing valid file')
    entered = asyncio.Event()

    async def operation(*args, **kwargs):
        entered.set()
        await asyncio.sleep(60)
    monkeypatch.setattr('ilias_sync.engine.synchronize', operation)
    task = asyncio.create_task(worker(SimpleNamespace(probe=None, profile=source.id, sync=True, discover=False)))
    await entered.wait()
    send_command(active_run(), 'stop')
    assert await task == 0
    assert original.read_bytes() == b'%PDF-1.4 existing valid file'
    status = read_json(data_dir() / 'sources' / source.id / 'status.json', {})
    assert status['state'] == 'Stopped'
    assert not status['login_required']
    assert status.get('failures',0) == 0


async def test_pause_time_is_excluded_from_job_deadline(source):
    control = RunControl(source, lambda event: None)

    async def operation():
        while True:
            await checkpoint()
            await asyncio.sleep(0.01)
    task = asyncio.create_task(control.run(operation(), deadline=0.55))
    await until(lambda: active_run() is not None)
    send_command(control.row, 'pause')
    await until(lambda: not control.gate.is_set())
    await asyncio.sleep(0.7)
    assert not task.done()
    send_command(control.row, 'resume')
    with pytest.raises(TimeoutError):
        await task
