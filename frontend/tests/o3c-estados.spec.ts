import {test,expect} from '@playwright/test';
import {intercept} from './fixtures';
for(const code of ['desocupacao','rendimento-real','caged-saldo'])for(const state of ['loading','error','unavailable','stale','calendar'])test(`O3C estados ${code} ${state}`,async({page})=>{
  await intercept(page,'caged',false,(data,received)=>{if(received!==code)return;if(state==='unavailable')Object.assign(data,{disponivel:false,motivo:'Fonte em verificação.',pontos:[]});if(state==='stale')data.desatualizado=true;if(state==='calendar')data.atrasado_calendario=true;});
  if(state==='loading')await page.route(`**/api/oil/indicadores/${code}/serie?*`,()=>{});
  if(state==='error')await page.route(`**/api/oil/indicadores/${code}/serie?*`,route=>route.fulfill({status:503,headers:{'Retry-After':'37'},json:{erro:{fonte:code,tentar_novamente_em:37}}}));
  await page.goto('/');const card=page.getByTestId(`card-${code}`);
  await expect(card).toContainText(state==='loading'?'Carregando dados':state==='error'?'37 segundos':state==='unavailable'?'Fonte em verificação.':state==='stale'?/última coleta válida/i:'Atraso no calendário');
  if(['loading','error','unavailable'].includes(state))await expect(card.getByTestId(`valor-atual-${code}`)).toHaveCount(0);
});
test('O3C estados selo depende do payload e nao do modo da pagina',async({page})=>{
  await intercept(page,'caged',true);await page.goto('/');for(const code of ['desocupacao','rendimento-real','caged-saldo']){const card=page.getByTestId(`card-${code}`);await expect(card.getByTestId(`valor-atual-${code}`)).toBeVisible();await expect(card.locator('.test-badge')).toHaveCount(0);}
});
