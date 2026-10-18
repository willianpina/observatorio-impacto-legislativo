"""Regressões da rodada O3-C; transporte e banco sempre de teste."""
import importlib
import shutil
import subprocess
import sys
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from backend.oil.models import Coleta,Observacao,Serie
from .conftest import ROOT
from .test_o3_caged import ingest_caged

def test_o3c_collect_from_root_excludes_poc():
    env=__import__('os').environ.copy();env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
    def collect(args):
        result=subprocess.run([sys.executable,'-m','pytest','-c','backend/pytest.ini','--collect-only','-q',*args],cwd=ROOT,env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        return [line for line in result.stdout.splitlines() if '::' in line]
    root=collect([]);explicit=collect(['backend/tests'])
    assert not any('poc/' in line.replace('\\','/') for line in root)
    assert len(root)==len(explicit)

@pytest.mark.parametrize('missing',['docs/README.md','docs/contrato-api-v1.3-indicadores.md','docs/metodologia-o2.md','docs/o3/contrato-api-v1.4.1-delta.md'])
def test_o3c_all_required_docs_are_enforced(monkeypatch,missing):
    module=importlib.import_module('backend.tests.test_language')
    names=subprocess.check_output(['git','ls-files','-z','docs'],cwd=ROOT).decode().split('\0')
    stdout='\0'.join(name for name in names if name!=missing).encode()
    monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=stdout))
    with pytest.raises(AssertionError):module.versioned_docs()

def test_o3c_invalid_collection_observation_is_ignored(sf,client):
    ingest_caged(sf)
    with sf.begin() as session:
        good=session.scalar(select(Coleta).where(Coleta.serie_codigo=='caged-saldo',Coleta.valida.is_(True)))
        bad=Coleta(fonte_id=good.fonte_id,serie_codigo=good.serie_codigo,url_consultada='https://www.gov.br/trabalho-e-emprego/pt-br/',
            coletado_em=good.coletado_em+timedelta(seconds=1),codigo_http=200,simulada=True,tipo=good.tipo,valida=False,
            mes_referencia=good.mes_referencia,periodo_inicio=good.periodo_inicio,periodo_fim=good.periodo_fim)
        session.add(bad);session.flush()
        sid=session.scalar(select(Serie.id).where(Serie.codigo=='caged-saldo'))
        session.add(Observacao(serie_id=sid,periodo='202608',valor=999999,cv=None,variacao_anual=None,diferenca_anual=None,
            classificacao=None,classificacao_origem=None,variacao_anual_origem='calculo_observatorio',coleta_id=bad.id,versao=2))
    from backend.oil.caged import reconstruct
    with sf() as session:assert reconstruct(session,'2026-08',test_mode=True)['202608']['valor']==165827
    data=client.get('/api/v1/indicadores/caged-saldo/serie').json()
    assert data['valor']==165827
    assert all(p['valor']!=999999 for p in data['pontos'])

def test_o3c_backend_mutations_do_not_publish_by_default(tmp_path,monkeypatch):
    module=importlib.import_module('backend.scripts.check_mutations_o3')
    repo=tmp_path/'repo';(repo/'docs/o3/evidencias').mkdir(parents=True)
    monkeypatch.setattr(module,'ROOT',repo)
    monkeypatch.setattr(module,'clean',lambda root:None)
    monkeypatch.setattr(module,'MUTATIONS',[('X','probe.py','sonda sintética',lambda text:text.replace('1','2'))])
    def git(root,*args):
        if args==('rev-parse','HEAD'):return 'a'*40
        if args[:2]==('worktree','add'):
            checkout=__import__('pathlib').Path(args[3]);checkout.mkdir(parents=True);(checkout/'probe.py').write_text('x=1')
        if args[:2]==('worktree','remove'):shutil.rmtree(args[2])
        return ''
    monkeypatch.setattr(module,'git',git)
    monkeypatch.setattr(module,'run_suite',lambda *a:dict(resultado='DETECTADA' if a[-1]!='baseline' else 'SOBREVIVENTE',pytest_resumo=[],teste=[],codigo_saida=0))
    module.execute({'X'})
    assert not [p for p in repo.rglob('*') if p.is_file()]
