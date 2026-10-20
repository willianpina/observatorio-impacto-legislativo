import {test, expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import {intercept} from './fixtures';

const TEXTO_FIXO = 'Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes). Série revisada mensalmente. Elaboração: OIL.';
const BASE_LEGAL = 'Decreto 8.777/2016, art. 4º';
const LINK = 'https://www.gov.br/trabalho-e-emprego/pt-br';

function frase(arquivo: string, data: string) {
  return `Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo ${arquivo}, coletado em ${data}. Série revisada mensalmente. Elaboração: OIL.`;
}

function atribuicao(arquivo: string | null, coletado: string | null) {
  return {texto: TEXTO_FIXO, link: LINK, base_legal: BASE_LEGAL, arquivo_referencia: arquivo, coletado_em: coletado};
}

async function abrir(page: import('@playwright/test').Page, width: number, corpo: ReturnType<typeof atribuicao>, extra?: (data: Record<string, unknown>) => void) {
  await page.setViewportSize({width, height: width === 360 ? 900 : 1000});
  await intercept(page, 'caged', false, (data, code) => {
    if (code !== 'caged-saldo') return;
    Object.assign(data, {atribuicao: corpo, link: corpo.link, coletado_em: corpo.coletado_em});
    extra?.(data);
  });
  await page.goto('/');
  await expect(page.locator('.test-banner')).toContainText('MODO DE TESTE');
  const card = page.getByTestId('card-caged-saldo');
  await expect(card.locator('.test-badge')).toContainText('Dado de teste');
  return card;
}

for (const width of [1280, 360]) {
  test(`v1.5.0 frase com mês do arquivo e data em Brasília, ${width}px`, async ({page}) => {
    const card = await abrir(page, width, atribuicao('2026-08', '2026-10-17T14:22:00Z'));
    const esperada = frase('agosto/2026', '17/10/2026');
    await expect(card.locator('.source a')).toHaveText(esperada);
    await expect(card.locator('.source a')).toHaveAttribute('href', LINK);
    expect((await card.innerText()).match(/Fonte: Novo Caged/g)).toHaveLength(1);
    await expect(card.getByText('Saldo com ajustes', {exact: true})).toBeVisible();
    await expect(card.getByText('Descritivo', {exact: true})).toBeVisible();
    await expect(page.getByText('É cedo para afirmar', {exact: false}).first()).toBeVisible();
    await expect(card.locator('.chart').getByText('s/d', {exact: true}).first()).toBeVisible();
    await card.getByText('Saiba mais', {exact: true}).click();
    await expect(card.getByTestId('caged-base-legal')).toHaveText(BASE_LEGAL);
    await expect(card).toContainText('revisadas mensalmente');
    await expect(card.locator('.source a')).toHaveAttribute('href', LINK);
    await expect(card.getByRole('link', {name: /Decreto/})).toHaveCount(0);
    const hrefs = await card.locator('a').evaluateAll(els => els.map(el => el.getAttribute('href')));
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(href).toBeTruthy();
      expect(href).not.toBe('undefined');
      expect(href).not.toMatch(/^javascript:/);
    }
    const tela = (await page.locator('body').innerText()).toLocaleLowerCase('pt-BR');
    expect(tela).not.toContain('cc by');
    expect(tela).not.toMatch(/licen[cç]a/);
    await card.screenshot({path: `test-results/v150-frase-${width}.png`});
    const axe = await new AxeBuilder({page}).analyze();
    const graves = axe.violations.filter(v => ['serious', 'critical'].includes(v.impact || ''));
    expect(graves).toEqual([]);
    await fs.writeFile(`test-results/v150-axe-${width}.json`, JSON.stringify({
      fixture: true, largura: width, graves_criticas: graves.length,
      violacoes: axe.violations.map(v => ({id: v.id, impacto: v.impact})),
    }, null, 2));
  });

  test(`v1.5.0 coleta perto da meia-noite UTC muda o dia em Brasília, ${width}px`, async ({page}) => {
    const card = await abrir(page, width, atribuicao('2026-08', '2026-10-20T01:30:00Z'));
    await expect(card.locator('.source a')).toHaveText(frase('agosto/2026', '19/10/2026'));
    await expect(card.locator('.source a')).not.toContainText('20/10/2026');
  });

  test(`v1.5.0 série desatualizada mantém mês e data da coleta, ${width}px`, async ({page}) => {
    const card = await abrir(page, width, atribuicao('2026-08', '2026-10-17T14:22:00Z'), data => {
      data.desatualizado = true;
    });
    const esperada = frase('agosto/2026', '17/10/2026');
    await expect(card.locator('.notice')).toHaveText('Fonte fora do ar. Mostrando a última coleta válida de 17/10/2026');
    await expect(card.locator('.source a')).toHaveText(esperada);
    await expect(card.locator('.source a')).not.toContainText('s/d');
    await expect(card.locator('.source a')).not.toContainText('20/10/2026');
    await expect(card.locator('.source a')).toHaveAttribute('href', LINK);
    const resumo = page.getByTestId('resumo-caged-saldo');
    await expect(resumo.locator('.notice')).toHaveText('Fonte fora do ar. Mostrando a última coleta válida de 17/10/2026');
    await expect(resumo.locator('.source a')).toHaveText(esperada);
    await expect(resumo.locator('.source a')).not.toContainText('s/d');
    await card.screenshot({path: `test-results/v150-desatualizado-${width}.png`});
  });

  test(`v1.5.0 arquivo ou coleta nulos mostram s/d, ${width}px`, async ({page}) => {
    const card = await abrir(page, width, atribuicao(null, null), data => {
      data.disponivel = true;
    });
    await expect(card.locator('.source a')).toHaveText(frase('s/d', 's/d'));
    await expect(card.locator('.source a')).not.toContainText(/\d{2}\/\d{2}\/\d{4}/);
    await expect(card.locator('.source a')).toHaveAttribute('href', LINK);
    await card.screenshot({path: `test-results/v150-sd-${width}.png`});

    await page.unroute('**/api/oil/indicadores/**');
    await intercept(page, 'normal', false, (data, code) => {
      if (code !== 'caged-saldo') return;
      Object.assign(data, {
        disponivel: false,
        motivo: 'Fonte oficial do Novo Caged em verificação.',
        pontos: [],
        atribuicao: atribuicao(null, null),
        link: LINK,
        coletado_em: null,
      });
    });
    await page.goto('/');
    const cardVazio = page.getByTestId('card-caged-saldo');
    await expect(cardVazio).toContainText('Dado ainda não disponível');
    await expect(cardVazio.locator('.source a')).toHaveCount(0);
    const resumo = page.getByTestId('resumo-caged-saldo');
    await expect(resumo.locator('.source a')).toHaveText(frase('s/d', 's/d'));
    await expect(resumo.locator('.source a')).not.toContainText(/\d{2}\/\d{2}\/\d{4}/);
  });
}

test('v1.5.0 um campo nulo não apaga o outro', async ({page}) => {
  const soData = await abrir(page, 1280, atribuicao(null, '2026-10-17T14:22:00Z'));
  await expect(soData.locator('.source a')).toHaveText(frase('s/d', '17/10/2026'));
  await page.unroute('**/api/oil/indicadores/**');
  const soArquivo = await abrir(page, 1280, atribuicao('2026-07', null));
  await expect(soArquivo.locator('.source a')).toHaveText(frase('julho/2026', 's/d'));
  await expect(soArquivo.locator('.source a')).not.toContainText(/\d{2}\/\d{2}\/\d{4}/);
});
