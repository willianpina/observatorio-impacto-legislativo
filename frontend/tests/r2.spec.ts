import {test,expect} from '@playwright/test';
import fs from 'node:fs/promises';
import {fixture,intercept} from './fixtures';

const summary='Em vigor desde 16/10/2026, data da publicação, exceto: repouso de 2 dias por semana e limite de 42 h semanais a partir de 16/12/2026 (prevista); limite de 40 h semanais a partir de 16/12/2027 (prevista).';
test.beforeEach(async({page})=>{await intercept(page);await page.clock.setFixedTime(new Date('2026-10-17T15:00:00Z'));});

test('R2-1 modo normal recusa série simulada: sem valor nem gráfico',async({page})=>{
  await page.goto('http://127.0.0.1:3102');
  for(const code of ['desocupacao','rendimento-real']){
    const card=page.getByTestId(`card-${code}`);
    await expect(card).toContainText('Resposta de teste recusada no modo normal.');
    await expect(card.getByTestId(`valor-atual-${code}`)).toHaveCount(0);
    await expect(card.locator('.recharts-wrapper')).toHaveCount(0);
    await expect(page.getByTestId(`resumo-${code}`)).toContainText('Dado ainda não disponível');
  }
});

test('R2-2 CSV conserva -10 numérico e neutraliza =1+1 e -x textuais',async({page})=>{
  await page.unroute('**/api/oil/indicadores/**');await intercept(page,'csv');
  await page.goto('/');const card=page.getByTestId('card-caged-saldo');await expect(card).toContainText('-10 postos de trabalho');
  await card.getByText('Saiba mais',{exact:true}).click();
  const downloading=page.waitForEvent('download');await card.getByRole('button',{name:'Baixar CSV'}).click();
  const csv=await fs.readFile((await(await downloading).path())!,'utf8');
  expect(csv).toContain(';"-10";');expect(csv).not.toContain(';"\'-10";');expect(csv).toContain("\"'=1+1\"");expect(csv).toContain("\"'-x\"");
});

test('R2-3 vigência exata, artigos e fontes nos detalhes',async({page})=>{
  await page.goto('/');await expect(page.getByTestId('vigencia-resumo')).toHaveText(summary);
  await page.getByText('Saiba mais sobre a vigência',{exact:true}).click();const block=page.locator('.vigencia');
  await expect(block).toContainText('As datas previstas foram calculadas a partir da publicação (2 meses e mais 1 ano), conforme o Art. 6º e o Art. 10 da EC. O texto da emenda não traz as datas por extenso.');
  await expect(block.locator('li').nth(1)).toContainText('16/12/2026 (prevista) · Art. 10, I; Art. 6º, I');
  await expect(block.locator('li').nth(2)).toContainText('16/12/2027 (prevista) · Art. 6º, II');
  await expect(block.getByRole('link')).toHaveCount(2);
});

test('R2-3 vigência sem prevista após a data e no dia exato',async({page})=>{
  await page.clock.setFixedTime(new Date('2027-12-16T15:00:00Z'));await page.goto('/');
  await expect(page.getByTestId('vigencia-resumo')).toContainText('Em vigor desde 16/10/2026');
  await expect(page.getByTestId('vigencia-resumo')).not.toContainText('(prevista)');
});

test('R2-3 mudar vigência no dado muda a tela; publicação nunca é prevista',async({page})=>{
  await page.route('**/api/oil/exemplo',async route=>{
    const body=await(await route.fetch()).json();const v=body.dados.vigencia;
    v.data_publicacao='2026-11-01';v.etapas[0].data_inicio='2027-01-01';v.etapas[0].descricao='etapa alterada';v.etapas[1].data_tipo='expressa';
    await route.fulfill({json:body});
  });
  await page.goto('/');const text=page.getByTestId('vigencia-resumo');
  await expect(text).toContainText('Em vigor desde 01/11/2026, data da publicação');
  await expect(text).toContainText('etapa alterada a partir de 01/01/2027 (prevista)');
  await expect(text).not.toContainText('01/11/2026 (prevista)');
  await expect(text).not.toContainText('16/12/2027 (prevista)');
});

test('R2-4 fixture trimestral mostra Trimestral e trimestre de calendário',async({page})=>{
  await page.unroute('**/api/oil/indicadores/**');await intercept(page,'trimestral');await page.goto('/');
  const card=page.getByTestId('card-desocupacao');await expect(card.locator('.metadata')).toContainText('Trimestral');
  await expect(card.locator('.metadata')).not.toContainText('Mensal');await expect(card.getByTestId('insight-desocupacao')).toContainText('2º trimestre de 2026');
});

test('R2-6 foco por Tab no marco revela fonte e link sem clique',async({page})=>{
  await page.goto('/');const card=page.getByTestId('card-desocupacao');await expect(card).toContainText('Último dado');
  const marker=card.locator('.marker-list details').first();await expect(marker).not.toHaveAttribute('open');
  await card.locator('.indicator-help summary').focus();await page.keyboard.press('Tab');
  await expect(marker.locator('summary')).toBeFocused();await expect(marker).toHaveAttribute('open','');
  const link=marker.getByRole('link',{name:'Fonte do marco: Senado',exact:true});await expect(link).toBeVisible();
  await page.keyboard.press('Tab');await expect(link).toBeFocused();await expect(link).toHaveAttribute('href',/^https:\/\/legis\.senado\.leg\.br/);
  await page.keyboard.press('Tab');await expect(marker).not.toHaveAttribute('open');
});

test('O3 card e resumo preservam rendimento não inteiro',async({page})=>{
  await page.route('**/api/oil/indicadores/rendimento-real/serie?*',async route=>{
    const body={...fixture('rendimento-real'),valor:3777.25};
    await route.fulfill({json:body});
  });
  await page.goto('/');
  await expect(page.getByTestId('valor-atual-rendimento-real')).toHaveText('R$ 3.777,25');
  await expect(page.getByTestId('resumo-valor-atual-rendimento-real')).toHaveText('R$ 3.777,25');
});

test('marco continua expansível e recolhível por clique',async({page})=>{
  await page.goto('/');const marker=page.getByTestId('card-desocupacao').locator('.marker-list details').first();
  const summary=marker.locator('summary');await summary.click();await expect(marker).toHaveAttribute('open','');
  await summary.click();await expect(marker).not.toHaveAttribute('open');
});

for(const code of ['desocupacao','rendimento-real'])test(`R2-9 card e resumo têm o mesmo valor: ${code}`,async({page})=>{
  await page.goto('/');const value=page.getByTestId(`card-${code}`).getByTestId(`valor-atual-${code}`);await expect(value).toBeVisible();
  await expect(page.getByTestId(`resumo-valor-atual-${code}`)).toHaveText((await value.textContent())!);
});
