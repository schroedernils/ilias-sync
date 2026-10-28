"""Loopback-only request, streaming, retry and cross-session acceptance tests."""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from email.utils import format_datetime
import time

import aiohttp
from aiohttp import web
import pytest

from ilias_sync.http_policy import HostBudget, HostDeferred, configured_limit, retry_delay


@asynccontextmanager
async def server(handler, *, ssl_context=None):
    app = web.Application()
    app.router.add_route('*', '/{path:.*}', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0, ssl_context=ssl_context)
    await site.start()
    port = runner.addresses[0][1]
    try:
        yield f'{"https" if ssl_context else "http"}://localhost:{port}'
    finally:
        await runner.cleanup()


async def test_limit_counts_redirects_and_stream_bodies_across_sessions(tmp_path):
    active = peak = received = 0
    async def handler(request):
        nonlocal active, peak, received
        received += 1
        if request.path == '/redirect':
            raise web.HTTPFound('/body')
        active += 1
        peak = max(peak, active)
        try:
            response = web.StreamResponse()
            await response.prepare(request)
            await response.write(b'first')
            await asyncio.sleep(0.015)
            await response.write(b'last')
            return response
        finally:
            active -= 1
    budget = HostBudget(limit=3, path=tmp_path/'cooldowns.json')
    meters = [budget.meter(), budget.meter()]
    async with server(handler) as base:
        async with aiohttp.ClientSession(**meters[0].session_options()) as one, aiohttp.ClientSession(**meters[1].session_options()) as two:
            async def read(client):
                async with client.get(base+'/redirect') as response:
                    return await response.read()
            data = await asyncio.gather(*(read((one, two)[i%2]) for i in range(18)))
    assert all(body == b'firstlast' for body in data)
    assert 1 < peak <= 3
    snapshots = [meter.snapshot()['hosts']['localhost'] for meter in meters]
    assert sum(row['requests'] for row in snapshots) == received == 36
    assert sum(row['statuses']['302'] for row in snapshots) == 18
    assert all(row['active'] == 0 and row['shared_host_peak'] <= 3 for row in snapshots)


async def test_throttle_retries_get_but_never_replays_post(tmp_path):
    seen = []
    async def handler(request):
        seen.append(request.method)
        if request.method == 'POST':
            return web.Response(status=503, headers={'Retry-After':'0'})
        failures = sum(method == 'GET' for method in seen)
        return web.Response(status=(429 if failures == 1 else 503 if failures == 2 else 200),
                            headers={'Retry-After':'0'}, text='result')
    meter = HostBudget(limit=2, path=tmp_path/'cooldowns.json').meter()
    async with server(handler) as base, aiohttp.ClientSession(**meter.session_options()) as client:
        async with client.get(base) as response:
            assert response.status == 200 and await response.text() == 'result'
        async with client.post(base, data={'test':'synthetic-only'}) as response:
            assert response.status == 503
    assert seen == ['GET', 'GET', 'GET', 'POST']
    assert meter.snapshot()['hosts']['localhost']['active'] == 0


async def test_long_retry_after_survives_new_budget_without_another_request(tmp_path):
    requests = 0
    async def handler(request):
        nonlocal requests
        requests += 1
        return web.Response(status=429, headers={'Retry-After':'3600'})
    path = tmp_path/'cooldowns.json'
    async with server(handler) as base:
        for _ in range(2):
            meter = HostBudget(path=path).meter()
            async with aiohttp.ClientSession(**meter.session_options()) as client:
                with pytest.raises(HostDeferred) as error:
                    await client.get(base)
                assert error.value.retry_at >= time.time()+3500
            assert meter.snapshot()['hosts']['localhost']['active'] == 0
    assert requests == 1


async def test_retry_storm_opens_shared_circuit_and_cancel_frees_queued_requests(tmp_path):
    received = 0
    async def overloaded(request):
        nonlocal received
        received += 1
        await asyncio.sleep(0.01)
        return web.Response(status=503, headers={'Retry-After':'0'})
    budget = HostBudget(limit=3, path=tmp_path/'cooldowns.json')
    meter = budget.meter()
    async with server(overloaded) as base, aiohttp.ClientSession(**meter.session_options()) as client:
        results = await asyncio.gather(*(client.get(base) for _ in range(30)), return_exceptions=True)
        for result in results:
            if isinstance(result, aiohttp.ClientResponse):
                result.close()
        assert any(isinstance(result, HostDeferred) for result in results)
    assert received <= 6
    assert budget.host('localhost')['active'] == 0

    started = asyncio.Event()
    stop = asyncio.Event()
    async def streaming(request):
        response = web.StreamResponse()
        await response.prepare(request)
        await response.write(b'first')
        started.set()
        await stop.wait()
        return response
    meter = HostBudget(limit=1, path=tmp_path/'other.json').meter()
    async with server(streaming) as base, aiohttp.ClientSession(**meter.session_options()) as client:
        async def read():
            async with client.get(base) as response:
                await response.read()
        tasks = [asyncio.create_task(read()) for _ in range(10)]
        await asyncio.wait_for(started.wait(), timeout=2)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        assert meter.snapshot()['hosts']['localhost']['active'] == 0
        stop.set()


async def test_authentication_requests_are_measured_and_401_is_not_auto_retried(tmp_path):
    authenticated = False
    seen = []
    async def handler(request):
        nonlocal authenticated
        seen.append((request.method, request.path))
        if request.path == '/login':
            assert request.method == 'POST'
            authenticated = True
            return web.Response(text='ok')
        return web.Response(status=200 if authenticated else 401)
    meter = HostBudget(path=tmp_path/'cooldowns.json').meter()
    async with server(handler) as base, aiohttp.ClientSession(**meter.session_options()) as client:
        async with client.get(base+'/auth') as response:
            assert response.status == 401
        async with client.post(base+'/login', data={'credential':'fixture-only'}) as response:
            await response.read()
        async with client.get(base+'/auth') as response:
            assert response.status == 200
    assert seen == [('GET','/auth'), ('POST','/login'), ('GET','/auth')]
    assert meter.snapshot()['hosts']['localhost']['requests'] == 3


def test_retry_after_dates_and_conservative_override(monkeypatch):
    now = 10000
    date = format_datetime(datetime.fromtimestamp(now+600, timezone.utc), usegmt=True)
    assert retry_delay(date, 1, now=now) == 600
    assert retry_delay('120', 1, now=now) == 120
    assert retry_delay('invalid', 1, now=now) > 0
    monkeypatch.setenv('ILIAS_SYNC_HTTP_LIMIT','2')
    assert configured_limit() == 2
    monkeypatch.setenv('ILIAS_SYNC_HTTP_LIMIT','64')
    with pytest.raises(ValueError):
        configured_limit()


async def test_real_crawler_has_identical_coverage_at_lower_http_concurrency(source, tmp_path, monkeypatch):
    import hashlib
    import json
    import ssl
    import subprocess
    from pathlib import Path
    from ilias_sync.engine import synchronize
    from ilias_sync.storage import data_dir, read_json
    from test_engine import page, file_html
    key, certificate = tmp_path/'localhost.key', tmp_path/'localhost.crt'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
        '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost',
        '-keyout',str(key),'-out',str(certificate)], check=True, capture_output=True)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(certificate, key)
    monkeypatch.setattr('ilias_sync.engine.certifi.where', lambda: str(certificate))
    async def handler(request):
        await asyncio.sleep(0.006)
        if 'Dashboard' in request.query.get('baseClass',''):
            content = '<a href="/go/crs/1">Algorithms</a><a href="/go/crs/2">Logic</a>'
        elif request.path.startswith('/go/crs/'):
            course = int(request.path.rsplit('/',1)[1])
            content = ''.join('<div class="ilContainerListItemOuter"><img class="ilListItemIcon" src="fold.svg" alt="Ordner"/>'
                f'<div class="il_ContainerItem"><a class="il_ContainerItemTitle" href="/go/fold/{course*100+n}">Week {n}</a></div></div>' for n in range(8))
        elif request.path.startswith('/go/fold/'):
            identity = request.path.rsplit('/',1)[1]
            content = file_html().replace('ref_id=987','ref_id='+identity).replace('>Lecture<',f'>Lecture {identity}<')
        elif request.query.get('cmd') == 'sendfile':
            return web.Response(body=b'%PDF-1.4 synthetic '+request.query['ref_id'].encode(), content_type='application/pdf')
        else:
            return web.Response(status=404)
        return web.Response(body=page(content), content_type='text/html')
    results = []
    async with server(handler, ssl_context=tls) as base:
        for limit in (1, 8):
            monkeypatch.setenv('ILIAS_SYNC_HTTP_LIMIT',str(limit))
            monkeypatch.setenv('ILIAS_SYNC_DATA_DIR',str(tmp_path/f'state-{limit}'))
            source.url = base+'/ilias'
            source.destination = str(tmp_path/f'out-{limit}')
            first = await synchronize(source)
            second = await synchronize(source)
            manifest = read_json(data_dir()/'sources'/source.id/'manifest.json',{})['files']
            files = {identity:hashlib.sha256((Path(source.destination)/entry['path']).read_bytes()).hexdigest() for identity, entry in manifest.items()}
            assert first['material_counts'] == {'added':16}
            assert second['material_counts'] == {'unchanged':16}
            assert first['http']['hosts']['localhost']['requests'] > 16
            assert first['http']['hosts']['localhost']['shared_host_peak'] <= limit
            assert not first['partial'] and not second['partial']
            results.append({'limit':limit,'files':files,'first':first,'unchanged':second})
    assert results[0]['files'] == results[1]['files']
    assert results[0]['first']['course_scope'] == results[1]['first']['course_scope']
    assert results[0]['first']['check_issues'] == results[1]['first']['check_issues'] == []
    output = __import__('os').environ.get('ILIAS_SYNC_HTTP_BENCHMARK')
    if output:
        Path(output).write_text(json.dumps(results,indent=2))


async def test_worker_defers_on_battery_without_requests_and_runs_sources_sequentially(source, tmp_path, monkeypatch):
    from dataclasses import replace
    from types import SimpleNamespace
    from uuid import uuid4
    from unittest.mock import AsyncMock
    from ilias_sync.__main__ import worker
    from ilias_sync.storage import Settings, data_dir, read_json
    settings = Settings()
    settings.save_source(source)
    settings.save_source(replace(source, id=str(uuid4()), destination=str(tmp_path/'other-output')))
    settings.value['battery_saver'] = True
    settings.save()
    monkeypatch.setattr('ilias_sync.__main__.on_battery', lambda: True)
    sync = AsyncMock()
    monkeypatch.setattr('ilias_sync.engine.synchronize', sync)
    args = SimpleNamespace(probe=None, profile=None, sync=True, discover=False)
    assert await worker(args) == 0
    sync.assert_not_awaited()
    assert all(read_json(data_dir()/'sources'/row.id/'status.json',{})['deferred'] == 'battery' for row in settings.sources())
    active = peak = calls = 0
    async def operation(*args, **kwargs):
        nonlocal active, peak, calls
        active += 1
        peak = max(peak, active)
        calls += 1
        await asyncio.sleep(0.01)
        active -= 1
        return {'partial':False, 'warnings':0, 'errors':0}
    monkeypatch.setattr('ilias_sync.__main__.on_battery', lambda: False)
    monkeypatch.setattr('ilias_sync.engine.synchronize', operation)
    assert await worker(args) == 0
    assert calls == 2 and peak == 1 and active == 0
