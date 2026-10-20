"""Transporte falso: tempos virtuais, nenhum acesso ao Drive ou outra rede externa."""
import asyncio
import hashlib
import json
import os
import sys
import time

import httpx
import pytest
from sqlalchemy import func, select

from backend.oil import caged, o3_cli
from backend.oil.ingest import SourceFailure
from backend.oil.models import Coleta, Observacao
from .conftest import no_sleep
from .test_o3_caged import entry, ingest_caged


class TimedStream(httpx.AsyncByteStream):
    """MockTransport não aplica deadlines: compara atrasos virtuais ao timeout da requisição."""
    def __init__(self, request, chunks):
        self.request, self.chunks = request, chunks
        self.closed = False

    async def __aiter__(self):
        for delay, content in self.chunks:
            if delay > self.request.extensions['timeout']['read']:
                raise httpx.ReadTimeout('Atraso virtual de teste', request=self.request)
            yield content

    async def aclose(self):
        self.closed = True


def run(sf, handler, metadata=None, *, clock=None, sleep=no_sleep, limit=None):
    async def collect():
        kwargs = {}
        if clock is not None:
            kwargs['clock'] = clock
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2, follow_redirects=False) as client:
            try:
                job = caged.CagedCollector(sf, client, simulada=True, sleep=sleep, **kwargs).collect(metadata or entry('2026-08')[0])
                if limit is None:
                    return await job
                try:
                    return await asyncio.wait_for(job, limit)
                except TimeoutError:
                    pytest.fail('a tentativa presa não foi cancelada pelo prazo total')
            finally:
                assert client.timeout.read == 2 and not client.follow_redirects
    return asyncio.run(collect())


class VirtualClock:
    """Relógio monotônico falso: os testes avançam o tempo, sem espera real."""
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class BudgetStream(httpx.AsyncByteStream):
    """Cada bloco avança o relógio da tentativa. ReadTimeout só se o bloco isolado passar do prazo de leitura."""
    def __init__(self, request, clock, chunks):
        self.request, self.clock, self.chunks = request, clock, chunks
        self.closed = False

    async def __aiter__(self):
        for delay, content in self.chunks:
            self.clock.advance(delay)
            if delay > self.request.extensions['timeout']['read']:
                raise httpx.ReadTimeout('Atraso virtual de teste', request=self.request)
            yield content

    async def aclose(self):
        self.closed = True


class HungStream(httpx.AsyncByteStream):
    """Nunca entrega o próximo bloco: o prazo tem de cancelar a espera."""
    def __init__(self):
        self.closed = False
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def __aiter__(self):
        self.started.set()
        await self.release.wait()
        yield b''

    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize('setting,passes', [(None, True), ('120', True), ('20', False)])
def test_first_byte_30_virtual_seconds(sf, monkeypatch, setting, passes):
    if setting is None: monkeypatch.delenv('OIL_CAGED_READ_TIMEOUT', raising=False)
    else: monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', setting)
    raw = entry('2026-08')[1]; requests = []; streams = []
    def handler(request):
        requests.append(request)
        stream = TimedStream(request, [(30, raw[:100]), (0, raw[100:])]); streams.append(stream)
        return httpx.Response(200, stream=stream)
    if passes:
        result = run(sf, handler)
        assert result['novas_versoes'] > 0 and len(requests) == 1
        assert requests[0].extensions['timeout'] == dict(connect=5, read=120, write=10, pool=10)
    else:
        with pytest.raises(SourceFailure, match='timeout_fonte'): run(sf, handler)
        assert len(requests) == 3  # Limite já existente de tentativas; sem esperas reais.
        with sf() as session:
            assert all(c.erro == 'timeout_primeiro_byte' and not c.valida for c in session.scalars(select(Coleta)))
    assert all(s.closed for s in streams)


@pytest.mark.parametrize('phase', ['conexao', 'primeiro_byte', 'leitura', 'escrita'])
def test_timeout_phase_is_persisted(sf, monkeypatch, phase):
    monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', '20')
    raw = entry('2026-08')[1]
    def handler(request):
        if phase == 'conexao': raise httpx.ConnectTimeout('Conexão falsa', request=request)
        if phase == 'primeiro_byte': raise httpx.ReadTimeout('Cabeçalhos falsos', request=request)
        if phase == 'escrita': raise httpx.WriteTimeout('Escrita falsa', request=request)
        return httpx.Response(200, stream=TimedStream(request, [(0, raw[:100]), (30, raw[100:])]))
    with pytest.raises(SourceFailure, match='timeout_fonte') as falha:
        run(sf, handler)
    assert falha.value.code == 'timeout_fonte' and falha.value.status == 504
    with sf() as session:
        rows = session.scalars(select(Coleta)).all()
        assert len(rows) == 3 and all(c.erro == 'timeout_' + phase and not c.valida for c in rows)
        if phase == 'leitura':
            assert all(c.codigo_http == 200 and c.tamanho_bytes == 100 and c.hash_sha256 == hashlib.sha256(raw[:100]).hexdigest() for c in rows)
        assert session.scalar(select(func.count()).select_from(Observacao)) == 0


@pytest.mark.parametrize('setting,expected', [('999', 300), ('300', 300), ('0.5', 0.5)])
def test_read_timeout_is_capped(sf, monkeypatch, setting, expected):
    monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', setting)
    def handler(request):
        assert request.extensions['timeout'] == dict(connect=5, read=expected, write=10, pool=10)
        return httpx.Response(200, content=entry('2026-08')[1])
    run(sf, handler)


@pytest.mark.parametrize('setting', ['0', '-1', 'nan', 'inf', 'abc', ''])
def test_invalid_timeout_never_disables_deadline(sf, monkeypatch, setting):
    monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', setting)
    def handler(request): raise AssertionError('Configuração inválida não deve chegar ao transporte')
    with pytest.raises(ValueError, match='OIL_CAGED_READ_TIMEOUT'): run(sf, handler)


def test_streaming_limit_aborts_above_100_mib(sf):
    assert caged.MAX_BYTES == 100 * 1024 * 1024
    class LargeStream(httpx.AsyncByteStream):
        consumed = 0; closed = False
        async def __aiter__(self):
            for _ in range(110):
                self.consumed += 1
                yield b'x' * (1024 * 1024)
        async def aclose(self): self.closed = True
    stream = LargeStream()
    with pytest.raises(SourceFailure, match='arquivo_invalido'):
        run(sf, lambda request: httpx.Response(200, stream=stream))
    assert stream.consumed == 101 and stream.closed
    with sf() as session:
        row = session.scalar(select(Coleta))
        assert not row.valida and row.erro == 'download' and row.tamanho_bytes > caged.MAX_BYTES
        received_hash = hashlib.sha256()
        for _ in range(stream.consumed): received_hash.update(b'x' * (1024 * 1024))
        assert row.hash_sha256 == received_hash.hexdigest()
        assert session.scalar(select(func.count()).select_from(Observacao)) == 0


def test_confirm_and_stream_hash_match_fixture(sf, monkeypatch, tmp_path):
    metadata, raw = entry('2026-08'); metadata['url_download'] += '&confirm=t'
    requests = []; streams = []; temporary = []; actual = caged.tempfile.TemporaryFile
    monkeypatch.setattr(caged.tempfile, 'tempdir', str(tmp_path))
    def temp(*args, **kwargs):
        stream = actual(*args, **kwargs); temporary.append(stream); return stream
    monkeypatch.setattr(caged.tempfile, 'TemporaryFile', temp)
    def handler(request):
        requests.append(request)
        assert request.url.params['confirm'] == 't'
        stream = TimedStream(request, [(0, raw[:100]), (0, raw[100:])]); streams.append(stream)
        return httpx.Response(200, stream=stream)
    result = run(sf, handler, metadata)
    assert len(requests) == 1 and all(s.closed for s in streams) and temporary
    assert_temporary_released(tmp_path, temporary)
    with sf() as session:
        row = session.get(Coleta, result['coleta_id'])
        assert row.valida and row.hash_sha256 == metadata['sha256'] == hashlib.sha256(raw).hexdigest()
        assert row.tamanho_bytes == len(raw) and row.resposta_bruta is None


@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
@pytest.mark.parametrize('location', [
    'http://drive.usercontent.google.com/download?id=fixture&confirm=t',
    'https://evil.example/arquivo.xlsx',
    'http://127.0.0.1/latest/meta-data',
    'http://169.254.169.254/latest/meta-data',
])
def test_302_is_invalid_without_following_location(sf, status, location):
    requests = []; metadata, raw = entry('2026-08')
    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(status, headers={'Location': location})
        return httpx.Response(200, content=raw)
    with pytest.raises(SourceFailure, match='http_fonte'):
        run(sf, handler, metadata)
    assert len(requests) == 1
    assert requests[0].url.scheme == 'https' and requests[0].url.host == 'drive.usercontent.google.com'
    with sf() as session:
        rows = session.scalars(select(Coleta)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.codigo_http == status and row.valida is False and row.erro == 'http_fonte'
        assert row.hash_sha256 is None
        assert session.scalar(select(func.count()).select_from(Observacao)) == 0


def assert_temporary_released(directory, opened):
    """O temporário deixa de existir e o descritor é solto. Só `closed` deixa passar arquivo nomeado que foi fechado e ficou no disco."""
    assert opened
    assert all(stream.closed for stream in opened)
    for stream in opened:
        name = getattr(stream, 'name', None)
        if isinstance(name, str):
            assert not os.path.exists(name)
    assert list(directory.iterdir()) == []
    if not os.path.isdir('/proc/self/fd'):
        return
    root = str(directory)
    leaked = []
    for item in os.scandir('/proc/self/fd'):
        try:
            target = os.readlink(item.path)
        except OSError:
            continue
        if target.startswith(root + os.sep) or (root in target and target.endswith(' (deleted)')):
            leaked.append(target)
    assert leaked == []


def test_temporary_file_is_released_after_success_and_failure(sf, monkeypatch, tmp_path):
    monkeypatch.setattr(caged.tempfile, 'tempdir', str(tmp_path))
    opened = []
    paths = []
    real = {
        'TemporaryFile': caged.tempfile.TemporaryFile,
        'NamedTemporaryFile': caged.tempfile.NamedTemporaryFile,
        'SpooledTemporaryFile': caged.tempfile.SpooledTemporaryFile,
    }
    real_mkstemp = caged.tempfile.mkstemp

    def spy(factory):
        def wrapper(*args, **kwargs):
            stream = factory(*args, **kwargs)
            opened.append(stream)
            return stream
        return wrapper

    for name, factory in real.items():
        monkeypatch.setattr(caged.tempfile, name, spy(factory))

    def spy_mkstemp(*args, **kwargs):
        descriptor, path = real_mkstemp(*args, **kwargs)
        paths.append(path)
        return descriptor, path

    monkeypatch.setattr(caged.tempfile, 'mkstemp', spy_mkstemp)
    metadata, raw = entry('2026-08')

    def released(since):
        created = opened[since:]
        assert_temporary_released(tmp_path, created)
        assert all(not os.path.exists(path) for path in paths)

    result = run(sf, lambda request: httpx.Response(200, content=raw), metadata)
    assert result['novas_versoes'] > 0
    released(0)
    before = len(opened)
    with pytest.raises(SourceFailure, match='arquivo_invalido'):
        run(sf, lambda request: httpx.Response(200, content=b'conteudo-invalido'), metadata)
    assert len(opened) > before
    released(before)


@pytest.mark.parametrize('setting', ['0', '-1', 'nan', 'inf', 'abc', ''])
def test_invalid_timeout_job_prints_config_error(sf, monkeypatch, capsys, setting):
    monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', setting)
    monkeypatch.setattr(sys, 'argv', ['o3_cli', 'caged', '2026-08'])
    requests = []

    def handler(request):
        requests.append(request)
        raise AssertionError('configuração inválida não deve gerar requisição')

    monkeypatch.setattr(o3_cli, 'make_client', lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), timeout=1, follow_redirects=False))
    with pytest.raises(SystemExit) as caught:
        o3_cli.main()
    assert caught.value.code not in (0, None)
    captured = capsys.readouterr()
    assert 'Traceback' not in captured.err and 'Traceback' not in captured.out
    payload = json.loads(captured.out)
    assert payload['erro'] == 'configuracao_invalida'
    assert 'OIL_CAGED_READ_TIMEOUT' in payload['mensagem']
    assert requests == []
    with sf() as session:
        assert session.scalar(select(func.count()).select_from(Coleta)) == 0
        assert session.scalar(select(func.count()).select_from(Observacao)) == 0


def test_attempt_budget_allows_transfer_inside_the_limit(sf, monkeypatch):
    monkeypatch.delenv('OIL_CAGED_ATTEMPT_TIMEOUT', raising=False)
    monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', '300')
    raw = entry('2026-08')[1]
    clock = VirtualClock()
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, stream=BudgetStream(request, clock, [(100, raw)]))

    result = run(sf, handler, clock=clock)
    assert result['novas_versoes'] > 0 and len(requests) == 1 and clock.now == 100


def test_attempt_budget_stops_without_retry(sf, monkeypatch):
    monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', '120')
    monkeypatch.setenv('OIL_CAGED_ATTEMPT_TIMEOUT', '20')
    raw = entry('2026-08')[1]
    clock = VirtualClock()
    requests = []
    delays = []
    streams = []

    async def spy_sleep(delay):
        delays.append(delay)

    def handler(request):
        requests.append(request)
        stream = BudgetStream(request, clock, [(10, raw[:80]), (15, raw[80:])])
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    with pytest.raises(SourceFailure, match='timeout_fonte') as falha:
        run(sf, handler, clock=clock, sleep=spy_sleep)
    assert falha.value.code == 'timeout_fonte' and falha.value.status == 504
    assert len(requests) == 1 and delays == [] and all(stream.closed for stream in streams)
    with sf() as session:
        rows = session.scalars(select(Coleta)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.erro == 'timeout_total' and row.valida is False and row.codigo_http == 200
        assert row.tamanho_bytes == 80 and row.hash_sha256 == hashlib.sha256(raw[:80]).hexdigest()
        assert session.scalar(select(func.count()).select_from(Observacao)) == 0


def test_attempt_budget_is_capped_at_300(sf, monkeypatch):
    monkeypatch.setenv('OIL_CAGED_ATTEMPT_TIMEOUT', '999')
    assert caged.attempt_budget() == 300
    seen = []
    real_timeout = caged.asyncio.timeout

    def spy(delay):
        seen.append(delay)
        return real_timeout(delay)

    monkeypatch.setattr(caged.asyncio, 'timeout', spy)
    raw = entry('2026-08')[1]
    result = run(sf, lambda request: httpx.Response(200, content=raw))
    assert result['novas_versoes'] > 0 and seen == [300]


def test_stalled_stream_is_cancelled_without_retry(sf, monkeypatch, tmp_path):
    monkeypatch.setenv('OIL_CAGED_ATTEMPT_TIMEOUT', '0.05')
    monkeypatch.setattr(caged.tempfile, 'tempdir', str(tmp_path))
    opened = []
    real_temp = caged.tempfile.TemporaryFile

    def spy_temp(*args, **kwargs):
        stream = real_temp(*args, **kwargs)
        opened.append(stream)
        return stream

    monkeypatch.setattr(caged.tempfile, 'TemporaryFile', spy_temp)
    requests = []
    delays = []
    streams = []

    async def spy_sleep(delay):
        delays.append(delay)

    def handler(request):
        requests.append(request)
        stream = HungStream()
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    started = time.monotonic()
    with pytest.raises(SourceFailure, match='timeout_fonte') as falha:
        run(sf, handler, sleep=spy_sleep, limit=1)
    elapsed = time.monotonic() - started
    assert falha.value.code == 'timeout_fonte' and falha.value.status == 504
    assert elapsed < 0.8
    assert len(requests) == 1 and delays == [] and len(streams) == 1
    assert streams[0].started.is_set() and streams[0].closed
    assert_temporary_released(tmp_path, opened)
    with sf() as session:
        rows = session.scalars(select(Coleta)).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.erro == 'timeout_total' and row.valida is False
        assert session.scalar(select(func.count()).select_from(Observacao)) == 0


@pytest.mark.parametrize('setting', ['0', '-1', 'nan', 'inf', 'abc', ''])
def test_invalid_attempt_budget_never_disables_deadline(sf, monkeypatch, setting):
    monkeypatch.setenv('OIL_CAGED_ATTEMPT_TIMEOUT', setting)

    def handler(request):
        raise AssertionError('prazo total inválido não deve chegar ao transporte')

    with pytest.raises(ValueError, match='OIL_CAGED_ATTEMPT_TIMEOUT'):
        run(sf, handler)


@pytest.mark.parametrize('setting', ['0', 'abc'])
def test_invalid_attempt_budget_job_prints_config_error(sf, monkeypatch, capsys, setting):
    monkeypatch.setenv('OIL_CAGED_ATTEMPT_TIMEOUT', setting)
    monkeypatch.setattr(sys, 'argv', ['o3_cli', 'caged', '2026-08'])
    requests = []

    def handler(request):
        requests.append(request)
        raise AssertionError('prazo total inválido não deve gerar requisição')

    monkeypatch.setattr(o3_cli, 'make_client', lambda: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), timeout=1, follow_redirects=False))
    with pytest.raises(SystemExit) as caught:
        o3_cli.main()
    assert caught.value.code not in (0, None)
    captured = capsys.readouterr()
    assert 'Traceback' not in captured.err and 'Traceback' not in captured.out
    payload = json.loads(captured.out)
    assert payload['erro'] == 'configuracao_invalida'
    assert 'OIL_CAGED_ATTEMPT_TIMEOUT' in payload['mensagem']
    assert requests == []
    with sf() as session:
        assert session.scalar(select(func.count()).select_from(Coleta)) == 0
        assert session.scalar(select(func.count()).select_from(Observacao)) == 0


def test_revised_month_keeps_previous_version_linked_to_collection(sf):
    july = ingest_caged(sf, '2026-07'); august = ingest_caged(sf, '2026-08')
    with sf() as session:
        versions = session.scalars(select(Observacao).where(Observacao.periodo == '202607').order_by(Observacao.versao)).all()
        assert [(o.versao, int(o.valor), o.coleta_id) for o in versions] == [
            (1, 58568, july['coleta_id']), (2, 55915, august['coleta_id'])]
