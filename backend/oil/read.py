from datetime import datetime, timezone

from sqlalchemy import select

from .catalog import SPECS
from .models import Coleta, Divulgacao, Observacao, Serie
from .ingest import SourceFailure
from .schemas import IndexResponse, SeriesResponse


def window_start(latest, janela):
    # Janela de meses terminando na última observação da fonte, não uma agregação.
    if janela == 'desde_2020':
        return '202001'
    months = 24 if janela == '2a' else 60
    index = int(latest[:4])*12 + int(latest[4:])-1 - months+1
    year, month = divmod(index, 12)
    return f'{year:04d}{month+1:02d}'


def read_series(session, codigo, janela, *, test_mode=False, now=None):
    spec = SPECS[codigo]
    now = now or datetime.now(timezone.utc)
    serie = session.scalar(select(Serie).where(Serie.codigo == codigo))
    good = session.scalar(select(Coleta).where(Coleta.serie_codigo == codigo,
        Coleta.simulada == test_mode, Coleta.valida.is_(True)).order_by(Coleta.id.desc()).limit(1))
    failed = session.scalar(select(Coleta).where(Coleta.serie_codigo == codigo,
        Coleta.simulada == test_mode, Coleta.erro.is_not(None)).order_by(Coleta.id.desc()).limit(1))
    if good is None and failed is not None:
        status = 504 if failed.erro == 'timeout_fonte' else 503 if (
            failed.erro == 'erro_conexao' or failed.codigo_http in {429,500,502,503,504}) else 502
        raise SourceFailure(failed.erro, status, failed.id)
    stale = good is not None and failed is not None and failed.id > good.id
    records = []
    if serie and good:
        records = session.execute(select(Observacao, Coleta).join(Coleta, Observacao.coleta_id == Coleta.id)
            .where(Observacao.serie_id == serie.id, Coleta.simulada == test_mode,
                   Coleta.valida.is_(True)).order_by(Observacao.periodo, Observacao.versao)).all()
    latest = {o.periodo: (o,c) for o,c in records}
    # Calendário conferido manualmente. Sem cadastro, nunca estima atraso por idade.
    delayed = False
    if serie:
        due = session.scalars(select(Divulgacao).where(Divulgacao.serie_id == serie.id,
                                                     Divulgacao.prevista_em < now)).all()
        delayed = any(item.periodo not in latest for item in due)
    common = dict(tipo_valor=spec.tipo_valor, medida=spec.medida, unidade=spec.unidade,
        fonte='IBGE / PNAD Contínua / SIDRA', tabela_ou_arquivo=spec.tabela,
        link=f'https://sidra.ibge.gov.br/tabela/{spec.tabela}',
        desatualizado=stale, atrasado_calendario=delayed,
        variacao_anual_unidade=spec.unidade_variacao, simulada=test_mode,
        variaveis={'valor': spec.variavel, 'cv': spec.cv,
                   'variacao_anual': spec.variacao, 'diferenca_anual': spec.diferenca})
    points = []
    if latest:
        start = window_start(max(latest), janela)
        for period, (obs, collection) in sorted(latest.items()):
            if period < start:
                continue
            points.append(dict(**common, periodo=period, valor=obs.valor, cv=obs.cv,
                lacuna=obs.valor is None, variacao_anual=obs.variacao_anual,
                classificacao=obs.classificacao, coleta_id=collection.id,
                coletado_em=collection.coletado_em, versao=obs.versao,
                disponivel=True, motivo=None))
    last = points[-1] if points else None
    return SeriesResponse(**common, codigo=codigo, nome=spec.nome, janela=janela, pontos=points,
        periodo=last['periodo'] if last else None, valor=last['valor'] if last else None,
        lacuna=last['lacuna'] if last else True, cv=last['cv'] if last else None,
        variacao_anual=last['variacao_anual'] if last else None,
        classificacao=last['classificacao'] if last else None,
        coleta_id=good.id if good else None, coletado_em=good.coletado_em if good else None,
        disponivel=bool(points), motivo=None if points else 'Nenhuma coleta válida disponível para esta janela.')


def read_index(session, janela, **kwargs):
    indicators = [read_series(session, code, janela, **kwargs) for code in SPECS]
    times = [x.coletado_em for x in indicators if x.coletado_em is not None]
    return IndexResponse(fonte='IBGE / PNAD Contínua / SIDRA',
        coletado_em=max(times) if times else None,
        atrasado_calendario=any(x.atrasado_calendario for x in indicators),
        desatualizado=any(x.desatualizado for x in indicators), indicadores=indicators)
