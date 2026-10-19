import {test,expect} from '@playwright/test';
import {intercept} from './fixtures';
import lawFixture from '../mocks/lei-v14.json';

for(const source of ['proposicao','casa','referencia'])test(`O4 revisão rodapé inclui coleta legislativa ${source}`,async({page})=>{
  await intercept(page,'caged',true);
  const data=structuredClone(lawFixture);data.simulada=false;
  if(source==='proposicao')data.coletado_em='2026-10-19T12:00:00-03:00';
  if(source==='casa')data.situacao[0].coletado_em='2026-10-19T12:00:00-03:00';
  if(source==='referencia')data.fontes_norma[0].coletado_em='2026-10-19T12:00:00-03:00';
  await page.route('**/api/oil/lei',route=>route.fulfill({json:data}));
  await page.goto('http://127.0.0.1:3102');await expect(page.locator('#lei')).toContainText('19/10/2026');
  await expect(page.locator('footer')).toContainText('Última coleta: 19/10/2026, 12:00 (BRT)');
});
