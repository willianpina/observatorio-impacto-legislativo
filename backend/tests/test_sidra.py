import hashlib
import json
from decimal import Decimal as D

import pytest

from backend.oil.catalog import SPECS
from backend.oil.sidra import number, parse, previous_year, validate_metadata
from .conftest import FIXTURES


@pytest.mark.parametrize('code', SPECS)
def test_recorded_response_and_yearly_difference(code):
    spec = SPECS[code]
    validate_metadata((FIXTURES/f'metadados-{spec.tabela}.json').read_bytes(), spec)
    points = parse((FIXTURES/f'sidra-{spec.tabela}.json').read_bytes(), spec)
    assert len(points) == 174
    indexed = {p.periodo: p for p in points}
    checked = 0
    for point in points:
        prev = indexed.get(previous_year(point.periodo))
        if prev and None not in (prev.valor, point.valor, point.diferenca_anual):
            # SIDRA arredonda níveis: diferença em p.p. a 1 casa ou R$ inteiros.
            tolerance = D('0.1') if spec.medida == 'taxa' else D('1')
            assert abs((point.valor-prev.valor)-point.diferenca_anual) <= tolerance
            checked += 1
    assert checked >= 150
    last = points[-1]
    assert last.periodo == '202608'
    assert last.valor == (D('5.3') if code == 'desocupacao' else D(3777))
    assert last.cv == (D('1.3') if code == 'desocupacao' else D('0.7'))


def test_replay_provenance():
    manifest = json.loads((FIXTURES/'manifesto.json').read_bytes())
    assert manifest['simulada'] is True
    for item in manifest['respostas']:
        assert hashlib.sha256((FIXTURES/item['arquivo']).read_bytes()).hexdigest() == item['sha256']
        assert item['url'].startswith(('https://apisidra.ibge.gov.br/', 'https://servicodados.ibge.gov.br/'))


@pytest.mark.parametrize('symbol', ['...','..','-','X'])
def test_gaps(symbol):
    assert number(symbol) is None


@pytest.mark.parametrize('value', ['NaN','Infinity','Z','abc','100000000000000','0.1234567',1,None])
def test_invalid_number(value):
    with pytest.raises(ValueError):
        number(value)


@pytest.mark.parametrize('mutation', [
    lambda p: p[0].update(D3C='Trimestre (Código)'),
    lambda p: p[1].update(D1C='2'),
    lambda p: p[1].update(D2C='8819'),
    lambda p: p[1].update(MN='Reais'),
    lambda p: p[1].update(D3C='202613'),
    lambda p: p.append(p[1]),
    lambda p: p.pop(1),
])
def test_invalid_shape(mutation):
    spec = SPECS['desocupacao']
    data = json.loads((FIXTURES/'sidra-6381.json').read_bytes())
    mutation(data)
    with pytest.raises(ValueError):
        parse(json.dumps(data), spec)


def test_internal_period_gap_is_not_interpolated():
    spec = SPECS['desocupacao']
    data = json.loads((FIXTURES/'sidra-6381.json').read_bytes())
    data = [data[0]] + [r for r in data[1:] if r['D3C'] != '202607']
    point = next(p for p in parse(json.dumps(data), spec) if p.periodo == '202607')
    assert point.valor is point.cv is point.variacao_anual is None


def test_excluded_variables_never_requested():
    assert '8819' not in SPECS['desocupacao'].url
    assert '8841' not in SPECS['rendimento-real'].url
