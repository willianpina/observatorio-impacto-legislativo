import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


def database_url():
    # Nunca carrega .env ou imprime a URL, mesmo em erros de configuração.
    value = os.environ.get('DATABASE_URL')
    try:
        parsed = make_url(value or '')
        if parsed.drivername != 'postgresql+psycopg' or not parsed.database:
            raise ValueError
    except Exception:
        raise RuntimeError('Configure DATABASE_URL com PostgreSQL/psycopg no ambiente.') from None
    return parsed


def make_engine():
    return create_engine(database_url(), pool_pre_ping=True, hide_parameters=True,
                         connect_args={'connect_timeout': 5})


def sessions(engine):
    return sessionmaker(engine, expire_on_commit=False)
