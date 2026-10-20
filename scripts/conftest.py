"""A coleta da raiz não inclui estes testes.

`pytest -c backend/pytest.ini` sem caminhos varre o diretório de invocação.
A bateria do backend exige que essa varredura coincida com `backend/tests`.
Os testes daqui só entram quando o comando aponta para `scripts/` ou parte de lá.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def _comando_aponta_para_scripts(config) -> bool:
    invocacao = Path(config.invocation_params.dir).resolve()
    try:
        invocacao.relative_to(RAIZ)
        return True
    except ValueError:
        pass
    for arg in config.invocation_params.args:
        if not arg or arg.startswith("-"):
            continue
        bruto = arg.split("::", 1)[0]
        if not bruto:
            continue
        candidato = Path(bruto)
        if not candidato.is_absolute():
            candidato = invocacao / candidato
        try:
            candidato.resolve().relative_to(RAIZ)
            return True
        except (ValueError, OSError):
            continue
    return False


def pytest_ignore_collect(collection_path, config):
    try:
        caminho = Path(collection_path).resolve()
    except OSError:
        return None
    try:
        caminho.relative_to(RAIZ)
    except ValueError:
        return None
    if _comando_aponta_para_scripts(config):
        return None
    return True
