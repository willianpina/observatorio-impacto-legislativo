"""Contrato 1.3.1: taxa sem tipo monetário e cadastro indisponível do Caged."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('fonte', 'link', existing_type=sa.Text(), nullable=True)
    for name in ('tabela','variavel','variavel_cv','variavel_variacao','variavel_diferenca','tipo_valor'):
        op.alter_column('serie', name, existing_type=sa.String(20), nullable=True)
    op.add_column('serie', sa.Column('disponivel', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('serie', sa.Column('motivo', sa.Text(), nullable=True))
    op.execute("UPDATE serie SET tipo_valor = NULL WHERE medida = 'taxa'")
    op.create_check_constraint('ck_serie_taxa_tipo_valor', 'serie', "medida <> 'taxa' OR tipo_valor IS NULL")
    op.execute("INSERT INTO fonte (codigo,nome,link) VALUES ('mte-caged','MTE / Novo Caged',NULL)")
    op.execute("""INSERT INTO serie
        (fonte_id,codigo,nome,unidade,unidade_variacao,medida,tipo_periodo,tipo_valor,disponivel,motivo)
        SELECT id,'caged-saldo','Saldo do Novo Caged — Brasil','vínculos','vínculos','saldo','mensal',
            'nominal',false,'Fonte de acesso e arquivo do Novo Caged ainda não confirmados.'
        FROM fonte WHERE codigo = 'mte-caged'""")


def downgrade():
    # A O2-R não coleta Caged. Evita apagar dados se uma fase posterior já o tiver feito.
    connection = op.get_bind()
    in_use = connection.scalar(sa.text("""SELECT EXISTS (
        SELECT 1 FROM observacao o JOIN serie s ON s.id=o.serie_id WHERE s.codigo='caged-saldo'
        UNION ALL SELECT 1 FROM coleta WHERE serie_codigo='caged-saldo'
        UNION ALL SELECT 1 FROM divulgacao d JOIN serie s ON s.id=d.serie_id WHERE s.codigo='caged-saldo'
    )"""))
    if in_use:
        raise RuntimeError('Downgrade indisponível: Caged já possui registros vinculados.')
    op.execute("DELETE FROM serie WHERE codigo='caged-saldo'")
    op.execute("DELETE FROM fonte WHERE codigo='mte-caged'")
    op.drop_constraint('ck_serie_taxa_tipo_valor','serie',type_='check')
    op.execute("UPDATE serie SET tipo_valor='nominal' WHERE tipo_valor IS NULL AND medida='taxa'")
    op.drop_column('serie','motivo')
    op.drop_column('serie','disponivel')
    for name in ('tabela','variavel','variavel_cv','variavel_variacao','variavel_diferenca','tipo_valor'):
        op.alter_column('serie', name, existing_type=sa.String(20), nullable=False)
    op.alter_column('fonte','link',existing_type=sa.Text(),nullable=False)
