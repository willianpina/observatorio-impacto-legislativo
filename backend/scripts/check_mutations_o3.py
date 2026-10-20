"""Mutações locais O3-R em worktree descartável e PostgreSQL exclusivo por execução."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import stat
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
LAW='backend/oil/legislation.py'
CAGED='backend/oil/caged.py'


def replace_once(old,new):
    def transform(source):
        if old not in source:raise ValueError('Alvo da mutação ausente.')
        return source.replace(old,new,1)
    return transform


def replace_all(old,new):
    def transform(source):
        if old not in source:raise ValueError('Alvo da mutação ausente.')
        return source.replace(old,new)
    return transform


def remove_law_limit(source):
    source=replace_once("if length and (not length.isdecimal() or int(length)>MAX_RESPONSE_BYTES):","if False:")(source)
    return replace_once('if len(raw)+len(chunk)>MAX_RESPONSE_BYTES:','if False:')(source)


MUTATIONS=[
    ('BA1',LAW,'Isolamento de coletas legislativas',replace_all('Coleta.simulada==test_mode,','')),
    ('BA2',CAGED,'Isolamento da leitura do Caged',replace_all('Coleta.simulada==test_mode,','')),
    ('BA3',LAW,'Trava de modo de teste',replace_once("if simulada and os.environ.get('OIL_TEST_MODE') != '1':",'if False:')),
    ('BA4',CAGED,'Trava de recorte',replace_once("if recorte and not (self.simulada and os.environ.get('OIL_TEST_MODE')=='1'):",'if False:')),
    ('BB',LAW,'Desempate entre casas',replace_once("s['casa']=='senado'","s['casa']=='camara'")),
    ('BC',LAW,'Divergência de estágios',replace_once("divergent=len(snapshots)==2 and len({stage(s.situacao_texto) for s in snapshots.values()})>1",'divergent=False')),
    ('BD',LAW,'Previsão do marco',replace_once('marker.prevista=False','marker.prevista=True')),
    ('BD2',LAW,'Origem do marco',replace_once("marker.origem='fonte'","marker.origem='calculado'")),
    ('BE',LAW,'Norma fixa sintética',replace_once("norm=dict(senate.norma_json,fonte=endpoints(identifier)['senado']) if senate and senate.norma_json else None","norm=dict(rotulo='Norma sintética fixa',data='2000-01-01',link='https://www.planalto.gov.br/',fonte=endpoints(identifier)['senado'])")),
    ('BF',CAGED,'Reconstrução pela ordem de chegada',replace_once('.order_by(Coleta.mes_referencia,Observacao.versao)).all()', '.order_by(Coleta.id,Observacao.versao)).all()')),
    ('BG',CAGED,'Comparação com versão antiga',replace_once("Coleta.mes_referencia<=entry['competencia']).order_by(Coleta.mes_referencia,Observacao.versao)","Coleta.mes_referencia<=entry['competencia']).order_by(Coleta.mes_referencia.desc(),Observacao.versao.desc())")),
    ('BH',CAGED,'Sinal da comparação anual',replace_once("difference=value-previous['valor']","difference=previous['valor']-value")),
    ('BI',CAGED,'Horário do calendário',replace_once("date+'T23:59:00-03:00'","date+'T00:00:00-03:00'")),
    ('BJ',LAW,'Referência do partido',replace_once("partido_referencia='atual'","partido_referencia='data_apresentacao'")),
    ('BK',CAGED,'Validação de ajustes',replace_once(" or 'COM AJUSTES' not in title",'')),
    ('BL',CAGED,'Aba sem ajuste aceita',replace_once("if 'Tabela 5.1' not in workbook.sheetnames: raise ValueError('Aba esperada ausente.')\n        sheet=workbook['Tabela 5.1']","if 'Tabela 5.1' not in workbook.sheetnames and 'Tabela 5' not in workbook.sheetnames: raise ValueError('Aba esperada ausente.')\n        sheet=workbook['Tabela 5.1' if 'Tabela 5.1' in workbook.sheetnames else 'Tabela 5']")),
    ('BM',CAGED,'Filtro redundante de validade',replace_once('Coleta.simulada==test_mode,Coleta.valida.is_(True),Coleta.mes_referencia<=competencia,','Coleta.simulada==test_mode,Coleta.mes_referencia<=competencia,')),
    ('BN',CAGED,'Saldo absoluto',replace_once('points[period]=int(value)','points[period]=abs(int(value))')),
    ('BO',CAGED,'Tipo monetário no saldo',replace_once("common=dict(tipo_valor=None,tipo_periodo='mensal'","common=dict(tipo_valor='nominal',tipo_periodo='mensal'")),
    ('BP',CAGED,'Atribuição sem indicação de ajuste',replace_once('Tabela 5.1 (com ajustes). Série','Tabela 5.1. Série')),
    ('BQ',LAW,'Data fixa no marco',replace_once("deliberation['tipoDeliberacao'],deliberation['data']","deliberation['tipoDeliberacao'],'2026-10-15'")),
    ('BR',LAW,'Rótulo fixo no marco',replace_once("deliberation['tipoDeliberacao'],deliberation['data']","'Aprovação',deliberation['data']")),
    ('S1',CAGED,'Manifesto sem hash aceito',replace_once("if not isinstance(expected_hash,str) or re.fullmatch(r'[0-9a-fA-F]{64}',expected_hash) is None:",'if False:')),
    ('S8',CAGED,'Teto expandido revertido a 200 MiB',replace_once('MAX_EXPANDED_BYTES=512*1024*1024','MAX_EXPANDED_BYTES=200*1024*1024')),
    ('S3',LAW,'Corpo completo de deputado armazenado',replace_once('raw=minimized_deputy(raw)','raw=raw')),
    ('S5',LAW,'Teto de resposta removido',remove_law_limit),
    ('S6',LAW,'Link de norma sem validação de origem',replace_once("if not official_norm_link(norm['link']):",'if False:')),
    ('S7',LAW,'Candidatos sem snapshot',replace_all(" and s['casa'] in snapshots",'')),
]


def git(root,*arguments):
    result=subprocess.run(['git','-C',str(root),*arguments],capture_output=True,text=True)
    if result.returncode:raise RuntimeError('Falhou verificação Git: '+' '.join(arguments))
    return result.stdout.strip()


def clean(root):
    git(root,'diff','--quiet','--exit-code')
    git(root,'diff','--cached','--quiet','--exit-code')


def prepare_own_metadata_removal(checkout):
    # OneDrive marca diretórios como ReadOnly; só altera o registro deste checkout.
    metadata=git(checkout,'rev-parse','--absolute-git-dir')
    if not metadata:return  # O teste de orquestração usa Git simulado.
    common=Path(git(ROOT,'rev-parse','--path-format=absolute','--git-common-dir'))
    target=Path(metadata)
    if target.parent.resolve()!=(common/'worktrees').resolve():raise RuntimeError('Registro temporário fora do diretório esperado.')
    for path in [*target.rglob('*'),target]:path.chmod(path.stat().st_mode|stat.S_IWRITE|stat.S_IREAD)


def run_suite(checkout,output,label):
    xml=output/(label+'.xml');log=output/(label+'.txt')
    environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    result=subprocess.run([sys.executable,'backend/scripts/test_postgres.py','backend/tests','-x',
        '--junitxml='+str(xml)],cwd=checkout,env=environment,capture_output=True,text=True,timeout=900)
    log.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if not xml.exists():raise RuntimeError('Execução não gerou relatório pytest: '+label)
    report=ET.parse(xml)
    cases=list(report.iter('testcase'))
    errors=[case for case in cases if case.find('error') is not None]
    failures=[case for case in cases if case.find('failure') is not None]
    summaries=re.findall(r'^\d+ (?:failed|passed)[^\r\n]*',result.stdout,re.M)
    if errors:raise RuntimeError('Erro de preparação não conta como mutação detectada: '+label)
    if result.returncode and not failures:raise RuntimeError('Falha externa aos testes de backend: '+label)
    return dict(resultado='DETECTADA' if failures else 'SOBREVIVENTE',
        teste=[case.attrib['classname']+'::'+case.attrib['name'] for case in failures],
        pytest_resumo=summaries,codigo_saida=result.returncode)


def execute(only=None,publicar_evidencia=False):
    clean(ROOT)
    revision=git(ROOT,'rev-parse','HEAD')
    scratch=Path(tempfile.mkdtemp(prefix='oil-o3r-backend-'))
    checkout=scratch/'checkout'
    output=ROOT.parent/'work-o3c'/('backend-mutacoes-'+revision[:8])
    output.mkdir(parents=True,exist_ok=True)
    report=dict(head=revision,isolamento='worktree descartável e PostgreSQL em porta aleatória de loopback',resultados=[])
    git(ROOT,'worktree','add','--detach',str(checkout),'HEAD')
    try:
        baseline=run_suite(checkout,output,'baseline')
        if baseline['resultado']!='SOBREVIVENTE':raise RuntimeError('A base precisa passar antes das mutações.')
        report['baseline']=baseline['pytest_resumo']
        for identifier,file,name,transform in MUTATIONS:
            if only and identifier not in only:continue
            path=checkout/file;original=path.read_bytes()
            mutated=transform(original.decode('utf-8').replace('\r\n','\n'))
            if mutated==original.decode('utf-8').replace('\r\n','\n'):raise RuntimeError('Mutação sem efeito: '+identifier)
            compile(mutated,file,'exec')
            try:
                path.write_text(mutated,encoding='utf-8',newline='\n')
                outcome=run_suite(checkout,output,identifier)
            finally:
                path.write_bytes(original)
                clean(checkout)
            item=dict(id=identifier,nome=name,arquivo=file,**outcome,restauracao_git_exit_code=0)
            report['resultados'].append(item)
            (output/'progresso.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(identifier+': '+outcome['resultado'],flush=True)
    finally:
        clean(checkout)
        clean(ROOT)
        prepare_own_metadata_removal(checkout)
        git(ROOT,'worktree','remove',str(checkout))
        scratch.rmdir()  # A pasta é a que este processo criou; nunca há remoção recursiva manual.
    report['total']=len(report['resultados'])
    report['detectadas']=sum(r['resultado']=='DETECTADA' for r in report['resultados'])
    report['sobreviventes']=[r['id'] for r in report['resultados'] if r['resultado']=='SOBREVIVENTE']
    report['restauracao_repo_principal_exit_code']=0
    if git(ROOT,'status','--porcelain'):raise RuntimeError('O checkout principal deve terminar limpo.')
    target=(ROOT/'docs/o3/evidencias/o3c-mutacoes-backend.json') if publicar_evidencia else output/'resultado.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if report['sobreviventes']:raise RuntimeError('Nenhum sobrevivente é aceito; consulte o relatório.')
    print('Evidência: '+os.path.relpath(target,ROOT))
    print(json.dumps({key:report[key] for key in ('total','detectadas','sobreviventes')},ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--check',action='store_true',help='Confere alvos e sintaxe sem executar Docker.')
    parser.add_argument('--only',nargs='+')
    parser.add_argument('--publicar-evidencia',action='store_true',help='Copia explicitamente o resultado para a documentação versionada.')
    args=parser.parse_args()
    if args.list:
        print(json.dumps([dict(id=i,arquivo=f,nome=n) for i,f,n,t in MUTATIONS],ensure_ascii=False));return
    if args.check:
        for identifier,file,name,transform in MUTATIONS:
            source=(ROOT/file).read_text(encoding='utf-8');compile(transform(source),file,'exec')
        print(str(len(MUTATIONS))+' alvos válidos, sintaxe conferida.');return
    execute(set(args.only) if args.only else None,args.publicar_evidencia)


if __name__=='__main__':main()
