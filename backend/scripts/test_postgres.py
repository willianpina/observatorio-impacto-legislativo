"""Cria PostgreSQL descartável exclusivo da O2 e executa testes; nunca lê .env."""
import os
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    name = 'oil-o2-test-' + uuid.uuid4().hex[:10]
    environment = os.environ.copy()
    environment['POSTGRES_PASSWORD'] = secrets.token_hex(32)
    environment['POSTGRES_USER'] = 'oil_test'
    environment['POSTGRES_DB'] = 'oil_o2_test'
    # Não herda URL de banco existente, mesmo que configurada pelo usuário.
    command = ['docker', 'run', '--rm', '--detach', '--name', name,
               '--label', 'oil.task=O2-tests', '--publish', '127.0.0.1::5432',
               '--env', 'POSTGRES_PASSWORD', '--env', 'POSTGRES_USER', '--env', 'POSTGRES_DB',
               'postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3']
    subprocess.run(command, env=environment, check=True, stdout=subprocess.DEVNULL)
    try:
        for _ in range(120):
            result = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'oil_test',
                                     '-d', 'oil_o2_test'], capture_output=True)
            if result.returncode == 0:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError('PostgreSQL descartável não iniciou.')
        endpoint = subprocess.check_output(['docker', 'port', name, '5432/tcp'], text=True).strip()
        port = int(endpoint.rsplit(':', 1)[1])
        environment['DATABASE_URL'] = ('postgresql+psycopg://oil_test:' + environment['POSTGRES_PASSWORD']
                                       + f'@127.0.0.1:{port}/oil_o2_test')
        environment['OIL_TEST_MODE'] = '1'
        environment['OIL_DISPOSABLE_DATABASE'] = '1'
        environment['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        # Em duas invocações para manter o import legado `from app import ...` intacto.
        new = subprocess.run([sys.executable, '-m', 'pytest', '-c', 'backend/pytest.ini',
                              '-q', '-p', 'no:cacheprovider', *sys.argv[1:]], cwd=ROOT, env=environment)
        old = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider'],
                             cwd=ROOT/'poc', env=environment)
        return 0 if new.returncode == old.returncode == 0 else 1
    finally:
        # Só encerra o contêiner nomeado e criado por esta execução; --rm remove o banco de teste.
        subprocess.run(['docker', 'stop', '--time', '3', name], check=True, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    raise SystemExit(main())
