// Verificação opt-in: somente API local com coletas reais; sem fixtures ou interceptação.
import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
const browser=await chromium.launch({channel:process.env.OIL_BROWSER_CHANNEL || 'msedge'});
const results={real:true,executado_em:new Date().toISOString(),series:[],axe:[]};
try {
  const context=await browser.newContext();
  const page=await context.newPage();
  for(const code of ['desocupacao','rendimento-real']){
    const response=await page.request.get(`http://127.0.0.1:3100/api/oil/indicadores/${code}/serie?janela=5a`);
    const data=await response.json();
    if(!response.ok()||!data.disponivel||data.simulada||data.pontos.length<8)throw Error(`Integração real não aprovada: ${code}`);
    results.series.push({codigo:code,valor:data.valor,cv:data.cv,periodo:data.periodo,unidade:data.unidade,fonte:data.fonte,link:data.link,coleta_id:data.coleta_id,coletado_em:data.coletado_em,pontos:data.pontos.length});
  }
  await fs.mkdir('evidencias',{recursive:true});
  for(const width of [360,1280]){
    await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:3100');
    await page.getByTestId('card-desocupacao').getByTestId('insight-desocupacao').waitFor();
    for(const s of results.series){await expect(page.getByTestId(`card-${s.codigo}`)).toContainText(new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(s.valor));}
    const scan=await new AxeBuilder({page}).analyze();const severe=scan.violations.filter(v=>['serious','critical'].includes(v.impact));
    results.axe.push({width,graves_criticas:severe.length});
    if(severe.length)throw Error('Acessibilidade real pendente.');
    await page.screenshot({path:`evidencias/real-${width}.png`,fullPage:true});
  }
  await fs.writeFile('evidencias/validacao-real.json',JSON.stringify(results,null,2));
  console.log(JSON.stringify(results,null,2));
}finally{await browser.close();}
