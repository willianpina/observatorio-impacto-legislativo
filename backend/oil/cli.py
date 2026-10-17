"""Job separado: python -m backend.oil.cli [desocupacao|rendimento-real]."""
import argparse
import asyncio
import json

from .catalog import SPECS
from .db import make_engine, sessions
from .ingest import Collector, SourceFailure, make_client


async def run(codes):
    engine = make_engine()
    failed = False
    try:
        async with make_client() as client:
            collector = Collector(sessions(engine), client)
            for code in codes:
                try:
                    print(json.dumps(await collector.collect(code), ensure_ascii=False))
                except SourceFailure as exc:
                    failed = True
                    print(json.dumps({'codigo': code, 'erro': exc.code, 'simulada': False}))
    finally:
        engine.dispose()
    return 1 if failed else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Coleta real SIDRA; nunca usa fallback simulado.')
    parser.add_argument('codigos', nargs='*', choices=list(SPECS))
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.codigos or list(SPECS))))
