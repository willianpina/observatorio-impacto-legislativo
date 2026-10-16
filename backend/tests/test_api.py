import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.oil.main import app
from backend.oil.ingest import SourceFailure
from backend.oil.models import Divulgacao, Serie
from backend.oil.read import read_series
from .conftest import ROOT, collect


@pytest.fixture
def client(sf):
    with TestClient(app) as client:
        app.state.sessions=sf
        yield client


@pytest.mark.parametrize('codigo', ['desocupacao','rendimento-real'])
def test_routes_contract(populated, client, codigo):
    response=client.get(f'/api/v1/indicadores/{codigo}/serie')
    assert response.status_code==200
    data=response.json()
    required={'valor','lacuna','unidade','periodo','tipo_periodo','tipo_valor','medida','base_precos',
              'cv','variacao_anual','classificacao','classificacao_origem','fonte','tabela_ou_arquivo',
              'link','coleta_id','coletado_em','desatualizado','atrasado_calendario',
              'nivel_evidencia','disponivel','motivo'}
    assert required<=set(data)
    assert len(data['pontos'])==60
    assert all(required<=set(p) for p in data['pontos'])
    assert data['simulada'] is True and data['nivel_evidencia']=='descritivo'
    assert data['tipo_periodo']=='trimestre_movel' and data['base_precos'] is None
    assert datetime.fromisoformat(data['coletado_em']).tzinfo is not None
    assert data['classificacao_origem']=='calculada'
    assert data['variaveis']['variacao_anual']==('8816' if codigo=='desocupacao' else '8837')
    assert client.get(f'/api/v1/indicadores/{codigo}').json()==data


def test_index(populated, client):
    data=client.get('/api/v1/indicadores').json()
    assert {'fonte','coletado_em','atrasado_calendario'}<=set(data)
    assert {s['codigo'] for s in data['indicadores']}=={'desocupacao','rendimento-real'}


@pytest.mark.parametrize('janela,count,first',[('2a',24,'202409'),('5a',60,'202109'),('desde_2020',80,'202001')])
def test_windows_do_not_aggregate_or_change_comparison(populated, client, janela,count,first):
    data=client.get('/api/v1/indicadores/rendimento-real/serie',params={'janela':janela}).json()
    assert len(data['pontos'])==count and data['pontos'][0]['periodo']==first
    assert data['pontos'][-1]['periodo']=='202608'
    assert data['comparacao']=='mesmo_periodo_ano_anterior'
    assert data['classificacao']=='subiu'


def test_invalid_params_and_unknown_code(client):
    invalid=client.get('/api/v1/indicadores/desocupacao/serie?janela=1a')
    assert invalid.status_code==422 and 'erro' in invalid.json()
    assert client.get('/api/v1/indicadores/inexistente/serie').status_code==404


def test_empty_database_no_fabrication(client):
    data=client.get('/api/v1/indicadores/desocupacao/serie').json()
    assert data['disponivel'] is False and data['pontos']==[]
    assert data['valor'] is None and data['motivo']


def test_production_does_not_serve_simulated_data(populated,client):
    app.state.test_mode=False
    try:
        data=client.get('/api/v1/indicadores/desocupacao/serie').json()
        assert not data['disponivel'] and data['pontos']==[] and not data['simulada']
    finally:
        app.state.test_mode=True


def test_last_good_collection_on_failure(populated,client):
    before=client.get('/api/v1/indicadores/desocupacao/serie').json()
    def failure(request):
        raise httpx.ConnectError('FALHA SIMULADA',request=request)
    with pytest.raises(SourceFailure):
        collect(populated,failure)
    response=client.get('/api/v1/indicadores/desocupacao/serie')
    assert response.status_code==200
    data=response.json()
    assert data['desatualizado'] is True and data['atrasado_calendario'] is False
    assert data['valor']==before['valor'] and data['coleta_id']==before['coleta_id']


def test_calendar_is_manual_and_independent(populated):
    now=datetime(2026,10,16,tzinfo=timezone.utc)
    with populated.begin() as session:
        serie=session.scalar(select(Serie).where(Serie.codigo=='desocupacao'))
        # Datas deste teste são SINTETICAS, não cadastro de calendário oficial.
        session.add(Divulgacao(serie_id=serie.id,periodo='202609',prevista_em=now-timedelta(days=1),
                              fonte='CALENDARIO SIMULADO',link='https://example.org/calendario-simulado'))
    with populated() as session:
        data=read_series(session,'desocupacao','5a',test_mode=True,now=now)
        assert data.atrasado_calendario is True and data.desatualizado is False
        before=read_series(session,'desocupacao','5a',test_mode=True,now=now-timedelta(days=2))
        assert before.atrasado_calendario is False


def test_legacy_routes_still_serve_recorded_poc_data(client):
    evidence=json.loads((ROOT/'poc/evidencias/consultas-reais.json').read_bytes())
    mapping={item['url']:item['payload'] for item in evidence if 'payload' in item}
    def replay(request):
        url=str(request.url)
        # HTTPX conserva espaços escapados; a URL original é conhecida pelo manifesto da PoC.
        assert url in mapping, 'URL da PoC não gravada'
        return httpx.Response(200,json=mapping[url])
    mock=httpx.AsyncClient(transport=httpx.MockTransport(replay))
    original=app.state.client
    app.state.client=mock
    try:
        assert client.get('/api/legislacao').status_code==200
        assert client.get('/api/indicadores/desemprego').status_code==200
    finally:
        app.state.client=original
        asyncio.run(mock.aclose())


@pytest.mark.parametrize('kind,status', [('connect',503),('timeout',504),('invalid',502)])
def test_source_error_without_previous_data(sf,replay,client,kind,status):
    def handler(request):
        if kind=='connect':
            raise httpx.ConnectError('FALHA SIMULADA',request=request)
        if kind=='timeout':
            raise httpx.ReadTimeout('FALHA SIMULADA',request=request)
        return httpx.Response(200,text='RESPOSTA INVALIDA SIMULADA')
    with pytest.raises(SourceFailure):
        collect(sf,handler)
    response=client.get('/api/v1/indicadores/desocupacao/serie')
    assert response.status_code==status
    assert set(response.json()['erro'])=={'codigo','mensagem','fonte','tentar_novamente_em','ultima_coleta_id'}
    if status==503:
        assert response.headers['Retry-After']=='60'


def test_gap_is_null_and_classification_is_null(sf,replay,client):
    def handler(request):
        response=replay(request)
        if 'apisidra' in str(request.url):
            payload=response.json()
            for row in payload[1:]:
                if row['D3C']=='202608' and row['D2C']=='4099':
                    row['V']='...'  # LACUNA SIMULADA, nunca dado de produção.
            return httpx.Response(200,json=payload)
        return response
    collect(sf,handler)
    data=client.get('/api/v1/indicadores/desocupacao/serie').json()
    assert data['valor'] is None and data['lacuna'] is True
    assert data['classificacao'] is None


def test_database_unavailable_does_not_expose_parameters(client):
    from sqlalchemy.exc import OperationalError
    from backend.oil.main import get_session
    def failure():
        raise OperationalError('SIMULADO',{},Exception('erro interno simulado'))
    app.dependency_overrides[get_session]=failure
    try:
        response=client.get('/api/v1/indicadores')
        assert response.status_code==503 and response.headers['Retry-After']=='60'
        assert 'SIMULADO' not in response.text and 'erro interno' not in response.text
    finally:
        app.dependency_overrides.clear()
