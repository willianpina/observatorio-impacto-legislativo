from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey, Integer,
                        LargeBinary, Numeric, String, Text, UniqueConstraint, JSON)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Fonte(Base):
    __tablename__ = 'fonte'
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    link: Mapped[str | None] = mapped_column(Text)


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
    mes_referencia: Mapped[str | None] = mapped_column(String(7))
    periodo_inicio: Mapped[str | None] = mapped_column(String(6))
    periodo_fim: Mapped[str | None] = mapped_column(String(6))
    tamanho_bytes: Mapped[int | None] = mapped_column(Integer)
    manifesto_json: Mapped[dict | None] = mapped_column(JSON)


class Serie(Base):
    __tablename__ = 'serie'
    __table_args__ = (
        CheckConstraint("tipo_periodo IN ('mensal', 'trimestral', 'trimestre_movel')", name='ck_serie_periodo'),
        CheckConstraint("tipo_valor IN ('real', 'nominal')", name='ck_serie_tipo_valor'),
        CheckConstraint("medida IN ('taxa', 'saldo', 'valor')", name='ck_serie_medida'),
        CheckConstraint("medida <> 'taxa' OR tipo_valor IS NULL", name='ck_serie_taxa_tipo_valor'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    fonte_id: Mapped[int] = mapped_column(ForeignKey('fonte.id'))
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    nome: Mapped[str] = mapped_column(Text)
    tabela: Mapped[str | None] = mapped_column(String(20))
    variavel: Mapped[str | None] = mapped_column(String(20))
    variavel_cv: Mapped[str | None] = mapped_column(String(20))
    variavel_variacao: Mapped[str | None] = mapped_column(String(20))
    variavel_diferenca: Mapped[str | None] = mapped_column(String(20))
    unidade: Mapped[str] = mapped_column(String(30))
    unidade_variacao: Mapped[str] = mapped_column(String(30))
    medida: Mapped[str] = mapped_column(String(20))
    tipo_periodo: Mapped[str] = mapped_column(String(30))
    tipo_valor: Mapped[str | None] = mapped_column(String(20))
    base_precos: Mapped[str | None] = mapped_column(String(7))
    disponivel: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    motivo: Mapped[str | None] = mapped_column(Text)


class Observacao(Base):
    __tablename__ = 'observacao'
    __table_args__ = (
        UniqueConstraint('serie_id', 'periodo', 'versao', name='uq_observacao_versao'),
        CheckConstraint('versao > 0', name='ck_observacao_versao'),
        CheckConstraint('cv IS NULL OR cv >= 0', name='ck_observacao_cv'),
        CheckConstraint("classificacao IS NULL OR classificacao IN ('subiu','caiu','estavel')", name='ck_observacao_classificacao'),
        CheckConstraint("classificacao_origem IS NULL OR classificacao_origem = 'calculada'", name='ck_observacao_origem'),
        CheckConstraint("variacao_anual_origem IS NULL OR variacao_anual_origem = 'calculo_observatorio'", name='ck_observacao_variacao_origem'),
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
    classificacao_origem: Mapped[str | None] = mapped_column(String(20))
    variacao_anual_origem: Mapped[str | None] = mapped_column(String(30))
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


class Proposicao(Base):
    __tablename__ = 'proposicao'
    id: Mapped[int] = mapped_column(primary_key=True)
    id_camara: Mapped[int] = mapped_column(unique=True)
    id_senado: Mapped[int] = mapped_column()
    sigla_tipo: Mapped[str | None] = mapped_column(String(20))
    numero: Mapped[int | None] = mapped_column()
    ano: Mapped[int | None] = mapped_column()


class ProposicaoSnapshot(Base):
    __tablename__ = 'proposicao_snapshot'
    __table_args__ = (UniqueConstraint('proposicao_id','casa','versao',name='uq_proposicao_snapshot_versao'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    proposicao_id: Mapped[int] = mapped_column(ForeignKey('proposicao.id'))
    casa: Mapped[str] = mapped_column(String(10))
    coleta_id: Mapped[int] = mapped_column(ForeignKey('coleta.id'))
    ementa: Mapped[str | None] = mapped_column(Text)
    autor_json: Mapped[dict] = mapped_column(JSON)
    situacao_texto: Mapped[str] = mapped_column(Text)
    situacao_data: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    norma_json: Mapped[dict | None] = mapped_column(JSON)
    link: Mapped[str] = mapped_column(Text)
    versao: Mapped[int] = mapped_column()


class Marco(Base):
    __tablename__ = 'marco'
    __table_args__ = (UniqueConstraint('proposicao_id','tipo','simulada',name='uq_marco_tipo'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    proposicao_id: Mapped[int] = mapped_column(ForeignKey('proposicao.id'))
    tipo: Mapped[str] = mapped_column(String(40))
    rotulo: Mapped[str] = mapped_column(Text)
    data: Mapped[str] = mapped_column(String(10))
    prevista: Mapped[bool] = mapped_column(Boolean)
    coleta_id: Mapped[int] = mapped_column(ForeignKey('coleta.id'))
    fonte: Mapped[str] = mapped_column(Text)
    link: Mapped[str] = mapped_column(Text)
    origem: Mapped[str] = mapped_column(String(20))
    artigo: Mapped[str | None] = mapped_column(Text)
    simulada: Mapped[bool] = mapped_column(Boolean)


class CagedArquivo(Base):
    __tablename__ = 'caged_arquivo'
    id: Mapped[int] = mapped_column(primary_key=True)
    competencia: Mapped[str] = mapped_column(String(7),unique=True)
    arquivo: Mapped[str] = mapped_column(Text)
    drive_file_id: Mapped[str] = mapped_column(Text)
    url_download: Mapped[str] = mapped_column(Text)
    pagina_oficial: Mapped[str] = mapped_column(Text)
    publicado_em: Mapped[str | None] = mapped_column(String(10))
    sha256: Mapped[str] = mapped_column(String(64))
    coleta_id: Mapped[int] = mapped_column(ForeignKey('coleta.id'))
