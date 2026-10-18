"""Regressões QA O3-R, anteriores às correções."""
import asyncio
import importlib
import io
import json
import subprocess
import sys
from types import SimpleNamespace

import httpx
import openpyxl
import pytest
from sqlalchemy import func, select

from backend.oil.caged import CagedCollector
from backend.oil.ingest import SourceFailure
from backend.oil.models import Coleta, Observacao
from .conftest import ROOT,no_sleep
from .test_o3_caged import entry,ingest_caged
from .test_o3_law import ingest_law,payload


def test_marker_dates_and_labels_are_literal_source_fields(sf,client):
    ingest_law(sf);data=client.get('/api/v1/proposicoes/2233802').json();source=payload('senado')
    markers={m['tipo']:m for m in data['marcos']}
    assert (markers['aprovacao_senado']['data'],markers['aprovacao_senado']['rotulo'])==(source['deliberacao']['data'],source['deliberacao']['tipoDeliberacao'])
    assert (markers['promulgacao']['data'],markers['promulgacao']['rotulo'])==(source['dataSituacaoAtual'],source['situacaoAtual'])


@pytest.mark.parametrize('simulada,mode',[(False,'1'),(True,None)])
def test_cutout_cannot_bypass_explicit_test_mode(sf,monkeypatch,simulada,mode):
    metadata,raw=entry('2026-08')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=raw))) as client:
            collector=CagedCollector(sf,client,simulada=simulada,sleep=no_sleep)
            if mode is None:monkeypatch.delenv('OIL_TEST_MODE')
            with pytest.raises(ValueError):await collector.collect(metadata)
    asyncio.run(run())
    with sf() as session:assert session.scalar(select(func.count()).select_from(Coleta))==0


def test_adjusted_table_title_is_required(sf):
    import hashlib
    wb=openpyxl.load_workbook(io.BytesIO(entry('2026-08')[1]));ws=wb['Tabela 5.1']
    ws.cell(2,2,'TABELA 5.1 - EVOLUÇÃO SEM AJUSTES')
    stream=io.BytesIO();wb.save(stream);raw=stream.getvalue()
    with pytest.raises(SourceFailure):ingest_caged(sf,raw=raw,override={'sha256':hashlib.sha256(raw).hexdigest()})
    with sf() as session:
        assert not session.scalar(select(Coleta).order_by(Coleta.id.desc())).valida
        assert session.scalar(select(func.count()).select_from(Observacao))==0


def test_postgres_invocation_explicitly_selects_backend_tests(monkeypatch):
    script=importlib.import_module('backend.scripts.test_postgres');commands=[]
    def run(command,**kwargs):commands.append(command);return SimpleNamespace(returncode=0)
    monkeypatch.setattr(script.subprocess,'run',run)
    monkeypatch.setattr(script.subprocess,'check_output',lambda *a,**k:'127.0.0.1:55444')
    monkeypatch.setattr(script.sys,'argv',['test_postgres.py'])
    assert script.main()==0
    backend=next(c for c in commands if 'backend/pytest.ini' in c)
    assert 'backend/tests' in backend
    assert '127.0.0.1::5432' in commands[0]


def docs_function():
    module=importlib.import_module('backend.tests.test_language')
    function=getattr(module,'versioned_docs',None)
    assert callable(function),'Guarda deve usar inventário versionado com falha explícita de Git.'
    return module,function


def test_language_inventory_is_git_tracked_and_has_required_documents(tmp_path):
    _,function=docs_function()
    names={p.relative_to(ROOT).as_posix() for p in function()}
    assert {'docs/o3/VALIDACAO.md','docs/o3/spec-b2-proposicao.md','docs/o3/spec-b4-caged.md','docs/o3/contrato-api-v1.4-delta.md'}<=names


def test_language_inventory_fails_if_git_is_missing(monkeypatch):
    module,function=docs_function()
    def missing(*a,**k):raise FileNotFoundError('GIT AUSENTE SIMULADO')
    monkeypatch.setattr(module.subprocess,'run',missing)
    with pytest.raises(RuntimeError):function()


def test_language_inventory_fails_if_known_document_is_untracked(monkeypatch):
    module,function=docs_function()
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=b'docs/o3/VALIDACAO.md\0'))
    with pytest.raises(AssertionError):function()


def test_backend_mutation_catalog_is_available_without_running_docker():
    script=ROOT/'backend/scripts/check_mutations_o3.py'
    result=subprocess.run([sys.executable,str(script),'--list'],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0
    catalog=json.loads(result.stdout)
    assert {'BA1','BA2','BA3','BA4','BB','BC','BD','BD2','BE','BF','BG','BH','BI','BJ','BK','BL','BM','BN','BO','BP','BQ','BR','S1','S3','S5','S6','S7'}<={m['id'] for m in catalog}
