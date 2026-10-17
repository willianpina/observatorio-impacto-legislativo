import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { intercept } from './fixtures';

const warning = 'É cedo para afirmar. A emenda começa a valer em etapas, e os dados oficiais saem com atraso. Mudanças nos indicadores podem ter várias causas.';
const legend = 'Marcos de calendário. Não indicam efeito da lei.';

test.beforeEach(async ({page}) => intercept(page));

test('aviso exato, origem e dado de teste; indicador sem tipo monetário', async ({page}) => {
  await page.goto('/');
  await expect(page.getByText(warning, {exact:true})).toBeVisible();
  await expect(page.getByText('MODO DE TESTE — dados simulados, não são reais')).toBeVisible();
  await expect(page.getByTestId('card-desocupacao').getByRole('heading', {name:'Taxa de desocupação',exact:true})).toBeVisible();
  await expect(page.getByTestId('card-desocupacao')).toContainText('p.p.');
  await expect(page.getByTestId('card-rendimento-real')).toContainText('Real, base de preços do IBGE em verificação');
  await expect(page.getByTestId('card-desocupacao')).not.toContainText('Nominal');
  await expect(page.getByText('Transformado em Norma Jurídica',{exact:true})).toBeVisible();
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
  await page.getByLabel('Período dos gráficos').selectOption('2a');
  await expect(insight).toHaveText(text);
  await page.getByLabel('Período dos gráficos').selectOption('desde_2020');
  await expect(insight).toHaveText(text);
});

for (const state of ['gap','error','stale','empty','unclassified']) test(`estado ${state}`, async ({page}) => {
  await page.unroute('**/api/oil/indicadores/**'); await intercept(page,state); await page.goto('/');
  const card=page.getByTestId('card-desocupacao');
  if(state==='gap') { await card.getByText('Saiba mais',{exact:true}).click(); await expect(card.getByText('sem dado',{exact:true})).toBeVisible(); await expect(card.locator('.recharts-line-curve')).toHaveAttribute('d',/M.*M/); }
  if(state==='error') { await expect(card.getByRole('button',{name:'Tentar de novo'})).toBeVisible(); await expect(page.getByTestId('card-rendimento-real')).toContainText('Último dado'); }
  if(state==='stale') await expect(card).toContainText('Fonte fora do ar. Mostrando a última coleta válida');
  if(state==='empty') await expect(card).toContainText('Ainda não há dados');
  if(state==='unclassified') await expect(card).not.toContainText('calculado pelo Observatório');
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
  await expect(card).toContainText('arquivo 08/2026, licença CC BY-ND 3.0');
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
  await expect(page.getByText('Art. 6º, I',{exact:false}).first()).toBeVisible();
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
  await page.route('**/api/oil/lei',async route=>{
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
  const text=await page.locator('body').evaluate(el=>{const copy=el.cloneNode(true) as HTMLElement;copy.querySelectorAll('script,style').forEach(node=>node.remove());return copy.textContent||'';});
  const attributes=await page.locator('[aria-label],[title],[alt]').evaluateAll(els=>els.map(e=>[e.getAttribute('aria-label'),e.getAttribute('title'),e.getAttribute('alt')].join(' ')).join(' '));
  const corpus=(text.split(legend).join('')+' '+attributes).toLocaleLowerCase('pt-BR');
  for(const phrase of ['causou','graças a','por causa da lei','depois da aprovação','desde a promulgação','efeito da lei','após a vigência']) expect(corpus).not.toContain(phrase);
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
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({path:`test-results/tela-${width}-${state}.png`,fullPage:true});
});
