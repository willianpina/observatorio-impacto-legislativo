"""Contrato v1.5.0 da atribuição do Caged. Os números vêm da API anterior à mudança."""
import json
import re
from datetime import datetime, timedelta

from sqlalchemy import select

from backend.oil.caged import MTE
from backend.oil.main import app
from backend.oil.models import Coleta
from .conftest import FIXTURES, ROOT
from .test_o3_caged import entry, ingest_caged

TEXTO = ('Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes). '
         'Série revisada mensalmente. Elaboração: OIL.')
BASE_LEGAL = 'Decreto 8.777/2016, art. 4º'
PAGINA = MTE + '/novo-caged'
MESES = ('janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro')
COMPETENCIA = re.compile(r'[0-9]{4}-(0[1-9]|1[0-2])')
SNAPSHOT = FIXTURES / 'o3' / 'caged_numeros_api.json'


def forbidden_designation():
    return 'C' + 'C BY-' + 'ND'


def atribuicao(client):
    response = client.get('/api/v1/indicadores/caged-saldo')
    assert response.status_code == 200
    return response.json()


def coleta_servida(sf, competencia):
    with sf() as session:
        item = session.scalar(select(Coleta).where(
            Coleta.mes_referencia == competencia, Coleta.valida.is_(True)
        ).order_by(Coleta.id.desc()).limit(1))
        session.expunge(item)
        return item


def numeros(data):
    return {
        'valor': data['valor'],
        'variacao_anual': data['variacao_anual'],
        'periodo': data['periodo'],
        'tipo_valor': data['tipo_valor'],
        'medida': data['medida'],
        'unidade': data['unidade'],
        'classificacao': data['classificacao'],
        'nota_revisao': data['nota_revisao'],
        'tipo_periodo': data['tipo_periodo'],
        'cv': data['cv'],
        'variacao_anual_origem': data['variacao_anual_origem'],
        'ajuste': data['ajuste'],
        'competencia_coleta': data['competencia_coleta'],
        'pontos': [
            {'periodo': ponto['periodo'], 'valor': ponto['valor'],
             'variacao_anual': ponto['variacao_anual'], 'lacuna': ponto['lacuna'],
             'versao': ponto['versao']}
            for ponto in data['pontos']],
    }


def test_v150_atribuicao_sem_licenca_e_base_legal_exata(sf, client):
    ingest_caged(sf)
    data = atribuicao(client)['atribuicao']
    rendered = json.dumps(data, ensure_ascii=False)
    assert forbidden_designation() not in rendered
    assert 'licenca' not in data
    assert data['base_legal'] == BASE_LEGAL


def test_v150_arquivo_referencia_da_coleta_servida(sf, client):
    ingest_caged(sf, '2026-07')
    julho = atribuicao(client)['atribuicao']
    assert COMPETENCIA.fullmatch(julho['arquivo_referencia'])
    assert julho['arquivo_referencia'] == '2026-07'
    julho_coleta = coleta_servida(sf, '2026-07')
    assert datetime.fromisoformat(julho['coletado_em']) == julho_coleta.coletado_em
    ingest_caged(sf, '2026-08')
    agosto = atribuicao(client)['atribuicao']
    agosto_coleta = coleta_servida(sf, '2026-08')
    assert COMPETENCIA.fullmatch(agosto['arquivo_referencia'])
    assert agosto['arquivo_referencia'] == '2026-08'
    assert datetime.fromisoformat(agosto['coletado_em']) == agosto_coleta.coletado_em
    assert agosto['coletado_em'] != julho['coletado_em']


def test_v150_coletado_em_utc_com_fuso(sf, client):
    ingest_caged(sf)
    bruto = atribuicao(client)['atribuicao']['coletado_em']
    assert isinstance(bruto, str)
    assert bruto.endswith('Z') or bruto.endswith('+00:00')
    instante = datetime.fromisoformat(bruto.replace('Z', '+00:00'))
    assert instante.utcoffset() == timedelta(0)
    servida = coleta_servida(sf, '2026-08')
    assert instante == servida.coletado_em


def test_v150_texto_fixo_sem_data_nem_mes(sf, client):
    ingest_caged(sf)
    data = atribuicao(client)['atribuicao']
    assert data['texto'] == TEXTO
    assert data['link'] == entry('2026-08')[0]['pagina_oficial']
    assert not re.search(r'\d{2}/\d{2}/\d{4}|\d{4}-\d{2}', data['texto'])
    assert not any(mes in data['texto'].casefold() for mes in MESES)


def test_v150_sem_coleta_campos_nulos(client):
    response = client.get('/api/v1/indicadores/caged-saldo')
    assert response.status_code == 200
    data = response.json()
    assert data['disponivel'] is False
    corpo = data['atribuicao']
    assert corpo['arquivo_referencia'] is None
    assert corpo['coletado_em'] is None
    assert corpo['texto'] == TEXTO
    assert corpo['base_legal'] == BASE_LEGAL
    assert corpo['link'] == PAGINA
    assert 'licenca' not in corpo


def test_v150_numeros_da_api_iguais_ao_snapshot(sf, client):
    ingest_caged(sf)
    esperado = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    assert numeros(atribuicao(client)) == esperado


def test_v150_openapi_atualizado():
    esquema = app.openapi()
    assert esquema['info']['version'] == '1.5.0'
    modelos = esquema['components']['schemas']
    atribuicao_esquema = modelos['Atribuicao']
    assert atribuicao_esquema['additionalProperties'] is False
    assert 'licenca' not in atribuicao_esquema['properties']
    assert 'BaseLegal' not in modelos
    assert atribuicao_esquema['properties']['base_legal']['type'] == 'string'
    assert 'arquivo_referencia' in atribuicao_esquema['required']
    assert 'coletado_em' in atribuicao_esquema['required']
    documento = json.loads((ROOT / 'docs/o3/openapi-v1.5.0.json').read_text(encoding='utf-8'))
    assert documento['info']['version'] == '1.5.0'
    assert documento['components']['schemas']['Atribuicao'] == atribuicao_esquema
    contrato = (ROOT / 'docs/o3/contrato-api-v1.5.0-delta.md').read_text(encoding='utf-8')
    especificacao = (ROOT / 'docs/o3/spec-b4-caged.md').read_text(encoding='utf-8')
    for texto in (contrato, especificacao):
        assert '1.5.0' in texto
        assert TEXTO in texto
        assert BASE_LEGAL in texto
        assert 'arquivo_referencia' in texto
