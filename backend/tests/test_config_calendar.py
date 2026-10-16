from datetime import datetime, timezone

import pytest

from backend.oil.calendar import register
from backend.oil.db import database_url
from backend.oil.models import Divulgacao
from sqlalchemy import select


def test_database_url_required_and_postgres_only(monkeypatch):
    monkeypatch.delenv('DATABASE_URL')
    with pytest.raises(RuntimeError,match='Configure DATABASE_URL'):
        database_url()
    monkeypatch.setenv('DATABASE_URL','sqlite:///example.sqlite')
    with pytest.raises(RuntimeError,match='PostgreSQL/psycopg'):
        database_url()


def test_invalid_url_not_logged(monkeypatch):
    monkeypatch.setenv('DATABASE_URL','SIMULADO_NAO_IMPRIMIR')
    with pytest.raises(RuntimeError) as error:
        database_url()
    assert 'SIMULADO_NAO_IMPRIMIR' not in str(error.value)


def test_manual_calendar_source(sf):
    # Registro de teste: não afirma que esta data seja uma divulgação oficial real.
    with sf.begin() as session:
        register(session,'desocupacao','202609',datetime(2026,10,16,tzinfo=timezone.utc),
                 'IBGE — CADASTRO SIMULADO','https://www.ibge.gov.br/calendario.html')
    with sf() as session:
        entry=session.scalar(select(Divulgacao))
        assert entry.prevista_em.tzinfo is not None and entry.fonte.endswith('SIMULADO')


@pytest.mark.parametrize('period,instant,link', [
    ('202613',datetime(2026,10,16,tzinfo=timezone.utc),'https://www.ibge.gov.br/'),
    ('202609',datetime(2026,10,16),'https://www.ibge.gov.br/'),
    ('202609',datetime(2026,10,16,tzinfo=timezone.utc),'https://example.org/'),
])
def test_invalid_calendar(sf,period,instant,link):
    with sf.begin() as session:
        with pytest.raises(ValueError):
            register(session,'desocupacao',period,instant,'SIMULADO',link)
