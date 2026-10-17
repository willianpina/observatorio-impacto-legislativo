import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from poc import app as legacy
from .catalog import INDICATOR_CODES
from .db import make_engine, sessions
from .read import read_index, read_series
from .ingest import SourceFailure
from .schemas import IndexResponse, SeriesResponse
from .models import Coleta


@asynccontextmanager
async def lifespan(app):
    engine = make_engine()
    app.state.sessions = sessions(engine)
    app.state.test_mode = os.environ.get('OIL_TEST_MODE') == '1'
    try:
        async with legacy.make_client() as client:
            app.state.client = client
            yield
    finally:
        engine.dispose()


app = FastAPI(title='OIL — séries IBGE', version='1.3.1', lifespan=lifespan)
# Mesmo código, caminho e tratamento de erros; nenhuma mudança em poc/.
app.add_exception_handler(legacy.SourceError, legacy.source_error)
for route in legacy.app.routes:
    if getattr(route, 'path', '') in {'/api/legislacao', '/api/indicadores/desemprego'}:
        app.router.routes.append(route)


def get_session(request: Request):
    with request.app.state.sessions() as session:
        yield session


@app.exception_handler(SourceFailure)
async def source_failure(request, exc):
    headers = {'Retry-After': '60'} if exc.status == 503 else None
    last_valid_id = None
    # O ID de auditoria da tentativa não é prova de coleta boa. Valida a referência
    # antes de expô-la, incluindo isolamento das respostas simuladas.
    if isinstance(exc.collection_id,int):
        try:
            with request.app.state.sessions() as session:
                query = select(Coleta.id).where(Coleta.id==exc.collection_id,
                    Coleta.valida.is_(True),Coleta.simulada==request.app.state.test_mode)
                codigo = request.path_params.get('codigo')
                if codigo is not None:
                    query = query.where(Coleta.serie_codigo==codigo)
                last_valid_id = session.scalar(query)
        except SQLAlchemyError:
            last_valid_id = None
    return JSONResponse(status_code=exc.status, headers=headers, content={
        'erro': {'codigo': exc.code, 'mensagem': 'A fonte não forneceu uma coleta válida.',
                 'fonte': 'IBGE / SIDRA', 'tentar_novamente_em': 60 if exc.status == 503 else None,
                 'ultima_coleta_id': last_valid_id}})


@app.exception_handler(RequestValidationError)
async def invalid_parameters(request, exc):
    if not indicator_path(request.url.path):
        return await request_validation_exception_handler(request, exc)
    parameters = ', '.join(sorted({'.'.join(map(str,item['loc'])) for item in exc.errors()}))
    return JSONResponse(status_code=422, content={
        'erro': {'codigo': 'parametro_invalido', 'mensagem': f'Parâmetro inválido: {parameters}.',
                 'fonte': 'api_local', 'tentar_novamente_em': None, 'ultima_coleta_id': None}})


@app.exception_handler(SQLAlchemyError)
async def database_failure(request, exc):
    # Não inclui exceção SQL, parâmetros ou URL do banco na resposta.
    return JSONResponse(status_code=503, headers={'Retry-After': '60'}, content={
        'erro': {'codigo': 'banco_indisponivel', 'mensagem': 'Banco local temporariamente indisponível.',
                 'fonte': 'banco_local', 'tentar_novamente_em': 60, 'ultima_coleta_id': None}})


def indicator_path(path):
    return path == '/api/v1/indicadores' or path.startswith('/api/v1/indicadores/')


@app.exception_handler(StarletteHTTPException)
async def http_failure(request, exc):
    if not indicator_path(request.url.path):
        return await http_exception_handler(request,exc)
    codes = {400:'requisicao_invalida',401:'nao_autorizado',403:'acesso_negado',
             404:'indicador_inexistente',405:'metodo_nao_permitido',503:'fonte_indisponivel'}
    headers = dict(exc.headers or {})
    if exc.status_code == 503:
        headers.setdefault('Retry-After','60')
    return JSONResponse(status_code=exc.status_code, headers=headers, content={
        'erro': {'codigo': codes.get(exc.status_code,f'http_{exc.status_code}'), 'mensagem': str(exc.detail),
                 'fonte': 'catalogo_local', 'tentar_novamente_em': None, 'ultima_coleta_id': None}})


Window = Literal['2a', '5a', 'desde_2020']


@app.get('/api/v1/indicadores', response_model=IndexResponse)
def indicators(request: Request, janela: Window = Query('5a'), session=Depends(get_session)):
    return read_index(session, janela, test_mode=request.app.state.test_mode)


@app.get('/api/v1/indicadores/{codigo}/serie', response_model=SeriesResponse)
def series(codigo: str, request: Request, janela: Window = Query('5a'), session=Depends(get_session)):
    if codigo not in INDICATOR_CODES:
        raise HTTPException(404, 'Indicador não cadastrado na O2.')
    return read_series(session, codigo, janela, test_mode=request.app.state.test_mode)


@app.get('/api/v1/indicadores/caged-saldo', response_model=SeriesResponse)
def unavailable_caged(request: Request,janela: Window = Query('5a'),session=Depends(get_session)):
    return read_series(session,'caged-saldo',janela,test_mode=request.app.state.test_mode)
