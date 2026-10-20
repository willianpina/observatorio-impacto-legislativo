"""Suíte do verificador com executores falsos: sem pytest real, Docker, navegador ou rede."""
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("oil_check", RAIZ / "scripts" / "check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

CAGED = (RAIZ / "backend/oil/caged.py").read_text(encoding="utf-8")
INGEST = (RAIZ / "backend/oil/ingest.py").read_text(encoding="utf-8")
SEGREDO = "SenhaUnicaOILCheck947e"
URL = f"postgresql+psycopg://oil_test:{SEGREDO}@127.0.0.1:59999/oil_check"


def git_falso():
    return {
        "head_sha": "a" * 40,
        "base_ref": "main",
        "base_sha": "b" * 40,
        "arvore_limpa_inicio": True,
        "arvore_limpa_fim": True,
    }


def relatorio(etapas, modo="completo", rede=False):
    momento = check.iso(check.agora())
    return check.montar_relatorio(
        etapas, modo=modo, rede_ao_vivo=rede, git=git_falso(), inicio=momento, fim=momento,
    )


def serie(inicio, quantidade, **valores):
    ano, mes = int(inicio[:4]), int(inicio[4:])
    pontos = {}
    for _ in range(quantidade):
        pontos[f"{ano:04d}{mes:02d}"] = 0
        mes += 1
        if mes == 13:
            mes, ano = 1, ano + 1
    pontos.update(valores)
    return pontos


def test_etapa_falha_sai_com_codigo_diferente_de_zero():
    etapas = [
        check.nova_etapa("ambiente", "ok"),
        check.nova_etapa("pytest_backend", "falhou", detalhes={"erro": "falha"}),
    ]
    assert check.codigo_saida(etapas) == 1
    corpo = relatorio(etapas)
    assert corpo["resumo"]["codigo_saida"] != 0
    assert corpo["resumo"]["status_geral"] == "falhou"
    assert corpo["resumo"]["etapas_falhas"] == ["pytest_backend"]


def test_pulado_nunca_vira_ok():
    etapas = [
        check.nova_etapa("caged_arquivos_reais", "pulado", motivo_pulo="arquivo ausente: 3-tabelas_Julho de 2026.xlsx"),
        check.nova_etapa("testes_ao_vivo", "pulado", motivo_pulo=check.MOTIVO_REDE),
    ]
    corpo = relatorio(etapas)
    assert corpo["resumo"]["ok"] == 0
    assert corpo["resumo"]["pulado"] == 2
    assert corpo["resumo"]["status_geral"] == "ok"
    assert corpo["resumo"]["codigo_saida"] == 0
    assert all(etapa["status"] == "pulado" for etapa in corpo["etapas"])
    assert all(etapa["status"] != "ok" for etapa in corpo["etapas"])


def test_pulado_obrigatorio_falha_no_completo():
    etapas = [
        check.nova_etapa("pytest_backend", "pulado", motivo_pulo="qualquer"),
        check.nova_etapa("frontend_build", "pulado", motivo_pulo=check.MOTIVO_RAPIDO),
        check.nova_etapa("limpeza", "pulado", motivo_pulo=None),
    ]
    corpo = relatorio(etapas, modo="completo")
    assert all(etapa["status"] == "falhou" for etapa in corpo["etapas"])
    assert corpo["resumo"]["codigo_saida"] == 1
    assert corpo["resumo"]["ok"] == 0
    assert "pytest_backend" in corpo["resumo"]["etapas_falhas"]
    rapido = relatorio([
        check.nova_etapa("frontend_build", "pulado", motivo_pulo=check.MOTIVO_RAPIDO),
    ], modo="rapido")
    assert rapido["etapas"][0]["status"] == "pulado"
    assert rapido["etapas"][0]["motivo_pulo"] == "modo rápido"


def test_deselected_marca_bateria_incompleta():
    comando = "python -m pytest backend/tests -q"
    rapido = check.classificar_testes("48 passed, 218 deselected", 0, "rapido", comando)
    assert rapido["contagens"]["deselected"] == 218
    assert rapido["bateria_completa"] is False
    assert rapido["status"] == "ok"
    completo = check.classificar_testes("48 passed, 218 deselected", 0, "completo", comando)
    assert completo["bateria_completa"] is False
    assert completo["status"] == "falhou"
    corpo = relatorio([rapido], modo="rapido")
    assert corpo["resumo"]["bateria_completa"] is False


def test_filtro_k_recusado_no_completo():
    with pytest.raises(check.ErroUso) as erro:
        check.recusar_filtro_no_completo("completo", "python -m pytest backend/tests -q -k caged")
    assert erro.value.codigo == 2
    check.recusar_filtro_no_completo("rapido", "python -m pytest backend/tests -q -k caged")
    assert check.comando_tem_filtro("python -m pytest backend/tests -q -rs") is False


def test_failed_com_exit_zero_ainda_falha():
    etapa = check.classificar_testes("1 failed, 9 passed", 0, "rapido", "python -m pytest backend/tests -q")
    assert etapa["status"] == "falhou"
    assert etapa["contagens"]["failed"] == 1


def test_contagem_ilegivel_falha():
    etapa = check.classificar_testes("pytest terminou sem resumo", 0, "completo", "python -m pytest backend/tests -q")
    assert etapa["status"] == "falhou"
    assert etapa["detalhes"]["erro"] == "contagem ilegível"
    assert etapa["contagens"] is None


def test_zero_testes_falha():
    etapa = check.classificar_testes("0 passed", 0, "rapido", "python -m pytest poc -q")
    assert etapa["status"] == "falhou"
    assert etapa["detalhes"]["erro"] == "nenhum teste executado"


@pytest.mark.parametrize("antigo,novo,item", [
    ("MAX_BYTES=100*1024*1024", "MAX_BYTES=200*1024*1024", "MAX_BYTES"),
    ("follow_redirects=False", "follow_redirects=True", "follow_redirects"),
    ("connect=5", "connect=60", "connect"),
    ("min(read,300)", "min(read,600)", "read_teto"),
    ("MAX_COMPRESSION_RATIO=100", "MAX_COMPRESSION_RATIO=1000", "MAX_COMPRESSION_RATIO"),
], ids=["MAX_BYTES", "follow_redirects", "connect", "read_teto", "MAX_COMPRESSION_RATIO"])
def test_limite_alterado_detectado(antigo, novo, item):
    assert CAGED.count(antigo) == 1
    base = check.extrair_limites(CAGED, INGEST)
    alterado = check.extrair_limites(CAGED.replace(antigo, novo, 1), INGEST)
    assert item in check.diferencas_limites(base, alterado)


def test_limite_identico_ok():
    base = check.extrair_limites(CAGED, INGEST)
    assert check.itens_ausentes(base) == []
    assert check.diferencas_limites(base, dict(base)) == []
    assert base["MAX_BYTES"] == 100 * 1024 * 1024
    assert base["MAX_EXPANDED_BYTES"] == 512 * 1024 * 1024
    assert base["MAX_DATA_ROWS"] == 1000
    assert base["follow_redirects"] is False
    assert base["follow_redirects_cliente"] is False
    assert base["connect"] == 5
    assert base["read_padrao"] == 120
    assert base["read_teto"] == 300
    assert base["write"] == 10
    assert base["pool"] == 10
    assert base["titulo_prefixo"] == "TABELA 5.1"
    assert base["titulo_contem"] == "COM AJUSTES"
    assert base["timeout_comum_total"] == 20
    assert base["timeout_comum_connect"] == 5


def test_caged_ausente_pulado_nunca_ok():
    bruto = check.classificar_caged_arquivos([
        {"competencia": "2026-07", "arquivo": "3-tabelas_Julho de 2026.xlsx", "presente": False},
        {"competencia": "2026-08", "arquivo": "3-tabelas_Agosto de 2026.xlsx", "presente": False},
    ])
    assert bruto["status"] == "pulado"
    assert bruto["status"] != "ok"
    assert "3-tabelas_Julho de 2026.xlsx" in bruto["motivo_pulo"]
    assert "3-tabelas_Agosto de 2026.xlsx" in bruto["motivo_pulo"]
    corpo = relatorio([check.nova_etapa("caged_arquivos_reais", bruto["status"], motivo_pulo=bruto["motivo_pulo"], detalhes=bruto["detalhes"])])
    assert corpo["resumo"]["ok"] == 0
    assert corpo["resumo"]["codigo_saida"] == 0
    assert "caged_arquivos_reais" in corpo["resumo"]["etapas_puladas"]


def test_caged_sha_divergente_falha():
    bruto = check.classificar_caged_arquivos([
        {
            "competencia": "2026-07", "arquivo": "3-tabelas_Julho de 2026.xlsx", "presente": True,
            "sha_encontrado": "abc123", "sha_esperado": check.CAGED_ESPERADO["2026-07"]["sha256"],
        },
        {
            "competencia": "2026-08", "arquivo": "3-tabelas_Agosto de 2026.xlsx", "presente": True,
            "sha_encontrado": check.CAGED_ESPERADO["2026-08"]["sha256"],
            "sha_esperado": check.CAGED_ESPERADO["2026-08"]["sha256"],
        },
    ])
    assert bruto["status"] == "falhou"
    assert bruto["status"] != "ok"
    assert "abc123" in bruto["detalhes"]["sha_encontrado"]


def test_caged_valores():
    assert check.CAGED_ESPERADO["2026-07"]["sha256"] == "367b66f4af878d0c1ab5b9fc881f228976e74a2240cb5d3afdc83aef78cabe01"
    assert check.CAGED_ESPERADO["2026-07"]["meses"] == 79
    assert check.CAGED_ESPERADO["2026-08"]["sha256"] == "d36c8ebe54e3e10ea877f5ea4dd6798a0a276c4fcff262c73102f4b9c8459e7d"
    assert check.CAGED_ESPERADO["2026-08"]["valores"]["202608"] == 165827
    assert check.CAGED_ESPERADO["2026-08"]["valores"]["202607"] == 55915
    assert check.CAGED_ESPERADO["2026-08"]["valores"]["202512"] == -635078
    assert check.VERSOES_ESPERADAS["202607"] == {1: 58568, 2: 55915}
    assert check.VERSOES_ESPERADAS["202606"] == {1: 137044, 2: 136959}
    pontos = {
        "2026-07": serie("202001", 79, **{"202607": 58568, "202606": 137044}),
        "2026-08": serie("202001", 80, **{"202608": 165827, "202607": 55915, "202512": -635078, "202606": 136959}),
    }
    versoes = {"202607": [(1, 58568), (2, 55915)], "202606": [(1, 137044), (2, 136959)]}
    assert check.conferir_valores_caged(pontos, versoes)["status"] == "ok"
    ruim = dict(pontos["2026-08"])
    ruim["202608"] = 1
    assert check.conferir_valores_caged({"2026-07": pontos["2026-07"], "2026-08": ruim}, versoes)["status"] == "falhou"
    download = {comp: {"requisicoes": 1, "valida": True, "timeout": (5, 120, 10, 10)} for comp in check.CAGED_ESPERADO}
    assert check.conferir_download(download)["status"] == "ok"
    download["2026-08"] = {"requisicoes": 2, "valida": True, "timeout": (5, 120, 10, 10)}
    assert check.conferir_download(download)["status"] == "falhou"
    assert check.titulo_sem_ajustes_recusado() is True


def test_json_sem_segredos():
    etapa = check.nova_etapa(
        "pytest_backend", "ok",
        comando=f"DATABASE_URL={URL} python -m pytest backend/tests -q",
        detalhes={"log": URL, "token": "ghp_abcdefghijklmnopqrstuvwxyz123456"},
        contagens={"passed": 1, "failed": 0, "skipped": 0, "deselected": 0, "errors": 0},
        bateria_completa=True,
    )
    texto = json.dumps(relatorio([etapa]), ensure_ascii=False)
    assert SEGREDO not in texto
    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in texto
    assert "<omitido>" in texto
    assert "oil_test:" + SEGREDO not in texto


def test_json_fora_do_git(tmp_path):
    momento = check.agora()
    with pytest.raises(check.ErroUso) as erro:
        check.resolver_saida(RAIZ / "scripts" / "relatorio.json", no_repo=False, raiz=RAIZ, modo="rapido", head="abc123def456", momento=momento)
    assert erro.value.codigo == 2
    with pytest.raises(check.ErroUso):
        check.resolver_saida(RAIZ / "scripts" / "relatorio.json", no_repo=True, raiz=RAIZ, modo="rapido", head="abc123def456", momento=momento)
    permitido = check.resolver_saida(RAIZ / "frontend" / ".next" / "relatorio.json", no_repo=True, raiz=RAIZ, modo="rapido", head="abc123def456", momento=momento)
    assert permitido.name == "relatorio.json"
    destino = check.resolver_saida(None, no_repo=False, raiz=RAIZ, modo="rapido", head="abc123def4567890", momento=momento, cache_dir=tmp_path)
    assert not check._dentro(destino, RAIZ)
    assert destino.name.startswith(momento.strftime("%Y%m%d") + "_abc123def456_rapido")


def test_json_formato():
    etapa = check.nova_etapa(
        "ambiente", "ok", comando="git rev-parse HEAD",
        contagens=None, bateria_completa=None, duracao_s=0.1, detalhes={"python": "3"},
    )
    corpo = relatorio([etapa, check.nova_etapa("testes_ao_vivo", "pulado", motivo_pulo=check.MOTIVO_REDE)])
    check.validar_formato(corpo)
    assert corpo["versao_formato"] == "1"
    assert corpo["script"]["nome"] == "scripts/check.py"
    assert corpo["script"]["versao"] == "0.1.0"
    assert corpo["fuso"] == "America/Sao_Paulo"
    assert corpo["inicio"].endswith("-03:00") or corpo["inicio"].endswith("-02:00")
    assert corpo["rede_ao_vivo"] is False
    assert corpo["etapas"][1]["motivo_pulo"] == check.MOTIVO_REDE
    assert corpo["etapas"][0]["motivo_pulo"] is None


def test_mutacao_revertida_conferida():
    item = check.concluir_mutacao(
        identificador="B-REDIR", arquivo="backend/oil/caged.py", ocorrencias=1,
        sha_antes="aaa", sha_depois="bbb",
        contagens={"passed": 1, "failed": 1, "skipped": 0, "deselected": 0, "errors": 0},
        testes_falhos=["backend/tests/test_caged_timeout.py::test_redirect"],
        toleradas=[],
    )
    assert item["status"] == "falhou"
    assert item["parar"] is True
    assert item["sha_blob_antes"] == "aaa"
    assert item["sha_blob_depois_reversao"] == "bbb"
    assert item["testes_falhos"] == ["backend/tests/test_caged_timeout.py::test_redirect"]


def test_mutacao_sobrevivente_falha():
    item = check.concluir_mutacao(
        identificador="B-TEMP", arquivo="backend/oil/caged.py", ocorrencias=1,
        sha_antes="aaa", sha_depois="aaa",
        contagens={"passed": 10, "failed": 0, "skipped": 0, "deselected": 0, "errors": 0},
        testes_falhos=[], toleradas=[],
    )
    assert item["detectada"] is False
    assert item["status"] == "falhou"
    assert item["parar"] is False
    tolerada = check.concluir_mutacao(
        identificador="B-TEMP", arquivo="backend/oil/caged.py", ocorrencias=1,
        sha_antes="aaa", sha_depois="aaa",
        contagens={"passed": 10, "failed": 0, "skipped": 0, "deselected": 0, "errors": 0},
        testes_falhos=[], toleradas=[{"id": "B-TEMP", "motivo": "motivo escrito pelo Willian"}],
    )
    assert tolerada["status"] == "ok"
    assert tolerada["detectada"] is False


def test_sem_rede_sem_flag():
    chamadas = []
    etapa = check.preparar_testes_ao_vivo(False, {"RUN_LIVE_IBGE": "1"}, lambda: chamadas.append("rede"))
    assert etapa["status"] == "pulado"
    assert etapa["motivo_pulo"] == "rede não autorizada (--ao-vivo ausente)"
    assert chamadas == []
    corpo = relatorio([etapa], rede=False)
    assert corpo["rede_ao_vivo"] is False
    assert "sidra.ibge.gov.br" not in json.dumps(corpo)


def test_limpeza_detecta_conteiner_restante():
    etapa = check.avaliar_limpeza(
        conteineres=["oil-check-abc"], processos=[], porcelain_inicio="", porcelain_fim="", temporarios=[],
    )
    assert etapa["status"] == "falhou"
    assert etapa["nome"] == "limpeza"
    assert "oil-check-abc" in etapa["detalhes"]["conteineres"]
    limpo = check.avaliar_limpeza(conteineres=[], processos=[], porcelain_inicio=" M arquivo\n", porcelain_fim=" M arquivo\n", temporarios=[])
    assert limpo["status"] == "ok"


def test_trecho_ausente_pulo_e_falha_a_etapa():
    item = check.concluir_mutacao(
        identificador="B-REDIR", arquivo="backend/oil/caged.py", ocorrencias=0,
        sha_antes=None, sha_depois=None, contagens=None, testes_falhos=[], toleradas=[],
    )
    assert item["status"] == "pulado"
    assert item["motivo_pulo"] == "trecho não encontrado (n=0)"
