// Opt-in: injeta regressões locais, exige falha dos testes e restaura os bytes.
// Sem comandos Git, acesso a .env ou mudanças em backend/poc. Execute com servidores parados.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const root=process.cwd();
if(!fs.existsSync(path.join(root,'components/indicator.tsx')))throw Error('Execute dentro de frontend/.');
const evidence=path.join(root,'evidencias');
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
function restore(){for(const [file,bytes] of originals)fs.writeFileSync(file,bytes);originals.clear();}
function run(args){return spawnSync(process.execPath,args,{cwd:root,env,encoding:'utf8',windowsHide:true,maxBuffer:16*1024*1024,timeout:240000});}
function testResult(output){
  if(output.error)throw output.error;
  const parsed=JSON.parse(output.stdout);
  if(parsed.errors.length||!parsed.stats.unexpected)throw Error('A regressão não foi detectada por uma asserção de teste. '+JSON.stringify(parsed.errors));
  return parsed;
}
function record(name,report){
  results.push({mutacao:name,detectada:true,stats:report.stats});
  fs.writeFileSync(path.join(evidence,'o4r2-mutacoes.json'),JSON.stringify({modo:'regressoes intencionais, nao sao falhas da entrega',resultados:results},null,2)+'\n');
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
    },'R2-8']
  ];
  for(const [name,file,replace,grep] of units){
    try{patch(file,replace);record(name,testResult(run(['node_modules/@playwright/test/cli.js','test','-c','playwright.unit.config.ts','--grep',grep])));}
    finally{restore();}
  }

  // Uma compilação com mutações independentes; cada asserção indicada deve falhar.
  patch('components/indicator.tsx',s=>s.replace('if(body.simulada&&!testMode)','if(false)').replace('<summary>Saiba mais</summary>','<summary>Saiba mais</summary><svg className="mutation-a11y" role="img" width="12" height="12"><rect width="12" height="12"/></svg>'));
  patch('components/vigencia.tsx',s=>s.replace('vigenciaText(vigencia,hoje)',JSON.stringify('Em vigor desde 16/10/2026, data da publicação, exceto: repouso de 2 dias por semana e limite de 42 h semanais a partir de 16/12/2026 (prevista); limite de 40 h semanais a partir de 16/12/2027 (prevista).')));
  patch('components/chart.tsx',s=>s.replace('event.currentTarget.open=true;','event.currentTarget.open=false;'));
  patch('components/dashboard.tsx',s=>s.replace('<Reading data={states[code].data} summary/>','<Reading data={{...states[code].data,valor:0}} summary/>'));
  patch('app/globals.css',s=>s+'\n.mutation-a11y{display:none}@media(min-width:1000px){.mutation-a11y{display:block}}\n');
  console.log('Compilando as mutações de interface...');
  const build=run(['node_modules/next/dist/bin/next','build','--webpack']);
  if(build.status!==0)throw Error('Build das mutações falhou; isso não conta como detecção. '+build.stderr);
  const output=run(['node_modules/@playwright/test/cli.js','test','--grep','R2-1|R2-3 mudar|R2-6|R2-9|axe 1280: detalhes abertos, modo normal','--reporter=json','--output=test-results/mutation-ui']);
  const report=testResult(output);
  function specs(suites){return suites.flatMap(s=>[...(s.specs||[]),...specs(s.suites||[])]);}
  const all=specs(report.suites);
  fs.writeFileSync(path.join(evidence,'o4r2-mutacoes-ui.json'),JSON.stringify(all.map(s=>({teste:s.title,aprovado:s.ok,resultados:s.tests.flatMap(t=>t.results.map(r=>({status:r.status,asserção:r.error?.message?.slice(0,1800)})))})),null,2)+'\n');
  for(const [prefix,name] of [
    ['R2-1','1: trava de simulada removida'],['R2-3 mudar','3: vigência volta a texto fixo'],
    ['R2-6','6: foco deixa de revelar fonte'],['R2-9','9: resumo diverge do card'],
    ['axe 1280: detalhes abertos, modo normal','9: imagem sem alternativa nos detalhes desktop']
  ]){
    const selected=all.filter(s=>s.title.startsWith(prefix));
    if(!selected.length||selected.some(s=>s.ok||!s.tests.some(t=>t.results.some(r=>r.status==='failed'))))throw Error(`Mutação não detectada: ${name}`);
    record(name,{stats:{testes: selected.length,unexpected:selected.length}});
  }
  console.log('Todas as regressões foram detectadas. Os fontes serão restaurados; recompile e rode a suíte final.');
} finally {restore();}
