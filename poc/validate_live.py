"""Execução explícita em rede real; salva respostas e tempos, e falha se não validar."""
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app import (Gateway, IndicatorResponse, LegislationResponse, SourceError,
                 legislation, make_client, unemployment)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'evidencias'


def save(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


async def main():
    OUT.mkdir(exist_ok=True)
    report = {'executado_em': datetime.now(timezone.utc).isoformat(), 'fontes': {}}
    async with make_client() as client:
        gateway = Gateway(client)
        for name, operation in [('camara', legislation), ('ibge', unemployment)]:
            start = time.perf_counter()
            try:
                result = await operation(gateway)
                assert len(result.dados) >= (8 if name == 'ibge' else 1)
                if name == 'ibge':
                    assert all(x.valor is not None for x in result.dados)
                save(f'{name}-normalizado.json', result.model_dump(mode='json'))
                report['fontes'][name] = {'aprovada': True, 'quantidade': len(result.dados)}
            except Exception as exc:
                report['fontes'][name] = {'aprovada': False,
                    'erro': getattr(exc, 'code', type(exc).__name__)}
            report['fontes'][name]['duracao_ms'] = round((time.perf_counter()-start)*1000, 2)
        # Amostra adicional em ano anterior para verificar situação quando preenchida.
        try:
            older = await legislation(gateway, limite=1, ano=2025)
            save('camara-2025-normalizado.json', older.model_dump(mode='json'))
            report['amostra_adicional_camara'] = {
                'id': older.dados[0].id, 'situacao': older.dados[0].situacao,
                'duracao_ms': older.meta.duracao_ms}
        except Exception as exc:
            report['amostra_adicional_camara'] = {'erro': getattr(exc, 'code', type(exc).__name__)}
        save('consultas-reais.json', gateway.evidence)
    # Servidor real em loopback e chamadas HTTP reais, além do teste dos adaptadores.
    with (OUT / 'servidor.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app',
            '--host', '127.0.0.1', '--port', '8765'], cwd=ROOT, stdout=log, stderr=log)
        try:
            async with httpx.AsyncClient(timeout=180, trust_env=False) as local:
                for _ in range(50):
                    if process.poll() is not None:
                        raise RuntimeError('Servidor não iniciou')
                    try:
                        ready = await local.get('http://127.0.0.1:8765/openapi.json')
                        ready.raise_for_status()
                        break
                    except httpx.TransportError:
                        await asyncio.sleep(0.1)
                report['api_local'] = {}
                for name, path, model in [
                    ('camara', '/api/legislacao', LegislationResponse),
                    ('ibge', '/api/indicadores/desemprego', IndicatorResponse)]:
                    start = time.perf_counter()
                    response = await local.get('http://127.0.0.1:8765' + path)
                    record = {'status_http': response.status_code,
                              'duracao_ms': round((time.perf_counter()-start)*1000, 2)}
                    save(f'{name}-api-local.json', response.json())
                    if response.status_code == 200:
                        parsed = model.model_validate(response.json())
                        record['aprovada'] = len(parsed.dados) >= (8 if name == 'ibge' else 1)
                    else:
                        record['aprovada'] = False
                    report['api_local'][name] = record
        except Exception as exc:
            report['erro_servidor'] = type(exc).__name__
        finally:
            process.terminate()
            process.wait(timeout=10)
    save('resultado.json', report)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in OUT.iterdir() if p.is_file() and p.name != 'sha256.json'}
    save('sha256.json', hashes)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    passed = (all(r['aprovada'] for r in report['fontes'].values())
              and len(report.get('api_local', {})) == 2
              and all(r['aprovada'] for r in report.get('api_local', {}).values()))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
