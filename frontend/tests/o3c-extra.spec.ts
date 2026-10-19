import {test,expect} from '@playwright/test';
import law from '../mocks/lei-v14.json';
import {intercept} from './fixtures';

test('O3C extra carregamento legislativo explicito',async({page})=>{
  await intercept(page,'caged');await page.route('**/api/oil/lei',()=>{});
  await page.goto('/');await expect(page.getByTestId('lei-v14')).toContainText('Carregando dados da lei');
});
test('O3C extra divergencia e norma preenchida permanecem literais',async({page})=>{
  await intercept(page);await page.route('**/api/oil/lei',route=>route.fulfill({json:{...law,situacao_atual:{...law.situacao_atual,divergencia:true},norma_gerada:{rotulo:'Norma sintética de teste',data:'2026-10-16',fonte:'Senado — teste',link:'https://www.senado.leg.br/'}}}));
  await page.goto('/');const panel=page.getByTestId('lei-v14');await expect(panel).toContainText('As casas informam situações diferentes.');await expect(panel).toContainText('Norma sintética de teste');await panel.getByText('Saiba mais sobre a lei').click();for(const s of law.situacao)await expect(panel).toContainText(s.situacao);
});
test('O3C extra atribuicao unica e base legal no Caged',async({page})=>{
  await intercept(page,'caged');await page.goto('/');const card=page.getByTestId('card-caged-saldo');await expect(card).toContainText('Elaboração: OIL.');expect((await card.innerText()).match(/Fonte: Novo Caged/g)).toHaveLength(1);await card.getByText('Saiba mais',{exact:true}).click();await expect(card).toContainText('Uso livre e gratuito');await expect(card).toContainText('Série revisada mensalmente pelo MTE');await expect(card.getByRole('link',{name:/Decreto nº 8.777/})).toHaveAttribute('href',/planalto.gov.br/);
});
test('O3C extra atraso calendario e erro independente em todos indicadores',async({page})=>{
  await intercept(page,'caged');await page.route('**/api/oil/indicadores/**',async route=>{const response=await route.fetch();const data=await response.json();return route.fulfill({json:{...data,atrasado_calendario:true}});});
  // A resposta é gravada no interceptador anterior; não consulta fonte externa.
  await page.unroute('**/api/oil/indicadores/**');
  const {fixture}=await import('./fixtures');await page.route('**/api/oil/indicadores/**',route=>{const code=new URL(route.request().url()).pathname.split('/')[4];return route.fulfill({json:{...fixture(code),atrasado_calendario:true}});});
  await page.goto('/');for(const code of ['desocupacao','rendimento-real','caged-saldo'])await expect(page.getByTestId(`card-${code}`)).toContainText('Atraso no calendário');
});
