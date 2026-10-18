"""O3 B2: testes escritos antes da implementação; replay sem rede."""
import asyncio
import copy
import importlib
import json

import httpx
import pytest
from alembic import command
from sqlalchemy import func, inspect, select

from backend.oil.ingest import SourceFailure
from backend.oil.main import app
from backend.oil.models import Coleta
from .conftest import FIXTURES, alembic_config, no_sleep

CAMARA='https://dadosabertos.camara.leg.br/api/v2/proposicoes/2233802'
SENADO='https://legis.senado.leg.br/dadosabertos/processo/9056435?v=1'


def payload(casa):
    name='camara_2233802_2026-10-17.json' if casa=='camara' else 'senado_9056435_2026-10-17.json'
    return json.loads((FIXTURES/'o3'/name).read_bytes())


def replay_law(*,camara=None,senado=None,fail=None):
    def handler(request):
        if str(request.url) not in {CAMARA,SENADO}:
            # Não inventa autoria ausente: resposta sintética vazia, marcada como teste pelo coletor.
            if str(request.url)==CAMARA+'/autores':return httpx.Response(200,json={'dados':[]})
            raise AssertionError('URL não gravada: '+str(request.url))
        casa='camara' if str(request.url)==CAMARA else 'senado'
        if fail in {casa,'ambas'}:raise httpx.ReadTimeout('TIMEOUT SIMULADO',request=request)
        return httpx.Response(200,json=(camara if casa=='camara' and camara is not None else senado if casa=='senado' and senado is not None else payload(casa)))
    return handler


def ingest_law(sf,handler=None):
    async def run():
        module=importlib.import_module('backend.oil.legislation')
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler or replay_law())) as client:
            return await module.LawCollector(sf,client,simulada=True,sleep=no_sleep).collect(2233802)
    return asyncio.run(run())


def test_o3_law_convergence_literal_status_tie_and_lineage(sf,client):
    ingest_law(sf)
    response=client.get('/api/v1/proposicoes/2233802');assert response.status_code==200
    data=response.json();assert data['simulada'] is True
    assert data['id_camara']==2233802 and data['id_senado']==9056435
    assert data['situacao_atual']['casa']=='senado' and data['situacao_atual']['divergencia'] is False
    assert data['situacao_atual']['regra']=='mais_recente'
    for item in data['situacao']:
        expected=payload('camara')['dados']['statusProposicao']['descricaoSituacao'] if item['casa']=='camara' else payload('senado')['situacaoAtual']
        assert item['situacao']==expected and item['coleta_id'] and item['coletado_em']
    assert data['norma_gerada'] is None and data['norma_gerada_motivo']
    assert len(data['fontes_norma'])==2
    assert {m['tipo'] for m in data['marcos']}=={'aprovacao_senado','promulgacao'}
    assert all(m['origem']=='fonte' and m['prevista'] is False for m in data['marcos'])


def test_o3_law_divergence_preserves_source_text(sf,client):
    altered=copy.deepcopy(payload('camara'));altered['dados']['statusProposicao']['descricaoSituacao']='Aguardando Apreciação pelo Senado'
    ingest_law(sf,replay_law(camara=altered));data=client.get('/api/v1/proposicoes/2233802').json()
    assert data['situacao_atual']['divergencia'] is True
    assert next(s for s in data['situacao'] if s['casa']=='camara')['situacao']=='Aguardando Apreciação pelo Senado'


def test_o3_law_newer_camara_wins(sf,client):
    altered=copy.deepcopy(payload('camara'));altered['dados']['statusProposicao']['dataHora']='2026-10-17T12:00'
    ingest_law(sf,replay_law(camara=altered));assert client.get('/api/v1/proposicoes/2233802').json()['situacao_atual']['casa']=='camara'


def test_o3_law_generated_norm_only_when_source_supplies(sf,client):
    altered=copy.deepcopy(payload('senado'));altered['normaGerada']={'rotulo':'Norma sintética de teste','data':'2026-10-16','link':'https://www.planalto.gov.br/'}
    ingest_law(sf,replay_law(senado=altered));norm=client.get('/api/v1/proposicoes/2233802').json()['norma_gerada']
    assert norm['rotulo']=='Norma sintética de teste'


def test_o3_law_one_house_offline(sf,client):
    ingest_law(sf,replay_law(fail='senado'));response=client.get('/api/v1/proposicoes/2233802')
    assert response.status_code==200;data=response.json()
    assert data['situacao_atual']['regra']=='unica_disponivel'
    assert next(s for s in data['situacao'] if s['casa']=='senado')['disponivel'] is False


def test_o3_law_both_offline_no_valid_id(sf,client):
    with pytest.raises(SourceFailure):ingest_law(sf,replay_law(fail='ambas'))
    response=client.get('/api/v1/proposicoes/2233802');assert response.status_code==504
    assert response.json()['erro']['ultima_coleta_id'] is None


def test_o3_law_invalid_schema_does_not_create_snapshot(sf):
    ingest_law(sf,replay_law(senado={'id':9056435}))
    with sf() as session:
        invalid=session.scalars(select(Coleta).where(Coleta.serie_codigo=='proposicao:2233802:senado')).all()
        assert invalid and all(not c.valida for c in invalid)


def test_o3_law_versions_only_on_change(sf):
    models=importlib.import_module('backend.oil.models');snapshot=getattr(models,'ProposicaoSnapshot')
    ingest_law(sf);ingest_law(sf)
    with sf() as session:assert session.scalar(select(func.count()).select_from(snapshot))==2
    altered=copy.deepcopy(payload('camara'));altered['dados']['statusProposicao']['descricaoSituacao']='Situação sintética alterada'
    ingest_law(sf,replay_law(camara=altered))
    with sf() as session:assert session.scalar(select(func.count()).select_from(snapshot))==3


@pytest.mark.parametrize('identifier,status',[('999',404),('nao-numerico',422)])
def test_o3_law_identifiers_have_standard_errors(client,identifier,status):
    response=client.get('/api/v1/proposicoes/'+identifier);assert response.status_code==status
    assert set(response.json()['erro'])=={'codigo','mensagem','fonte','tentar_novamente_em','ultima_coleta_id'}


def test_o3_law_test_data_not_exposed_in_normal_mode(sf,client):
    ingest_law(sf);app.state.test_mode=False
    try:
        response=client.get('/api/v1/proposicoes/2233802');assert response.status_code in {502,503,504}
        assert response.json()['erro']['ultima_coleta_id'] is None
    finally:app.state.test_mode=True


def test_o3_law_authorship_principal_and_party_reference(sf,client):
    def handler(request):
        if str(request.url)==CAMARA+'/autores':
            return httpx.Response(200,json={'dados':[{'nome':'Autor simulado','ordemAssinatura':1,'uri':'https://dadosabertos.camara.leg.br/api/v2/deputados/1'},{'nome':'Coautor simulado','ordemAssinatura':2}]})
        if str(request.url)=='https://dadosabertos.camara.leg.br/api/v2/deputados/1':
            return httpx.Response(200,json={'dados':{'ultimoStatus':{'siglaPartido':'TESTE','siglaUf':'DF'}}})
        return replay_law()(request)
    ingest_law(sf,handler);data=client.get('/api/v1/proposicoes/2233802').json()
    assert data['autor']=='Autor simulado' and data['coautores']==1
    assert data['partido']=='TESTE' and data['uf']=='DF' and data['partido_referencia']=='atual'


def test_o3_law_no_hardcoded_norm_or_status_in_runtime():
    for path in (FIXTURES.parents[1]/'oil').glob('*.py'):
        text=path.read_text(encoding='utf-8')
        assert 'EC 141' not in text and 'Promulgada' not in text, path.name


@pytest.mark.parametrize('phrase',['causou','graças a','por causa da lei','depois da aprovação','desde a promulgação','efeito da lei'])
def test_o3_new_route_has_no_causal_phrases(sf,client,phrase):
    ingest_law(sf)
    assert phrase not in json.dumps(client.get('/api/v1/proposicoes/2233802').json(),ensure_ascii=False).casefold()


def test_o3_law_migration_up_down_up(sf,engine):
    command.downgrade(alembic_config(),'0002');assert 'proposicao' not in inspect(engine).get_table_names()
    command.upgrade(alembic_config(),'0003');assert {'proposicao','proposicao_snapshot','marco'}<=set(inspect(engine).get_table_names())
    command.upgrade(alembic_config(),'head')
