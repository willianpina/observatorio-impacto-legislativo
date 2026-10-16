"""PoC: somente fontes oficiais, consultas limitadas, sem persistência implícita."""
import asyncio
import logging
import ssl
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Literal

import httpx
import truststore
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

CAMARA = 'https://dadosabertos.camara.leg.br/api/v2/proposicoes'
METADATA = 'https://servicodados.ibge.gov.br/api/v3/agregados/4099/metadados'
SIDRA = 'https://apisidra.ibge.gov.br/values/t/4099/n1/all/v/4099/p/last%208'
logger = logging.getLogger('observatorio')


class SourceError(Exception):
    def __init__(self, code: str, source: str, status: int = 502):
        self.code, self.source, self.status = code, source, status


class Model(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)


class Status(Model):
    descricaoSituacao: str | None = None


class RawBill(Model):
    id: int = Field(gt=0)
    siglaTipo: str = Field(min_length=1)
    numero: int = Field(gt=0)
    ano: int = Field(ge=1900, le=2100)
    ementa: str  # Pode ser vazia na fonte; nunca é inventada.
    statusProposicao: Status | None = None


class Bill(Model):
    id: int
    tipo: str
    numero: int
    ano: int
    ementa: str
    situacao: str | None
    origem: str


class Observation(Model):
    periodo: str = Field(pattern=r'^\d{4}0[1-4]$')
    rotulo: str = Field(min_length=1)
    valor: float | None = Field(ge=0, le=100, allow_inf_nan=False)
    unidade: Literal['%']
    territorio: Literal['Brasil'] = 'Brasil'
    status: Literal['disponivel', 'ausente']
    valor_original: str
    origem: str


class Meta(Model):
    fonte: str
    coletado_em: str
    duracao_ms: float
    quantidade: int
    urls: list[str]
    periodicidade: str | None = None
    tabela: str | None = None
    variavel: str | None = None


class LegislationResponse(Model):
    dados: list[Bill]
    meta: Meta


class IndicatorResponse(Model):
    dados: list[Observation]
    meta: Meta


class SidraRow(Model):
    NC: Literal['1']
    D1C: Literal['1']
    D1N: Literal['Brasil']
    D2C: Literal['4099']
    D3C: str = Field(pattern=r'^\d{4}0[1-4]$')
    D3N: str = Field(min_length=1)
    MN: Literal['%']
    V: str


def metadata_check(data):
    if not isinstance(data, dict) or data.get('id') != 4099:
        raise ValueError('Tabela inesperada')
    if data.get('periodicidade', {}).get('frequencia') != 'trimestral':
        raise ValueError('Periodicidade inesperada')
    variables = data.get('variaveis', [])
    variable = next(v for v in variables if v['id'] == 4099)
    if variable['unidade'] != '%' or not variable['nome'].startswith('Taxa de desocupação,'):
        raise ValueError('Variável inesperada')


def parse_sidra(payload):
    if not isinstance(payload, list) or len(payload) != 9:
        raise ValueError('Esperados cabeçalho e oito períodos')
    header = payload[0]
    if not isinstance(header, dict) or header.get('D3C') != 'Trimestre (Código)':
        raise ValueError('Dimensões SIDRA inesperadas')
    results = []
    for item in payload[1:]:
        row = SidraRow.model_validate(item)
        missing = row.V in {'...', '..', '-', 'X'}
        results.append(Observation(
            periodo=row.D3C, rotulo=row.D3N,
            valor=None if missing else float(row.V.replace(',', '.')),
            unidade=row.MN, status='ausente' if missing else 'disponivel',
            valor_original=row.V, origem=SIDRA,
        ))
    results.sort(key=lambda x: x.periodo)
    if len({x.periodo for x in results}) != 8:
        raise ValueError('Períodos duplicados')
    ordinals = [int(x.periodo[:4]) * 4 + int(x.periodo[-2:]) for x in results]
    if any(b - a != 1 for a, b in zip(ordinals, ordinals[1:])):
        raise ValueError('Série não consecutiva')
    return results


class Gateway:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.evidence = []

    async def get(self, url, source, params=None):
        for attempt in range(3):
            start = perf_counter()
            record = {'url': str(httpx.URL(url, params=params)), 'tentativa': attempt + 1,
                      'coletado_em': datetime.now(timezone.utc).isoformat()}
            try:
                response = await self.client.get(url, params=params)
                record['status_http'] = response.status_code
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise SourceError('fonte_indisponivel', source, 503)
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError:
                    raise SourceError('resposta_invalida', source) from None
                record['payload'] = payload
                return payload
            except httpx.TimeoutException:
                error = SourceError('timeout_fonte', source, 504)
            except httpx.TransportError:
                error = SourceError('erro_conexao', source, 503)
            except httpx.HTTPStatusError:
                raise SourceError('http_fonte', source) from None
            except SourceError as exc:
                if exc.status != 503:
                    raise
                error = exc
            finally:
                record['duracao_ms'] = round((perf_counter() - start) * 1000, 2)
                self.evidence.append(record)
                logger.info('consulta fonte=%s tentativa=%s status=%s duracao_ms=%s',
                            source, attempt + 1, record.get('status_http'), record['duracao_ms'])
            if attempt < 2:
                await asyncio.sleep(0.25 * 2 ** attempt)
        raise error


def meta(source, start, data, urls, **kwargs):
    return Meta(fonte=source, coletado_em=datetime.now(timezone.utc).isoformat(),
                duracao_ms=round((perf_counter() - start) * 1000, 2),
                quantidade=len(data), urls=urls, **kwargs)


async def legislation(gateway, limite=3, ano=2026):
    start = perf_counter()
    payload = await gateway.get(CAMARA, 'camara', {
        'itens': limite, 'siglaTipo': 'PL', 'ano': ano, 'ordem': 'DESC', 'ordenarPor': 'id'})
    try:
        if not isinstance(payload['dados'], list) or len(payload['dados']) > limite:
            raise ValueError('Lista inesperada')
        summaries = [RawBill.model_validate(row) for row in payload['dados']]
        if len({x.id for x in summaries}) != len(summaries):
            raise ValueError('Identificador duplicado')
        if any(x.ano != ano or x.siglaTipo != 'PL' for x in summaries):
            raise ValueError('Filtros não respeitados')
        data, urls = [], [str(httpx.URL(CAMARA, params={
            'itens': limite, 'siglaTipo': 'PL', 'ano': ano, 'ordem': 'DESC', 'ordenarPor': 'id'}))]
        for summary in summaries:
            url = f'{CAMARA}/{summary.id}'  # Nunca segue URI arbitrária da resposta.
            detail = await gateway.get(url, 'camara')
            bill = RawBill.model_validate(detail['dados'])
            if (bill.id, bill.siglaTipo, bill.numero, bill.ano) != (
                    summary.id, summary.siglaTipo, summary.numero, summary.ano):
                raise ValueError('Detalhe diverge da listagem')
            data.append(Bill(id=bill.id, tipo=bill.siglaTipo, numero=bill.numero,
                             ano=bill.ano, ementa=bill.ementa,
                             situacao=bill.statusProposicao.descricaoSituacao
                             if bill.statusProposicao else None, origem=url))
            urls.append(url)
    except (KeyError, TypeError, ValueError, ValidationError):
        raise SourceError('resposta_invalida', 'camara') from None
    return LegislationResponse(dados=data, meta=meta('Câmara dos Deputados', start, data, urls))


async def unemployment(gateway):
    start = perf_counter()
    metadata = await gateway.get(METADATA, 'ibge')
    try:
        metadata_check(metadata)
    except (KeyError, TypeError, ValueError, StopIteration, AttributeError):
        raise SourceError('metadados_invalidos', 'ibge') from None
    payload = await gateway.get(SIDRA, 'ibge')
    try:
        data = parse_sidra(payload)
    except (KeyError, TypeError, ValueError, ValidationError):
        raise SourceError('resposta_invalida', 'ibge') from None
    return IndicatorResponse(dados=data, meta=meta('IBGE / SIDRA / PNAD Contínua', start,
        data, [METADATA, SIDRA], periodicidade='trimestral', tabela='4099', variavel='4099'))


def make_client():
    return httpx.AsyncClient(verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        timeout=httpx.Timeout(20, connect=5), follow_redirects=False,
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
        headers={'Accept': 'application/json', 'User-Agent': 'ObservatorioLegislativo-PoC/1.0'})


@asynccontextmanager
async def lifespan(app):
    async with make_client() as client:
        app.state.client = client
        yield


app = FastAPI(title='Observatório de Impacto Legislativo — PoC', lifespan=lifespan)


@app.exception_handler(SourceError)
async def source_error(request, exc):
    return JSONResponse(status_code=exc.status,
                        content={'erro': {'codigo': exc.code, 'fonte': exc.source}})


@app.get('/api/legislacao', response_model=LegislationResponse)
async def get_legislation(request: Request, limite: int = Query(3, ge=1, le=5),
                          ano: int = Query(2026, ge=1900, le=2100)):
    return await legislation(Gateway(request.app.state.client), limite, ano)


@app.get('/api/indicadores/desemprego', response_model=IndicatorResponse)
async def get_unemployment(request: Request):
    return await unemployment(Gateway(request.app.state.client))
