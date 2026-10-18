import hashlib
import json
from decimal import Decimal as D

import httpx
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, inspect, select

from backend.oil.catalog import SPECS
from backend.oil.ingest import Collector, SourceFailure
from backend.oil.models import Base, Coleta, Fonte, Observacao, Serie
from .conftest import FIXTURES, alembic_config, collect


def test_migration_up_down_up(engine, sf):
    expected = {'fonte','coleta','serie','observacao','divulgacao'}
    assert expected <= set(inspect(engine).get_table_names())
    command.downgrade(alembic_config(), 'base')
    assert not expected.intersection(inspect(engine).get_table_names())
    command.upgrade(alembic_config(), 'head')
    assert expected <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_collections_keep_raw_hash_and_lineage(sf, replay):
    result = collect(sf, replay)
    assert result['simulada'] is True and result['novas_versoes'] == 174
    with sf() as session:
        collections = session.scalars(select(Coleta).order_by(Coleta.id)).all()
        assert len(collections) == 2
        for item in collections:
            assert item.simulada is True
            assert item.coletado_em.tzinfo is not None
            assert item.codigo_http == 200
            assert hashlib.sha256(item.resposta_bruta).hexdigest() == item.hash_sha256
        assert collections[1].valida is True
        serie = session.scalar(select(Serie).where(Serie.codigo=='desocupacao'))
        assert (serie.tabela,serie.variavel,serie.tipo_periodo,serie.base_precos)==('6381','4099','trimestre_movel',None)
        assert session.scalar(select(Fonte.nome).where(Fonte.codigo=='ibge-sidra')) == 'IBGE / PNAD Contínua / SIDRA'
        observation = session.scalar(select(Observacao).where(Observacao.periodo=='202608'))
        assert observation.coleta_id == result['coleta_id']
        assert observation.classificacao_origem == 'calculada'
        assert observation.valor == D('5.3')


def test_identical_response_does_not_create_versions(sf, replay):
    collect(sf,replay)
    result = collect(sf,replay)
    assert result['novas_versoes'] == 0
    with sf() as session:
        assert session.scalar(select(func.count()).select_from(Observacao)) == 174
        assert session.scalar(select(func.count()).select_from(Coleta)) == 4


def test_revision_preserves_previous_version(sf, replay):
    first = collect(sf,replay)
    def revised(r):
        if str(r.url)==SPECS['desocupacao'].url:
            data=json.loads((FIXTURES/'sidra-6381.json').read_bytes())
            for row in data[1:]:
                if row['D3C']=='202608' and row['D2C']=='4099':
                    row['V']='5.4'  # MUTACAO SINTETICA exclusiva de teste de revisão.
            return httpx.Response(200,json=data)
        return replay(r)
    second=collect(sf,revised)
    assert second['novas_versoes']==1
    with sf() as session:
        versions=session.scalars(select(Observacao).where(Observacao.periodo=='202608')
                                 .order_by(Observacao.versao)).all()
        assert [(o.versao,o.valor) for o in versions]==[(1,D('5.3')),(2,D('5.4'))]
        assert [o.coleta_id for o in versions]==[first['coleta_id'],second['coleta_id']]


def test_income_lineage_and_classification(populated):
    with populated() as session:
        serie=session.scalar(select(Serie).where(Serie.codigo=='rendimento-real'))
        assert (serie.variavel_variacao,serie.variavel_diferenca)==('8837','8838')
        item=session.scalar(select(Observacao).where(Observacao.serie_id==serie.id,Observacao.periodo=='202608'))
        assert item.valor==D(3777) and item.cv==D('0.7')
        assert item.diferenca_anual==D(136) and item.classificacao=='subiu'
        assert item.variacao_anual != item.diferenca_anual


@pytest.mark.parametrize('kind,expected_status,attempts', [('timeout',504,3),('connect',503,3),(503,503,3),(404,502,1)])
def test_errors_are_audited_and_retries_limited(sf, kind, expected_status, attempts):
    def handler(request):
        if kind=='timeout':
            raise httpx.ReadTimeout('SIMULADA',request=request)
        if kind=='connect':
            raise httpx.ConnectError('SIMULADA',request=request)
        return httpx.Response(kind)
    with pytest.raises(SourceFailure) as error:
        collect(sf,handler)
    assert error.value.status==expected_status
    with sf() as session:
        rows=session.scalars(select(Coleta)).all()
        assert len(rows)==attempts and all(r.erro and r.simulada for r in rows)
        assert session.scalar(select(func.count()).select_from(Observacao))==0


def test_unexpected_response_keeps_raw_without_observations(sf, replay):
    def handler(request):
        if 'apisidra' in str(request.url):
            return httpx.Response(200,text='INVALIDO SIMULADO')
        return replay(request)
    with pytest.raises(SourceFailure) as error:
        collect(sf,handler)
    assert error.value.code=='resposta_invalida'
    with sf() as session:
        assert session.scalar(select(func.count()).select_from(Observacao))==0
        failed=session.scalar(select(Coleta).where(Coleta.tipo=='valores'))
        assert failed.resposta_bruta==b'INVALIDO SIMULADO' and failed.erro=='resposta_invalida'


def test_simulation_requires_explicit_test_mode(sf, monkeypatch):
    monkeypatch.delenv('OIL_TEST_MODE')
    with pytest.raises(ValueError,match='somente em modo de teste'):
        Collector(sf,None,simulada=True)


@pytest.mark.parametrize('mode',['omitted','missing'])
def test_missing_cv_keeps_level_but_no_classification(sf,replay,mode):
    def handler(request):
        response=replay(request)
        if 'apisidra' in str(request.url):
            payload=response.json()
            if mode=='omitted':
                payload=[payload[0]]+[r for r in payload[1:] if not (r['D3C']=='202608' and r['D2C']=='4103')]
            else:
                for row in payload[1:]:
                    if row['D3C']=='202608' and row['D2C']=='4103':
                        row['V']='...'
            return httpx.Response(200,json=payload)
        return response
    collect(sf,handler)
    with sf() as session:
        point=session.scalar(select(Observacao).where(Observacao.periodo=='202608'))
        assert point.valor==D('5.3') and point.cv is None and point.classificacao is None


def test_revision_of_previous_year_cv_recalculates_current_classification(sf,replay):
    collect(sf,replay)
    def revised(request):
        response=replay(request)
        if 'apisidra' in str(request.url):
            data=response.json()
            for row in data[1:]:
                if row['D3C']=='202508' and row['D2C']=='4103':
                    row['V']='100'  # REVISAO SINTETICA para alterar margem de erro.
            return httpx.Response(200,json=data)
        return response
    collect(sf,revised)
    with sf() as session:
        points=session.scalars(select(Observacao).where(Observacao.periodo=='202608')
                               .order_by(Observacao.versao)).all()
        assert [(p.versao,p.classificacao) for p in points]==[(1,'caiu'),(2,'estavel')]
