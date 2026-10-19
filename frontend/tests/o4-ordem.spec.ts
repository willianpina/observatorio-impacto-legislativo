import {test,expect} from '@playwright/test';
import {intercept} from './fixtures';

test('O4 revisão ordem móvel e de leitura termina em Fontes e dados',async({page})=>{
  await page.setViewportSize({width:360,height:1000});await intercept(page,'caged',true);
  await page.goto('http://127.0.0.1:3102');await expect(page.getByTestId('card-desocupacao')).toContainText('Último dado');
  const ids=['lei','indicadores','evidencias','votacao','fontes'];
  expect(await page.locator('#panel-overview section[id]').evaluateAll((sections,wanted)=>sections.map(s=>s.id).filter(id=>wanted.includes(id)),ids)).toEqual(ids);
  const positions=[];for(const id of ids)positions.push((await page.locator(`#${id}`).boundingBox())!.y);
  expect(positions).toEqual([...positions].sort((a,b)=>a-b));
});
