"""Guarda textual da API e de toda a documentação: somente descrição dos dados."""
import asyncio
import json
import unicodedata

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError

from backend.oil.ingest import SourceFailure
from backend.oil.main import app, get_session
from backend.oil.models import Coleta, Observacao, Serie
from .conftest import ROOT, collect

FORBIDDEN = ('causou','graças a','por causa da lei','depois da aprovação',
             'desde a promulgação','efeito da lei')


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC',text).casefold().split())


def strings(value,path='$'):
    if isinstance(value,str):
        yield path,value
    elif isinstance(value,dict):
        for key,item in value.items():
            yield from strings(item,f'{path}.{key}')
    elif isinstance(value,list):
        for index,item in enumerate(value):
            yield from strings(item,f'{path}[{index}]')


@pytest.fixture
def response_texts(populated,client):
    corpus=[]
    def capture(path,method='get'):
        response=getattr(client,method)(path)
        corpus.extend(strings(response.json(),f'{method} {path}'))
        return response
    for path in ['/api/v1/indicadores',
                 '/api/v1/indicadores/desocupacao/serie',
                 '/api/v1/indicadores/rendimento-real/serie',
                 '/api/v1/indicadores/caged-saldo',
                 '/api/v1/indicadores/caged-saldo/serie',
                 '/api/v1/indicadores/inexistente/serie',
                 '/api/v1/indicadores?janela=invalida','/nao-existe']:
        capture(path)
    capture('/api/v1/indicadores','post')
    # Inclui nomes, motivos das lacunas e resposta indisponível por ausência de coleta.
    with populated.begin() as session:
        sid=session.scalar(select(Serie.id).where(Serie.codigo=='desocupacao'))
        session.execute(delete(Observacao).where(Observacao.serie_id==sid,Observacao.periodo=='202607'))
    capture('/api/v1/indicadores/desocupacao/serie')
    app.state.test_mode=False
    try:
        capture('/api/v1/indicadores/desocupacao/serie')
    finally:
        app.state.test_mode=True
    # Erros de fonte sem coleta boa, sempre simulados.
    with populated.begin() as session:
        sid=session.scalar(select(Serie.id).where(Serie.codigo=='rendimento-real'))
        session.execute(delete(Observacao).where(Observacao.serie_id==sid))
        session.execute(delete(Coleta).where(Coleta.serie_codigo=='rendimento-real'))
    for kind in ('connect','timeout','invalid'):
        def failure(request):
            if kind=='connect':
                raise httpx.ConnectError('FALHA SIMULADA',request=request)
            if kind=='timeout':
                raise httpx.ReadTimeout('FALHA SIMULADA',request=request)
            return httpx.Response(200,text='RESPOSTA INVALIDA SIMULADA')
        with pytest.raises(SourceFailure):
            collect(populated,failure,'rendimento-real')
        capture('/api/v1/indicadores/rendimento-real/serie')
    for status in (400,401,403,404,405,409,503):
        def deny():
            raise HTTPException(status,'Requisição de teste indisponível.')
        app.dependency_overrides[get_session]=deny
        try:
            capture('/api/v1/indicadores')
        finally:
            app.dependency_overrides.clear()
    def db_failure():
        raise OperationalError('SIMULADO',{},Exception('Falha simulada'))
    app.dependency_overrides[get_session]=db_failure
    try:
        capture('/api/v1/indicadores')
    finally:
        app.dependency_overrides.clear()
    # Inclui também as duas rotas originais, com suas respostas gravadas inalteradas.
    evidence=json.loads((ROOT/'poc/evidencias/consultas-reais.json').read_bytes())
    mapping={r['url']:r['payload'] for r in evidence if 'payload' in r}
    mock=httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request:httpx.Response(200,json=mapping[str(request.url)])))
    original=app.state.client
    app.state.client=mock
    try:
        capture('/api/legislacao')
        capture('/api/indicadores/desemprego')
        capture('/api/legislacao?limite=invalido')
    finally:
        app.state.client=original
        asyncio.run(mock.aclose())
    return corpus


@pytest.mark.parametrize('phrase',FORBIDDEN)
def test_no_forbidden_phrases_in_api(response_texts,phrase):
    for path,text in response_texts:
        assert normalized(phrase) not in normalized(text), f'Texto proibido no campo {path}'


@pytest.mark.parametrize('phrase',FORBIDDEN)
def test_no_forbidden_phrases_in_all_docs(phrase):
    documents=[p for p in (ROOT/'docs').rglob('*') if p.is_file()]
    assert documents
    for document in documents:
        assert not (document.name=='.env' or document.name.startswith('.env.')), 'Arquivo de ambiente não permitido em docs/.'
        assert normalized(phrase) not in normalized(document.read_text(encoding='utf-8')), str(document.relative_to(ROOT))
