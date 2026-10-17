import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


MISSING = {'...', '..', '-', 'X'}


@dataclass(frozen=True)
class Point:
    periodo: str
    valor: Decimal | None
    cv: Decimal | None
    variacao_anual: Decimal | None
    diferenca_anual: Decimal | None


def validate_metadata(raw, spec):
    data = json.loads(raw)
    if (not isinstance(data, dict) or str(data.get('id')) != spec.tabela
            or data.get('periodicidade', {}).get('frequencia') != 'trimestral móvel'):
        raise ValueError('Tabela ou periodicidade inesperada.')
    variables = {str(v['id']): v for v in data['variaveis']}
    if any(variables.get(code, {}).get('unidade') != unit for code, unit in spec.units.items()):
        raise ValueError('Variáveis ou unidades inesperadas.')


def number(value):
    if not isinstance(value, str):
        raise ValueError('Valor SIDRA deve ser texto.')
    if value in MISSING:
        return None
    try:
        result = Decimal(value.replace(',', '.'))
    except InvalidOperation:
        raise ValueError('Valor SIDRA inválido.') from None
    if not result.is_finite() or abs(result) >= Decimal('1e14') or result.as_tuple().exponent < -6:
        raise ValueError('Número fora da precisão suportada.')
    return result


def parse(raw, spec):
    import re
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) < 2 or data[0].get('D3C') != 'Trimestre Móvel (Código)':
        raise ValueError('Cabeçalho SIDRA inesperado.')
    grouped = {}
    for row in data[1:]:
        if (row.get('NC'), row.get('D1C'), row.get('D1N')) != ('1', '1', 'Brasil'):
            raise ValueError('Território inesperado.')
        period, code = row['D3C'], row['D2C']
        if not re.fullmatch(r'\d{4}(0[1-9]|1[0-2])', period):
            raise ValueError('Período móvel inválido.')
        # Nos primeiros 12 períodos, a variação anual vem como "...", MC/MN vazios.
        # A unidade só pode faltar nesse caso; a definição foi validada nos metadados.
        absent_unit = row.get('MN') == '' and row.get('MC') == '' and row.get('V') in MISSING
        if code not in spec.variaveis or (row['MN'] != spec.units[code] and not absent_unit):
            raise ValueError('Variável ou unidade inesperada.')
        group = grouped.setdefault(period, {})
        if code in group:
            raise ValueError('Observação duplicada.')
        group[code] = number(row['V'])
    points = {}
    for period, variables in grouped.items():
        if not (set(spec.variaveis) - {spec.cv}) <= set(variables):
            raise ValueError('Resposta parcial: variáveis ausentes.')
        point = Point(period, variables[spec.variavel], variables.get(spec.cv),
                      variables[spec.variacao], variables[spec.diferenca])
        if any(v is not None and v < 0 for v in (point.valor, point.cv)):
            raise ValueError('Nível ou CV negativo.')
        if spec.medida == 'taxa' and point.valor is not None and point.valor > 100:
            raise ValueError('Taxa fora de 0 a 100.')
        points[period] = point
    # Períodos intermediários ausentes serão materializados como lacunas, nunca interpolados.
    start, end = min(points), max(points)
    index = int(start[:4]) * 12 + int(start[4:]) - 1
    finish = int(end[:4]) * 12 + int(end[4:]) - 1
    while index <= finish:
        year, month = divmod(index, 12)
        period = f'{year:04d}{month + 1:02d}'
        points.setdefault(period, Point(period, None, None, None, None))
        index += 1
    return [points[p] for p in sorted(points)]


def previous_year(period):
    return f'{int(period[:4]) - 1:04d}{period[4:]}'
