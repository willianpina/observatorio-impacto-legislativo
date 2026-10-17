"""Cadastro manual de calendário oficial; nenhuma previsão aproximada automática."""
import argparse
import re
from datetime import datetime
from urllib.parse import urlparse

from sqlalchemy import select

from .catalog import SPECS
from .db import make_engine, sessions
from .ingest import ensure_catalog
from .models import Divulgacao, Serie


def bounded_text(value):
    if len(value) > 500:
        raise argparse.ArgumentTypeError('Use no máximo 500 caracteres.')
    return value


def register(session, code, period, expected_at, source, link):
    if len(source) > 500 or len(link) > 500:
        raise ValueError('Fonte e link devem ter no máximo 500 caracteres.')
    hostname=urlparse(link).hostname or ''
    if (not re.fullmatch(r'\d{4}(0[1-9]|1[0-2])',period)
            or expected_at.tzinfo is None or expected_at.utcoffset() is None
            or urlparse(link).scheme != 'https'
            or not (hostname=='ibge.gov.br' or hostname.endswith('.ibge.gov.br')) or not source.strip()):
        raise ValueError('Informe período válido, instante com fuso e fonte/link oficial do IBGE.')
    ensure_catalog(session,SPECS[code])
    serie=session.scalar(select(Serie).where(Serie.codigo==code))
    item=session.scalar(select(Divulgacao).where(Divulgacao.serie_id==serie.id,Divulgacao.periodo==period))
    if item is None:
        item=Divulgacao(serie_id=serie.id,periodo=period)
        session.add(item)
    item.prevista_em, item.fonte, item.link=expected_at,source,link


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Cadastrar só data conferida no calendário público IBGE.')
    parser.add_argument('codigo',choices=list(SPECS))
    parser.add_argument('--periodo',required=True)
    parser.add_argument('--prevista-em',type=datetime.fromisoformat,required=True)
    parser.add_argument('--fonte',type=bounded_text,required=True)
    parser.add_argument('--link',type=bounded_text,required=True)
    args=parser.parse_args()
    engine=make_engine()
    try:
        with sessions(engine).begin() as session:
            register(session,args.codigo,args.periodo,args.prevista_em,args.fonte,args.link)
        print('Calendário manual registrado com fonte e link.')
    finally:
        engine.dispose()
