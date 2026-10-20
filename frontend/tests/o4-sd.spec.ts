import {test, expect, type Locator, type Page} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {intercept} from './fixtures';
import {scanLanguageBlocks} from './linguagem';
import law from '../mocks/lei-v14.json';

function contrast(foreground: string, background = '#ffffff') {
  const linear = (hex: string) => [0, 2, 4].map(offset => {
    const channel = parseInt(hex.replace('#', '').slice(offset, offset + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  const luminance = (hex: string) => {
    const [red, green, blue] = linear(hex);
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
  };
  const [lighter, darker] = [luminance(foreground), luminance(background)].sort((left, right) => right - left);
  return (lighter + 0.05) / (darker + 0.05);
}

async function openCaged(page: Page, valores?: Array<number | null>) {
  await intercept(page, 'caged', false, (data, code) => {
    if (code !== 'caged-saldo' || !valores) return;
    const template = (data.pontos as Array<Record<string, unknown>>)[0];
    const pontos = valores.map((valor, index) => ({
      ...template,
      periodo: `2026${String(index + 1).padStart(2, '0')}`,
      valor,
      lacuna: valor === null,
      ajuste: 'com_ajuste',
    }));
    const last = [...pontos].reverse().find(point => point.valor != null);
    Object.assign(data, {
      pontos,
      valor: last ? last.valor : null,
      periodo: last ? last.periodo : pontos.at(-1)!.periodo,
      disponivel: true,
      simulada: true,
    });
  });
  await page.goto('/');
  const card = page.getByTestId('card-caged-saldo');
  await expect(card.getByText('Dado de teste · simulado')).toBeVisible();
  await card.locator('.chart').scrollIntoViewIfNeeded();
  await expect(card.locator('.recharts-cartesian-grid')).toBeVisible();
  return card;
}

async function expectMarksInside(card: Locator, expected: number) {
  const marks = card.locator('.gap-mark');
  await expect(marks).toHaveCount(expected);
  const grid = await card.locator('.recharts-cartesian-grid').boundingBox();
  expect(grid).toBeTruthy();
  const boxes = [];
  for (const mark of await marks.all()) {
    await expect(mark).toBeVisible();
    await expect(mark).toHaveText('s/d');
    const fill = await mark.getAttribute('fill');
    expect(fill).toBeTruthy();
    expect(contrast(fill!)).toBeGreaterThanOrEqual(4.5);
    const box = await mark.boundingBox();
    expect(box).toBeTruthy();
    expect(box!.width).toBeGreaterThan(8);
    expect(box!.height).toBeGreaterThan(8);
    expect(box!.x).toBeGreaterThanOrEqual(grid!.x - 1);
    expect(box!.y).toBeGreaterThanOrEqual(grid!.y - 1);
    expect(box!.x + box!.width).toBeLessThanOrEqual(grid!.x + grid!.width + 1);
    expect(box!.y + box!.height).toBeLessThanOrEqual(grid!.y + grid!.height + 1);
    boxes.push(box!);
  }
  for (let left = 0; left < boxes.length; left++) {
    for (let right = left + 1; right < boxes.length; right++) {
      const a = boxes[left], b = boxes[right];
      const overlapX = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
      const overlapY = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
      expect(Math.max(0, overlapX) * Math.max(0, overlapY)).toBeLessThan(1);
    }
  }
  const bars = [];
  for (const bar of await card.locator('.recharts-bar-rectangle').all()) {
    const box = await bar.boundingBox();
    if (box && box.width > 0 && box.height > 0) bars.push(box);
  }
  for (const mark of boxes) {
    const cx = mark.x + mark.width / 2, cy = mark.y + mark.height / 2;
    for (const bar of bars) expect(cx > bar.x && cx < bar.x + bar.width && cy > bar.y && cy < bar.y + bar.height).toBe(false);
  }
  await expect(card.locator('.chart')).toHaveAttribute('aria-describedby', 'lacunas-caged-saldo');
  const list = card.locator('#lacunas-caged-saldo');
  await expect(list.locator('li')).toHaveCount(expected);
  for (const item of await list.locator('li').all()) await expect(item).toContainText(/^sem dado em /);
  await expect(card.locator('.chart')).toHaveAttribute('aria-label', /Há marcas sem dado no gráfico/);
}

async function expectTableKeepsNulls(card: Locator, valores: Array<number | null>) {
  await card.getByText('Saiba mais', {exact: true}).click();
  const rows = card.locator('tbody tr');
  await expect(rows).toHaveCount(valores.length);
  for (let index = 0; index < valores.length; index++) {
    const value = rows.nth(index).locator('td').nth(0);
    const gap = rows.nth(index).locator('td').nth(4);
    if (valores[index] === null) {
      await expect(value).toHaveText('sem dado');
      await expect(gap).toHaveText('sim');
    } else {
      await expect(value).not.toHaveText('sem dado');
      await expect(value).not.toHaveText('0');
      await expect(gap).toHaveText('não');
    }
  }
}

const cases = {
  'null no fim': [12, -6, 9, 4, null],
  'vários null no fim': [12, -6, 9, null, null, null],
  'null no início e no meio': [null, 12, null, -6, 9],
} as const;

for (const width of [1280, 360]) {
  for (const [name, valores] of Object.entries(cases)) {
    test(`marca s/d com ${name} em ${width}px`, async ({page}) => {
      await page.setViewportSize({width, height: 1000});
      const series = [...valores];
      const card = await openCaged(page, series);
      await expect(card.locator('.recharts-bar-rectangle')).toHaveCount(series.filter(valor => valor != null).length);
      await expectMarksInside(card, series.filter(valor => valor == null).length);
      const axe = await new AxeBuilder({page}).include('[data-testid="card-caged-saldo"]').analyze();
      expect(axe.violations.filter(violation => ['serious', 'critical'].includes(violation.impact || ''))).toEqual([]);
      await expectTableKeepsNulls(card, series);
      const markers = law.marcos.flatMap(marco => [marco.rotulo, marco.data]);
      expect(await scanLanguageBlocks(page, markers)).toEqual([]);
    });
  }

  test(`marca s/d de ajuste incompatível em ${width}px`, async ({page}) => {
    await page.setViewportSize({width, height: 1000});
    const card = await openCaged(page);
    await expect(card.locator('.recharts-bar-rectangle')).toHaveCount(1);
    await expectMarksInside(card, 2);
    await card.getByText('Saiba mais', {exact: true}).click();
    await expect(card.locator('tbody tr')).toHaveCount(3);
    await expect(card.locator('tbody td').nth(0)).not.toHaveText('0');
    await expect(card.locator('tbody td').nth(0)).not.toHaveText('sem dado');
    const axe = await new AxeBuilder({page}).include('[data-testid="card-caged-saldo"]').analyze();
    expect(axe.violations.filter(violation => ['serious', 'critical'].includes(violation.impact || ''))).toEqual([]);
  });
}
