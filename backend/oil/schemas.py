from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Common(BaseModel):
    model_config = ConfigDict(extra='forbid')
    valor: float | None
    lacuna: bool
    unidade: str
    periodo: str | None
    tipo_periodo: Literal['mensal', 'trimestre_movel'] = 'trimestre_movel'
    tipo_valor: Literal['real', 'nominal'] | None
    medida: Literal['taxa', 'saldo', 'valor']
    base_precos: None = None
    cv: float | None
    variacao_anual: float | None
    variacao_anual_unidade: str
    classificacao: Literal['subiu', 'caiu', 'estavel'] | None
    classificacao_origem: Literal['calculada'] = 'calculada'
    fonte: str
    tabela_ou_arquivo: str | None
    link: str | None
    coleta_id: int | None
    coletado_em: datetime | None
    desatualizado: bool
    atrasado_calendario: bool
    nivel_evidencia: Literal['descritivo'] = 'descritivo'
    disponivel: bool
    motivo: str | None
    comparacao: Literal['mesmo_periodo_ano_anterior'] = 'mesmo_periodo_ano_anterior'
    simulada: bool
    variaveis: dict[str, str]


class PointResponse(Common):
    versao: int | None


class SeriesResponse(Common):
    codigo: str
    nome: str
    janela: Literal['2a', '5a', 'desde_2020']
    pontos: list[PointResponse]


class IndexResponse(BaseModel):
    fonte: str
    coletado_em: datetime | None
    atrasado_calendario: bool
    desatualizado: bool
    indicadores: list[SeriesResponse]
