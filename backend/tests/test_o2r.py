import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
from alembic import command
from fastapi import HTTPException, Query
from sqlalchemy import delete, select

from backend.oil.calendar import bounded_text, register
from backend.oil.ingest import Collector, SourceFailure, make_client, retry_delay
from backend.oil.main import app, get_session
from backend.oil.models import Coleta, Fonte, Observacao, Serie
from .conftest import alembic_config, collect


def test_caged_registered_unavailable(sf,client):
    with sf() as session:
        registered=session.scalar(select(Serie).where(Serie.codigo=='caged-saldo'))
        assert registered.disponivel is False and registered.motivo
        assert registered.tabela is registered.variavel is None
        assert session.get(Fonte,registered.fonte_id).codigo=='mte-caged'
    for path in ['/api/v1/indicadores/caged-saldo','/api/v1/indicadores/caged-saldo/serie']:
        response=client.get(path)
        assert response.status_code==200
        data=response.json()
        assert data['disponivel'] is False and data['motivo'] and data['pontos']==[]
        assert data['valor'] is data['cv'] is data['coleta_id'] is data['link'] is None


def test_gap_in_database_is_returned_not_omitted(populated,client):
    with populated.begin() as session:
        serie_id=session.scalar(select(Serie.id).where(Serie.codigo=='desocupacao'))
        session.execute(delete(Observacao).where(Observacao.serie_id==serie_id,Observacao.periodo=='202607'))
    data=client.get('/api/v1/indicadores/desocupacao/serie').json()
    assert len(data['pontos'])==60
    point=next(p for p in data['pontos'] if p['periodo']=='202607')
    assert point['valor'] is None and point['lacuna'] is True
    assert point['cv'] is point['variacao_anual'] is point['classificacao'] is None
    assert point['coleta_id'] is point['coletado_em'] is point['versao'] is None


def test_no_duplicated_generic_route(client):
    paths=client.get('/openapi.json').json()['paths']
    assert '/api/v1/indicadores/{codigo}/serie' in paths
    assert '/api/v1/indicadores/{codigo}' not in paths
    assert '/api/v1/indicadores/caged-saldo' in paths


@pytest.mark.parametrize('path,body',[('/nao-existe',{'detail':'Not Found'}),
                                    ('/api/v1/outro',{'detail':'Not Found'}),
                                    ('/api/legislacao/nao-existe',{'detail':'Not Found'})])
def test_404_outside_indicators_is_unchanged(client,path,body):
    response=client.get(path)
    assert response.status_code==404 and response.json()==body


def test_405_is_not_classified_as_missing_indicator(client):
    response=client.post('/api/v1/indicadores')
    assert response.status_code==405
    assert response.json()['erro']['codigo']=='metodo_nao_permitido'
    assert 'GET' in response.headers['Allow']


@pytest.mark.parametrize('status,code',[(403,'acesso_negado'),(404,'indicador_inexistente'),(409,'http_409')])
def test_http_handler_maps_actual_status(client,status,code):
    def failure():
        raise HTTPException(status,'Requisição de teste indisponível.')
    app.dependency_overrides[get_session]=failure
    try:
        response=client.get('/api/v1/indicadores')
        assert response.status_code==status and response.json()['erro']['codigo']==code
    finally:
        app.dependency_overrides.clear()


def test_422_reports_actual_parameter(client):
    response=client.get('/api/v1/indicadores?janela=invalida')
    assert response.status_code==422 and 'query.janela' in response.json()['erro']['mensagem']
    def dependency(limite: int=Query(...)):
        raise AssertionError('Parâmetro inválido deve ser rejeitado antes da execução.')
    app.dependency_overrides[get_session]=dependency
    try:
        response=client.get('/api/v1/indicadores?limite=invalido')
        assert response.status_code==422
        assert 'query.limite' in response.json()['erro']['mensagem']
        assert 'janela' not in response.json()['erro']['mensagem']
    finally:
        app.dependency_overrides.clear()


def test_valid_id_kept_on_fallback_and_failed_ids_not_exposed(populated,client):
    before=client.get('/api/v1/indicadores/desocupacao/serie').json()
    with populated() as session:
        assert session.get(Coleta,before['coleta_id']).valida is True
    def failure(request):
        return httpx.Response(503,headers={'Retry-After':'0'})
    with pytest.raises(SourceFailure):
        collect(populated,failure)
    after=client.get('/api/v1/indicadores/desocupacao/serie').json()
    assert after['desatualizado'] is True and after['coleta_id']==before['coleta_id']
    with populated() as session:
        failed_ids=set(session.scalars(select(Coleta.id).where(Coleta.erro.is_not(None))))
    assert after['coleta_id'] not in failed_ids


@pytest.mark.parametrize('kind',['valid','failed','metadata','other_series','wrong_mode'])
def test_error_handler_only_exposes_valid_collection_reference(populated,client,kind):
    def failure(request):
        return httpx.Response(503)
    with pytest.raises(SourceFailure):
        collect(populated,failure)
    with populated() as session:
        if kind=='failed':
            candidate=session.scalar(select(Coleta.id).where(Coleta.erro.is_not(None)))
        elif kind=='metadata':
            candidate=session.scalar(select(Coleta.id).where(Coleta.tipo=='metadados'))
        else:
            code='rendimento-real' if kind=='other_series' else 'desocupacao'
            candidate=session.scalar(select(Coleta.id).where(Coleta.valida.is_(True),Coleta.serie_codigo==code))
    def fail_dependency():
        raise SourceFailure('erro_conexao',503,candidate)
    app.dependency_overrides[get_session]=fail_dependency
    if kind=='wrong_mode':
        app.state.test_mode=False
    try:
        response=client.get('/api/v1/indicadores/desocupacao/serie')
        assert response.status_code==503
        assert response.json()['erro']['ultima_coleta_id']==(candidate if kind=='valid' else None)
    finally:
        app.dependency_overrides.clear()
        app.state.test_mode=True


@pytest.mark.parametrize('status,header,expected',[(429,'2',2),(503,'80',60),(503,'0',0),
    (503,'0000',0),(503,'9'*100,60),(503,'bad',0.25),(503,'-1',0.25),
    (503,None,0.25),(500,'30',0.25)])
def test_retry_after_seconds_and_fallback(status,header,expected):
    response=httpx.Response(status,headers={'Retry-After':header} if header is not None else {})
    assert retry_delay(response,0)==expected


@pytest.mark.parametrize('seconds,expected',[(-10,0),(10,10),(600,60)])
def test_retry_after_http_date(seconds,expected):
    now=datetime(2026,10,16,12,tzinfo=timezone.utc)
    response=httpx.Response(503,headers={'Retry-After':format_datetime(now+timedelta(seconds=seconds),usegmt=True)})
    assert retry_delay(response,0,now=now)==expected


@pytest.mark.parametrize('status,expected',[(429,[60,60]),(503,[60,60])])
def test_collector_obeys_retry_after_without_real_wait(sf,status,expected):
    delays=[]
    async def sleep(delay):
        delays.append(delay)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda r:httpx.Response(status,headers={'Retry-After':'90'}))) as client:
            with pytest.raises(SourceFailure):
                await Collector(sf,client,simulada=True,sleep=sleep).collect('desocupacao')
    asyncio.run(run())
    assert delays==expected


def test_httpx_connection_limits(monkeypatch):
    received={}
    original=httpx.AsyncClient
    def factory(**kwargs):
        received.update(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(httpx,'AsyncClient',factory)
    client=make_client()
    try:
        assert received['limits'].max_connections==5
        assert received['limits'].max_keepalive_connections==5
    finally:
        asyncio.run(client.aclose())


@pytest.mark.parametrize('length',[500,501])
def test_calendar_cli_length(length):
    if length==500:
        assert bounded_text('x'*length)=='x'*length
    else:
        with pytest.raises(argparse.ArgumentTypeError):
            bounded_text('x'*length)


@pytest.mark.parametrize('field',['source','link'])
@pytest.mark.parametrize('length',[500,501])
def test_calendar_register_length(sf,field,length):
    source='x'*length if field=='source' else 'IBGE — teste simulado'
    prefix='https://www.ibge.gov.br/'
    link=prefix+'x'*(length-len(prefix)) if field=='link' else prefix
    with sf.begin() as session:
        if length==501:
            with pytest.raises(ValueError,match='500'):
                register(session,'desocupacao','202609',datetime(2026,10,16,tzinfo=timezone.utc),source,link)
        else:
            register(session,'desocupacao','202609',datetime(2026,10,16,tzinfo=timezone.utc),source,link)


def test_migration_131_preserves_existing_ibge_data(engine,sf,replay):
    collect(sf,replay)
    command.downgrade(alembic_config(),'0001')
    with engine.connect() as connection:
        from sqlalchemy import text
        assert connection.scalar(text("SELECT tipo_valor FROM serie WHERE codigo='desocupacao'"))=='nominal'
        assert connection.scalar(text('SELECT count(*) FROM observacao'))==174
    command.upgrade(alembic_config(),'head')
    with sf() as session:
        assert session.scalar(select(Serie.tipo_valor).where(Serie.codigo=='desocupacao')) is None
        assert session.scalar(select(Serie.disponivel).where(Serie.codigo=='caged-saldo')) is False
