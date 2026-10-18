import {test,expect} from '@playwright/test';
import * as language from './linguagem';
import type {Page} from '@playwright/test';

for(const [id,sentence] of [
  ['FC4','A partir da promulgação, a desocupação caiu.'],
  ['FC5','Em 14/10, a desocupação caiu.'],
  ['FD3','Compare antes e depois de 16/10/2026.']
])test(`O3R ${id}: guarda reconhece a sonda`,()=>{
  expect(language.languageViolations(sentence)).not.toEqual([]);
});

for(const tag of ['summary','li','strong','span','small','dd','dt','label','button','caption'])test(`O3R bloco ${tag}: data e variação são detectadas`,async({page})=>{
  const scan=(language as unknown as {scanLanguageBlocks?:(page:Page)=>Promise<string[]>}).scanLanguageBlocks;
  expect(typeof scan).toBe('function');
  await page.setContent(`<${tag}>Em 14/10/2026, a desocupação caiu</${tag}>`);
  expect(await scan!(page)).not.toEqual([]);
});

test('O3R blocos separados não criam associação textual',async({page})=>{
  const scan=(language as unknown as {scanLanguageBlocks?:(page:Page)=>Promise<string[]>}).scanLanguageBlocks;
  expect(typeof scan).toBe('function');
  await page.setContent('<p>Aprovação em 14/10/2026.</p><p>A desocupação caiu.</p>');
  expect(await scan!(page)).toEqual([]);
});
