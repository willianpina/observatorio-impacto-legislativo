import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import {intercept} from './fixtures';
import {TITLES} from '../lib/types';
import {languageViolations,scanLanguageBlocks} from './linguagem';

const codes=['desocupacao','rendimento-real','caged-saldo'];
for(const code of codes){
  test(`O4 revisão resumo indisponível ${code} preserva motivo`,async({page})=>{
    await intercept(page,'caged',false,(data,received)=>{if(received===code)Object.assign(data,{disponivel:false,motivo:'Arquivo oficial em verificação.',pontos:[]});});
    await page.goto('/');const summary=page.getByTestId(`resumo-${code}`);
    await expect(summary).toContainText('Arquivo oficial em verificação.');
    await expect(summary.locator('[data-testid^="resumo-valor-atual-"]')).toHaveCount(0);
  });
  test(`O4 revisão resumo vazio ${code} não mostra valor`,async({page})=>{
    await intercept(page,'caged',false,(data,received)=>{if(received===code)data.pontos=[];});
    await page.goto('/');const summary=page.getByTestId(`resumo-${code}`);
    await expect(page.getByTestId(`card-${code}`)).toContainText('Ainda não há dados');
    await expect(summary).toContainText('Ainda não há dados');
    await expect(summary.locator('[data-testid^="resumo-valor-atual-"]')).toHaveCount(0);
  });
  test(`O4 revisão resumo ${code} mostra fonte link BRT e selo do payload`,async({page})=>{
    await intercept(page,'caged');await page.goto('/');const summary=page.getByTestId(`resumo-${code}`);
    await expect(summary.locator('.source')).toHaveCount(1);
    await expect(summary.locator('.source')).toContainText('Fonte:');
    await expect(summary.locator('.source')).toContainText(/Coletado em \d{2}\/\d{2}\/\d{4}, \d{2}:\d{2} \(BRT\)/);
    await expect(summary.locator('.source a')).toHaveAttribute('href',/^https:\/\//);
    await expect(summary.locator('.test-badge')).toContainText('Dado de teste');
  });
}

test('O4 revisão resumo preserva os sinais de coleta e calendário',async({page})=>{
  await intercept(page,'caged',false,data=>Object.assign(data,{desatualizado:true,atrasado_calendario:true}));
  await page.goto('/');for(const code of codes){const summary=page.getByTestId(`resumo-${code}`);await expect(summary).toContainText('Mostrando a última coleta válida');await expect(summary).toContainText('Atraso no calendário');}
});

test('O4 revisão fontes distingue falha de conexão de ausência de dados',async({page})=>{
  await intercept(page,'error');await page.goto('/');
  const source=page.locator('#fontes article').filter({has:page.getByRole('heading',{name:TITLES.desocupacao,exact:true})});
  await expect(source).toContainText('Fonte indisponível');
  await expect(source).not.toContainText('Dado ainda não disponível');
});

test('O4 revisão rodapé usa a coleta mais recente mesmo se índice for antigo',async({page})=>{
  await intercept(page,'caged',false,(data,code)=>{if(code==='caged-saldo')data.coletado_em='2026-10-18T15:00:00-03:00';});
  await page.route('**/api/oil/indicadores?*',route=>route.fulfill({json:{indicadores:[],coletado_em:'2026-10-16T15:00:00-03:00',simulada:true}}));
  await page.goto('/');await expect(page.getByTestId('card-caged-saldo')).toContainText('18/10/2026');
  await expect(page.locator('footer')).toContainText('Última coleta: 18/10/2026, 15:00 (BRT)');
});

for(const width of [360,1280])for(const state of ['normal','gap','unavailable','stale','test'])test(`O4 revisão captura fixture ${width} ${state}`,async({page})=>{
  await page.setViewportSize({width,height:1000});
  const normal=state!=='test';
  await intercept(page,'caged',normal,(data,code)=>{
    if(state==='unavailable'&&code==='caged-saldo')Object.assign(data,{disponivel:false,motivo:'Fonte sem arquivo válido.',pontos:[]});
    if(state==='stale')data.desatualizado=true;
    if(state==='gap'&&code==='desocupacao'&&Array.isArray(data.pontos))data.pontos[20]={...data.pontos[20],valor:null,lacuna:true};
  });
  await page.goto(normal?'http://127.0.0.1:3102':'/');
  await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  if(state==='unavailable')await expect(page.getByTestId('card-caged-saldo')).toContainText('Fonte sem arquivo válido.');
  if(state==='stale')await expect(page.getByTestId('card-desocupacao')).toContainText('Mostrando a última coleta válida');
  if(state==='test')await expect(page.locator('.test-banner')).toBeVisible();else await expect(page.locator('.test-banner')).toHaveCount(0);
  for(const detail of await page.locator('details.more > summary').all())await detail.click();
  if(state==='gap')await expect(page.getByTestId('card-desocupacao').getByRole('cell',{name:'sem dado',exact:true}).first()).toBeVisible();
  const axe=await new AxeBuilder({page}).analyze();const severe=axe.violations.filter(v=>['serious','critical'].includes(v.impact||''));expect(severe).toEqual([]);
  expect(await scanLanguageBlocks(page)).toEqual([]);
  expect(languageViolations(await page.locator('body').innerText())).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:`test-results/o4-revisao-${width}-${state}-fixture.png`,fullPage:true});
  await fs.writeFile(`test-results/o4-revisao-axe-${width}-${state}.json`,JSON.stringify({fixture:true,rede_oficial:false,estado:state,width,detalhes_abertos:true,graves_criticas:severe.length,violacoes:axe.violations.map(v=>({id:v.id,impacto:v.impact}))},null,2));
});
