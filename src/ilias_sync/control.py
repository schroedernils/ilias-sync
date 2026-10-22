"""Per-run cooperative control. Only an active worker watches commands; idle workers exit."""
import asyncio
import contextlib
import contextvars
import os
import time
from uuid import uuid4

import psutil

from .storage import data_dir, read_json, write_json

CURRENT = contextvars.ContextVar('sync_control', default=None)


def active_run():
    row = read_json(data_dir() / 'active-run.json', {})
    if not row:
        return None
    try:
        process = psutil.Process(row['pid'])
        if abs(process.create_time() - row['created']) > 0.1 or not process.is_running():
            return None
        return row
    except (psutil.Error, KeyError):
        return None


def send_command(run, action):
    if action not in {'pause', 'resume', 'stop'}:
        raise ValueError('Unknown synchronization action')
    write_json(data_dir() / 'run-command.json', {'token': run['token'], 'action': action})


async def checkpoint():
    control = CURRENT.get()
    if control:
        await control.gate.wait()
    # Yield between publications so stop is acted on only at safe boundaries.
    await asyncio.sleep(0)


class RunControl:
    def __init__(self, source, emit):
        self.source = source
        self.emit = emit
        self.gate = asyncio.Event()
        self.gate.set()
        self.row = {'token': str(uuid4()), 'source': source.id, 'pid': os.getpid(),
                    'created': psutil.Process().create_time(), 'state': 'running'}
        self.stopped = False
        self.active_seconds = 0
        self.timed_out = False

    def save(self, state):
        self.row['state'] = state
        write_json(data_dir() / 'active-run.json', self.row)
        self.emit({'event': 'control', 'state': state})

    async def watch(self, task):
        last = time.monotonic()
        while not task.done():
            await asyncio.sleep(0.25)
            now = time.monotonic()
            if self.gate.is_set():
                self.active_seconds += now - last
            last = now
            if self.active_seconds > self.deadline:
                self.timed_out = True
                task.cancel()
                return
            command = read_json(data_dir() / 'run-command.json', {})
            if command.get('token') != self.row['token']:
                continue
            action = command.get('action')
            if action == 'stop':
                self.stopped = True
                self.save('stopping')
                task.cancel()
                return
            if action == 'pause' and self.gate.is_set():
                self.gate.clear()
                self.save('paused')
            elif action == 'resume' and not self.gate.is_set():
                self.gate.set()
                self.save('running')

    async def run(self, operation, deadline=5400):
        self.deadline = deadline
        token = CURRENT.set(self)
        task = asyncio.create_task(operation)
        monitor = asyncio.create_task(self.watch(task))
        self.save('running')
        try:
            return await task
        except asyncio.CancelledError:
            if self.timed_out:
                raise TimeoutError("Synchronization exceeded its active time limit") from None
            raise
        finally:
            monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor
            CURRENT.reset(token)
            self.row['state'] = 'stopped' if self.stopped else 'finished'
            write_json(data_dir() / 'active-run.json', self.row)
