import asyncio
import hashlib
import os
import ssl
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re

import httpx
import truststore
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .catalog import CAGED, SPECS
from .classification import classify
from .models import Coleta, Fonte, Observacao, Serie
from .sidra import parse, previous_year, validate_metadata


class SourceFailure(Exception):
    def __init__(self, code, status=502, collection_id=None):
        self.code, self.status, self.collection_id = code, status, collection_id
        super().__init__(code)


def make_client():
    return httpx.AsyncClient(verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        timeout=httpx.Timeout(20, connect=5), follow_redirects=False,
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
        headers={'Accept': 'application/json', 'User-Agent': 'OIL-O2/1.0'})


def retry_delay(response, attempt, *, now=None):
    fallback = 0.25 * 2 ** attempt
    if response is None or response.status_code not in {429,503}:
        return fallback
    header = response.headers.get('Retry-After','').strip()
    if re.fullmatch(r'[0-9]+',header):
        header = header.lstrip('0') or '0'
        # Evita conversão de inteiros com milhares de dígitos fornecidos pela fonte.
        return min(int(header),60) if len(header) <= 3 else 60
    try:
        instant = parsedate_to_datetime(header)
        if instant.tzinfo is None:
            return fallback
        delay = (instant-(now or datetime.now(timezone.utc))).total_seconds()
        return min(max(delay,0),60)
    except (TypeError,ValueError,OverflowError):
        return fallback


def ensure_catalog(session, spec):
    session.execute(insert(Fonte).values(codigo='ibge-sidra', nome='IBGE / PNAD Contínua / SIDRA',
        link='https://sidra.ibge.gov.br/').on_conflict_do_nothing(index_elements=['codigo']))
    source = session.scalar(select(Fonte).where(Fonte.codigo == 'ibge-sidra'))
    session.execute(insert(Serie).values(fonte_id=source.id, codigo=spec.codigo, nome=spec.nome,
        tabela=spec.tabela, variavel=spec.variavel, variavel_cv=spec.cv,
        variavel_variacao=spec.variacao, variavel_diferenca=spec.diferenca,
        unidade=spec.unidade, unidade_variacao=spec.unidade_variacao,
        medida=spec.medida, tipo_valor=spec.tipo_valor, tipo_periodo='trimestre_movel',
        base_precos=None).on_conflict_do_nothing(index_elements=['codigo']))
    return source.id


def ensure_unavailable_catalog(session):
    session.execute(insert(Fonte).values(codigo='mte-caged',nome='MTE / Novo Caged',link=None)
                    .on_conflict_do_nothing(index_elements=['codigo']))
    source_id = session.scalar(select(Fonte.id).where(Fonte.codigo=='mte-caged'))
    session.execute(insert(Serie).values(fonte_id=source_id,**CAGED)
                    .on_conflict_do_nothing(index_elements=['codigo']))


class Collector:
    def __init__(self, session_factory, client, *, simulada=False, sleep=asyncio.sleep):
        if simulada and os.environ.get('OIL_TEST_MODE') != '1':
            raise ValueError('Resposta simulada permitida somente em modo de teste explícito.')
        self.sessions, self.client, self.simulada, self.sleep = session_factory, client, simulada, sleep

    def record(self, spec, url, kind, response=None, error=None):
        raw = response.content if response is not None else None
        with self.sessions.begin() as session:
            source_id = ensure_catalog(session, spec)
            item = Coleta(fonte_id=source_id, serie_codigo=spec.codigo, url_consultada=url,
                coletado_em=datetime.now(timezone.utc), codigo_http=response.status_code if response is not None else None,
                resposta_bruta=raw, hash_sha256=hashlib.sha256(raw).hexdigest() if raw is not None else None,
                simulada=self.simulada, erro=error, tipo=kind, valida=False)
            session.add(item)
            session.flush()
            return item.id

    async def fetch(self, spec, url, kind):
        for attempt in range(3):
            response = None
            try:
                response = await self.client.get(url)
            except httpx.TimeoutException:
                error = SourceFailure('timeout_fonte', 504)
                self.record(spec, url, kind, error=error.code)
            except httpx.TransportError:
                error = SourceFailure('erro_conexao', 503)
                self.record(spec, url, kind, error=error.code)
            else:
                ok = response.status_code == 200
                error = SourceFailure('http_fonte', 503 if response.status_code in {429,500,502,503,504} else 502)
                collection_id = self.record(spec, url, kind, response, None if ok else error.code)
                if ok:
                    return response.content, collection_id
                if error.status != 503:
                    raise error
            if attempt < 2:
                await self.sleep(retry_delay(response,attempt))
        raise error

    def invalidate(self, collection_id):
        with self.sessions.begin() as session:
            session.get(Coleta, collection_id).erro = 'resposta_invalida'

    async def collect(self, codigo):
        spec = SPECS[codigo]
        metadata, mid = await self.fetch(spec, spec.metadata_url, 'metadados')
        try:
            validate_metadata(metadata, spec)
        except (ValueError, KeyError, TypeError, AttributeError):
            self.invalidate(mid)
            raise SourceFailure('metadados_invalidos') from None
        raw, collection_id = await self.fetch(spec, spec.url, 'valores')
        try:
            points = parse(raw, spec)
        except (ValueError, KeyError, TypeError, AttributeError):
            self.invalidate(collection_id)
            raise SourceFailure('resposta_invalida') from None
        count = self.persist(spec, points, collection_id)
        return {'codigo': codigo, 'coleta_id': collection_id, 'novas_versoes': count,
                'simulada': self.simulada}

    def persist(self, spec, points, collection_id):
        with self.sessions.begin() as session:
            # Serializa ingestões da mesma série, incluindo revisões simultâneas.
            serie = session.scalar(select(Serie).where(Serie.codigo == spec.codigo).with_for_update())
            old = session.scalars(select(Observacao).where(Observacao.serie_id == serie.id)
                                  .order_by(Observacao.periodo, Observacao.versao)).all()
            max_versions = {o.periodo: o.versao for o in old}
            mode_ids = set(session.scalars(select(Coleta.id).where(Coleta.simulada == self.simulada)))
            latest = {o.periodo: o for o in old if o.coleta_id in mode_ids}
            incoming = {p.periodo: p for p in points}
            count = 0
            for point in points:
                # Não mistura snapshots: o CV anterior precisa vir da mesma resposta.
                previous = incoming.get(previous_year(point.periodo))
                classification = classify(point.valor, point.cv,
                    previous.valor if previous else None, previous.cv if previous else None,
                    point.diferenca_anual)
                values = dict(valor=point.valor, cv=point.cv, variacao_anual=point.variacao_anual,
                    diferenca_anual=point.diferenca_anual, classificacao=classification,
                    classificacao_origem='calculada')
                previous_version = latest.get(point.periodo)
                if previous_version and all(getattr(previous_version,k) == v for k,v in values.items()):
                    continue
                session.add(Observacao(serie_id=serie.id, periodo=point.periodo,
                    coleta_id=collection_id, versao=max_versions.get(point.periodo, 0)+1, **values))
                count += 1
            session.get(Coleta, collection_id).valida = True
            session.flush()
            return count
