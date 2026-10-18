"""Gera recortes PEQUENOS da aba «Tabela 5.1» das planilhas oficiais do Novo Caged (MTE).
Só para teste. Copia sem alterar nenhum número. Colunas C (Estoque) e G (Variação Relativa)
são fórmulas no original; aqui vão como o valor já calculado e guardado no próprio arquivo
(data_only=True), porque as fórmulas apontam para linhas que não estão no recorte."""
import hashlib, json, sys, openpyxl
from openpyxl import Workbook

ORIG = sys.argv[1]   # pasta com tabelas_2026-07.xlsx e tabelas_2026-08.xlsx
OUT = sys.argv[2]
MESES = ["Junho/2025","Julho/2025","Agosto/2025","Setembro/2025","Outubro/2025","Novembro/2025",
         "Dezembro/2025","Janeiro/2026","Fevereiro/2026","Março/2026","Abril/2026","Maio/2026",
         "Junho/2026","Julho/2026","Agosto/2026"]

def recorte(src, dst):
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    ws = wb["Tabela 5.1"]
    rows = list(ws.iter_rows(min_col=1, max_col=7, values_only=True))
    wb.close()
    out = Workbook(); o = out.active; o.title = "Tabela 5.1"
    for r in range(4):                      # linhas 1-4 como no original
        for c, v in enumerate(rows[r], 1):
            if v is not None: o.cell(r+1, c, v)
    for c, v in enumerate(rows[4], 1):      # cabeçalho na linha 5
        if v is not None: o.cell(5, c, v)
    dados = [row for row in rows[5:] if row[1] in MESES]
    for i, row in enumerate(dados):
        for c, v in enumerate(row, 1):
            if v is not None: o.cell(6+i, c, v)
    rodape = [row for row in rows[5:] if isinstance(row[1], str) and (row[1].startswith("Fonte") or row[1].startswith("*"))]
    r = 6 + len(dados) + 1                  # uma linha em branco, como no original
    for row in rodape:
        o.cell(r, 2, row[1]); r += 1
    out.save(dst)
    return [(row[1], row[5]) for row in dados]

for mes, nome in (("2026-07","tabelas_2026-07"), ("2026-08","tabelas_2026-08")):
    print(nome, recorte(f"{ORIG}/{nome}.xlsx", f"{OUT}/caged_t51_{mes}_recorte.xlsx"))

# --- Pós-processamento: o openpyxl grava float com menos dígitos. Para não mudar nenhum
# número, a coluna G recebe o texto <v> exato do XML original.
import re, zipfile, shutil, os
def _sheet_path(z, nome):
    wbx = z.read("xl/workbook.xml").decode()
    rid = re.search(r'<sheet [^>]*name="%s"[^>]*r:id="([^"]+)"' % re.escape(nome), wbx).group(1)
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    alvo = re.search(r'<Relationship [^>]*Id="%s"[^>]*Target="([^"]+)"' % rid, rels) or \
           re.search(r'<Relationship [^>]*Target="([^"]+)"[^>]*Id="%s"' % rid, rels)
    t = alvo.group(1).lstrip("/")
    return t if t.startswith("xl/") else "xl/" + t

def _valores_brutos(src):
    with zipfile.ZipFile(src) as z:
        xml = z.read(_sheet_path(z, "Tabela 5.1")).decode()
    brutos = {}
    for m in re.finditer(r'<c r="G(\d+)"[^>]*>(.*?)</c>', xml, re.S):
        v = re.search(r'<v>([^<]*)</v>', m.group(2))
        if v: brutos[int(m.group(1))] = v.group(1)
    return brutos

def corrigir_g(src, dst):
    brutos = _valores_brutos(src)
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    linha_orig = {r[0].value: r[0].row for r in wb["Tabela 5.1"].iter_rows(min_row=6, min_col=2, max_col=2) if r[0].value}
    wb.close()
    with zipfile.ZipFile(dst) as z:
        itens = {n: z.read(n) for n in z.namelist()}
    xml = itens["xl/worksheets/sheet1.xml"].decode()
    fx = openpyxl.load_workbook(dst, read_only=True)["Tabela 5.1"]
    mapa = {r[0].row: linha_orig[r[0].value] for r in fx.iter_rows(min_row=6, min_col=2, max_col=2) if r[0].value in linha_orig}
    for nova, orig in mapa.items():
        xml = re.sub(r'(<c r="G%d" t="n"><v>)[^<]*(</v>)' % nova, lambda m: m.group(1) + brutos[orig] + m.group(2), xml)
    itens["xl/worksheets/sheet1.xml"] = xml.encode()
    tmp = dst + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in itens.items(): z.writestr(n, b)
    os.replace(tmp, dst)

for mes, nome in (("2026-07","tabelas_2026-07"), ("2026-08","tabelas_2026-08")):
    corrigir_g(f"{ORIG}/{nome}.xlsx", f"{OUT}/caged_t51_{mes}_recorte.xlsx")
