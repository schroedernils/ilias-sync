"""Bound actual requests, including redirects and streamed bodies, per host."""
from __future__ import annotations

import asyncio
from collections import Counter
from datetime import timezone
from email.utils import parsedate_to_datetime
import os
import time
import weakref

import aiohttp

from .control import checkpoint
from .storage import data_dir, read_json, write_json

DEFAULT_HTTP_LIMIT = 8
MAX_INLINE_WAIT = 30
_budgets = weakref.WeakKeyDictionary()


class HostDeferred(RuntimeError):
    def __init__(self, retry_at):
        super().__init__('The server asked to retry later. Automatic sync will respect the requested time.')
        self.retry_at = retry_at


def configured_limit():
    value = int(os.environ.get('ILIAS_SYNC_HTTP_LIMIT', DEFAULT_HTTP_LIMIT))
    if not 1 <= value <= DEFAULT_HTTP_LIMIT:
        raise ValueError('ILIAS_SYNC_HTTP_LIMIT must be between 1 and 8.')
    return value


def retry_delay(value, failures, *, now=None):
    now = time.time() if now is None else now
    fallback = min(30, 0.25 * 2 ** min(failures, 7))
    if value:
        try:
            if str(value).strip().isdigit():
                return max(0.1, int(value))
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return max(0.1, date.timestamp() - now)
        except (ValueError, TypeError, OverflowError):
            pass
    return fallback


class GuardedResponse(aiohttp.ClientResponse):
    """An early close/cancel releases the same lease as a completely read body."""
    _http_release = None

    def release(self):
        try:
            return super().release()
        finally:
            if self._http_release:
                self._http_release()

    def close(self):
        try:
            return super().close()
        finally:
            if self._http_release:
                self._http_release()


class HostBudget:
    def __init__(self, *, limit=None, path=None):
        self.limit = configured_limit() if limit is None else limit
        self.path = path or data_dir()/'http-cooldowns.json'
        self.cooldowns = read_json(self.path, {})
        self.hosts = {}

    def host(self, hostname):
        return self.hosts.setdefault(hostname, {'gate':asyncio.Semaphore(self.limit), 'active':0,
                                               'peak':0, 'throttles':0, 'circuit':False})

    def meter(self):
        return RequestMeter(self)

    async def wait(self, hostname):
        while True:
            await checkpoint()
            host = self.host(hostname)
            retry_at = self.cooldowns.get(hostname, 0)
            delay = retry_at - time.time()
            if host['circuit'] or delay > MAX_INLINE_WAIT:
                raise HostDeferred(max(retry_at, time.time() + 30))
            if delay <= 0:
                return
            await asyncio.sleep(min(delay, 0.25))

    def throttle(self, hostname, value):
        host = self.host(hostname)
        host['throttles'] += 1
        host['circuit'] = host['throttles'] >= 3
        delay = retry_delay(value, host['throttles'])
        if host['circuit']:
            delay = max(delay, 30)
        self.cooldowns[hostname] = max(self.cooldowns.get(hostname, 0), time.time() + delay)
        # A new one-shot process must also honor a server's long Retry-After.
        now = time.time()
        self.cooldowns = {host:stamp for host, stamp in self.cooldowns.items() if stamp > now}
        write_json(self.path, self.cooldowns)


def shared_budget():
    """Share limits across sessions/sources in one event loop without owning it."""
    loop = asyncio.get_running_loop()
    roots = _budgets.setdefault(loop, {})
    key = str(data_dir())
    previous = roots.get(key)
    budget = previous() if previous else None
    if budget is None:
        budget = HostBudget()
        roots[key] = weakref.ref(budget)
    return budget


class RequestMeter:
    def __init__(self, budget):
        self.budget = budget
        self.hosts = {}

    def row(self, hostname):
        return self.hosts.setdefault(hostname, {'requests':0, 'attempts':0, 'active':0, 'peak':0,
                                              'statuses':Counter(), 'wait_seconds':0.0})

    @staticmethod
    def lease(host, row):
        released = False
        def release():
            nonlocal released
            if not released:
                released = True
                row['active'] -= 1
                host['active'] -= 1
                host['gate'].release()
        return release

    async def middleware(self, request, handler):
        hostname = request.url.host.lower()
        host = self.budget.host(hostname)
        row = self.row(hostname)
        for attempt in range(3):
            start = time.monotonic()
            await self.budget.wait(hostname)
            await host['gate'].acquire()
            try:
                # Another active request may have received Retry-After while
                # this one was queued. Never send before rechecking the host.
                await self.budget.wait(hostname)
            except BaseException:
                host['gate'].release()
                raise
            row['wait_seconds'] += time.monotonic() - start
            row['attempts'] += 1
            row['active'] += 1
            host['active'] += 1
            row['peak'] = max(row['peak'], row['active'])
            host['peak'] = max(host['peak'], host['active'])
            release = self.lease(host, row)

            try:
                response = await handler(request)
            except BaseException:
                release()
                raise
            response._http_release = release
            response.content.on_eof(release)
            row['statuses'][str(response.status)] += 1
            if response.status in (429, 503):
                try:
                    self.budget.throttle(hostname, response.headers.get('Retry-After'))
                except BaseException:
                    response.close()
                    raise
                if request.method in {'GET', 'HEAD'} and attempt < 2:
                    response.close()
                    continue
            elif response.status < 400:
                host['throttles'] = 0
            return response
        raise AssertionError('Unreachable retry state')

    def session_options(self):
        trace = aiohttp.TraceConfig()
        async def sent(session, context, params):
            self.row(params.url.host.lower())['requests'] += 1
        trace.on_request_headers_sent.append(sent)
        return {'middlewares':(self.middleware,), 'response_class':GuardedResponse, 'trace_configs':[trace]}

    def snapshot(self):
        return {'limit_per_host':self.budget.limit,
                'retry_at':max((self.budget.cooldowns.get(host, 0) for host in self.hosts), default=0),
                'hosts':{host:{'requests':row['requests'], 'attempts':row['attempts'], 'peak_in_flight':row['peak'],
                               'shared_host_peak':self.budget.host(host)['peak'],
                               'active':row['active'], 'statuses':dict(row['statuses']),
                               'wait_seconds':round(row['wait_seconds'], 3)}
                         for host, row in self.hosts.items()}}
