from decimal import Decimal, localcontext


def classify(valor, cv, valor_anterior, cv_anterior, diferenca):
    """Contrato v1.3: diferença na unidade do nível (p.p. ou R$), não em %."""
    values = (valor, cv, valor_anterior, cv_anterior, diferenca)
    if any(v is None for v in values):
        return None
    value, coeff, previous, previous_coeff, diff = map(Decimal, values)
    if not all(v.is_finite() for v in (value, coeff, previous, previous_coeff, diff)):
        raise ValueError('A fórmula exige valores finitos.')
    if min(value, coeff, previous, previous_coeff) < 0:
        raise ValueError('Nível e CV devem ser não negativos.')
    with localcontext() as ctx:
        ctx.prec = 40
        error = ((coeff * value / 100) ** 2 + (previous_coeff * previous / 100) ** 2).sqrt()
        if abs(diff) <= Decimal('1.96') * error:
            return 'estavel'
    return 'subiu' if diff > 0 else 'caiu'
