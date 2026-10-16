from decimal import Decimal as D

import pytest

from backend.oil.classification import classify


@pytest.mark.parametrize('current,cv,previous,previous_cv,diff,expected', [
    ('10','1','10','1','0','estavel'),
    ('10','1','9','1','1','subiu'),
    ('9','1','10','1','-1','caiu'),
    ('10','0','10','0','0','estavel'),
    ('10','0','9','0','1','subiu'),
    ('5.3','1.3','5.6','1.3','-0.3','caiu'),
    ('3777','0.7','3641','0.7','136','subiu'),
    # Fronteira exata: ep_atual=1, ep_anterior=0, margem=1.96.
    ('100','1','100','0','1.96','estavel'),
    ('100','1','100','0','1.960001','subiu'),
    ('100','1','100','0','-1.960001','caiu'),
])
def test_formula(current, cv, previous, previous_cv, diff, expected):
    assert classify(*map(D, (current,cv,previous,previous_cv,diff))) == expected


@pytest.mark.parametrize('position', range(5))
def test_missing(position):
    values = [D('10'), D('1'), D('9'), D('1'), D('1')]
    values[position] = None
    assert classify(*values) is None


def test_income_uses_reais_not_percentage():
    assert classify(D(3777), D('0.7'), D(3641), D('0.7'), D(136)) == 'subiu'
    assert classify(D(3777), D('0.7'), D(3641), D('0.7'), D('3.7')) == 'estavel'


@pytest.mark.parametrize('invalid', [D('-1'), D('NaN'), D('Infinity')])
def test_invalid_cv(invalid):
    with pytest.raises(ValueError):
        classify(D(10), invalid, D(10), D(1), D(0))
