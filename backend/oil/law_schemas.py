"""Contrato público legislativo v1.4, com texto literal e disponibilidade por casa."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Situation(Strict):
    casa: Literal['camara','senado']
    situacao: str
    data: str | None
    link: str
    fonte: str
    coleta_id: int | None
    coletado_em: datetime | None
    disponivel: bool
    motivo: str | None


class CurrentSituation(Situation):
    regra: Literal['mais_recente','unica_disponivel']
    divergencia: bool


class GeneratedNorm(Strict):
    rotulo: str
    data: str
    link: str
    fonte: str


class Reference(Strict):
    rotulo: str
    link: str
    coletado_em: datetime


class Marker(Strict):
    tipo: str
    rotulo: str
    data: str
    prevista: bool
    fonte: str
    link: str
    origem: Literal['fonte','calculado']
    artigo: str | None


class LawResponse(Strict):
    id_camara: int
    id_senado: int
    sigla_tipo: str | None
    numero: int | None
    ano: int | None
    ementa: str | None
    autor: str | None
    partido: str | None
    uf: str | None
    coautores: int | None
    partido_referencia: Literal['atual','apresentacao'] | None
    autoria_motivo: str | None
    data_apresentacao: str | None
    situacao: list[Situation]
    situacao_atual: CurrentSituation
    norma_gerada: GeneratedNorm | None
    norma_gerada_motivo: str | None
    marcos: list[Marker]
    fontes_norma: list[Reference]
    nivel_evidencia: Literal['descritivo']='descritivo'
    desatualizado: bool
    simulada: bool
    fonte: str
    coleta_id: int
    coletado_em: datetime
