"""Guarda da atribuição dos dados e da versão contratual corrigida."""
import re
import subprocess
from .conftest import ROOT

EXCLUDED=frozenset({'frontend/package-lock.json','frontend/referencias/o3/missao-o3c-codex.md'})

def license_pattern():
    return re.compile('c'+'c'+r'[\s_-]*by|by'+'-nd|sem'+'deriva|'+r'\b'+'c'+'c'+'0'+r'\b|dom[ií]nio p[uú]blico',re.I)

def test_o3c_license_guard_detects_standalone_designation_and_preserves_ids():
    pattern=license_pattern()
    for text in ['c'+'c'+'0','c'+'c BY','by'+'-nd','domínio '+'público']:
        assert pattern.search(text)
    assert not pattern.search('32a1c8da79eda1a4f21c-ce23a5bb41c41ef6fc'+'c0')

def test_o3c_no_inapplicable_license_in_versioned_text():
    result=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True)
    names=filter(None,result.stdout.decode().split('\0'))
    pattern=license_pattern()
    found=[]
    for name in names:
        if name in EXCLUDED:continue
        raw=(ROOT/name).read_bytes()
        if b'\0' in raw:continue
        try:text=raw.decode('utf-8')
        except UnicodeDecodeError:continue
        if pattern.search(text):found.append(name)
    assert not found,found

def test_o3c_api_patch_and_explicit_attribution_schema():
    from backend.oil.main import app
    schema=app.openapi()
    assert schema['info']['version']=='1.5.0'
    models=schema['components']['schemas']
    assert models['Atribuicao']['additionalProperties'] is False
    assert 'licenca' not in models['Atribuicao']['properties']
    assert 'BaseLegal' not in models
    assert (ROOT/'docs/o3/contrato-api-v1.4.1-delta.md').exists()
    assert (ROOT/'docs/o3/openapi-v1.4.1.json').exists()
    assert (ROOT/'docs/o3/contrato-api-v1.5.0-delta.md').exists()
    assert (ROOT/'docs/o3/openapi-v1.5.0.json').exists()
