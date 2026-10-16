"""Opt-in. Falha de fonte usa replay identificado; nunca aprova conexão inexistente."""
import asyncio
import os
import warnings
from decimal import Decimal as D

import pytest

from backend.oil.ingest import Collector, SourceFailure, make_client
from backend.oil.read import read_series
from .conftest import collect


@pytest.mark.live
@pytest.mark.skipif(os.environ.get('RUN_LIVE_IBGE') != '1', reason='Teste ao vivo desligado por padrão.')
@pytest.mark.parametrize('codigo,valor,cv', [('desocupacao',D('5.3'),D('1.3')),
                                          ('rendimento-real',D(3777),D('0.7'))])
def test_latest_against_sidra_optional(sf, replay, record_property, codigo, valor, cv):
    async def live():
        async with make_client() as client:
            return await Collector(sf,client).collect(codigo)
    try:
        asyncio.run(live())
        simulated=False
    except SourceFailure:
        collect(sf,replay,codigo)
        simulated=True
        warnings.warn(f'{codigo}: fonte indisponível; validação SIMULADA com resposta gravada, não conexão aprovada.')
    record_property('simulada',str(simulated).lower())
    with sf() as session:
        result=read_series(session,codigo,'5a',test_mode=simulated)
        assert result.periodo=='202608', 'Expectativa de referência da O2 (jun–ago/2026) mudou; conferir fonte.'
        assert D(str(result.valor))==valor and D(str(result.cv))==cv
