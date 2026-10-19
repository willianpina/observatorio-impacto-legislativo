import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fixture,intercept } from './fixtures';
import fs from 'node:fs/promises';
import {languageViolations,scanLanguageBlocks} from './linguagem';
import {lei} from '../mocks/lei';

const warning = 'É cedo para afirmar. A emenda começa a valer em etapas, e os dados oficiais saem com atraso. Mudanças nos indicadores podem ter várias causas.';
const legend = 'Marcos de calendário. Não indicam efeito da lei.';

test.beforeEach(async ({page}) => {await intercept(page);await page.clock.setFixedTime(new Date('2026-10-17T15:00:00Z'));});

test('resumo do Caged separa valor oficial e cálculo, como o card',async({page})=>{
  await page.unroute('**/api/oil/indicadores/**');await intercept(page,'caged');await page.goto('/');
  const summary=page.getByTestId('resumo-caged-saldo');
  await expect(summary.getByTestId('resumo-caged-valor-oficial')).toContainText('-10 postos de trabalho');
  await expect(summary.getByTestId('resumo-caged-valor-oficial')).not.toContainText('Cálculo');
  await expect(summary.getByTestId('resumo-caged-comparacao')).toHaveText(await page.getByTestId('card-caged-saldo').getByTestId('caged-comparacao').textContent()||'');
  await expect(summary.getByText('Saldo com ajustes',{exact:true})).toBeVisible();
  await expect(page.getByText('Em vigor desde 16/10/2026, data da publicação, exceto: repouso de 2 dias por semana e limite de 42 h semanais a partir de 16/12/2026 (prevista); limite de 40 h semanais a partir de 16/12/2027 (prevista).',{exact:true})).toBeVisible();
});

for(const code of ['desocupacao','rendimento-real','caged-saldo'])test(`card ${code}: valor único, fonte, horário e selo`,async({page})=>{
  await page.unroute('**/api/oil/indicadores/**');await intercept(page,'caged');await page.goto('/');
  const card=page.getByTestId(`card-${code}`),value=card.getByTestId(`valor-atual-${code}`);
  await expect(value).toHaveCount(1);await expect(value).toHaveText(code==='desocupacao'?'5,3 %':code==='rendimento-real'?'R$ 3.777':'-10 postos de trabalho');
  await expect(card.locator('.source').first()).toContainText('Fonte:');
  await expect(card.locator('.source').first()).toContainText(/Coletado em \d{2}\/\d{2}\/\d{4}, \d{2}:\d{2} \(BRT\)/);
  await expect(card.getByText('Descritivo',{exact:true})).toBeVisible();
  if(code!=='caged-saldo')await expect(card).toContainText('jun.–ago. de 2026');
  await expect(card).not.toContainText('p.p..');
});

test('cabeçalhos de segurança preservam hidratação e consultas',async({page})=>{
  const blocked:string[]=[];page.on('console',msg=>{if(/Refused|Content Security Policy/i.test(msg.text()))blocked.push(msg.text());});
  const response=await page.goto('/');const headers=response!.headers();
  for(const directive of ["default-src 'self'","frame-ancestors 'none'","object-src 'none'","base-uri 'self'"])expect(headers['content-security-policy']).toContain(directive);
  expect(headers['x-content-type-options']).toBe('nosniff');expect(headers['referrer-policy']).toBe('strict-origin-when-cross-origin');
  await fs.writeFile('test-results/o4r-security-headers.json',JSON.stringify({csp:headers['content-security-policy'],content_type_options:headers['x-content-type-options'],referrer_policy:headers['referrer-policy']},null,2));
  await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  await page.getByLabel('Período dos gráficos').selectOption('2a');await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  expect(blocked).toEqual([]);
});

for(const bad of ['javascript:alert(1)','https://estranho.example/roubo'])test(`links inválidos viram texto: ${bad}`,async({page})=>{
  for(const endpoint of ['lei','exemplo'])await page.route(`**/api/oil/${endpoint}`,async route=>{const body=await(await route.fetch()).json();const data=body.dados||body;data.link=bad;if(data.situacao_norma)data.situacao_norma.link=bad;if(data.norma_gerada)data.norma_gerada.link=bad;for(const item of [...(data.situacao||[]),...(data.marcos||[]),...(data.votacoes||[]),...(data.tramitacoes||[]),...(data.fontes_norma||[])])item.link=bad;await route.fulfill({json:body});});
  await page.route('**/api/oil/indicadores/**',route=>{const code=new URL(route.request().url()).pathname.split('/')[4];return route.fulfill({json:{...fixture(code),link:bad}});});
  await page.goto('/');await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  await expect(page.locator('a[href]').filter({hasText:'Ver texto da lei completo'})).toHaveCount(0);
  await expect(page.getByText('Ver texto da lei completo',{exact:true})).toBeVisible();
  expect(await page.locator('a[href]').evaluateAll(els=>els.some(el=>/javascript:|estranho\.example/.test(el.getAttribute('href')||'')))).toBe(false);
  await expect(page.getByTestId('card-desocupacao').locator('.source').first()).toContainText('IBGE');
});

test('marco dentro da série desenha linha vertical cinza e tracejada',async({page})=>{
  await page.route('**/api/oil/exemplo',async route=>{const body=await(await route.fetch()).json();body.dados.marcos=[{...body.dados.marcos[0],data:'2024-01-15',prevista:true}];await route.fulfill({json:body});});
  await page.goto('/');const line=page.getByTestId('card-desocupacao').locator('.recharts-reference-line line');
  await expect(line).toHaveCount(1);await expect(line).toHaveAttribute('stroke','#64748b');await expect(line).toHaveAttribute('stroke-dasharray','4 4');
  expect(await line.getAttribute('x1')).toBe(await line.getAttribute('x2'));
});

test('CSV preserva e neutraliza todos os prefixos perigosos',async({page})=>{
  const prefixes=['=','+','-','@','\t','\r'];
  await page.route('**/api/oil/indicadores/**',route=>{const body=fixture('desocupacao');body.pontos.slice(0,6).forEach((p,i)=>p.unidade=prefixes[i]+'teste');return route.fulfill({json:body});});
  await page.goto('/');const card=page.getByTestId('card-desocupacao');await card.getByText('Saiba mais',{exact:true}).click();
  const downloading=page.waitForEvent('download');await card.getByRole('button',{name:'Baixar CSV'}).click();
  const csv=await fs.readFile((await(await downloading).path())!,'utf8');for(const prefix of prefixes)expect(csv).toContain(`"'${prefix}teste"`);
});

test('erro informa o prazo recebido da API',async({page})=>{
  await page.unroute('**/api/oil/indicadores/**');await intercept(page,'error');await page.goto('/');await expect(page.getByTestId('card-desocupacao')).toContainText('Tente novamente em 60 segundos.');
});

for(const width of [360,1280])for(const mode of ['caged','normal','gap','stale','unclassified'])test(`axe ${width}: detalhes abertos, modo ${mode}`,async({page})=>{
  await page.setViewportSize({width,height:1000});await page.unroute('**/api/oil/indicadores/**');await intercept(page,mode,mode==='normal');
  await page.goto(mode==='normal'?'http://127.0.0.1:3102':'/');
  await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  await expect(page.getByText(warning,{exact:true})).toBeVisible();
  for(const more of await page.locator('details.more > summary,.vigencia details > summary').all())await more.click();
  await expect(page.locator('details.more[open]')).toHaveCount(mode==='caged'?3:2);
  const axe=await new AxeBuilder({page}).analyze();const severe=axe.violations.filter(v=>['serious','critical'].includes(v.impact||''));
  expect(severe).toEqual([]);
  await fs.writeFile(`test-results/o4r2-axe-${width}-aberto-${mode}.json`,JSON.stringify({fixture:true,modo:mode,width,detalhes_abertos:true,graves_criticas:severe.length,violacoes:axe.violations.map(v=>({id:v.id,impacto:v.impact}))},null,2));
  for(const graph of await page.locator('.chart[role="img"]').all())await expect(graph.locator('[tabindex]:not([tabindex="-1"]),a[href],button,input,summary')).toHaveCount(0);
  await expect(page.getByTestId('card-desocupacao').locator('.chart[role="img"]')).toHaveAttribute('aria-label',mode==='unclassified'?/5,3 %.*Classificação não disponível/:/5,3 %.*caiu/);
  await expect(page.locator('figcaption').first()).not.toContainText('trimestre_movel');
  await page.screenshot({path:`test-results/o4r2-${width}-aberto-${mode}-fixture.png`,fullPage:true});
});

test('aviso exato, origem e dado de teste; indicador sem tipo monetário', async ({page}) => {
  await page.goto('/');
  await expect(page.getByText(warning, {exact:true})).toBeVisible();
  await expect(page.getByText('MODO DE TESTE — dados simulados, não são reais')).toBeVisible();
  await expect(page.getByTestId('card-desocupacao').getByRole('heading', {name:'Taxa de desocupação',exact:true})).toBeVisible();
  await expect(page.getByTestId('card-desocupacao')).toContainText('p.p.');
  await expect(page.getByTestId('card-rendimento-real')).toContainText('Real, base de preços do IBGE em verificação');
  await expect(page.getByTestId('card-desocupacao')).not.toContainText('Nominal');
  await expect(page.locator('#lei').getByText('Transformado em Norma Jurídica',{exact:true})).toBeVisible();
});

test('modo normal não exibe mock nem aceita dados simulados', async ({page}) => {
  await page.goto('http://127.0.0.1:3102');
  await expect(page.getByText(warning,{exact:true})).toBeVisible();
  await expect(page.getByText('MODO DE TESTE', {exact:false})).toHaveCount(0);
  await expect(page.getByText('Transformado em Norma Jurídica',{exact:true})).toHaveCount(0);
  await expect(page.locator('#lei').getByText('Dado ainda não disponível',{exact:true})).toBeVisible();
  await expect(page.getByText('472',{exact:true})).toHaveCount(0);
});

test('janela altera só o gráfico; classificação vem da API', async ({page}) => {
  await page.goto('/');
  const insight=page.getByTestId('insight-desocupacao');
  await expect(insight).toContainText('caiu');
  const text=(await insight.textContent())!;
  const card=page.getByTestId('card-desocupacao');await card.getByText('Saiba mais',{exact:true}).click();
  const rows=card.locator('tbody tr');await expect(rows).toHaveCount(60);
  const fullPath=await card.locator('.recharts-line-curve').getAttribute('d');
  await page.getByLabel('Período dos gráficos').selectOption('2a');
  await expect(rows).toHaveCount(24);
  await expect(card.locator('.recharts-line-curve')).not.toHaveAttribute('d',fullPath!);
  await expect(insight).toHaveText(text);
  await page.getByLabel('Período dos gráficos').selectOption('desde_2020');
  await expect.poll(()=>rows.count()).toBeGreaterThan(60);
  await expect(insight).toHaveText(text);
});

for (const state of ['gap','error','stale','empty','unclassified']) test(`estado ${state}`, async ({page}) => {
  await page.unroute('**/api/oil/indicadores/**'); await intercept(page,state); await page.goto('/');
  const card=page.getByTestId('card-desocupacao');
  if(state==='gap') { await card.getByText('Saiba mais',{exact:true}).click(); await expect(card.getByText('sem dado',{exact:true})).toBeVisible(); await expect(card.locator('.recharts-line-curve')).toHaveAttribute('d',/M.*M/); }
  if(state==='error') { await expect(card.getByRole('button',{name:'Tentar de novo'})).toBeVisible(); await expect(page.getByTestId('card-rendimento-real')).toContainText('Último dado'); }
  if(state==='stale') await expect(card).toContainText('Fonte fora do ar. Mostrando a última coleta válida');
  if(state==='empty') await expect(card).toContainText('Ainda não há dados');
  if(state==='unclassified') { await expect(card).toContainText('Último dado');await expect(card).not.toContainText('calculado pelo Observatório');await expect(card).not.toContainText('▲');await expect(card).not.toContainText('▼');await expect(card.locator('.classification')).toHaveCount(0); }
});

test('Caged indisponível não tem eixos, números ou gráfico', async ({page}) => {
  await page.goto('/'); const card=page.getByTestId('card-caged-saldo');
  await expect(card).toContainText('Dado ainda não disponível');
  await expect(card.locator('.recharts-wrapper')).toHaveCount(0);
});

test('Caged com ajustes, atribuição e cálculo separados, sem misturar séries', async ({page}) => {
  await page.unroute('**/api/oil/indicadores/**'); await intercept(page,'caged'); await page.goto('/');
  const card=page.getByTestId('card-caged-saldo');
  await expect(card.getByText('Saldo com ajustes',{exact:true})).toBeVisible();
  await expect(card).toContainText('Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo agosto/2026, coletado em');
  await card.getByText('Saiba mais',{exact:true}).click();
  await expect(card).toContainText('Uso livre e gratuito, com citação da fonte');
  await expect(card.getByRole('link',{name:/Decreto nº 8.777/})).toHaveAttribute('href','https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm');
  await card.getByText('Saiba mais',{exact:true}).click();
  await expect(card.getByTestId('caged-comparacao')).toContainText('Cálculo do Observatório a partir de dados do MTE');
  await expect(card.getByTestId('caged-valor-oficial')).not.toContainText('Variação');
  await expect(card.locator('.recharts-bar-rectangle')).toHaveCount(1);
  await card.getByText('Saiba mais',{exact:true}).click();
  await expect(card).toContainText('revisadas mensalmente');
  await expect(card).toContainText('Meses com outro tipo de ajuste não entram no gráfico.');
});

test('marcos neutros, previsões com artigo e sem estender dados', async ({page}) => {
  await page.goto('/'); const card=page.getByTestId('card-desocupacao');
  await expect(card.getByText(legend,{exact:true})).toBeVisible();
  await expect(card.locator('[data-prevista="true"]')).toHaveCount(2);
  for(const marker of await card.locator('[data-marker]').all()) {
    await expect(marker).toHaveCSS('border-left-color','rgb(100, 116, 139)');
    if(await marker.getAttribute('data-prevista')==='true') await expect(marker).toHaveCSS('border-left-style','dashed');
  }
  await expect(page.getByText('data calculada pelo Observatório a partir da publicação').first()).toBeVisible();
  await expect(page.locator('.law-milestones').getByText('Art. 6º, I',{exact:false}).first()).toBeVisible();
});

test('placar conferido: total 494, obstrução 1 separada', async ({page}) => {
  await page.goto('/'); const vote=page.getByTestId('vote-2233802-424');
  await expect(vote).toContainText('472'); await expect(vote).toContainText('22');
  await expect(vote).toContainText('Total: 494'); await expect(vote).toContainText('Obstrução: 1 (fora do total)');
  await expect(vote.getByText('Aprovada',{exact:true})).toBeVisible();
  await expect(page.getByTestId('vote-2233802-438').getByText('Placar em conferência',{exact:true})).toBeVisible();
});

test('tramitação e votos paginam, sigla ausente não é completada', async ({page}) => {
  await page.goto('/'); await page.getByTestId('vote-2233802-424').getByText('Ver votos individuais',{exact:true}).click();
  await expect(page.getByText('sigla não informada pela fonte',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Carregar mais votos'}).click();
  await expect(page.getByRole('button',{name:'Carregar mais votos'})).toHaveCount(0);
  await page.getByRole('button',{name:'Carregar mais tramitações'}).click();
  await expect(page.getByRole('button',{name:'Carregar mais tramitações'})).toHaveCount(0);
});

test('votação simbólica fica sem números', async ({page}) => {
  await page.goto('/');
  await page.getByText('Outras votações — Câmara',{exact:true}).click();
  const vote=page.getByTestId('vote-simbolica-teste');
  await expect(vote).toContainText('sem registro de votos individuais');
  await expect(vote.locator('.score')).toHaveCount(0);
});

test('inconsistência entre partidos e placar não exibe aprovação', async ({page}) => {
  await page.route('**/api/oil/exemplo',async route=>{
    const response=await route.fetch();const body=await response.json();
    body.dados.votacoes[0].votos_por_partido=[{partido:'TESTE',sim:471,nao:23,abstencao:0,presentes:494,percentual_sim:95.34,base_percentual:'presentes'}];
    await route.fulfill({json:body});
  });
  await page.goto('/');
  const vote=page.getByTestId('vote-2233802-424');
  await expect(vote).toContainText('Total: 494');
  await expect(vote.getByText('Aprovada',{exact:true})).toHaveCount(0);
  await expect(vote.locator('.party-chart')).toHaveCount(0);
});

test('frases proibidas em todo texto, dicas, tabelas e rótulos', async ({page}) => {
  await page.unroute('**/api/oil/indicadores/**');await intercept(page,'caged');
  await page.goto('/'); await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  const text=await page.locator('body').innerText();
  const attributes=await page.locator('[aria-label],[title],[alt]').evaluateAll(els=>els.map(e=>[e.getAttribute('aria-label'),e.getAttribute('title'),e.getAttribute('alt')].join(' ')).join(' '));
  const corpus=(text.split(legend).join('')+' '+attributes).toLocaleLowerCase('pt-BR');
  expect(languageViolations(text+'\n'+attributes)).toEqual([]);
  const markers=lei.marcos.flatMap(m=>[m.rotulo,m.data]);
  expect(await scanLanguageBlocks(page,markers)).toEqual([]);
});

test('abas funcionam com teclado e CSV pode ser baixado',async({page})=>{
  await page.goto('/');
  const tab=page.getByRole('tab',{name:'Visão geral',exact:true});await tab.focus();await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab',{name:'Indicadores',exact:true})).toBeFocused();
  const card=page.getByTestId('card-desocupacao');await expect(card).toContainText('Último dado');
  await card.getByText('Saiba mais',{exact:true}).click();
  const download=page.waitForEvent('download');await card.getByRole('button',{name:'Baixar CSV'}).click();
  expect((await download).suggestedFilename()).toBe('desocupacao-5a.csv');
});

for(const width of [360,1280]) for(const state of ['normal','gap','error','empty','stale']) test(`axe e captura ${width}px ${state}`, async ({page}) => {
  await page.setViewportSize({width,height:1000}); await page.unroute('**/api/oil/indicadores/**'); await intercept(page,state); await page.goto('/');
  await expect(page.getByTestId('card-desocupacao')).not.toContainText('Carregando');
  const results=await new AxeBuilder({page}).analyze();
  expect(results.violations.filter(v=>['serious','critical'].includes(v.impact || ''))).toEqual([]);
  await fs.writeFile(`test-results/o4r-axe-${width}-${state}.json`,JSON.stringify({fixture:true,width,estado:state,detalhes_abertos:false,graves_criticas:results.violations.filter(v=>['serious','critical'].includes(v.impact||'')).length,violacoes:results.violations.map(v=>({id:v.id,impacto:v.impact}))},null,2));
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({path:`test-results/tela-${width}-${state}.png`,fullPage:true});
});
