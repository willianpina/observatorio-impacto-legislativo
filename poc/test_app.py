"""Todos os dados deste arquivo são sintéticos; não comprovam disponibilidade real."""
import asyncio
import copy

import httpx
import pytest
from fastapi.testclient import TestClient

from app import (CAMARA, Gateway, SourceError, app, legislation, metadata_check,
                 parse_sidra, unemployment)


def sidra():
    periods = ['202403', '202404', '202501', '202502', '202503', '202504', '202601', '202602']
    return [{'D3C': 'Trimestre (Código)'}] + [dict(
        NC='1', D1C='1', D1N='Brasil', D2C='4099', D3C=p,
        D3N=f'Trimestre {p}', MN='%', V='7.0') for p in periods]


def metadata():
    return {'id': 4099, 'periodicidade': {'frequencia': 'trimestral'},
            'variaveis': [{'id': 4099, 'nome': 'Taxa de desocupação, teste', 'unidade': '%'}]}


def bill():
    return dict(id=123, siglaTipo='PL', numero=1, ano=2026, ementa='Fixture sintética')


def run(handler, operation):
    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await operation(Gateway(client))
    return asyncio.run(execute())


def test_series_contract():
    result = run(lambda r: httpx.Response(200, json=metadata() if 'metadados' in str(r.url)
                                       else sidra()), unemployment)
    assert len(result.dados) == 8
    assert result.meta.periodicidade == 'trimestral'
    assert result.dados[0].valor == 7.0
    assert result.dados[0].origem.startswith('https://apisidra.ibge.gov.br/')
    assert result.dados[-1].periodo == '202602'


@pytest.mark.parametrize('marker', ['...', '..', '-', 'X'])
def test_missing_not_zero(marker):
    payload = sidra()
    payload[1]['V'] = marker
    point = parse_sidra(payload)[0]
    assert point.valor is None and point.status == 'ausente'


@pytest.mark.parametrize('mutation', [
    lambda p: p[1].pop('V'), lambda p: p[1].update(MN='Pessoas'),
    lambda p: p[1].update(D2C='4103'), lambda p: p[1].update(D1C='2'),
    lambda p: p[1].update(V='NaN'), lambda p: p[1].update(V='101'),
    lambda p: p[1].update(V='abc'), lambda p: p[1].update(D3C='202413'),
    lambda p: p[1].update(D3C=p[2]['D3C']), lambda p: p.pop(),
    lambda p: p[0].update(D3C='Mês (Código)'),
])
def test_unexpected_series(mutation):
    payload = sidra()
    mutation(payload)
    with pytest.raises(ValueError):
        parse_sidra(payload)


def test_list_and_real_id_flow_synthetic_fixture():
    seen = []
    def handler(request):
        seen.append(str(request.url))
        item = bill()
        if request.url.path.endswith('/123'):
            item['statusProposicao'] = {'descricaoSituacao': 'Situação sintética'}
            return httpx.Response(200, json={'dados': item})
        return httpx.Response(200, json={'dados': [item]})
    result = run(handler, legislation)
    assert seen[1] == f'{CAMARA}/123'
    assert result.dados[0].situacao == 'Situação sintética'
    assert result.meta.quantidade == 1


def test_optional_status():
    result = run(lambda r: httpx.Response(200, json={'dados': bill() if r.url.path.endswith('/123')
                                                 else [bill()]}), legislation)
    assert result.dados[0].situacao is None


@pytest.mark.parametrize('field', ['id', 'siglaTipo', 'numero', 'ano', 'ementa'])
def test_required_bill_fields(field):
    item = bill()
    item.pop(field)
    with pytest.raises(SourceError) as err:
        run(lambda r: httpx.Response(200, json={'dados': [item]}), legislation)
    assert err.value.code == 'resposta_invalida'


def test_detail_mismatch():
    def handler(r):
        item = bill()
        if r.url.path.endswith('/123'):
            item['id'] = 124
            return httpx.Response(200, json={'dados': item})
        return httpx.Response(200, json={'dados': [item]})
    with pytest.raises(SourceError):
        run(handler, legislation)


@pytest.mark.parametrize('kind,status,code,attempts', [
    ('connect', 503, 'erro_conexao', 3), ('timeout', 504, 'timeout_fonte', 3),
    (503, 503, 'fonte_indisponivel', 3), (429, 503, 'fonte_indisponivel', 3),
    (404, 502, 'http_fonte', 1), ('html', 502, 'resposta_invalida', 1),
])
def test_failures_retry_and_http_mapping(kind, status, code, attempts):
    seen = []
    def handler(request):
        seen.append(request)
        if kind == 'connect':
            raise httpx.ConnectError('synthetic', request=request)
        if kind == 'timeout':
            raise httpx.ReadTimeout('synthetic', request=request)
        if kind == 'html':
            return httpx.Response(200, text='<html>bad gateway</html>')
        return httpx.Response(kind)
    with TestClient(app) as client:
        original = app.state.client
        mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.client = mock
        try:
            response = client.get('/api/indicadores/desemprego')
        finally:
            app.state.client = original
            asyncio.run(mock.aclose())
    assert response.status_code == status
    assert response.json()['erro']['codigo'] == code
    assert len(seen) == attempts


def test_transient_recovery():
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(503 if len(seen) == 1 else 200, json={'ok': True})
    result = run(handler, lambda g: g.get(CAMARA, 'camara'))
    assert result == {'ok': True} and len(seen) == 2


@pytest.mark.parametrize('payload', [None, [], {}, {'dados': None}, {'dados': 'oops'}])
def test_bad_envelope(payload):
    with pytest.raises(SourceError):
        run(lambda r: httpx.Response(200, json=payload), legislation)


def test_metadata_guard_before_series_request():
    seen = []
    invalid = copy.deepcopy(metadata())
    invalid['periodicidade']['frequencia'] = 'mensal'
    def handler(r):
        seen.append(r)
        return httpx.Response(200, json=invalid)
    with pytest.raises(SourceError) as err:
        run(handler, unemployment)
    assert err.value.code == 'metadados_invalidos' and len(seen) == 1


def test_query_limits():
    with TestClient(app) as client:
        assert client.get('/api/legislacao?limite=100').status_code == 422
        assert client.get('/api/legislacao?ano=abc').status_code == 422


def test_local_endpoint_contract():
    def handler(r):
        if 'metadados' in str(r.url):
            return httpx.Response(200, json=metadata())
        if 'apisidra' in str(r.url):
            return httpx.Response(200, json=sidra())
        return httpx.Response(200, json={'dados': bill() if r.url.path.endswith('/123') else [bill()]})
    with TestClient(app) as client:
        original = app.state.client
        mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.client = mock
        try:
            for path in ['/api/legislacao', '/api/indicadores/desemprego']:
                response = client.get(path)
                assert response.status_code == 200
                assert set(response.json()) == {'dados', 'meta'}
        finally:
            app.state.client = original
            asyncio.run(mock.aclose())
