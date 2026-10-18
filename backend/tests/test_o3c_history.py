"""Replay minimizado do histórico oficial, sem rede."""
import json
import httpx
from sqlalchemy import select
from backend.oil.models import Coleta
from .conftest import FIXTURES
from .test_o3_law import CAMARA,payload,replay_law,ingest_law

HISTORY='https://dadosabertos.camara.leg.br/api/v2/deputados/74161/historico'

def test_o3c_party_at_presentation_from_recorded_history(sf,client):
    fixture=json.loads((FIXTURES/'o3/camara_74161_historico_2026-10-18.json').read_text(encoding='utf8'))
    assert fixture['simulada'] is True
    def handler(request):
        if str(request.url)==CAMARA+'/autores':return httpx.Response(200,json={'dados':[{'nome':'Reginaldo Lopes','ordemAssinatura':1,'uri':HISTORY.removesuffix('/historico')}]})
        if str(request.url)==HISTORY:return httpx.Response(200,json={'dados':fixture['dados']})
        if str(request.url)==HISTORY.removesuffix('/historico'):return httpx.Response(200,json={'dados':{'id':74161,'ultimoStatus':{'siglaPartido':'TESTE','siglaUf':'DF'}}})
        return replay_law()(request)
    ingest_law(sf,handler);data=client.get('/api/v1/proposicoes/2233802').json()
    when=payload('camara')['dados']['dataApresentacao']
    expected=max((r for r in fixture['dados'] if r['dataHora']<=when),key=lambda r:r['dataHora'])
    assert data['partido']==expected['siglaPartido'] and data['uf']==expected['siglaUf']
    assert data['partido_referencia']=='apresentacao' and data['autoria_motivo']
    with sf() as session:
        collection=session.scalar(select(Coleta).where(Coleta.url_consultada==HISTORY))
        assert collection is not None
        saved=json.loads(collection.resposta_bruta)
        assert all(set(r)<={'id','nome','siglaPartido','siglaUf','dataHora'} for r in saved['dados'])

def test_o3c_history_body_is_minimized_even_with_synthetic_extras(sf,client):
    def handler(request):
        if str(request.url)==CAMARA+'/autores':return httpx.Response(200,json={'dados':[{'nome':'Autor sintético','ordemAssinatura':1,'uri':HISTORY.removesuffix('/historico')}]})
        if str(request.url)==HISTORY:return httpx.Response(200,json={'dados':[{'id':74161,'nome':'Autor sintético','siglaPartido':'TESTE','siglaUf':'DF','dataHora':'2019-02-01T00:00','cpf':'CPF_SINTETICO_INVALIDO','email':'EMAIL_SINTETICO_INVALIDO'}]})
        if str(request.url)==HISTORY.removesuffix('/historico'):return httpx.Response(200,json={'dados':{'ultimoStatus':{'siglaPartido':'TESTE','siglaUf':'DF'}}})
        return replay_law()(request)
    ingest_law(sf,handler)
    with sf() as session:
        collection=session.scalar(select(Coleta).where(Coleta.url_consultada==HISTORY))
        assert collection is not None
        raw=collection.resposta_bruta.decode()
        assert 'cpf' not in raw and 'email' not in raw and 'SINTETICO_INVALIDO' not in raw
