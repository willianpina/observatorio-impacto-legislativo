from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey, Integer,
                        LargeBinary, Numeric, String, Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Fonte(Base):
    __tablename__ = 'fonte'
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    link: Mapped[str] = mapped_column(Text)


class Coleta(Base):
    __tablename__ = 'coleta'
    __table_args__ = (
        CheckConstraint('codigo_http IS NULL OR codigo_http BETWEEN 100 AND 599', name='ck_coleta_http'),
        CheckConstraint('hash_sha256 IS NULL OR length(hash_sha256) = 64', name='ck_coleta_hash'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    fonte_id: Mapped[int] = mapped_column(ForeignKey('fonte.id'))
    serie_codigo: Mapped[str] = mapped_column(String(50), index=True)
    url_consultada: Mapped[str] = mapped_column(Text)
    coletado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    codigo_http: Mapped[int | None] = mapped_column(Integer)
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    resposta_bruta: Mapped[bytes | None] = mapped_column(LargeBinary)
    simulada: Mapped[bool] = mapped_column(Boolean, default=False)
    erro: Mapped[str | None] = mapped_column(Text)
    # Inclui metadados e tentativas falhas; só a consulta de valores pode ser válida.
    tipo: Mapped[str] = mapped_column(String(20))
    valida: Mapped[bool] = mapped_column(Boolean, default=False)


class Serie(Base):
    __tablename__ = 'serie'
    __table_args__ = (
        CheckConstraint("tipo_periodo IN ('mensal', 'trimestral', 'trimestre_movel')", name='ck_serie_periodo'),
        CheckConstraint("tipo_valor IN ('real', 'nominal')", name='ck_serie_tipo_valor'),
        CheckConstraint("medida IN ('taxa', 'saldo', 'valor')", name='ck_serie_medida'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    fonte_id: Mapped[int] = mapped_column(ForeignKey('fonte.id'))
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(Text)
    tabela: Mapped[str] = mapped_column(String(20))
    variavel: Mapped[str] = mapped_column(String(20))
    variavel_cv: Mapped[str] = mapped_column(String(20))
    variavel_variacao: Mapped[str] = mapped_column(String(20))
    variavel_diferenca: Mapped[str] = mapped_column(String(20))
    unidade: Mapped[str] = mapped_column(String(30))
    unidade_variacao: Mapped[str] = mapped_column(String(30))
    medida: Mapped[str] = mapped_column(String(20))
    tipo_periodo: Mapped[str] = mapped_column(String(30))
    tipo_valor: Mapped[str] = mapped_column(String(20))
    base_precos: Mapped[str | None] = mapped_column(String(7))


class Observacao(Base):
    __tablename__ = 'observacao'
    __table_args__ = (
        UniqueConstraint('serie_id', 'periodo', 'versao', name='uq_observacao_versao'),
        CheckConstraint('versao > 0', name='ck_observacao_versao'),
        CheckConstraint('valor IS NULL OR valor >= 0', name='ck_observacao_valor'),
        CheckConstraint('cv IS NULL OR cv >= 0', name='ck_observacao_cv'),
        CheckConstraint("classificacao IS NULL OR classificacao IN ('subiu','caiu','estavel')", name='ck_observacao_classificacao'),
        CheckConstraint("classificacao_origem = 'calculada'", name='ck_observacao_origem'),
        CheckConstraint("periodo ~ '^[0-9]{4}(0[1-9]|1[0-2])$'", name='ck_observacao_periodo'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey('serie.id'), index=True)
    periodo: Mapped[str] = mapped_column(String(6))
    valor: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    cv: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    variacao_anual: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    diferenca_anual: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    classificacao: Mapped[str | None] = mapped_column(String(10))
    classificacao_origem: Mapped[str] = mapped_column(String(20), default='calculada')
    coleta_id: Mapped[int] = mapped_column(ForeignKey('coleta.id'))
    versao: Mapped[int] = mapped_column(Integer)


class Divulgacao(Base):
    """Calendário manual: somente datas conferidas em fonte pública, sem estimativa."""
    __tablename__ = 'divulgacao'
    __table_args__ = (UniqueConstraint('serie_id', 'periodo', name='uq_divulgacao_periodo'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    serie_id: Mapped[int] = mapped_column(ForeignKey('serie.id'))
    periodo: Mapped[str] = mapped_column(String(6))
    prevista_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fonte: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(Text)
