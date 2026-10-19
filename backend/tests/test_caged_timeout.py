"""Transporte falso: tempos virtuais, nenhum acesso ao Drive ou outra rede externa."""
import asyncio
import hashlib

import httpx
import pytest
from sqlalchemy import func, select

from backend.oil import caged
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


def run(sf, handler, metadata=None):
    async def collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2, follow_redirects=False) as client:
            try:
                return await caged.CagedCollector(sf, client, simulada=True, sleep=no_sleep).collect(metadata or entry('2026-08')[0])
            finally:
                assert client.timeout.read == 2 and not client.follow_redirects
    return asyncio.run(collect())


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


@pytest.mark.parametrize('phase', ['conexao', 'primeiro_byte', 'leitura'])
def test_timeout_phase_is_persisted(sf, monkeypatch, phase):
    monkeypatch.setenv('OIL_CAGED_READ_TIMEOUT', '20')
    raw = entry('2026-08')[1]
    def handler(request):
        if phase == 'conexao': raise httpx.ConnectTimeout('Conexão falsa', request=request)
        if phase == 'primeiro_byte': raise httpx.ReadTimeout('Cabeçalhos falsos', request=request)
        return httpx.Response(200, stream=TimedStream(request, [(0, raw[:100]), (30, raw[100:])]))
    with pytest.raises(SourceFailure, match='timeout_fonte'): run(sf, handler)
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


def test_redirect_confirm_and_stream_hash_match_fixture(sf, monkeypatch):
    metadata, raw = entry('2026-08'); metadata['url_download'] += '&confirm=t'
    requests = []; streams = []; temporary = []; actual = caged.tempfile.TemporaryFile
    def temp():
        stream = actual(); temporary.append(stream); return stream
    monkeypatch.setattr(caged.tempfile, 'TemporaryFile', temp)
    def handler(request):
        requests.append(request)
        assert request.url.params['confirm'] == 't'
        if len(requests) == 1:
            return httpx.Response(302, headers={'Location': str(request.url) + '&resolved=1'})
        stream = TimedStream(request, [(0, raw[:100]), (0, raw[100:])]); streams.append(stream)
        return httpx.Response(200, stream=stream)
    result = run(sf, handler, metadata)
    assert len(requests) == 2 and all(s.closed for s in streams) and all(s.closed for s in temporary)
    with sf() as session:
        row = session.get(Coleta, result['coleta_id'])
        assert row.valida and row.hash_sha256 == metadata['sha256'] == hashlib.sha256(raw).hexdigest()
        assert row.tamanho_bytes == len(raw) and row.resposta_bruta is None


def test_revised_month_keeps_previous_version_linked_to_collection(sf):
    july = ingest_caged(sf, '2026-07'); august = ingest_caged(sf, '2026-08')
    with sf() as session:
        versions = session.scalars(select(Observacao).where(Observacao.periodo == '202607').order_by(Observacao.versao)).all()
        assert [(o.versao, int(o.valor), o.coleta_id) for o in versions] == [
            (1, 58568, july['coleta_id']), (2, 55915, august['coleta_id'])]
