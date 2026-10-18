"""Arquivos mensais do Caged, revisões e saldo negativo restrito."""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = depends_on = None


def upgrade():
    op.drop_constraint('ck_observacao_valor','observacao',type_='check')
    op.execute("""CREATE FUNCTION oil_validar_saldo() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.valor < 0 AND NOT EXISTS (SELECT 1 FROM serie WHERE id=NEW.serie_id AND medida='saldo') THEN
        RAISE EXCEPTION 'Valor negativo permitido somente para saldo' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute('CREATE TRIGGER validar_saldo BEFORE INSERT OR UPDATE ON observacao FOR EACH ROW EXECUTE FUNCTION oil_validar_saldo()')
    op.drop_constraint('ck_observacao_origem','observacao',type_='check')
    op.alter_column('observacao','classificacao_origem',existing_type=sa.String(20),nullable=True)
    op.create_check_constraint('ck_observacao_origem','observacao',"classificacao_origem IS NULL OR classificacao_origem = 'calculada'")
    op.add_column('observacao',sa.Column('variacao_anual_origem',sa.String(30)))
    op.create_check_constraint('ck_observacao_variacao_origem','observacao',"variacao_anual_origem IS NULL OR variacao_anual_origem = 'calculo_observatorio'")
    for name,length in [('mes_referencia',7),('periodo_inicio',6),('periodo_fim',6)]:
        op.add_column('coleta',sa.Column(name,sa.String(length)))
    op.add_column('coleta',sa.Column('tamanho_bytes',sa.Integer()))
    op.add_column('coleta',sa.Column('manifesto_json',sa.JSON()))
    op.create_table('caged_arquivo',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('competencia',sa.String(7),unique=True,nullable=False),
        *[sa.Column(name,sa.Text(),nullable=False) for name in ('arquivo','drive_file_id','url_download','pagina_oficial')],
        sa.Column('publicado_em',sa.String(10)),sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('coleta_id',sa.Integer(),sa.ForeignKey('coleta.id'),nullable=False))
    op.execute("UPDATE serie SET tipo_valor=NULL, unidade='postos de trabalho', unidade_variacao='postos de trabalho' WHERE codigo='caged-saldo'")


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT EXISTS(SELECT 1 FROM observacao o JOIN serie s ON s.id=o.serie_id WHERE s.codigo='caged-saldo')")):
        raise RuntimeError('Downgrade indisponível: existem observações do Caged.')
    op.drop_table('caged_arquivo')
    for name in ('mes_referencia','periodo_inicio','periodo_fim','tamanho_bytes','manifesto_json'):
        op.drop_column('coleta',name)
    op.drop_constraint('ck_observacao_variacao_origem','observacao',type_='check')
    op.drop_column('observacao','variacao_anual_origem')
    op.drop_constraint('ck_observacao_origem','observacao',type_='check')
    op.execute("UPDATE observacao SET classificacao_origem='calculada' WHERE classificacao_origem IS NULL")
    op.alter_column('observacao','classificacao_origem',existing_type=sa.String(20),nullable=False)
    op.create_check_constraint('ck_observacao_origem','observacao',"classificacao_origem = 'calculada'")
    op.execute('DROP TRIGGER validar_saldo ON observacao')
    op.execute('DROP FUNCTION oil_validar_saldo()')
    op.create_check_constraint('ck_observacao_valor','observacao','valor IS NULL OR valor >= 0')
    op.execute("UPDATE serie SET tipo_valor='nominal',unidade='vínculos',unidade_variacao='vínculos' WHERE codigo='caged-saldo'")
