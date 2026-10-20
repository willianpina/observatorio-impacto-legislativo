"""Jobs O3 explícitos; não usam fixtures nem fazem descoberta de arquivos."""
import argparse
import asyncio
import json
from pathlib import Path

from .caged import CagedCollector, download_timeout, register_calendar
from .catalog import PROPOSICOES
from .db import make_engine, sessions
from .ingest import SourceFailure, make_client
from .legislation import LawCollector


async def run(args):
    if args.job=='caged':
        try:
            download_timeout()
        except ValueError as exc:
            print(json.dumps({'erro':'configuracao_invalida','mensagem':str(exc)},ensure_ascii=False))
            return 1
    engine=make_engine();factory=sessions(engine)
    try:
        if args.job=='calendario-caged':
            register_calendar(factory)
            print(json.dumps({'calendario':'caged','cadastrado':True}));return 0
        async with make_client() as client:
            if args.job=='lei':
                result=await LawCollector(factory,client).collect(args.id)
            else:
                manifest=json.loads((Path(__file__).parents[1]/'data/caged_manifesto.json').read_text(encoding='utf-8'))
                entry=next((item for item in manifest if item['competencia']==args.competencia),None)
                if entry is None:
                    print(json.dumps({'erro':'competencia_nao_cadastrada'}));return 1
                result=await CagedCollector(factory,client).collect(entry)
            print(json.dumps(result,ensure_ascii=False));return 0
    except SourceFailure as exc:
        print(json.dumps({'erro':exc.code,'status':exc.status,'simulada':False}));return 1
    finally:
        engine.dispose()


def main():
    parser=argparse.ArgumentParser(description='Coletas reais O3 por manifesto versionado; sem fallback simulado.')
    sub=parser.add_subparsers(dest='job',required=True)
    sub.add_parser('lei').add_argument('--id',type=int,choices=list(PROPOSICOES),default=next(iter(PROPOSICOES)))
    sub.add_parser('caged').add_argument('competencia')
    sub.add_parser('calendario-caged')
    raise SystemExit(asyncio.run(run(parser.parse_args())))


if __name__=='__main__': main()
