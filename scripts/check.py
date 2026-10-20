"""Verificação local do Observatório de Impacto Legislativo.

Roda somente quando este arquivo é executado. Não consulta fontes externas
sem ``--ao-vivo`` e não deixa contêiner, volume nem processo para trás.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(__file__).resolve().parent / "dados" / "mutacoes.json"
FUSO = ZoneInfo("America/Sao_Paulo")
VERSAO_FORMATO = "1"
VERSAO_SCRIPT = "0.1.0"
NOME_SCRIPT = "scripts/check.py"
MOTIVO_REDE = "rede não autorizada (--ao-vivo ausente)"
MOTIVO_RAPIDO = "modo rápido"
PULO_PERMITIDO_NO_COMPLETO = {"caged_arquivos_reais", "testes_ao_vivo"}
IMAGEM_POSTGRES = "postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3"
HOSTS_VIVOS = (
    "sidra.ibge.gov.br", "apisidra.ibge.gov.br", "servicodados.ibge.gov.br",
    "dadosabertos.camara.leg.br", "legis.senado.leg.br", "www.camara.leg.br",
    "www.senado.leg.br", "drive.google.com", "drive.usercontent.google.com",
    "www.gov.br", "planalto.gov.br", "in.gov.br",
)
MARCAS_FIXTURE = ("fixture", "Fixture sintética", "— fixture de teste")
CONTAS = ("passed", "failed", "skipped", "deselected", "errors")
CAGED_ESPERADO = {
    "2026-07": {
        "sha256": "367b66f4af878d0c1ab5b9fc881f228976e74a2240cb5d3afdc83aef78cabe01",
        "arquivo": "3-tabelas_Julho de 2026.xlsx",
        "meses": 79,
        "inicio": "202001",
        "fim": "202607",
        "valores": {"202607": 58568, "202606": 137044},
    },
    "2026-08": {
        "sha256": "d36c8ebe54e3e10ea877f5ea4dd6798a0a276c4fcff262c73102f4b9c8459e7d",
        "arquivo": "3-tabelas_Agosto de 2026.xlsx",
        "meses": 80,
        "inicio": "202001",
        "fim": "202608",
        "valores": {"202608": 165827, "202607": 55915, "202512": -635078, "202606": 136959},
    },
}
VERSOES_ESPERADAS = {
    "202607": {1: 58568, 2: 55915},
    "202606": {1: 137044, 2: 136959},
}
TIMEOUT_CAGED = (5, 120, 10, 10)


class ErroUso(Exception):
    codigo = 2


class ErroInterno(Exception):
    codigo = 3


def agora():
    return datetime.now(FUSO)


def iso(momento):
    return momento.isoformat(timespec="seconds")


def redigir(texto):
    if not isinstance(texto, str) or texto == "":
        return texto
    texto = re.sub(r"://[^/\s:@]+:[^/\s@]+@", "://<omitido>:<omitido>@", texto)
    texto = re.sub(
        r"(?i)\b([A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|DATABASE_URL|DSN|COOKIE|CREDENTIAL)[A-Z0-9_]*)=([^\s\"']+)",
        r"\1=<omitido>",
        texto,
    )
    texto = re.sub(
        r"(?i)\b([A-Z0-9_]*(?:API_KEY|SECRET_KEY|ACCESS_KEY)[A-Z0-9_]*)=([^\s\"']+)",
        r"\1=<omitido>",
        texto,
    )
    texto = re.sub(r"(?i)\b(authorization|cookie|set-cookie)\s*[:=]\s*\S+", r"\1: <omitido>", texto)
    texto = re.sub(r"\b(?:ghp_|github_pat_|sk-|xox[baprs]-|AKIA)[A-Za-z0-9_\-]{8,}\b", "<omitido>", texto)
    return texto


def redigir_obj(obj):
    if isinstance(obj, str):
        return redigir(obj)
    if isinstance(obj, list):
        return [redigir_obj(item) for item in obj]
    if isinstance(obj, dict):
        return {chave: redigir_obj(valor) for chave, valor in obj.items()}
    return obj


def nova_etapa(nome, status, *, contagens=None, bateria_completa=None, duracao_s=0.0,
               comando=None, motivo_pulo=None, detalhes=None):
    return {
        "nome": nome,
        "status": status,
        "contagens": contagens,
        "bateria_completa": bateria_completa,
        "duracao_s": duracao_s,
        "comando": comando,
        "motivo_pulo": motivo_pulo,
        "detalhes": detalhes or {},
    }


def codigo_saida(etapas, *, uso=False, interno=False):
    if uso:
        return 2
    if interno:
        return 3
    for etapa in etapas:
        if etapa["status"] == "falhou":
            return 1
    return 0


def contar_por_status(etapas):
    ok = sum(etapa["status"] == "ok" for etapa in etapas)
    falhou = sum(etapa["status"] == "falhou" for etapa in etapas)
    pulado = sum(etapa["status"] == "pulado" for etapa in etapas)
    return {"ok": ok, "falhou": falhou, "pulado": pulado}


def finalizar_etapa(etapa, modo):
    etapa = dict(etapa)
    etapa["detalhes"] = dict(etapa.get("detalhes") or {})
    if etapa["status"] == "pulado" and not etapa.get("motivo_pulo"):
        etapa["status"] = "falhou"
        etapa["detalhes"]["erro"] = "pulado sem motivo_pulo"
        etapa["motivo_pulo"] = None
    if modo == "completo" and etapa["status"] == "pulado" and etapa["nome"] not in PULO_PERMITIDO_NO_COMPLETO:
        etapa["detalhes"]["pulo_recusado"] = etapa.get("motivo_pulo")
        etapa["status"] = "falhou"
        etapa["motivo_pulo"] = None
    if etapa["status"] != "pulado":
        etapa["motivo_pulo"] = None
    return etapa


def bateria_do_resumo(etapas, modo):
    if modo == "rapido":
        return False
    if any(etapa["bateria_completa"] is False for etapa in etapas):
        return False
    return True


def montar_relatorio(etapas, *, modo, rede_ao_vivo, git, inicio, fim, uso=False, interno=False):
    finais = [finalizar_etapa(etapa, modo) for etapa in etapas]
    contagem = contar_por_status(finais)
    status = "falhou" if interno or any(etapa["status"] == "falhou" for etapa in finais) else "ok"
    relatorio = {
        "versao_formato": VERSAO_FORMATO,
        "script": {"nome": NOME_SCRIPT, "versao": VERSAO_SCRIPT},
        "modo": modo,
        "rede_ao_vivo": bool(rede_ao_vivo),
        "git": git,
        "inicio": inicio,
        "fim": fim,
        "fuso": "America/Sao_Paulo",
        "etapas": finais,
        "resumo": {
            "status_geral": status,
            "ok": contagem["ok"],
            "falhou": contagem["falhou"],
            "pulado": contagem["pulado"],
            "bateria_completa": bateria_do_resumo(finais, modo),
            "etapas_falhas": [etapa["nome"] for etapa in finais if etapa["status"] == "falhou"],
            "etapas_puladas": [etapa["nome"] for etapa in finais if etapa["status"] == "pulado"],
            "codigo_saida": codigo_saida(finais, uso=uso, interno=interno),
        },
    }
    return redigir_obj(relatorio)


def validar_formato(relatorio):
    obrigatorios = {
        "versao_formato", "script", "modo", "rede_ao_vivo", "git", "inicio", "fim", "fuso", "etapas", "resumo",
    }
    faltando = obrigatorios - set(relatorio)
    if faltando:
        raise ValueError("campos ausentes: " + ", ".join(sorted(faltando)))
    if relatorio["versao_formato"] != "1":
        raise ValueError("versao_formato")
    if relatorio["script"] != {"nome": NOME_SCRIPT, "versao": VERSAO_SCRIPT}:
        raise ValueError("script")
    if relatorio["modo"] not in {"rapido", "completo"}:
        raise ValueError("modo")
    if not isinstance(relatorio["rede_ao_vivo"], bool):
        raise ValueError("rede_ao_vivo")
    if relatorio["fuso"] != "America/Sao_Paulo":
        raise ValueError("fuso")
    for campo in ("inicio", "fim"):
        momento = datetime.fromisoformat(relatorio[campo])
        if momento.tzinfo is None or momento.utcoffset() is None:
            raise ValueError(campo)
    git = relatorio["git"]
    for campo in ("head_sha", "base_ref", "base_sha", "arvore_limpa_inicio", "arvore_limpa_fim"):
        if campo not in git:
            raise ValueError("git." + campo)
    resumo = relatorio["resumo"]
    for campo in ("status_geral", "ok", "falhou", "pulado", "bateria_completa", "etapas_falhas", "etapas_puladas", "codigo_saida"):
        if campo not in resumo:
            raise ValueError("resumo." + campo)
    if resumo["status_geral"] not in {"ok", "falhou"}:
        raise ValueError("status_geral")
    if not isinstance(resumo["bateria_completa"], bool):
        raise ValueError("bateria_completa")
    for etapa in relatorio["etapas"]:
        for campo in ("nome", "status", "contagens", "bateria_completa", "duracao_s", "comando", "motivo_pulo", "detalhes"):
            if campo not in etapa:
                raise ValueError("etapa." + campo)
        if etapa["status"] not in {"ok", "falhou", "pulado"}:
            raise ValueError("status da etapa")
        if etapa["status"] == "pulado" and not etapa["motivo_pulo"]:
            raise ValueError("motivo_pulo")
        if etapa["status"] != "pulado" and etapa["motivo_pulo"] is not None:
            raise ValueError("motivo_pulo indevido")
        if etapa["contagens"] is not None:
            for chave in CONTAS:
                if chave not in etapa["contagens"]:
                    raise ValueError("contagens." + chave)
        if not isinstance(etapa["duracao_s"], (int, float)):
            raise ValueError("duracao_s")
    return True


def comando_tem_filtro(comando):
    tokens = (comando or "").split()
    indice = 0
    while indice < len(tokens):
        token = tokens[indice]
        if token == "-m" and indice + 1 < len(tokens) and tokens[indice + 1] == "pytest":
            indice += 2
            continue
        if token in {"-k", "-m", "--grep"} or token.startswith(("-k=", "-m=", "--grep=")):
            return True
        if token.startswith("-k") and len(token) > 2:
            return True
        indice += 1
    for token in tokens:
        normal = token.replace("\\", "/").rstrip("/")
        if normal.startswith("-") or normal in {"backend/tests", "poc", "frontend/tests"}:
            continue
        if normal.startswith(("backend/tests/", "poc/", "frontend/tests/")) or normal.endswith(".spec.ts"):
            return True
    return False


def recusar_filtro_no_completo(modo, comando):
    if modo == "completo" and comando_tem_filtro(comando):
        raise ErroUso("filtro no completo recusado antes de rodar")


def parse_contagens_pytest(texto):
    if not texto or not re.search(r"\d+\s+(?:passed|failed|skipped|deselected|errors?)\b", texto):
        return None
    candidatas = [linha for linha in texto.splitlines() if re.search(r"\d+\s+(?:passed|failed|skipped|deselected|errors?)\b", linha)]
    linha = candidatas[-1] if candidatas else texto
    contagens = {chave: 0 for chave in CONTAS}
    achou = False
    for numero, tipo in re.findall(r"(\d+)\s+(passed|failed|skipped|deselected|errors|error)\b", linha):
        chave = "errors" if tipo == "error" else tipo
        contagens[chave] = int(numero)
        achou = True
    return contagens if achou else None


def calcular_bateria_completa(contagens, comando):
    if contagens.get("deselected", 0) > 0 or comando_tem_filtro(comando or ""):
        return False
    return True


def status_pelas_contagens(contagens, exit_code):
    if contagens["failed"] > 0 or contagens["errors"] > 0:
        return "falhou", None
    if contagens["passed"] == 0:
        return "falhou", "nenhum teste executado"
    if exit_code not in (0, None):
        return "falhou", None
    return "ok", None


def classificar_contagens(contagens, exit_code, modo, comando, nome):
    if contagens is None:
        return nova_etapa(nome, "falhou", comando=comando, detalhes={"erro": "contagem ilegível"})
    bateria = calcular_bateria_completa(contagens, comando)
    status, erro = status_pelas_contagens(contagens, exit_code)
    if modo == "completo" and bateria is False:
        status = "falhou"
        erro = erro or "bateria incompleta no completo"
    detalhes = {"erro": erro} if erro else {}
    return nova_etapa(nome, status, contagens=contagens, bateria_completa=bateria, comando=comando, detalhes=detalhes)


def classificar_testes(texto, exit_code, modo, comando, nome="pytest_backend"):
    return classificar_contagens(parse_contagens_pytest(texto), exit_code, modo, comando, nome)


def chaves_limite():
    return (
        "MAX_BYTES", "MAX_EXPANDED_BYTES", "MAX_COMPRESSION_RATIO", "MAX_DATA_ROWS",
        "follow_redirects", "connect", "read_padrao", "read_teto", "write", "pool",
        "titulo_prefixo", "titulo_contem",
        "timeout_comum_total", "timeout_comum_connect", "follow_redirects_cliente",
    )


def _numero(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _numero(node.left) * _numero(node.right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_numero(node.operand)
    raise ValueError("expressão numérica não suportada")


def _booleano(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    raise ValueError("booleano esperado")


def extrair_caged(fonte):
    arvore = ast.parse(fonte)
    dados = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id in {"MAX_BYTES", "MAX_EXPANDED_BYTES", "MAX_COMPRESSION_RATIO", "MAX_DATA_ROWS"}:
                    dados[alvo.id] = _numero(no.value)
        if isinstance(no, ast.FunctionDef) and no.name == "download_timeout":
            for sub in ast.walk(no):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "get":
                    if len(sub.args) >= 2 and isinstance(sub.args[0], ast.Constant) and sub.args[0].value == "OIL_CAGED_READ_TIMEOUT":
                        dados["read_padrao"] = int(sub.args[1].value)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "min":
                    if len(sub.args) == 2 and isinstance(sub.args[1], ast.Constant):
                        dados["read_teto"] = _numero(sub.args[1])
                if isinstance(sub, ast.Call) and ((isinstance(sub.func, ast.Attribute) and sub.func.attr == "Timeout") or (isinstance(sub.func, ast.Name) and sub.func.id == "Timeout")):
                    for chave in sub.keywords:
                        if chave.arg in {"connect", "write", "pool"} and isinstance(chave.value, ast.Constant):
                            dados[chave.arg] = _numero(chave.value)
        if isinstance(no, ast.FunctionDef) and no.name == "parse_workbook":
            for sub in ast.walk(no):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "startswith":
                    if sub.args and isinstance(sub.args[0], ast.Constant) and sub.args[0].value == "TABELA 5.1":
                        dados["titulo_prefixo"] = "TABELA 5.1"
                if isinstance(sub, ast.Compare) and isinstance(sub.left, ast.Constant) and sub.left.value == "COM AJUSTES":
                    dados["titulo_contem"] = "COM AJUSTES"
    redirects = []
    for sub in ast.walk(arvore):
        if isinstance(sub, ast.keyword) and sub.arg == "follow_redirects":
            redirects.append(_booleano(sub.value))
    if len(redirects) == 1:
        dados["follow_redirects"] = redirects[0]
    elif redirects:
        dados["follow_redirects"] = tuple(redirects)
    return dados


def extrair_ingest(fonte):
    arvore = ast.parse(fonte)
    dados = {}
    for no in arvore.body:
        if not isinstance(no, ast.FunctionDef) or no.name != "make_client":
            continue
        for sub in ast.walk(no):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "Timeout":
                if sub.args and isinstance(sub.args[0], ast.Constant):
                    dados["timeout_comum_total"] = _numero(sub.args[0])
                for chave in sub.keywords:
                    if chave.arg == "connect" and isinstance(chave.value, ast.Constant):
                        dados["timeout_comum_connect"] = _numero(chave.value)
            if isinstance(sub, ast.keyword) and sub.arg == "follow_redirects":
                dados["follow_redirects_cliente"] = _booleano(sub.value)
    return dados


def extrair_limites(fonte_caged, fonte_ingest):
    dados = {chave: None for chave in chaves_limite()}
    try:
        dados.update(extrair_caged(fonte_caged))
    except SyntaxError:
        pass
    try:
        dados.update(extrair_ingest(fonte_ingest))
    except SyntaxError:
        pass
    return dados


def diferencas_limites(base, cabeca):
    return [chave for chave in chaves_limite() if base.get(chave) != cabeca.get(chave)]


def itens_ausentes(dados):
    return [chave for chave in chaves_limite() if dados.get(chave) is None]


def classificar_caged_arquivos(itens):
    divergentes = [
        item for item in itens
        if item.get("presente") and item.get("sha_encontrado") != item.get("sha_esperado")
    ]
    ausentes = [item for item in itens if not item.get("presente")]
    if divergentes:
        return {
            "status": "falhou",
            "motivo_pulo": None,
            "detalhes": {
                "sha_encontrado": [item.get("sha_encontrado") for item in divergentes],
                "arquivos": [item.get("arquivo") for item in divergentes],
            },
        }
    if ausentes:
        nomes = ", ".join(item.get("arquivo") or item.get("competencia") or "?" for item in ausentes)
        return {
            "status": "pulado",
            "motivo_pulo": f"arquivo ausente: {nomes}",
            "detalhes": {"arquivos": [item.get("arquivo") for item in ausentes]},
        }
    return {"status": "sha_ok", "motivo_pulo": None, "detalhes": {}}


def conferir_valores_caged(pontos_por_competencia, versoes):
    erros = []
    for competencia, spec in CAGED_ESPERADO.items():
        pontos = pontos_por_competencia.get(competencia) or {}
        if len(pontos) != spec["meses"] or (pontos and (min(pontos) != spec["inicio"] or max(pontos) != spec["fim"])):
            erros.append(f"{competencia}: meses {len(pontos)} faixa {min(pontos) if pontos else None}-{max(pontos) if pontos else None}")
        for periodo, valor in spec["valores"].items():
            if pontos.get(periodo) != valor:
                erros.append(f"{competencia} {periodo}={pontos.get(periodo)}")
    for periodo, esperado in VERSOES_ESPERADAS.items():
        obtido = versoes.get(periodo)
        pares = [[versao, esperado[versao]] for versao in sorted(esperado)]
        obtido_norm = [[int(item[0]), int(item[1])] for item in obtido] if obtido else obtido
        if obtido_norm != pares:
            erros.append(f"versoes {periodo}={obtido}")
    return {"status": "ok" if not erros else "falhou", "detalhes": {"erros": erros}}


def conferir_download(info_por_competencia):
    erros = []
    for competencia in CAGED_ESPERADO:
        info = info_por_competencia.get(competencia) or {}
        if info.get("requisicoes") != 1:
            erros.append(f"{competencia} requisicoes={info.get('requisicoes')}")
        if info.get("valida") is not True:
            erros.append(f"{competencia} valida={info.get('valida')}")
        timeout = tuple(info.get("timeout") or ())
        if timeout != TIMEOUT_CAGED:
            erros.append(f"{competencia} timeout={timeout}")
    return {"status": "ok" if not erros else "falhou", "detalhes": {"erros": erros}}


def titulo_sem_ajustes_recusado():
    import io
    import zipfile

    import openpyxl

    livro = openpyxl.Workbook()
    aba = livro.active
    aba.title = "Tabela 5.1"
    aba.cell(2, 2).value = "TABELA 5.1 SEM AJUSTES"
    bruto = io.BytesIO()
    livro.save(bruto)
    origem = zipfile.ZipFile(io.BytesIO(bruto.getvalue()))
    destino = io.BytesIO()
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_STORED) as arquivo:
        for item in origem.infolist():
            arquivo.writestr(item.filename, origem.read(item.filename))
    from backend.oil.caged import parse_workbook

    try:
        parse_workbook(destino.getvalue(), "2026-08")
    except ValueError as exc:
        return str(exc) == "Título inesperado."
    return False


def reversao_confere(sha_antes, sha_depois):
    return sha_antes == sha_depois


def concluir_mutacao(*, identificador, arquivo, ocorrencias, sha_antes, sha_depois, contagens, testes_falhos, toleradas):
    if ocorrencias == 0:
        return {
            "id": identificador, "arquivo": arquivo, "status": "pulado",
            "motivo_pulo": "trecho não encontrado (n=0)", "detectada": None,
            "sha_blob_antes": sha_antes, "sha_blob_depois_reversao": sha_depois,
            "contagens": contagens, "testes_falhos": testes_falhos, "parar": False,
        }
    if ocorrencias != 1:
        return {
            "id": identificador, "arquivo": arquivo, "status": "falhou",
            "motivo_pulo": None, "detectada": None,
            "sha_blob_antes": sha_antes, "sha_blob_depois_reversao": sha_depois,
            "contagens": contagens, "testes_falhos": testes_falhos, "parar": False,
            "detalhe": f"trecho encontrado n={ocorrencias}",
        }
    if not reversao_confere(sha_antes, sha_depois):
        return {
            "id": identificador, "arquivo": arquivo, "status": "falhou",
            "motivo_pulo": None, "detectada": None,
            "sha_blob_antes": sha_antes, "sha_blob_depois_reversao": sha_depois,
            "contagens": contagens, "testes_falhos": testes_falhos, "parar": True,
            "detalhe": "blob não voltou ao SHA original",
        }
    motivo = None
    for item in toleradas:
        if item.get("id") == identificador and isinstance(item.get("motivo"), str) and item["motivo"].strip():
            motivo = item["motivo"].strip()
    detectada = bool(testes_falhos) or bool(contagens and (contagens.get("failed") or contagens.get("errors")))
    if not detectada and not motivo:
        return {
            "id": identificador, "arquivo": arquivo, "status": "falhou",
            "motivo_pulo": None, "detectada": False,
            "sha_blob_antes": sha_antes, "sha_blob_depois_reversao": sha_depois,
            "contagens": contagens, "testes_falhos": testes_falhos, "parar": False,
            "detalhe": "sobrevivente",
        }
    return {
        "id": identificador, "arquivo": arquivo, "status": "ok",
        "motivo_pulo": None, "detectada": detectada,
        "sha_blob_antes": sha_antes, "sha_blob_depois_reversao": sha_depois,
        "contagens": contagens, "testes_falhos": testes_falhos, "parar": False,
        "detalhe": motivo,
    }


def avaliar_limpeza(*, conteineres, processos, porcelain_inicio, porcelain_fim, temporarios):
    problemas = []
    if conteineres:
        problemas.append("contêiner restante: " + ", ".join(conteineres))
    if processos:
        problemas.append("processo restante")
    if porcelain_inicio != porcelain_fim:
        problemas.append("git status divergente")
    if temporarios:
        problemas.append("temporário restante")
    return nova_etapa("limpeza", "falhou" if problemas else "ok", comando="docker ps -a --filter name=oil-", detalhes={"problemas": problemas, "conteineres": list(conteineres)})


def preparar_testes_ao_vivo(ao_vivo, ambiente, executar):
    del ambiente
    if not ao_vivo:
        return nova_etapa("testes_ao_vivo", "pulado", motivo_pulo=MOTIVO_REDE, detalhes={"rede_ao_vivo": False})
    return executar()


def diretorio_padrao():
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "oil-check"
    return Path.home() / ".cache" / "oil-check"


def _dentro(caminho, raiz):
    try:
        caminho.resolve().relative_to(raiz.resolve())
        return True
    except ValueError:
        return False


def ignorado_pelo_git(caminho, raiz):
    resultado = subprocess.run(["git", "-C", str(raiz), "check-ignore", "-q", "--", str(caminho)], capture_output=True)
    return resultado.returncode == 0


def resolver_saida(caminho, *, no_repo, raiz, modo, head, momento, cache_dir=None):
    if caminho is None:
        pasta = Path(cache_dir) if cache_dir else diretorio_padrao()
        nome = f"{momento.strftime('%Y%m%d')}_{head[:12]}_{modo}.json"
        return pasta / nome
    destino = Path(caminho)
    if not destino.is_absolute():
        destino = Path.cwd() / destino
    destino = destino.resolve()
    if _dentro(destino, raiz) and not no_repo:
        raise ErroUso("saída dentro do repositório recusada; use um caminho fora do Git ou --saida-no-repo")
    if _dentro(destino, raiz) and no_repo and not ignorado_pelo_git(destino, raiz):
        raise ErroUso("caminho no repositório precisa ser ignorado pelo .gitignore")
    return destino


def _git(argumentos, raiz=RAIZ):
    resultado = subprocess.run(["git", "-C", str(raiz), *argumentos], capture_output=True)
    if resultado.returncode != 0:
        return None
    return resultado.stdout.decode().strip()


def porcelain(raiz=RAIZ):
    resultado = subprocess.run(["git", "-C", str(raiz), "status", "--porcelain"], capture_output=True, text=True)
    if resultado.returncode != 0:
        raise ErroInterno(redigir(resultado.stderr[-400:]))
    return resultado.stdout


def nome_secreto(nome):
    alto = nome.upper()
    return any(parte in alto for parte in ("PASSWORD", "SECRET", "TOKEN", "DATABASE_URL", "DSN", "COOKIE", "CREDENTIAL", "API_KEY", "SECRET_KEY"))


def ambiente_base():
    ambiente = {}
    for chave, valor in os.environ.items():
        if nome_secreto(chave) or chave.startswith(("OIL_", "PYTEST_")) or chave == "RUN_LIVE_IBGE":
            continue
        ambiente[chave] = valor
    ambiente["PYTHONDONTWRITEBYTECODE"] = "1"
    ambiente["PYTHONPATH"] = str(RAIZ) + os.pathsep + ambiente.get("PYTHONPATH", "")
    ambiente["PYTHONPATH"] = ambiente["PYTHONPATH"].rstrip(os.pathsep)
    return ambiente


def linha_comando(argv, variaveis=()):
    prefixo = " ".join(f"{nome}=<omitido>" if nome_secreto(nome) else f"{nome}={valor}" for nome, valor in variaveis)
    corpo = " ".join(argv)
    return f"{prefixo} {corpo}".strip()


def executar_processo(argv, *, cwd, env, timeout):
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, start_new_session=True)


def parse_junit(caminho):
    import xml.etree.ElementTree as ET

    raiz = ET.parse(caminho).getroot()
    suites = list(raiz.findall("testsuite")) if raiz.tag == "testsuites" else [raiz]
    testes = falhas = erros = pulados = 0
    nomes = []
    for suite in suites:
        testes += int(suite.attrib.get("tests", 0))
        falhas += int(suite.attrib.get("failures", 0))
        erros += int(suite.attrib.get("errors", 0))
        pulados += int(suite.attrib.get("skipped", 0))
        for caso in suite.iter("testcase"):
            if caso.find("failure") is None and caso.find("error") is None:
                continue
            arquivo = caso.attrib.get("file") or caso.attrib.get("classname", "").replace(".", "/")
            nomes.append(f"{arquivo}::{caso.attrib.get('name')}")
    return {"passed": testes - falhas - erros - pulados, "failed": falhas, "errors": erros, "skipped": pulados, "deselected": 0}, nomes


def contagens_da_saida(stdout, junit):
    texto = parse_contagens_pytest(stdout or "")
    if junit and Path(junit).is_file():
        try:
            contagens, falhos = parse_junit(junit)
        except (OSError, ValueError, Exception):
            contagens, falhos = None, []
        else:
            if texto and texto.get("deselected"):
                contagens["deselected"] = texto["deselected"]
            return contagens, falhos
    if texto is None:
        return None, []
    return texto, []


def comando_de_rede(comando):
    baixo = (comando or "").lower()
    return any(host in baixo for host in HOSTS_VIVOS)


def carregar_frases():
    texto = (RAIZ / "frontend/tests/linguagem.ts").read_text(encoding="utf-8")
    bloco = re.search(r"bannedPhrases=\[(.*?)\]", texto, re.S)
    if not bloco:
        raise ErroInterno("bannedPhrases ausente")
    frases = re.findall(r"'([^']+)'", bloco.group(1))
    tipos = (RAIZ / "frontend/lib/types.ts").read_text(encoding="utf-8")
    legenda = re.search(r"export const LEGEND='([^']+)'", tipos)
    if not legenda:
        raise ErroInterno("LEGEND ausente")
    return frases, legenda.group(1)


def violacoes_linguagem(texto, frases, legenda, marcos=()):
    corpus = unicodedata.normalize("NFKC", texto.replace(legenda, " ")).casefold()
    encontradas = [frase for frase in frases if frase.casefold() in corpus]
    if re.search(r"antes e depois d[aoe]\b", corpus):
        encontradas.append("antes e depois de evento")
    variacao = re.compile(r"\b(subiu|caiu|aumentou|diminuiu|variação)\b")
    data = re.compile(r"\b\d{2}/\d{2}(?:/\d{4})?\b")
    marco = re.compile(r"\b(?:com [ao]|a partir d[ao]) (promulgação|aprovação|vigência|marco|lei)\b")
    marcos_norm = [item.casefold() for item in marcos]
    for frase in re.split(r"[.!?\n]+", corpus):
        if variacao.search(frase) and (any(item in frase for item in marcos_norm) or data.search(frase) or marco.search(frase)):
            encontradas.append("marco e variação na mesma frase")
    return encontradas


def trecho_curto(texto):
    limpo = " ".join(texto.split())
    return limpo[:120]


def varrer_fontes_backend(frases, legenda):
    ocorrencias = []
    for caminho in sorted((RAIZ / "backend/oil").glob("**/*.py")):
        try:
            arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        except SyntaxError:
            ocorrencias.append({"arquivo": str(caminho.relative_to(RAIZ)), "trecho": "sintaxe ilegível"})
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Constant) and isinstance(no.value, str):
                for violacao in violacoes_linguagem(no.value, frases, legenda):
                    ocorrencias.append({"arquivo": str(caminho.relative_to(RAIZ)), "violacao": violacao, "trecho": trecho_curto(no.value)})
    return ocorrencias


def excecoes_publicadas():
    arquivos = [caminho for caminho in RAIZ.rglob("metodologia-v1.md") if ".git" not in caminho.parts]
    if not arquivos:
        return [], "metodologia-v1 ausente; nenhuma exceção extra"
    return [], str(arquivos[0].relative_to(RAIZ))


def sha256_arquivo(caminho):
    digest = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def manifesto_caged():
    return json.loads((RAIZ / "backend/data/caged_manifesto.json").read_text(encoding="utf-8"))


def localizar_caged(diretorio):
    manifesto = manifesto_caged()
    por_nome = {}
    por_hash = {}
    if diretorio and Path(diretorio).is_dir():
        for caminho in Path(diretorio).iterdir():
            if caminho.is_file():
                por_nome[caminho.name] = caminho
                por_hash[sha256_arquivo(caminho)] = caminho
    itens = []
    for competencia, spec in CAGED_ESPERADO.items():
        entrada = next((item for item in manifesto if item.get("competencia") == competencia), None)
        caminho = None
        if diretorio and Path(diretorio).is_dir():
            caminho = por_nome.get(spec["arquivo"]) or por_hash.get(spec["sha256"])
            if entrada and caminho is None:
                caminho = por_nome.get(entrada.get("arquivo", "")) or por_hash.get(entrada.get("sha256", ""))
        sha = sha256_arquivo(caminho) if caminho else None
        itens.append({
            "competencia": competencia,
            "arquivo": spec["arquivo"],
            "presente": caminho is not None,
            "sha_encontrado": sha,
            "sha_esperado": spec["sha256"],
            "sha_manifesto": None if entrada is None else entrada.get("sha256"),
            "caminho": None if caminho is None else str(caminho),
        })
    return itens


def filhos_vivos():
    vivos = []
    proc = Path("/proc")
    if not proc.is_dir():
        return vivos
    for entrada in proc.iterdir():
        if not entrada.name.isdigit():
            continue
        try:
            campos = (entrada / "stat").read_text().split()
            if int(campos[3]) != os.getpid():
                continue
            if campos[2] == "Z":
                continue
            vivos.append(int(entrada.name))
        except (OSError, IndexError, ValueError):
            continue
    return vivos


def conteineres_oil():
    if shutil.which("docker") is None:
        return None
    resultado = subprocess.run(["docker", "ps", "-a", "--filter", "name=oil-", "--format", "{{.Names}}"], capture_output=True, text=True)
    if resultado.returncode != 0:
        return None
    return [linha.strip() for linha in resultado.stdout.splitlines() if linha.strip()]


def remover_conteiner(nome):
    subprocess.run(["docker", "rm", "-f", "-v", nome], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def artefatos_gerados():
    return [
        RAIZ / "frontend/test-results",
        RAIZ / "frontend/playwright-report",
        RAIZ / "frontend/blob-report",
        RAIZ / "frontend/tsconfig.tsbuildinfo",
        RAIZ / ".pytest_cache",
        RAIZ / "backend/.pytest_cache",
        RAIZ / "poc/.pytest_cache",
    ]


def limpar_artefatos():
    for caminho in artefatos_gerados():
        if caminho.is_dir():
            shutil.rmtree(caminho, ignore_errors=True)
        elif caminho.is_file():
            caminho.unlink(missing_ok=True)


class PostgresDescartavel:
    def __init__(self):
        self.nome = "oil-check-" + uuid.uuid4().hex[:10]
        self.senha = uuid.uuid4().hex + uuid.uuid4().hex
        self.porta = None
        self.url = None

    def iniciar(self):
        if shutil.which("docker") is None:
            raise RuntimeError("Docker não encontrado")
        ambiente = os.environ.copy()
        ambiente["POSTGRES_PASSWORD"] = self.senha
        ambiente["POSTGRES_USER"] = "oil_test"
        ambiente["POSTGRES_DB"] = "oil_check"
        subprocess.run([
            "docker", "run", "--rm", "--detach", "--name", self.nome,
            "--label", "oil.task=check", "--publish", "127.0.0.1::5432",
            "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_USER", "--env", "POSTGRES_DB",
            IMAGEM_POSTGRES,
        ], env=ambiente, check=True, stdout=subprocess.DEVNULL)
        try:
            for _ in range(120):
                pronto = subprocess.run(["docker", "exec", self.nome, "pg_isready", "-U", "oil_test", "-d", "oil_check"], capture_output=True)
                if pronto.returncode == 0:
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("PostgreSQL descartável não iniciou")
            porta = subprocess.check_output(["docker", "port", self.nome, "5432/tcp"], text=True).strip()
            self.porta = int(porta.rsplit(":", 1)[1])
            if self.porta == 5432:
                raise RuntimeError("porta 5432 recusada")
            self.url = f"postgresql+psycopg://oil_test:{self.senha}@127.0.0.1:{self.porta}/oil_check"
        except Exception:
            self.parar()
            raise

    def parar(self):
        remover_conteiner(self.nome)


def proteger(nome, func):
    inicio = time.monotonic()
    try:
        etapa = func()
    except ErroUso:
        raise
    except Exception as exc:
        etapa = nova_etapa(nome, "falhou", detalhes={"erro": "falha interna da etapa", "mensagem": redigir(str(exc))[:400]})
    etapa["duracao_s"] = round(time.monotonic() - inicio, 3)
    return etapa


def etapa_pulada(nome, motivo):
    return nova_etapa(nome, "pulado", motivo_pulo=motivo)


def versoes_ambiente():
    def versao(argv):
        if shutil.which(argv[0]) is None:
            return "ausente"
        resultado = subprocess.run(argv, capture_output=True, text=True)
        linha = (resultado.stdout or resultado.stderr or "").strip().splitlines()
        return linha[0] if linha else "ausente"
    return {
        "python": versao([sys.executable, "--version"]),
        "node": versao(["node", "--version"]),
        "docker": versao(["docker", "--version"]),
    }


def coletar_git():
    head = _git(["rev-parse", "HEAD"]) or ""
    base_ref, base_sha = "main", None
    for ref in ("origin/main", "main"):
        sha = _git(["rev-parse", ref])
        if sha:
            base_ref = "main" if ref.endswith("main") else ref
            base_sha = sha
            break
    estado = porcelain()
    return {
        "head_sha": head,
        "base_ref": base_ref,
        "base_sha": base_sha or "",
        "arvore_limpa_inicio": estado == "",
        "arvore_limpa_fim": False,
        "_porcelain": estado,
    }


def etapa_ambiente(git_info):
    detalhes = versoes_ambiente()
    if not git_info["head_sha"] or not git_info["base_sha"]:
        return nova_etapa("ambiente", "falhou", comando="git rev-parse HEAD", detalhes={**detalhes, "erro": "SHA do HEAD ou da base ausente"})
    if not git_info["arvore_limpa_inicio"]:
        return nova_etapa("ambiente", "falhou", comando="git status --porcelain", detalhes={**detalhes, "erro": "árvore suja"})
    return nova_etapa("ambiente", "ok", comando="git rev-parse HEAD", detalhes=detalhes)


def etapa_gitleaks(nome, historico, pasta):
    if shutil.which("gitleaks") is None:
        return nova_etapa(nome, "falhou", comando="gitleaks", detalhes={"erro": "gitleaks não encontrado", "achados": None})
    relatorio = pasta / f"{nome}.json"
    if historico:
        argv = ["gitleaks", "detect", "--source", str(RAIZ), "--log-opts=--all", "--redact",
                "--config", str(RAIZ / ".gitleaks.toml"), "--report-format", "json", "--report-path", str(relatorio)]
    else:
        argv = ["gitleaks", "protect", "--staged", "--redact", "--config", str(RAIZ / ".gitleaks.toml"),
                "--report-format", "json", "--report-path", str(relatorio)]
    comando = " ".join(argv)
    if comando_de_rede(comando):
        return nova_etapa(nome, "falhou", comando=comando, detalhes={"erro": MOTIVO_REDE})
    resultado = executar_processo(argv, cwd=RAIZ, env=ambiente_base(), timeout=600)
    achados = None
    if relatorio.is_file():
        try:
            bruto = json.loads(relatorio.read_text(encoding="utf-8") or "[]")
            achados = len(bruto) if isinstance(bruto, list) else len(bruto.get("findings", bruto.get("Findings", [])))
        except json.JSONDecodeError:
            return nova_etapa(nome, "falhou", comando=comando, detalhes={"erro": "contagem ilegível", "achados": None})
    if resultado.returncode != 0 or achados not in (0,):
        return nova_etapa(nome, "falhou", comando=comando, detalhes={"achados": achados, "codigo": resultado.returncode})
    return nova_etapa(nome, "ok", comando=comando, detalhes={"achados": 0})


def etapa_pytest(nome, argv, variaveis, cwd, modo):
    comando = linha_comando(argv, variaveis)
    recusar_filtro_no_completo(modo, comando)
    if comando_de_rede(comando):
        return nova_etapa(nome, "falhou", comando=redigir(comando), detalhes={"erro": MOTIVO_REDE})
    junit = next((item.split("=", 1)[1] for item in argv if item.startswith("--junitxml=")), None)
    ambiente = ambiente_base()
    ambiente["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    for chave, valor in variaveis:
        ambiente[chave] = valor
    resultado = executar_processo(argv, cwd=cwd, env=ambiente, timeout=1800)
    contagens, falhos = contagens_da_saida(resultado.stdout + "\n" + resultado.stderr, junit)
    etapa = classificar_contagens(contagens, resultado.returncode, modo, comando, nome)
    etapa["comando"] = redigir(comando)
    if falhos:
        etapa["detalhes"]["testes_falhos"] = falhos[:50]
    return etapa


def etapa_typecheck(modo):
    comando = "npx tsc --noEmit --incremental false"
    recusar_filtro_no_completo(modo, comando)
    if not (RAIZ / "frontend/node_modules").is_dir():
        return nova_etapa("frontend_typecheck", "falhou", comando=comando, detalhes={"erro": "frontend/node_modules ausente"})
    resultado = executar_processo(["npx", "tsc", "--noEmit", "--incremental", "false"], cwd=RAIZ / "frontend", env=ambiente_base(), timeout=300)
    status = "ok" if resultado.returncode == 0 else "falhou"
    return nova_etapa("frontend_typecheck", status, comando=comando, detalhes={"codigo": resultado.returncode})


def etapa_build():
    comando = "NEXT_TELEMETRY_DISABLED=1 npx next build --webpack"
    if not (RAIZ / "frontend/node_modules").is_dir():
        return nova_etapa("frontend_build", "falhou", comando=comando, detalhes={"erro": "frontend/node_modules ausente"})
    ambiente = ambiente_base()
    ambiente["NEXT_TELEMETRY_DISABLED"] = "1"
    resultado = executar_processo(["npx", "next", "build", "--webpack"], cwd=RAIZ / "frontend", env=ambiente, timeout=900)
    return nova_etapa("frontend_build", "ok" if resultado.returncode == 0 else "falhou", comando=comando, detalhes={"codigo": resultado.returncode})


def listar_playwright(grep, ambiente):
    argv = ["npx", "playwright", "test", "--list"]
    if grep:
        argv.extend(["--grep", grep])
    resultado = executar_processo(argv, cwd=RAIZ / "frontend", env=ambiente, timeout=180)
    total = re.search(r"Total:\s+(\d+)\s+test", resultado.stdout)
    if total:
        return int(total.group(1)), resultado.returncode
    linhas = [linha for linha in resultado.stdout.splitlines() if "›" in linha]
    return (len(linhas) if resultado.returncode == 0 else None), resultado.returncode


def etapa_playwright(modo, pasta):
    grep = "@rapido" if modo == "rapido" else None
    argv = ["npx", "playwright", "test", "--reporter=json"]
    if grep:
        argv.extend(["--grep", grep])
    variaveis = [("OIL_BROWSER_CHANNEL", "chromium")] if sys.platform.startswith("linux") else []
    comando = linha_comando(argv, variaveis)
    recusar_filtro_no_completo(modo, comando)
    if not (RAIZ / "frontend/node_modules").is_dir():
        return nova_etapa("playwright", "falhou", comando=comando, bateria_completa=False if modo == "rapido" else None, detalhes={"erro": "frontend/node_modules ausente"})
    ambiente = ambiente_base()
    for chave, valor in variaveis:
        ambiente[chave] = valor
    relatorio = pasta / "playwright.json"
    ambiente["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(relatorio)
    total, _ = listar_playwright(None, ambiente)
    selecionados, _ = listar_playwright(grep, ambiente) if grep else (total, 0)
    resultado = executar_processo(argv, cwd=RAIZ / "frontend", env=ambiente, timeout=1800)
    bruto = resultado.stdout
    if relatorio.is_file() and not bruto.strip().startswith("{"):
        bruto = relatorio.read_text(encoding="utf-8")
    contagens = parse_playwright(bruto)
    if contagens is None and selecionados == 0 and total:
        contagens = {"passed": 0, "failed": 0, "skipped": 0, "deselected": total, "errors": 0}
    if contagens is not None and total is not None:
        executados = contagens["passed"] + contagens["failed"] + contagens["skipped"] + contagens["errors"]
        contagens["deselected"] = max(contagens["deselected"], total - executados)
    etapa = classificar_contagens(contagens, resultado.returncode, modo, comando, "playwright")
    etapa["comando"] = comando
    return etapa


def parse_playwright(texto):
    if not texto:
        return None
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio < 0 or fim < inicio:
        return None
    try:
        dados = json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError:
        return None
    stats = dados.get("stats") or {}
    if not stats and "suites" not in dados:
        return None
    return {
        "passed": int(stats.get("expected", 0)),
        "failed": int(stats.get("unexpected", 0)) + int(stats.get("flaky", 0)),
        "skipped": int(stats.get("skipped", 0)),
        "deselected": 0,
        "errors": 0,
    }


def cenarios_axe(texto):
    if not texto:
        return None
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio < 0 or fim < inicio:
        return None
    try:
        dados = json.loads(texto[inicio:fim + 1])
    except json.JSONDecodeError:
        return None

    def visitar(no, acumulado):
        for spec in no.get("specs", []):
            titulo = spec.get("title", "")
            if "axe" not in titulo.casefold():
                continue
            ok = any(teste.get("status") in {"expected", "skipped"} for teste in spec.get("tests", []))
            falha = any(teste.get("status") not in {"expected", "skipped"} for teste in spec.get("tests", []))
            acumulado.append({"titulo": titulo, "ok": ok and not falha})
        for filho in no.get("suites", []):
            visitar(filho, acumulado)

    achados = []
    visitar(dados, achados)
    return achados


def etapa_axe(modo, pasta, playwright):
    relatorio = pasta / "playwright.json"
    texto = relatorio.read_text(encoding="utf-8") if relatorio.is_file() else ""
    cenarios = cenarios_axe(texto)
    comando = playwright.get("comando")
    if cenarios is None:
        return nova_etapa("axe", "falhou", comando=comando, detalhes={"erro": "contagem ilegível"})
    passed = sum(1 for item in cenarios if item["ok"])
    failed = len(cenarios) - passed
    deselected = 0
    if modo == "rapido":
        origem = (playwright.get("contagens") or {}) if isinstance(playwright, dict) else {}
        deselected = int(origem.get("deselected") or 0)
        if deselected == 0:
            deselected = 1
    contagens = {"passed": passed, "failed": failed, "skipped": 0, "deselected": deselected, "errors": 0}
    etapa = classificar_contagens(contagens, 0 if failed == 0 else 1, modo, comando or "", "axe")
    etapa["detalhes"]["cenarios"] = len(cenarios)
    return etapa


def etapa_frases(servidor):
    frases, legenda = carregar_frases()
    excecoes, origem = excecoes_publicadas()
    ocorrencias = varrer_fontes_backend(frases, legenda)
    html_erro = None
    if servidor is None:
        html_erro = "navegador ou servidor de teste indisponível"
    else:
        try:
            blocos = servidor.varrer()
            for bloco in blocos:
                for violacao in violacoes_linguagem(bloco["texto"], frases, legenda):
                    if violacao in excecoes:
                        continue
                    ocorrencias.append({"rota": bloco["rota"], "trecho": trecho_curto(bloco["texto"]), "violacao": violacao})
        except Exception as exc:
            html_erro = redigir(str(exc))[:300]
    if html_erro or ocorrencias:
        return nova_etapa("frases_causais", "falhou", comando="varredura de linguagem", detalhes={"ocorrencias": ocorrencias[:80], "erro": html_erro, "excecoes": excecoes, "metodologia": origem})
    return nova_etapa("frases_causais", "ok", comando="varredura de linguagem", detalhes={"ocorrencias": [], "excecoes": excecoes, "metodologia": origem})


def etapa_simulado(database_url, servidor):
    comando = "DATABASE_URL=<omitido> OIL_TEST_MODE=0 python -c teste_negativo_api"
    if not database_url:
        return nova_etapa("simulado_como_real", "falhou", comando=comando, detalhes={"erro": "Postgres descartável indisponível"})
    ambiente = ambiente_base()
    ambiente["DATABASE_URL"] = database_url
    ambiente["OIL_TEST_MODE"] = "0"
    ambiente["OIL_DISPOSABLE_DATABASE"] = "1"
    resultado = executar_processo([sys.executable, "-c", "import scripts.check as verificacao; raise SystemExit(verificacao.teste_negativo_api_cli())"], cwd=RAIZ, env=ambiente, timeout=180)
    try:
        api = json.loads(resultado.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        api = {"ok": False, "erro": "contagem ilegível"}
    ui = {"ok": False, "erro": "navegador ou servidor de teste indisponível"}
    if servidor is not None:
        try:
            ui = servidor.simulado()
        except Exception as exc:
            ui = {"ok": False, "erro": redigir(str(exc))[:300]}
    status = "ok" if api.get("ok") and ui.get("ok") else "falhou"
    return nova_etapa("simulado_como_real", status, comando=comando, detalhes={"api": api, "ui": ui})


def teste_negativo_api_cli():
    os.environ["OIL_TEST_MODE"] = "0"
    try:
        from datetime import timezone
        from decimal import Decimal

        from alembic import command
        from alembic.config import Config
        from fastapi.testclient import TestClient
        from sqlalchemy import select

        from backend.oil.catalog import SPECS
        from backend.oil.db import make_engine, sessions
        from backend.oil.ingest import ensure_catalog
        from backend.oil.main import app
        from backend.oil.models import Coleta, Observacao, Serie

        engine = make_engine()
        command.upgrade(Config(str(RAIZ / "backend/alembic.ini")), "head")
        fabrica = sessions(engine)
        spec = SPECS["desocupacao"]
        with fabrica.begin() as sessao:
            fonte_id = ensure_catalog(sessao, spec)
            serie = sessao.scalar(select(Serie).where(Serie.codigo == "desocupacao"))
            coleta = Coleta(
                fonte_id=fonte_id, serie_codigo="desocupacao", url_consultada="https://exemplo.invalid/simulada",
                coletado_em=datetime.now(timezone.utc), codigo_http=200, simulada=True, tipo="serie", valida=True,
                hash_sha256="a" * 64,
            )
            sessao.add(coleta)
            sessao.flush()
            sessao.add(Observacao(
                serie_id=serie.id, periodo="202608", valor=Decimal("424242"), cv=Decimal("1"),
                coleta_id=coleta.id, versao=1,
            ))
        with TestClient(app) as cliente:
            respostas = [cliente.get(rota).json() for rota in (
                "/api/v1/indicadores/desocupacao/serie",
                "/api/v1/indicadores",
                "/api/v1/proposicoes/2233802",
            )]
        engine.dispose()
        texto = json.dumps(respostas, ensure_ascii=False)

        def simulado(valor):
            if isinstance(valor, dict):
                if valor.get("simulada") is True:
                    return True
                return any(simulado(item) for item in valor.values())
            if isinstance(valor, list):
                return any(simulado(item) for item in valor)
            return False

        if simulado(respostas) or "424242" in texto:
            print(json.dumps({"ok": False, "erro": "payload simulado vazou em modo normal"}))
            return 1
        for marca in MARCAS_FIXTURE:
            if marca.casefold() in texto.casefold():
                print(json.dumps({"ok": False, "erro": "marca de fixture na API"}))
                return 1
        print(json.dumps({"ok": True, "bloqueado": True}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "erro": redigir(str(exc))[:300]}))
        return 1


def etapa_caged(diretorio, database_url):
    manifesto = {item["competencia"]: item for item in manifesto_caged()}
    erros_manifesto = []
    for competencia, spec in CAGED_ESPERADO.items():
        entrada = manifesto.get(competencia)
        if not entrada:
            erros_manifesto.append(competencia + " ausente no manifesto")
        elif entrada.get("sha256") != spec["sha256"]:
            erros_manifesto.append({"competencia": competencia, "sha_encontrado": entrada.get("sha256")})
    if erros_manifesto:
        return nova_etapa("caged_arquivos_reais", "falhou", comando="sha256 local", detalhes={"erro": "sha do manifesto divergente", "sha_encontrado": erros_manifesto})
    itens = localizar_caged(diretorio)
    classe = classificar_caged_arquivos(itens)
    if classe["status"] != "sha_ok":
        return nova_etapa("caged_arquivos_reais", classe["status"], motivo_pulo=classe["motivo_pulo"], comando="sha256 local", detalhes=classe["detalhes"])
    if not titulo_sem_ajustes_recusado():
        return nova_etapa("caged_arquivos_reais", "falhou", comando="parse_workbook", detalhes={"erro": "título SEM AJUSTES não foi recusado"})
    if not database_url:
        return nova_etapa("caged_arquivos_reais", "falhou", comando="MockTransport", detalhes={"erro": "Postgres descartável indisponível"})
    ambiente = ambiente_base()
    ambiente["DATABASE_URL"] = database_url
    ambiente["OIL_CAGED_DIR"] = diretorio or ""
    ambiente.pop("OIL_CAGED_READ_TIMEOUT", None)
    resultado = executar_processo([sys.executable, "-c", "import scripts.check as verificacao; raise SystemExit(verificacao.exercitar_caged_cli())"], cwd=RAIZ, env=ambiente, timeout=600)
    try:
        corpo = json.loads(resultado.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return nova_etapa("caged_arquivos_reais", "falhou", comando="DATABASE_URL=<omitido> MockTransport", detalhes={"erro": "contagem ilegível"})
    if not corpo.get("ok"):
        return nova_etapa("caged_arquivos_reais", "falhou", comando="DATABASE_URL=<omitido> MockTransport", detalhes={"erro": corpo.get("erro", "falha na coleta simulada local")})
    valores = conferir_valores_caged(corpo.get("pontos") or {}, corpo.get("versoes") or {})
    download = conferir_download(corpo.get("download") or {})
    if valores["status"] != "ok" or download["status"] != "ok":
        return nova_etapa("caged_arquivos_reais", "falhou", comando="DATABASE_URL=<omitido> MockTransport", detalhes={"valores": valores["detalhes"], "download": download["detalhes"]})
    return nova_etapa("caged_arquivos_reais", "ok", comando="DATABASE_URL=<omitido> MockTransport", detalhes={"arquivos": 2, "requisicoes": 2})


def exercitar_caged_cli():
    try:
        import asyncio

        import httpx
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import select, text

        from backend.oil.caged import CagedCollector, download_timeout, parse_workbook
        from backend.oil.db import make_engine, sessions
        from backend.oil.models import Coleta, Observacao, Serie

        os.environ.pop("OIL_CAGED_READ_TIMEOUT", None)
        diretorio = Path(os.environ["OIL_CAGED_DIR"])
        engine = make_engine()
        command.upgrade(Config(str(RAIZ / "backend/alembic.ini")), "head")
        with engine.begin() as conexao:
            conexao.execute(text("TRUNCATE observacao, divulgacao, caged_arquivo, coleta, marco, proposicao_snapshot, proposicao, serie, fonte RESTART IDENTITY CASCADE"))
        fabrica = sessions(engine)
        pontos = {}
        download = {}
        manifesto = {item["competencia"]: item for item in manifesto_caged()}

        async def sem_espera(_atraso):
            return None

        async def ingerir(competencia, caminho):
            bruto = caminho.read_bytes()
            pontos[competencia] = {chave: int(valor) for chave, valor in parse_workbook(bruto, competencia).items()}
            entrada = dict(manifesto[competencia])
            pedido = {"n": 0}
            prazo = download_timeout()

            def handler(_request):
                pedido["n"] += 1
                return httpx.Response(200, content=bruto)

            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as cliente:
                await CagedCollector(fabrica, cliente, simulada=False, sleep=sem_espera).collect(entrada)
            with fabrica() as sessao:
                coleta = sessao.scalar(select(Coleta).where(Coleta.mes_referencia == competencia, Coleta.valida.is_(True)).order_by(Coleta.id.desc()))
                valida = bool(coleta and coleta.valida)
            download[competencia] = {"requisicoes": pedido["n"], "valida": valida, "timeout": [int(prazo.connect), int(prazo.read), int(prazo.write), int(prazo.pool)]}

        async def principal():
            for competencia in ("2026-07", "2026-08"):
                caminho = next(diretorio.glob(CAGED_ESPERADO[competencia]["arquivo"]))
                await ingerir(competencia, caminho)

        asyncio.run(principal())
        versoes = {}
        with fabrica() as sessao:
            serie = sessao.scalar(select(Serie.id).where(Serie.codigo == "caged-saldo"))
            for periodo in VERSOES_ESPERADAS:
                linhas = sessao.scalars(select(Observacao).where(Observacao.serie_id == serie, Observacao.periodo == periodo).order_by(Observacao.versao)).all()
                versoes[periodo] = [[linha.versao, int(linha.valor)] for linha in linhas]
        engine.dispose()
        print(json.dumps({"ok": True, "pontos": pontos, "versoes": versoes, "download": download}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "erro": redigir(str(exc))[:400]}))
        return 1


def etapa_limites(git_info):
    comando = "git show <base>:backend/oil/caged.py"
    try:
        base_caged = subprocess.check_output(["git", "-C", str(RAIZ), "show", f"{git_info['base_sha']}:backend/oil/caged.py"])
        base_ingest = subprocess.check_output(["git", "-C", str(RAIZ), "show", f"{git_info['base_sha']}:backend/oil/ingest.py"])
    except subprocess.CalledProcessError as exc:
        return nova_etapa("limites_seguranca", "falhou", comando=comando, detalhes={"erro": redigir(exc.stderr.decode()[:300] if exc.stderr else "git show falhou")})
    cabeca = extrair_limites((RAIZ / "backend/oil/caged.py").read_text(encoding="utf-8"), (RAIZ / "backend/oil/ingest.py").read_text(encoding="utf-8"))
    base = extrair_limites(base_caged.decode(), base_ingest.decode())
    diffs = diferencas_limites(base, cabeca)
    ausentes = sorted(set(itens_ausentes(base) + itens_ausentes(cabeca)))
    runtime = executar_processo([sys.executable, "-c", "import scripts.check as verificacao; raise SystemExit(verificacao.exercitar_timeout_cli())"], cwd=RAIZ, env=ambiente_base(), timeout=60)
    try:
        prazo = json.loads(runtime.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        prazo = {"ok": False, "erro": "contagem ilegível"}
    if diffs or ausentes or not prazo.get("ok"):
        return nova_etapa("limites_seguranca", "falhou", comando=comando, detalhes={"diferencas": diffs, "ausentes": ausentes, "runtime": prazo})
    return nova_etapa("limites_seguranca", "ok", comando=comando, detalhes={"diferencas": [], "ausentes": [], "runtime": prazo})


def exercitar_timeout_cli():
    os.environ.pop("OIL_CAGED_READ_TIMEOUT", None)
    from backend.oil.caged import download_timeout

    padrao = download_timeout()
    os.environ["OIL_CAGED_READ_TIMEOUT"] = "999"
    teto = download_timeout()
    ok = (int(padrao.connect), int(padrao.read), int(padrao.write), int(padrao.pool)) == TIMEOUT_CAGED and int(teto.read) == 300
    print(json.dumps({"ok": ok, "padrao": [int(padrao.connect), int(padrao.read), int(padrao.write), int(padrao.pool)], "teto": int(teto.read)}))
    return 0 if ok else 1


def carregar_mutacoes():
    return json.loads(DADOS.read_text(encoding="utf-8"))


def sha_blob(caminho):
    resultado = subprocess.check_output(["git", "-C", str(RAIZ), "hash-object", "--", str(caminho)], text=True)
    return resultado.strip()


def etapa_mutacoes(grupo, modo, postgres_url, git_info):
    nome = "mutacoes_" + grupo
    if git_info and not git_info.get("arvore_limpa_inicio"):
        return nova_etapa(nome, "falhou", detalhes={"erro": "árvore suja; mutação não aplicada"})
    dados = carregar_mutacoes()
    toleradas = dados.get("mutacoes_toleradas") or []
    resultados = []
    parar = False
    for mutacao in dados[grupo]:
        if parar:
            break
        caminho = RAIZ / mutacao["arquivo"]
        texto = caminho.read_text(encoding="utf-8")
        ocorrencias = texto.count(mutacao["de"])
        if ocorrencias != 1:
            item = concluir_mutacao(
                identificador=mutacao["id"], arquivo=mutacao["arquivo"], ocorrencias=ocorrencias,
                sha_antes=None, sha_depois=None, contagens=None, testes_falhos=[], toleradas=toleradas,
            )
            resultados.append(item)
            continue
        antes = sha_blob(caminho)
        caminho.write_text(texto.replace(mutacao["de"], mutacao["para"], 1), encoding="utf-8")
        try:
            if grupo == "backend":
                contagens, falhos = rodar_bateria_backend(postgres_url, modo)
            else:
                contagens, falhos = rodar_bateria_frontend(modo)
        finally:
            subprocess.run(["git", "-C", str(RAIZ), "checkout", "--", mutacao["arquivo"]], check=False)
        depois = sha_blob(caminho)
        item = concluir_mutacao(
            identificador=mutacao["id"], arquivo=mutacao["arquivo"], ocorrencias=1,
            sha_antes=antes, sha_depois=depois, contagens=contagens, testes_falhos=falhos, toleradas=toleradas,
        )
        resultados.append(item)
        parar = item["parar"]
    status = "falhou" if any(item["status"] != "ok" for item in resultados) or parar else "ok"
    if any(item["status"] == "pulado" for item in resultados):
        status = "falhou"
    return nova_etapa(nome, status, bateria_completa=True, comando=f"git checkout -- <arquivo> ({grupo})", detalhes={"mutacoes": resultados})


def rodar_bateria_backend(database_url, modo):
    if not database_url:
        return None, []
    pasta = diretorio_padrao()
    pasta.mkdir(parents=True, exist_ok=True)
    junit = pasta / "mutacao-backend.xml"
    argv = [sys.executable, "-m", "pytest", "backend/tests", "-q", "-rs", f"--junitxml={junit}", "-p", "no:cacheprovider"]
    variaveis = [("DATABASE_URL", database_url), ("OIL_TEST_MODE", "1"), ("OIL_DISPOSABLE_DATABASE", "1")]
    etapa = etapa_pytest("mutacao", argv, variaveis, RAIZ, modo)
    return etapa["contagens"], etapa["detalhes"].get("testes_falhos", [])


def rodar_bateria_frontend(modo):
    pasta = diretorio_padrao()
    pasta.mkdir(parents=True, exist_ok=True)
    etapa = etapa_playwright("completo" if modo == "completo" else modo, pasta)
    return etapa["contagens"], etapa["detalhes"].get("testes_falhos", [])


class ServidorFrontend:
    def __init__(self, pasta):
        self.pasta = pasta
        self.processo = None
        self.porta = None

    def iniciar(self):
        if not (RAIZ / "frontend/node_modules").is_dir() or shutil.which("npx") is None:
            raise RuntimeError("frontend/node_modules ausente")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.porta = sock.getsockname()[1]
        ambiente = ambiente_base()
        ambiente.update({"OIL_TEST_MODE": "0", "NEXT_TELEMETRY_DISABLED": "1"})
        self.processo = subprocess.Popen(
            ["npx", "next", "dev", "--hostname", "127.0.0.1", "--port", str(self.porta)],
            cwd=RAIZ / "frontend", env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
        )
        import urllib.request
        prazo = time.monotonic() + 120
        while time.monotonic() < prazo:
            if self.processo.poll() is not None:
                raise RuntimeError("servidor de teste encerrou")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.porta}/", timeout=2)
                return
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("servidor de teste não respondeu")

    def _rodar_js(self, modo):
        script = self.pasta / "varredura.mjs"
        script.write_text(SCRIPT_VARREDURA, encoding="utf-8")
        ambiente = ambiente_base()
        if sys.platform.startswith("linux"):
            ambiente["OIL_BROWSER_CHANNEL"] = "chromium"
        resultado = executar_processo(["node", str(script), modo, f"http://127.0.0.1:{self.porta}"], cwd=RAIZ / "frontend", env=ambiente, timeout=180)
        return json.loads(resultado.stdout.strip().splitlines()[-1])

    def varrer(self):
        corpo = self._rodar_js("frases")
        if not corpo.get("ok"):
            raise RuntimeError(corpo.get("erro") or "varredura falhou")
        return corpo["blocos"]

    def simulado(self):
        return self._rodar_js("simulado")

    def parar(self):
        if self.processo and self.processo.poll() is None:
            os.killpg(self.processo.pid, signal.SIGTERM)
            try:
                self.processo.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.processo.pid, signal.SIGKILL)


SCRIPT_VARREDURA = r"""
import { chromium } from '@playwright/test';
const modo = process.argv[2];
const base = process.argv[3];
const channel = process.env.OIL_BROWSER_CHANNEL || undefined;
const browser = await chromium.launch(channel ? {channel} : {});
const page = await browser.newPage();
try {
  if (modo === 'simulado') {
    await page.route('**/api/oil/**', route => {
      const url = route.request().url();
      if (url.includes('/serie')) {
        return route.fulfill({json:{disponivel:true,simulada:true,pontos:[{periodo:'202608',valor:424242,lacuna:false,unidade:'%',cv:1,variacao_anual:0}],codigo:'desocupacao',nome:'Sentinela',valor:424242,unidade:'%',fonte:'MTE',motivo:null}});
      }
      if (url.includes('/lei')) return route.fulfill({json:{simulada:true,ementa:'SENTINELA_LEI'}});
      return route.fulfill({status:404,json:{}});
    });
    await page.setViewportSize({width:1280,height:900});
    await page.goto(base, {waitUntil:'networkidle'});
    const texto = await page.locator('body').innerText();
    const bloqueado = texto.includes('Resposta de teste recusada no modo normal.') && !texto.includes('424242') && !texto.includes('424.242') && !texto.includes('SENTINELA_LEI');
    const rotulado = texto.includes('Dado de teste') && (texto.includes('424242') || texto.includes('424.242') || texto.includes('SENTINELA_LEI'));
    const marcas = ['fixture','Fixture sintética','— fixture de teste'].filter(marca => texto.toLocaleLowerCase('pt-BR').includes(marca.toLocaleLowerCase('pt-BR')));
    console.log(JSON.stringify({ok: (bloqueado || rotulado) && marcas.length===0, bloqueado, rotulado, marcas}));
  } else {
    const blocos = [];
    for (const width of [360,1280]) {
      await page.setViewportSize({width, height:900});
      await page.goto(base, {waitUntil:'networkidle'});
      await page.evaluate(() => document.querySelectorAll('details').forEach(item => { item.open = true; }));
      const textos = await page.locator('p,h1,h2,h3,h4,figcaption,td,th,summary,li,strong,span,small,dd,dt,label,button,caption,[aria-label],[title],[alt]').evaluateAll(elements => elements.map(element => (element.textContent||'')+' '+['aria-label','title','alt'].map(attribute => element.getAttribute(attribute)||'').join(' ')));
      const divs = await page.locator('div').evaluateAll(elements => elements.map(element => Array.from(element.childNodes).filter(node => node.nodeType===Node.TEXT_NODE).map(node => node.textContent||'').join(' ')));
      for (const texto of [...textos, ...divs]) blocos.push({rota:`/ ${width}`, texto});
    }
    console.log(JSON.stringify({ok:true, blocos}));
  }
} catch (error) {
  console.log(JSON.stringify({ok:false, erro:String(error)}));
  process.exitCode = 1;
} finally {
  await browser.close();
}
"""


def executar(opcoes):
    inicio = agora()
    git_info = coletar_git()
    pasta = resolver_saida(opcoes.saida, no_repo=opcoes.saida_no_repo, raiz=RAIZ, modo=opcoes.modo, head=git_info["head_sha"] or "sem-head", momento=inicio).parent
    if opcoes.saida:
        destino = resolver_saida(opcoes.saida, no_repo=opcoes.saida_no_repo, raiz=RAIZ, modo=opcoes.modo, head=git_info["head_sha"] or "sem-head", momento=inicio)
        pasta = destino.parent
    else:
        destino = resolver_saida(None, no_repo=False, raiz=RAIZ, modo=opcoes.modo, head=git_info["head_sha"] or "sem-head", momento=inicio)
        pasta = destino.parent
    pasta.mkdir(parents=True, exist_ok=True)
    postgres = None
    servidor = None
    conteineres = []

    def limpar(*_args):
        if postgres:
            postgres.parar()
        if servidor:
            servidor.parar()
        for nome in conteineres:
            remover_conteiner(nome)
        limpar_artefatos()

    def interromper(_signum, _frame):
        raise KeyboardInterrupt

    sinal_int = signal.signal(signal.SIGINT, interromper)
    sinal_term = signal.signal(signal.SIGTERM, interromper)
    etapas = []
    try:
        etapas.append(proteger("ambiente", lambda: etapa_ambiente(git_info)))
        etapas.append(proteger("gitleaks_staging", lambda: etapa_gitleaks("gitleaks_staging", False, pasta)))
        if opcoes.modo == "completo":
            etapas.append(proteger("gitleaks_historico", lambda: etapa_gitleaks("gitleaks_historico", True, pasta)))
        else:
            etapas.append(etapa_pulada("gitleaks_historico", MOTIVO_RAPIDO))
        if shutil.which("docker"):
            try:
                postgres = PostgresDescartavel()
                postgres.iniciar()
                conteineres.append(postgres.nome)
            except Exception as exc:
                postgres = None
                etapas.append(nova_etapa("pytest_backend", "falhou", comando="docker run --publish 127.0.0.1::5432", detalhes={"erro": redigir(str(exc))[:300]}))
        else:
            etapas.append(nova_etapa("pytest_backend", "falhou", comando="docker run --publish 127.0.0.1::5432", detalhes={"erro": "Docker não encontrado"}))
        if postgres:
            junit = pasta / "pytest_backend.xml"
            etapas.append(proteger("pytest_backend", lambda: etapa_pytest(
                "pytest_backend",
                [sys.executable, "-m", "pytest", "backend/tests", "-q", "-rs", f"--junitxml={junit}", "-p", "no:cacheprovider"],
                [("DATABASE_URL", postgres.url), ("OIL_TEST_MODE", "1"), ("OIL_DISPOSABLE_DATABASE", "1")],
                RAIZ, opcoes.modo,
            )))
        junit_poc = pasta / "pytest_poc.xml"
        etapas.append(proteger("pytest_poc", lambda: etapa_pytest(
            "pytest_poc",
            [sys.executable, "-m", "pytest", "poc", "-q", "-rs", f"--junitxml={junit_poc}", "-p", "no:cacheprovider"],
            [], RAIZ, opcoes.modo,
        )))
        etapas.append(proteger("frontend_typecheck", lambda: etapa_typecheck(opcoes.modo)))
        if opcoes.modo == "completo":
            etapas.append(proteger("frontend_build", etapa_build))
        else:
            etapas.append(etapa_pulada("frontend_build", MOTIVO_RAPIDO))
        etapas.append(proteger("playwright", lambda: etapa_playwright(opcoes.modo, pasta)))
        etapas.append(proteger("axe", lambda: etapa_axe(opcoes.modo, pasta, etapas[-1])))
        if (RAIZ / "frontend/node_modules").is_dir():
            try:
                servidor = ServidorFrontend(pasta)
                servidor.iniciar()
            except Exception:
                if servidor:
                    servidor.parar()
                servidor = None
        etapas.append(proteger("frases_causais", lambda: etapa_frases(servidor)))
        etapas.append(proteger("simulado_como_real", lambda: etapa_simulado(postgres.url if postgres else None, servidor)))
        caged_dir = opcoes.caged_dir or os.environ.get("OIL_CAGED_DIR")
        etapas.append(proteger("caged_arquivos_reais", lambda: etapa_caged(caged_dir, postgres.url if postgres else None)))
        etapas.append(proteger("limites_seguranca", lambda: etapa_limites(git_info)))
        if opcoes.modo == "completo":
            etapas.append(proteger("mutacoes_backend", lambda: etapa_mutacoes("backend", opcoes.modo, postgres.url if postgres else None, git_info)))
            etapas.append(proteger("mutacoes_frontend", lambda: etapa_mutacoes("frontend", opcoes.modo, postgres.url if postgres else None, git_info)))
        else:
            etapas.append(etapa_pulada("mutacoes_backend", MOTIVO_RAPIDO))
            etapas.append(etapa_pulada("mutacoes_frontend", MOTIVO_RAPIDO))
        if opcoes.ao_vivo:
            junit_vivo = pasta / "pytest_ao_vivo.xml"
            def ao_vivo():
                etapa = etapa_pytest(
                    "testes_ao_vivo",
                    [sys.executable, "-m", "pytest", "backend/tests", "-q", "-rs", "-m", "live", f"--junitxml={junit_vivo}", "-p", "no:cacheprovider"],
                    [("RUN_LIVE_IBGE", "1"), ("OIL_TEST_MODE", "0"), ("DATABASE_URL", postgres.url or ""), ("OIL_DISPOSABLE_DATABASE", "1")],
                    RAIZ, "rapido",
                )
                etapa["bateria_completa"] = None
                return etapa

            etapas.append(proteger("testes_ao_vivo", lambda: preparar_testes_ao_vivo(True, os.environ, ao_vivo)))
        else:
            etapas.append(preparar_testes_ao_vivo(False, os.environ, lambda: None))
    except KeyboardInterrupt:
        etapas.append(nova_etapa("interrompido", "falhou", detalhes={"erro": "interrompido"}))
    finally:
        signal.signal(signal.SIGINT, sinal_int)
        signal.signal(signal.SIGTERM, sinal_term)
        limpar()
        if postgres:
            conteineres = [nome for nome in conteineres if nome != postgres.nome]
        restantes = conteineres_oil()
        limpar_artefatos()
        fim_porcelain = porcelain()
        etapas.append(avaliar_limpeza(
            conteineres=restantes or ([] if restantes == [] else ["docker-indisponivel"]),
            processos=filhos_vivos(),
            porcelain_inicio=git_info["_porcelain"],
            porcelain_fim=fim_porcelain,
            temporarios=[],
        ))
        if restantes is None:
            etapas[-1] = nova_etapa("limpeza", "falhou", comando="docker ps -a --filter name=oil-", detalhes={"problemas": ["docker indisponível para conferir contêineres"], "conteineres": []})
        git_publico = {chave: valor for chave, valor in git_info.items() if not chave.startswith("_")}
        git_publico["arvore_limpa_fim"] = fim_porcelain == ""
        relatorio = montar_relatorio(etapas, modo=opcoes.modo, rede_ao_vivo=opcoes.ao_vivo, git=git_publico, inicio=iso(inicio), fim=iso(agora()))
        validar_formato(relatorio)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(destino)
    return relatorio["resumo"]["codigo_saida"]


def analisar(argv):
    parser = argparse.ArgumentParser(prog=NOME_SCRIPT, description="Verificação local do OIL. Exige exatamente um modo.")
    parser.add_argument("--rapido", action="store_true")
    parser.add_argument("--completo", action="store_true")
    parser.add_argument("--ao-vivo", action="store_true")
    parser.add_argument("--saida")
    parser.add_argument("--caged-dir")
    parser.add_argument("--saida-no-repo", action="store_true")
    args, desconhecidos = parser.parse_known_args(argv)
    if desconhecidos:
        raise ErroUso("argumento desconhecido: " + " ".join(desconhecidos))
    if args.rapido == args.completo:
        raise ErroUso("informe exatamente um modo: --rapido ou --completo")
    return argparse.Namespace(
        modo="rapido" if args.rapido else "completo",
        ao_vivo=args.ao_vivo,
        saida=args.saida,
        caged_dir=args.caged_dir,
        saida_no_repo=args.saida_no_repo,
    )


def main(argv=None):
    try:
        opcoes = analisar(sys.argv[1:] if argv is None else argv)
    except ErroUso as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        return executar(opcoes)
    except ErroUso as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(redigir(str(exc))[:400], file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
