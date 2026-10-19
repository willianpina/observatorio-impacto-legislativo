import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import law from '../mocks/lei-v14.json';
import {intercept} from './fixtures';
import {scanLanguageBlocks,languageViolations} from './linguagem';

async function setup(page:import('@playwright/test').Page,state='normal',simulada=true){
  await intercept(page,'caged');
  await page.route('**/api/oil/lei',async route=>{
    if(state==='error')return route.fulfill({status:503,headers:{'Retry-After':'45'},json:{erro:{fonte:'API local',mensagem:'Fonte temporariamente indisponível',tentar_novamente_em:45}}});
    if(state==='unavailable')return route.fulfill({json:{disponivel:false,motivo:'Fonte legislativa em verificação.',simulada}});
    return route.fulfill({json:{...law,simulada,desatualizado:state==='stale'}});
  });
}
test('O3C lei v14 mostra texto literal, autoria, situacao e linhagem',async({page})=>{
  await setup(page);await page.goto('/');const panel=page.getByTestId('lei-v14');
  await expect(panel).toContainText('Ementa (texto da fonte)');await expect(panel).toContainText(law.ementa!);
  await expect(panel).toContainText(law.autor!);await expect(panel).toContainText(law.partido!);await expect(panel).toContainText(law.uf!);
  await expect(panel).toContainText('apresentacao');await expect(panel).toContainText(law.autoria_motivo!);
  await expect(panel).toContainText(law.situacao_atual.situacao);await expect(panel).toContainText(law.norma_gerada_motivo!);
  await panel.getByText('Saiba mais sobre a lei',{exact:true}).click();
  for(const marker of law.marcos){await expect(panel).toContainText(marker.rotulo);await expect(panel).toContainText(marker.origem);}
  await expect(panel).toContainText('Coletado em');await expect(panel).toContainText('(BRT)');
});
test('O3C lei sem simulacao nao tem selo nem vigencia inventada',async({page})=>{
  await setup(page,'normal',false);await page.goto('http://127.0.0.1:3102');const panel=page.getByTestId('lei-v14');
  await expect(panel).toContainText('Ementa (texto da fonte)');await expect(panel.getByText('Dado de teste',{exact:true})).toHaveCount(0);
  await expect(panel).toContainText('Dado ainda não disponível');await expect(page.locator('#votacao')).toContainText('As votações entram numa próxima etapa');
});
for(const state of ['error','unavailable','stale'])test(`O3C lei estado ${state}`,async({page})=>{
  await setup(page,state);await page.goto('/');const panel=page.getByTestId('lei-v14');
  await expect(panel).toContainText(state==='error'?'45 segundos':state==='unavailable'?'Fonte legislativa em verificação.':'Última coleta válida');
});
test('O3C resumo e cards mantem os mesmos numeros',async({page})=>{
  await setup(page);await page.goto('/');for(const code of ['desocupacao','rendimento-real','caged-saldo']){
    const card=page.getByTestId(`card-${code}`);await expect(card.getByTestId(`valor-atual-${code}`)).toBeVisible();
    expect(await page.getByTestId(`resumo-valor-atual-${code}`).innerText()).toBe(await card.getByTestId(`valor-atual-${code}`).innerText());
  }
});
for(const width of [360,1280])for(const state of ['normal','unavailable','error'])test(`O3C axe ${width} ${state} detalhes abertos`,async({page})=>{
  await page.setViewportSize({width,height:1000});await setup(page,state);await page.goto('/');
  await expect(page.getByTestId('lei-v14')).toBeVisible();await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  for(const details of await page.locator('details').all())await details.evaluate(el=>(el as HTMLDetailsElement).open=true);
  const scan=await new AxeBuilder({page}).analyze();const severe=scan.violations.filter(v=>['serious','critical'].includes(v.impact!));
  await fs.writeFile(`test-results/o3c-axe-${width}-${state}.json`,JSON.stringify({width,state,graves_criticas:severe.length,violacoes:severe.map(v=>v.id)}));
  expect(severe).toEqual([]);expect(await scanLanguageBlocks(page)).toEqual([]);expect(languageViolations(await page.locator('body').innerText())).toEqual([]);
});
