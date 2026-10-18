"""Proposição, snapshots e marcos com linhagem por coleta."""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = depends_on = None


def upgrade():
    op.create_table('proposicao',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('id_camara',sa.Integer(),nullable=False,unique=True),
        sa.Column('id_senado',sa.Integer(),nullable=False),sa.Column('sigla_tipo',sa.String(20)),
        sa.Column('numero',sa.Integer()),sa.Column('ano',sa.Integer()))
    op.create_table('proposicao_snapshot',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('proposicao_id',sa.Integer(),sa.ForeignKey('proposicao.id'),nullable=False),
        sa.Column('casa',sa.String(10),nullable=False),
        sa.Column('coleta_id',sa.Integer(),sa.ForeignKey('coleta.id'),nullable=False),
        sa.Column('ementa',sa.Text()),sa.Column('autor_json',sa.JSON(),nullable=False),
        sa.Column('situacao_texto',sa.Text(),nullable=False),
        sa.Column('situacao_data',sa.DateTime(timezone=True),nullable=False),
        sa.Column('norma_json',sa.JSON()),sa.Column('link',sa.Text(),nullable=False),
        sa.Column('versao',sa.Integer(),nullable=False),
        sa.UniqueConstraint('proposicao_id','casa','versao',name='uq_proposicao_snapshot_versao'))
    op.create_table('marco',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('proposicao_id',sa.Integer(),sa.ForeignKey('proposicao.id'),nullable=False),
        sa.Column('tipo',sa.String(40),nullable=False),sa.Column('rotulo',sa.Text(),nullable=False),
        sa.Column('data',sa.String(10),nullable=False),sa.Column('prevista',sa.Boolean(),nullable=False),
        sa.Column('coleta_id',sa.Integer(),sa.ForeignKey('coleta.id'),nullable=False),
        sa.Column('fonte',sa.Text(),nullable=False),sa.Column('link',sa.Text(),nullable=False),
        sa.Column('origem',sa.String(20),nullable=False),sa.Column('artigo',sa.Text()),
        sa.Column('simulada',sa.Boolean(),nullable=False),
        sa.UniqueConstraint('proposicao_id','tipo','simulada',name='uq_marco_tipo'))
    op.execute("INSERT INTO fonte(codigo,nome,link) VALUES ('camara-dados-abertos','Câmara dos Deputados','https://dadosabertos.camara.leg.br/'),('senado-dados-abertos','Senado Federal','https://legis.senado.leg.br/dadosabertos/')")


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT EXISTS(SELECT 1 FROM proposicao_snapshot)')):
        raise RuntimeError('Downgrade indisponível: existem snapshots legislativos.')
    op.drop_table('marco')
    op.drop_table('proposicao_snapshot')
    op.drop_table('proposicao')
    op.execute("DELETE FROM fonte WHERE codigo IN ('camara-dados-abertos','senado-dados-abertos') AND id NOT IN (SELECT fonte_id FROM coleta)")
