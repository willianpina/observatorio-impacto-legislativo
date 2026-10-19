import {test,expect} from '@playwright/test';
import {scanLanguageBlocks} from './linguagem';

test('O3C div próprio detecta data e variação',async({page})=>{
  await page.setContent('<section><div>Em 14/10/2026, a desocupação caiu.</div></section>');
  expect(await scanLanguageBlocks(page)).not.toEqual([]);
});

test('O3C div não une textos de filhos distintos',async({page})=>{
  await page.setContent('<div><p>Em 14/10/2026.</p><p>A desocupação caiu.</p></div>');
  expect(await scanLanguageBlocks(page)).toEqual([]);
});
