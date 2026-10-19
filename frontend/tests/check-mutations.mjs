// Opt-in: regressões somente em worktree descartável, com Git após cada restauração.
// Não lê ambientes nem altera backend/poc; execute diretamente com servidores parados.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const root=process.cwd();
if(!fs.existsSync(path.join(root,'components/indicator.tsx')))throw Error('Execute dentro de frontend/.');
const repo=path.resolve(root,'..');
const prefix=process.env.OIL_MUTATION_EVIDENCE_PREFIX||'o3c';
if(!/^[a-z0-9-]+$/.test(prefix))throw Error('Prefixo de evidência inválido.');
function git(cwd,args){const result=spawnSync('git',['-C',cwd,...args],{encoding:'utf8',windowsHide:true});if(result.status!==0)throw Error('Verificação Git falhou: '+args.join(' '));return result.stdout.trim();}
function clean(cwd){git(cwd,['diff','--quiet','--exit-code']);git(cwd,['diff','--cached','--quiet','--exit-code']);}
function prepareOwnMetadataRemoval(checkout){
  const target=git(checkout,['rev-parse','--absolute-git-dir']);
  const common=git(repo,['rev-parse','--path-format=absolute','--git-common-dir']);
  if(path.resolve(path.dirname(target))!==path.resolve(common,'worktrees'))throw Error('Registro temporário fora do diretório esperado.');
  function writable(directory){for(const entry of fs.readdirSync(directory,{withFileTypes:true})){const item=path.join(directory,entry.name);if(entry.isDirectory())writable(item);else fs.chmodSync(item,0o600);}fs.chmodSync(directory,0o700);}
  writable(checkout);writable(target);
}
if(!process.argv.includes('--isolated')) {
  clean(repo);
  const head=git(repo,['rev-parse','HEAD']);
  // Mesmo volume das dependências: evita caminhos relativos entre unidades no webpack.
  const temporaryParent=path.join(path.dirname(repo),'work-o3r');
  fs.mkdirSync(temporaryParent,{recursive:true});
  const scratch=fs.mkdtempSync(path.join(temporaryParent,'frontend-worktree-'));
  const checkout=path.join(scratch,'checkout'),copyFrontend=path.join(checkout,'frontend');
  const output=path.join(path.dirname(repo),'work-o3r',`frontend-mutacoes-${head.slice(0,8)}`);
  fs.mkdirSync(output,{recursive:true});
  git(repo,['worktree','add','--detach',checkout,'HEAD']);
  const dependencyLink=path.join(copyFrontend,'node_modules');
  let status=1;
  try {
    fs.symlinkSync(path.join(root,'node_modules'),dependencyLink,process.platform==='win32'?'junction':'dir');
    const child=spawnSync(process.execPath,[path.join(copyFrontend,'tests/check-mutations.mjs'),'--isolated'],{
      cwd:copyFrontend,env:{...process.env,OIL_MUTATION_ISOLATED:checkout,OIL_MUTATION_EVIDENCE_DIR:output,OIL_MUTATION_EVIDENCE_PREFIX:prefix},stdio:'inherit',windowsHide:true});
    if(child.error)throw child.error;
    status=child.status??1;
  } finally {
    clean(checkout);clean(repo);
    if(fs.existsSync(dependencyLink)&&fs.lstatSync(dependencyLink).isSymbolicLink())fs.unlinkSync(dependencyLink);
    prepareOwnMetadataRemoval(checkout);git(repo,['worktree','remove',checkout]);
    fs.rmdirSync(scratch);
  }
  // Primeiro prova a integridade do repo principal; só depois copia os relatórios.
  if(git(repo,['status','--porcelain']))throw Error('O checkout principal deve terminar limpo.');
  if(process.argv.includes('--publicar-evidencia'))for(const name of fs.readdirSync(output).filter(name=>name.startsWith(prefix+'-')&&name.endsWith('.json')))fs.copyFileSync(path.join(output,name),path.join(root,'evidencias',name));
  console.log('Evidência: '+path.relative(repo,output));
  console.log('Worktree removido; git diff --exit-code retornou zero no repo principal.');
  process.exit(status);
}
if(path.resolve(process.env.OIL_MUTATION_ISOLATED||'')!==repo)throw Error('Execução isolada exige worktree próprio.');
const evidence=process.env.OIL_MUTATION_EVIDENCE_DIR;
if(!evidence)throw Error('Diretório externo de evidência obrigatório.');
const env={...process.env,NEXT_TELEMETRY_DISABLED:'1',OIL_BROWSER_CHANNEL:process.env.OIL_BROWSER_CHANNEL||'msedge'};
const results=[];
const originals=new Map();
function patch(file,replace){
  const target=path.join(root,file);
  if(!originals.has(target))originals.set(target,fs.readFileSync(target));
  const before=fs.readFileSync(target,'utf8').replaceAll('\r\n','\n'),after=replace(before);
  if(before===after)throw Error(`Mutação sem efeito: ${file}`);
  fs.writeFileSync(target,after);
}
function restore(){for(const [file,bytes] of originals){fs.writeFileSync(file,bytes);if(!fs.readFileSync(file).equals(bytes))throw Error(`Restauração divergente: ${file}`);}originals.clear();clean(repo);}
function run(args){return spawnSync(process.execPath,args,{cwd:root,env,encoding:'utf8',windowsHide:true,maxBuffer:16*1024*1024,timeout:240000});}
function testResult(output){
  if(output.error)throw output.error;
  const parsed=JSON.parse(output.stdout);
  if(parsed.errors.length||!parsed.stats.unexpected)throw Error('A regressão não foi detectada por uma asserção de teste. '+JSON.stringify(parsed.errors));
  return parsed;
}
function record(name,report){
  results.push({mutacao:name,detectada:true,stats:report.stats});
  fs.writeFileSync(path.join(evidence,`${prefix}-mutacoes.json`),JSON.stringify({modo:'regressoes intencionais, nao sao falhas da entrega',isolamento:'worktree descartável',restauracao_git_exit_code:0,resultados:results},null,2)+'\n');
  console.log(`DETECTADA: ${name} (${report.stats.unexpected} teste(s) falhou/falharam como esperado)`);
}
try {
  const units=[
    ['2: CSV volta a escapar números','lib/csv.ts',s=>s.replace("typeof value === 'string' ? value.replace", "true ? String(value ?? '').replace"),'R2-2'],
    ['3: previsão ignora passagem do tempo','lib/vigencia.ts',s=>s.replace('etapa.data_inicio > hoje','true'),'R2-3'],
    ['4: trimestral volta a mensal','lib/types.ts',s=>s.replace("value==='trimestral'","false"),'R2-4'],
    ['5: guarda de marco e variação removida','tests/linguagem.ts',s=>s.replace('variation.test(sentence)','false'),'R2-5'],
    ['7: domínio perde fronteira de subdomínio','lib/safe-href.ts',s=>s.replace('url.hostname.endsWith(`.${domain}`)','url.hostname.endsWith(domain)'),'R2-7'],
    ['8: quota contada antes da validação','app/api/oil/indicadores/[[...path]]/route.ts',s=>{
      const start=s.indexOf('  for (const [key, client]'),end=s.indexOf('\n\n  const base',start);
      const block=s.slice(start,end);const without=s.slice(0,start)+s.slice(end);
      return without.replace('  const { path = [] }',block+'\n\n  const { path = [] }');
    },'R2-8'],
    ['FC4: evento genérico não é verificado','tests/linguagem.ts',s=>s.replace('a partir d[ao]','início d[ao]'),'O3R FC4'],
    ['FC5: data sem ano não é verificada','tests/linguagem.ts',s=>s.replace(String.raw`(?:\/\d{4})?`,String.raw`\/\d{4}`),'O3R FC5'],
    ['FD3: comparação com data não é verificada','tests/linguagem.ts',s=>s.replace('d[aoe]','d[ao]'),'O3R FD3'],
    ['B1: div próprio deixa de ser verificado','tests/linguagem.ts',s=>s.replace('[...blocks,...ownDivText]','blocks'),'O3C div próprio']
  ];
  for(const [name,file,replace,grep] of units){
    try{patch(file,replace);record(name,testResult(run(['node_modules/@playwright/test/cli.js','test','-c','playwright.unit.config.ts','--grep',grep])));}
    finally{restore();}
  }

  // A injeção no div é conferida isoladamente, sem a sonda do summary.
  try {
    patch('components/dashboard.tsx',s=>s.replace('const law=<Law','const law=<><div>Em 14/10/2026, a desocupação caiu.</div><Law').replace('onData={onLawData}/>;','onData={onLawData}/></>;'));
    const build=run(['node_modules/next/dist/bin/next','build','--webpack']);
    if(build.status!==0)throw Error('Build da sonda do div falhou; não conta como detecção.');
    record('B1: data e variação no div do dashboard',testResult(run(['node_modules/@playwright/test/cli.js','test','--grep','frases proibidas','--reporter=json','--output=test-results/mutation-div'])));
  }finally{restore();}

  // Uma compilação com mutações independentes; cada asserção indicada deve falhar.
  patch('components/indicator.tsx',s=>s.replace('if(body.simulada&&!testMode)','if(false)').replace('<summary>Saiba mais</summary>','<summary>Saiba mais</summary><svg className="mutation-a11y" role="img" width="12" height="12"><rect width="12" height="12"/></svg>'));
  patch('components/vigencia.tsx',s=>s.replace('vigenciaText(vigencia,hoje)',JSON.stringify('Em vigor desde 16/10/2026, data da publicação, exceto: repouso de 2 dias por semana e limite de 42 h semanais a partir de 16/12/2026 (prevista); limite de 40 h semanais a partir de 16/12/2027 (prevista).')).replace('Saiba mais sobre a vigência','Saiba mais sobre a vigência. Em 14/10/2026, a desocupação caiu'));
  patch('components/chart.tsx',s=>s.replace('event.currentTarget.open=true;','event.currentTarget.open=false;'));
  patch('components/dashboard.tsx',s=>s.replace('<Reading data={states[code].data} summary/>','<Reading data={{...states[code].data,valor:0}} summary/>'));
  patch('app/globals.css',s=>s+'\n.mutation-a11y{display:none}@media(min-width:1000px){.mutation-a11y{display:block}}\n');
  console.log('Compilando as mutações de interface...');
  const build=run(['node_modules/next/dist/bin/next','build','--webpack']);
  if(build.status!==0)throw Error('Build das mutações falhou; isso não conta como detecção. '+build.stderr);
  const output=run(['node_modules/@playwright/test/cli.js','test','--grep','R2-1|R2-3 mudar|R2-6|R2-9|axe 1280: detalhes abertos, modo normal|frases proibidas','--reporter=json','--output=test-results/mutation-ui']);
  const report=testResult(output);
  function specs(suites){return suites.flatMap(s=>[...(s.specs||[]),...specs(s.suites||[])]);}
  const all=specs(report.suites);
  const redact=text=>text?.replace(/(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\r\n"<>]*?(?=:\d+(?::|$)|[\r\n"<>]|$)/g,'<local>');
  fs.writeFileSync(path.join(evidence,`${prefix}-mutacoes-ui.json`),JSON.stringify(all.map(s=>({teste:s.title,aprovado:s.ok,resultados:s.tests.flatMap(t=>t.results.map(r=>({status:r.status,asserção:redact(r.error?.message?.slice(0,1800))})))})),null,2)+'\n');
  for(const [prefix,name] of [
    ['R2-1','1: trava de simulada removida'],['R2-3 mudar','3: vigência volta a texto fixo'],
    ['R2-6','6: foco deixa de revelar fonte'],['R2-9','9: resumo diverge do card'],
    ['axe 1280: detalhes abertos, modo normal','9: imagem sem alternativa nos detalhes desktop'],
    ['frases proibidas','Q2: data e variação dentro do summary']
  ]){
    const selected=all.filter(s=>s.title.startsWith(prefix));
    if(!selected.length||selected.some(s=>s.ok||!s.tests.some(t=>t.results.some(r=>r.status==='failed'))))throw Error(`Mutação não detectada: ${name}`);
    record(name,{stats:{testes: selected.length,unexpected:selected.length}});
  }
  console.log('Todas as regressões foram detectadas. Os fontes serão restaurados; recompile e rode a suíte final.');
} finally {restore();}
