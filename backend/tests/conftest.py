import asyncio
import os
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from backend.oil.catalog import SPECS
from backend.oil.db import make_engine, sessions
from backend.oil.ingest import Collector

FIXTURES = Path(__file__).parent / 'fixtures'
ROOT = Path(__file__).resolve().parents[2]


def alembic_config():
    return Config(str(ROOT/'backend/alembic.ini'))


@pytest.fixture(scope='session')
def engine():
    if os.environ.get('OIL_DISPOSABLE_DATABASE') != '1':
        pytest.fail('Execute backend/scripts/test_postgres.py: testes exigem banco descartável exclusivo.')
    engine = make_engine()
    command.upgrade(alembic_config(), 'head')
    yield engine
    engine.dispose()


@pytest.fixture
def sf(engine):
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE divulgacao, observacao, coleta, serie, fonte RESTART IDENTITY CASCADE'))
    return sessions(engine)


@pytest.fixture
def replay():
    def handler(request):
        for spec in SPECS.values():
            if str(request.url) == spec.url:
                return httpx.Response(200, content=(FIXTURES/f'sidra-{spec.tabela}.json').read_bytes())
            if str(request.url) == spec.metadata_url:
                return httpx.Response(200, content=(FIXTURES/f'metadados-{spec.tabela}.json').read_bytes())
        raise AssertionError('Teste tentou consultar URL não gravada.')
    return handler


def collect(sf, handler, code='desocupacao'):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Collector(sf, client, simulada=True, sleep=no_sleep).collect(code)
    return asyncio.run(run())


async def no_sleep(delay):
    pass


@pytest.fixture
def populated(sf, replay):
    for code in SPECS:
        collect(sf, replay, code)
    return sf
