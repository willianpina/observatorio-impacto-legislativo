import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from sqlalchemy.exc import SQLAlchemyError

from poc import app as legacy
from .catalog import SPECS
from .db import make_engine, sessions
from .read import read_index, read_series
from .ingest import SourceFailure
from .schemas import IndexResponse, SeriesResponse


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


app = FastAPI(title='OIL — séries IBGE', version='1.3', lifespan=lifespan)
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
    return JSONResponse(status_code=exc.status, headers=headers, content={
        'erro': {'codigo': exc.code, 'mensagem': 'A fonte não forneceu uma coleta válida.',
                 'fonte': 'IBGE / SIDRA', 'tentar_novamente_em': 60 if exc.status == 503 else None,
                 'ultima_coleta_id': exc.collection_id}})


@app.exception_handler(RequestValidationError)
async def invalid_parameters(request, exc):
    if not request.url.path.startswith('/api/v1/'):
        return await request_validation_exception_handler(request, exc)
    return JSONResponse(status_code=422, content={
        'erro': {'codigo': 'parametro_invalido', 'mensagem': 'Use janela=2a, 5a ou desde_2020.',
                 'fonte': 'api_local', 'tentar_novamente_em': None, 'ultima_coleta_id': None}})


@app.exception_handler(SQLAlchemyError)
async def database_failure(request, exc):
    # Não inclui exceção SQL, parâmetros ou URL do banco na resposta.
    return JSONResponse(status_code=503, headers={'Retry-After': '60'}, content={
        'erro': {'codigo': 'banco_indisponivel', 'mensagem': 'Banco local temporariamente indisponível.',
                 'fonte': 'banco_local', 'tentar_novamente_em': 60, 'ultima_coleta_id': None}})


@app.exception_handler(HTTPException)
async def http_failure(request, exc):
    return JSONResponse(status_code=exc.status_code, content={
        'erro': {'codigo': 'indicador_inexistente', 'mensagem': str(exc.detail),
                 'fonte': 'catalogo_local', 'tentar_novamente_em': None, 'ultima_coleta_id': None}})


Window = Literal['2a', '5a', 'desde_2020']


@app.get('/api/v1/indicadores', response_model=IndexResponse)
def indicators(request: Request, janela: Window = Query('5a'), session=Depends(get_session)):
    return read_index(session, janela, test_mode=request.app.state.test_mode)


@app.get('/api/v1/indicadores/{codigo}/serie', response_model=SeriesResponse)
@app.get('/api/v1/indicadores/{codigo}', response_model=SeriesResponse)
def series(codigo: str, request: Request, janela: Window = Query('5a'), session=Depends(get_session)):
    if codigo not in SPECS:
        raise HTTPException(404, 'Indicador não cadastrado na O2.')
    return read_series(session, codigo, janela, test_mode=request.app.state.test_mode)
