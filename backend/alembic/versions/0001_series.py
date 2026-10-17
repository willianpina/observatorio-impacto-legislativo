"""Fontes, coletas, séries, versões de observações e calendário manual."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('fonte',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('codigo', sa.String(40), nullable=False, unique=True),
        sa.Column('nome', sa.String(200), nullable=False),
        sa.Column('link', sa.Text(), nullable=False))
    op.create_table('serie',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('fonte_id', sa.Integer(), sa.ForeignKey('fonte.id'), nullable=False),
        sa.Column('codigo', sa.String(50), nullable=False, unique=True),
        sa.Column('nome', sa.Text(), nullable=False),
        sa.Column('tabela', sa.String(20), nullable=False),
        sa.Column('variavel', sa.String(20), nullable=False),
        sa.Column('variavel_cv', sa.String(20), nullable=False),
        sa.Column('variavel_variacao', sa.String(20), nullable=False),
        sa.Column('variavel_diferenca', sa.String(20), nullable=False),
        sa.Column('unidade', sa.String(30), nullable=False),
        sa.Column('unidade_variacao', sa.String(30), nullable=False),
        sa.Column('medida', sa.String(20), nullable=False),
        sa.Column('tipo_periodo', sa.String(30), nullable=False),
        sa.Column('tipo_valor', sa.String(20), nullable=False),
        sa.Column('base_precos', sa.String(7)),
        sa.CheckConstraint("tipo_periodo IN ('mensal', 'trimestral', 'trimestre_movel')", name='ck_serie_periodo'),
        sa.CheckConstraint("tipo_valor IN ('real', 'nominal')", name='ck_serie_tipo_valor'),
        sa.CheckConstraint("medida IN ('taxa', 'saldo', 'valor')", name='ck_serie_medida'))
    op.create_table('coleta',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('fonte_id', sa.Integer(), sa.ForeignKey('fonte.id'), nullable=False),
        sa.Column('serie_codigo', sa.String(50), nullable=False),
        sa.Column('url_consultada', sa.Text(), nullable=False),
        sa.Column('coletado_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('codigo_http', sa.Integer()),
        sa.Column('hash_sha256', sa.String(64)),
        sa.Column('resposta_bruta', sa.LargeBinary()),
        sa.Column('simulada', sa.Boolean(), nullable=False),
        sa.Column('erro', sa.Text()),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('valida', sa.Boolean(), nullable=False),
        sa.CheckConstraint('codigo_http IS NULL OR codigo_http BETWEEN 100 AND 599', name='ck_coleta_http'),
        sa.CheckConstraint('hash_sha256 IS NULL OR length(hash_sha256) = 64', name='ck_coleta_hash'))
    op.create_index('ix_coleta_serie_codigo', 'coleta', ['serie_codigo'])
    op.create_index('ix_coleta_coletado_em', 'coleta', ['coletado_em'])
    op.create_table('observacao',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('serie_id', sa.Integer(), sa.ForeignKey('serie.id'), nullable=False),
        sa.Column('periodo', sa.String(6), nullable=False),
        sa.Column('valor', sa.Numeric(20, 6)),
        sa.Column('cv', sa.Numeric(20, 6)),
        sa.Column('variacao_anual', sa.Numeric(20, 6)),
        sa.Column('diferenca_anual', sa.Numeric(20, 6)),
        sa.Column('classificacao', sa.String(10)),
        sa.Column('classificacao_origem', sa.String(20), nullable=False),
        sa.Column('coleta_id', sa.Integer(), sa.ForeignKey('coleta.id'), nullable=False),
        sa.Column('versao', sa.Integer(), nullable=False),
        sa.UniqueConstraint('serie_id', 'periodo', 'versao', name='uq_observacao_versao'),
        sa.CheckConstraint('versao > 0', name='ck_observacao_versao'),
        sa.CheckConstraint('valor IS NULL OR valor >= 0', name='ck_observacao_valor'),
        sa.CheckConstraint('cv IS NULL OR cv >= 0', name='ck_observacao_cv'),
        sa.CheckConstraint("classificacao IS NULL OR classificacao IN ('subiu','caiu','estavel')", name='ck_observacao_classificacao'),
        sa.CheckConstraint("classificacao_origem = 'calculada'", name='ck_observacao_origem'),
        sa.CheckConstraint("periodo ~ '^[0-9]{4}(0[1-9]|1[0-2])$'", name='ck_observacao_periodo'))
    op.create_index('ix_observacao_serie_id', 'observacao', ['serie_id'])
    op.create_table('divulgacao',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('serie_id', sa.Integer(), sa.ForeignKey('serie.id'), nullable=False),
        sa.Column('periodo', sa.String(6), nullable=False),
        sa.Column('prevista_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fonte', sa.Text(), nullable=False),
        sa.Column('link', sa.Text(), nullable=False),
        sa.UniqueConstraint('serie_id', 'periodo', name='uq_divulgacao_periodo'))


def downgrade():
    op.drop_table('divulgacao')
    op.drop_index('ix_observacao_serie_id', table_name='observacao')
    op.drop_table('observacao')
    op.drop_index('ix_coleta_coletado_em', table_name='coleta')
    op.drop_index('ix_coleta_serie_codigo', table_name='coleta')
    op.drop_table('coleta')
    op.drop_table('serie')
    op.drop_table('fonte')
