import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import {intercept} from './fixtures';

for(const [casa,sim,quorum,resultado,approved] of [
  ['camara',307,308,'Aprovada',false],['camara',308,308,'Aprovada',true],
  ['senado',48,49,'Aprovada',false],['senado',49,49,'Aprovada',true],
  ['camara',400,308,'Não aprovada',false],['camara',400,308,' NÃO APROVADA ',false],
  ['camara',300,257,'Aprovada',false],['senado',48,41,'Aprovada',false],
] as const)test(`O4 correção placar ${casa} ${sim} quorum ${quorum} ${resultado}`,async({page})=>{
  await intercept(page);
  await page.route('**/api/oil/exemplo',async route=>{
    const body=await(await route.fetch()).json();const vote=body.dados.votacoes[0];
    Object.assign(vote,{casa,resultado,quorum_exigido:quorum,placar_conferido:true,inconsistencia:null,votos_por_partido:null,placar:{sim,nao:0,abstencao:0,total:sim,obstrucao:0,ausentes:null}});
    await route.fulfill({json:body});
  });
  await page.goto('/');const vote=page.getByTestId('vote-2233802-424');
  await expect(vote).toContainText(`Quórum exigido: ${casa==='camara'?308:49}`);
  await expect(vote.getByText('Aprovada',{exact:true})).toHaveCount(approved?1:0);
});

for(const width of [360,1280])test(`O4 correção B8 rotulado e CSV ${width}`,async({page})=>{
  await page.setViewportSize({width,height:1000});await intercept(page,'caged');await page.goto('/');
  const sources=page.locator('#fontes');await expect(sources.locator('.evidence-card')).toHaveCount(7);
  for(const card of await sources.locator('.evidence-card').all()){
    for(const label of ['O que fornece','Tabela/ID','Situação'])await expect(card.locator('dt').filter({hasText:label})).toHaveCount(1);
    await expect(card.locator('h3')).not.toContainText('https://');
  }
  const downloads=sources.getByRole('button',{name:/Baixar CSV/});await expect(downloads).toHaveCount(7);
  const pending=page.waitForEvent('download');await downloads.first().click();expect((await pending).suggestedFilename()).toMatch(/\.csv$/);
  await sources.scrollIntoViewIfNeeded();await sources.screenshot({path:`test-results/o4-correcao-b8-${width}-fixture.png`});
  const axe=await new AxeBuilder({page}).include('#fontes').analyze();expect(axe.violations.filter(v=>['serious','critical'].includes(v.impact||''))).toEqual([]);
  await fs.writeFile(`test-results/o4-correcao-axe-${width}.json`,JSON.stringify({fixture:true,width,violacoes:axe.violations.map(v=>({id:v.id,impact:v.impact}))},null,2));
});

test('O4 correção cabeçalho liga a proposição e barras marcam lacuna',async({page})=>{
  await intercept(page,'caged');await page.goto('/');
  await expect(page.locator('.hero').getByRole('link',{name:'PEC 221/2019',exact:true})).toHaveAttribute('href','https://www.camara.leg.br/propostas-legislativas/2233802');
  await expect(page.getByTestId('card-caged-saldo').locator('.chart').getByText('s/d',{exact:true}).first()).toBeVisible();
});
