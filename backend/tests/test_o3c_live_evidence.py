"""Valida somente a evidência gravada; nunca faz requisição externa."""
import hashlib,json
import pytest
from .conftest import ROOT

@pytest.mark.parametrize('job',['migracao','ibge','lei','caged-2026-07','caged-2026-08','calendario-caged'])
def test_o3c_manual_collection_evidence_is_safe_and_explicit(job):
    path=ROOT/'docs/o3/evidencias/o3c-coleta-real.json'
    assert path.exists(),'Evidência da execução manual ainda ausente.'
    data=json.loads(path.read_text(encoding='utf8'))
    record=next(item for item in data['jobs'] if item['job']==job)
    assert record['execucoes']==1
    assert record['inicio_utc'] and record['fim_utc'] and record['inicio_brt'] and record['fim_brt']
    assert record['simulada'] is False
    for collection in record['coletas']:
        assert collection['coleta_id']>0 and collection['url']
        assert collection['simulada'] is False
        assert collection['http'] is None or 100<=collection['http']<=599
        assert collection['sha256'] is None or len(collection['sha256'])==64
        assert isinstance(collection['valida'],bool)
    corpus=json.dumps(data).casefold()
    assert 'database_url' not in corpus and 'postgresql+' not in corpus
    assert 'resposta_bruta' not in corpus

def test_o3c_real_api_response_hashes_are_reproducible():
    path=ROOT/'docs/o3/evidencias/o3c-coleta-real.json'
    assert path.exists(),'Evidência da execução manual ainda ausente.'
    data=json.loads(path.read_text(encoding='utf8'))
    assert len(data['respostas'])==4
    for item in data['respostas']:
        raw=json.dumps(item['json'],ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()
        assert hashlib.sha256(raw).hexdigest()==item['sha256_json_canonico']
        assert item['json'].get('simulada') is not True
