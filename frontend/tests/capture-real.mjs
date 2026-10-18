// Verificação opt-in: somente API local com coletas reais; sem fixtures ou interceptação.
import {chromium,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
const browser=await chromium.launch({channel:process.env.OIL_BROWSER_CHANNEL || 'msedge'});
const results={real:true,executado_em:new Date().toISOString(),series:[],lei:null,axe:[],falhas:[],aprovado:false};
try {
  const context=await browser.newContext();
  const page=await context.newPage();
  for(const code of ['desocupacao','rendimento-real','caged-saldo']){
    const response=await page.request.get(`http://127.0.0.1:3100/api/oil/indicadores/${code}/serie?janela=5a`);
    const data=await response.json();
    if(!response.ok()||!data.disponivel||data.simulada||data.pontos?.length<8||data.atribuicao?.texto?.toLocaleLowerCase('pt-BR').includes('licença'))results.falhas.push(`Integração real não aprovada: ${code}`);
    results.series.push({codigo:code,http:response.status(),disponivel:data.disponivel,simulada:data.simulada,motivo:data.motivo,valor:data.valor,cv:data.cv,periodo:data.periodo,unidade:data.unidade,fonte:data.fonte,link:data.link,coleta_id:data.coleta_id,coletado_em:data.coletado_em,pontos:data.pontos?.length||0});
  }
  const lawResponse=await page.request.get('http://127.0.0.1:3100/api/oil/lei');const law=await lawResponse.json();
  results.lei={http:lawResponse.status(),id_camara:law.id_camara,simulada:law.simulada,coleta_id:law.coleta_id,coletado_em:law.coletado_em,partido_referencia:law.partido_referencia};
  if(!lawResponse.ok()||law.simulada||law.disponivel===false||law.id_camara!==2233802)results.falhas.push('Integração real não aprovada: lei');
  await fs.mkdir('evidencias',{recursive:true});
  for(const width of [360,1280]){
    await page.setViewportSize({width,height:1000});await page.goto('http://127.0.0.1:3100');
    await page.getByTestId('card-desocupacao').getByTestId('insight-desocupacao').waitFor();
    for(const s of results.series){const card=page.getByTestId(`card-${s.codigo}`);if(s.disponivel){const label=await card.getByTestId(`valor-atual-${s.codigo}`).innerText();await expect(page.getByTestId(`resumo-valor-atual-${s.codigo}`)).toHaveText(label);await expect(card).toContainText(new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(s.valor));}else await expect(card).toContainText('Dado ainda não disponível');}
    if(law.id_camara===2233802)await expect(page.getByTestId('lei-v14')).toContainText(law.ementa);
    const scan=await new AxeBuilder({page}).analyze();const severe=scan.violations.filter(v=>['serious','critical'].includes(v.impact));
    results.axe.push({width,graves_criticas:severe.length});
    if(severe.length)results.falhas.push(`Acessibilidade real pendente: ${width}`);
    await page.screenshot({path:`evidencias/o3c-real-${width}.png`,fullPage:true});
  }
}catch(error){results.falhas.push(error.name||'Falha na captura');}
finally{results.aprovado=results.falhas.length===0;await fs.mkdir('evidencias',{recursive:true});await fs.writeFile('evidencias/o3c-validacao-real.json',JSON.stringify(results,null,2)+'\n');console.log(JSON.stringify(results,null,2));await browser.close();if(!results.aprovado)process.exitCode=1;}
