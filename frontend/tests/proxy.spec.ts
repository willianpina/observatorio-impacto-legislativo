import { test, expect } from '@playwright/test';
import { NextRequest } from 'next/server';
import { GET } from '../app/api/oil/indicadores/[[...path]]/route';
import { safeHref } from '../lib/safe-href';
import { csvCell } from '../lib/csv';
import { vigenciaText, etapaPrevista } from '../lib/vigencia';
import { periodType } from '../lib/types';
import { lei } from '../mocks/lei';
import { languageViolations } from './linguagem';

test('R2-2 CSV preserva número negativo e escapa somente texto',()=>{
  expect(csvCell(-10)).toBe('"-10"');expect(csvCell('=1+1')).toBe('"\'=1+1"');expect(csvCell('-x')).toBe('"\'-x"');
});

test('R2-3 vigência é derivada do dado, e prevista exige data calculada futura',()=>{
  const original=lei.vigencia;
  const changed=structuredClone(original);changed.data_publicacao='2025-09-10';changed.etapas[0].data_inicio='2025-11-10';changed.etapas[0].descricao='descrição alterada';
  expect(vigenciaText(changed,'2025-09-11')).toContain('10/09/2025');expect(vigenciaText(changed,'2025-09-11')).toContain('descrição alterada a partir de 10/11/2025 (prevista)');
  expect(vigenciaText(original,'2028-01-01')).not.toContain('(prevista)');
  expect(vigenciaText(original,'2026-01-01')).not.toContain('16/10/2026 (prevista)');
  expect(etapaPrevista({...original.etapas[0],data_tipo:'expressa'},'2026-01-01')).toBe(false);
  expect(etapaPrevista(original.etapas[0],'2026-12-16')).toBe(false);
});

test('R2-4 periodicidade trimestral não vira mensal',()=>expect(periodType('trimestral')).toBe('Trimestral'));

for(const sentence of ['Após a Aprovação no Senado, a desocupação caiu.','antes e depois da lei','Aprovação no Senado: variação anual de -0,3 p.p.']) test(`R2-5 linguagem rejeita: ${sentence}`,()=>{
  expect(languageViolations(sentence,['Aprovação no Senado'])).not.toEqual([]);
});
test('R2-5 exceção restrita à legenda literal',()=>{
  expect(languageViolations('Marcos de calendário. Não indicam efeito da lei.')).toEqual([]);
  expect(languageViolations('Não indicam efeito da lei.')).toContain('efeito da lei');
});

test('R2-7 safeHref testa domínios ambíguos e canonicalização',()=>{
  for(const link of ['https://evilcamara.leg.br/','https://camara.leg.br@evil.com/','https://camara.leg.br./'])expect(safeHref(link)).toBeUndefined();
  expect(safeHref('https://CAMARA.LEG.BR/')).toBe('https://camara.leg.br/');
});

test('R2-8 requisições inválidas não consomem cota',async()=>{
  const oldFetch=globalThis.fetch,oldBase=process.env.OIL_API_URL,oldTrust=process.env.OIL_TRUST_PROXY;
  process.env.OIL_API_URL='http://127.0.0.1:9999';process.env.OIL_TRUST_PROXY='1';
  globalThis.fetch=async()=>new Response('{"simulada":true}',{status:200});
  const get=(path:string[],janela='5a')=>GET(new NextRequest(`http://localhost/api/oil/indicadores?janela=${janela}`,{headers:{'x-forwarded-for':'192.0.2.90'}}),{params:Promise.resolve({path})});
  try {
    for(let i=0;i<61;i++){expect((await get(['desconhecido','serie'])).status).toBe(404);expect((await get(['desocupacao','serie'],'invalida')).status).toBe(422);}
    for(let i=0;i<60;i++)expect((await get(['desocupacao','serie'])).status).toBe(200);
    expect((await get(['desocupacao','serie'])).status).toBe(429);
  } finally {
    globalThis.fetch=oldFetch;
    if(oldBase===undefined)delete process.env.OIL_API_URL;else process.env.OIL_API_URL=oldBase;
    if(oldTrust===undefined)delete process.env.OIL_TRUST_PROXY;else process.env.OIL_TRUST_PROXY=oldTrust;
  }
});

test('safeHref aceita só HTTPS das fontes, com fronteiras de domínio e caminho MTE',()=>{
  for(const link of ['javascript:alert(1)','https://estranho.example/x','http://ibge.gov.br','https://ibge.gov.br.estranho.example','https://www.gov.br/outra-pasta','https://www.gov.br/trabalho-e-emprego-falso','https://usuario@ibge.gov.br','https://ibge.gov.br:444/']) expect(safeHref(link)).toBeUndefined();
  for(const link of ['https://sidra.ibge.gov.br/tabela/6381','https://dadosabertos.camara.leg.br/api','https://legis.senado.leg.br/','https://www.planalto.gov.br/','https://www.in.gov.br/','https://www.gov.br/trabalho-e-emprego/pt-br']) expect(safeHref(link)).toBe(link);
});

test('proxy: cache de 15 segundos, janela isolada, 429 por IP e Retry-After',async()=>{
  const originalFetch=globalThis.fetch, originalNow=Date.now;
  const oldBase=process.env.OIL_API_URL,oldTrust=process.env.OIL_TRUST_PROXY;
  // Começa após caches criados por outros testes, sem fazer o relógio retroceder.
  let now=Date.now()+120_000,calls=0;
  Date.now=()=>now;
  process.env.OIL_API_URL='http://127.0.0.1:9999';process.env.OIL_TRUST_PROXY='1';
  globalThis.fetch=async()=>new Response(JSON.stringify({simulada:true,sequencia:++calls}),{status:200,headers:{'Content-Type':'application/json'}});
  const get=(ip:string,janela='5a')=>GET(new NextRequest(`http://localhost/api/oil/indicadores/desocupacao/serie?janela=${janela}`,{headers:{'x-forwarded-for':ip}}),{params:Promise.resolve({path:['desocupacao','serie']})});
  try {
    const first=await get('192.0.2.1');expect(first.headers.get('X-OIL-Cache')).toBe('MISS');
    const cached=await get('192.0.2.1');expect(cached.headers.get('X-OIL-Cache')).toBe('HIT');expect(await cached.json()).toEqual({simulada:true,sequencia:1});expect(calls).toBe(1);
    await get('192.0.2.1','2a');expect(calls).toBe(2);
    now+=15_001;await get('192.0.2.1');expect(calls).toBe(3);
    for(let i=0;i<57;i++)await get('192.0.2.1');
    const limited=await get('192.0.2.1');expect(limited.status).toBe(429);
    expect(Number(limited.headers.get('Retry-After'))).toBeGreaterThan(0);
    expect((await limited.json()).erro.tentar_novamente_em).toBeLessThanOrEqual(60);
    expect((await get('192.0.2.2')).status).toBe(200);
    now+=60_001;expect((await get('192.0.2.1')).status).toBe(200);
    globalThis.fetch=async()=>new Response('{"erro":{"fonte":"teste","tentar_novamente_em":30}}',{status:503,headers:{'Retry-After':'30'}});
    const failure=await get('192.0.2.3','desde_2020');expect(failure.status).toBe(503);expect(failure.headers.get('Retry-After')).toBe('30');
    globalThis.fetch=async()=>new Response('{"simulada":true}',{status:200});
    expect((await get('192.0.2.3','desde_2020')).headers.get('X-OIL-Cache')).toBe('MISS');
  } finally {
    globalThis.fetch=originalFetch;Date.now=originalNow;
    if(oldBase===undefined)delete process.env.OIL_API_URL;else process.env.OIL_API_URL=oldBase;
    if(oldTrust===undefined)delete process.env.OIL_TRUST_PROXY;else process.env.OIL_TRUST_PROXY=oldTrust;
  }
});
