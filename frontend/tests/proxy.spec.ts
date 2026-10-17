import { test, expect } from '@playwright/test';
import { NextRequest } from 'next/server';
import { GET } from '../app/api/oil/indicadores/[[...path]]/route';
import { safeHref } from '../lib/safe-href';

test('safeHref aceita só HTTPS das fontes, com fronteiras de domínio e caminho MTE',()=>{
  for(const link of ['javascript:alert(1)','https://estranho.example/x','http://ibge.gov.br','https://ibge.gov.br.estranho.example','https://www.gov.br/outra-pasta','https://www.gov.br/trabalho-e-emprego-falso','https://usuario@ibge.gov.br','https://ibge.gov.br:444/']) expect(safeHref(link)).toBeUndefined();
  for(const link of ['https://sidra.ibge.gov.br/tabela/6381','https://dadosabertos.camara.leg.br/api','https://legis.senado.leg.br/','https://www.planalto.gov.br/','https://www.in.gov.br/','https://www.gov.br/trabalho-e-emprego/pt-br']) expect(safeHref(link)).toBe(link);
});

test('proxy: cache de 15 segundos, janela isolada, 429 por IP e Retry-After',async()=>{
  const originalFetch=globalThis.fetch, originalNow=Date.now;
  const oldBase=process.env.OIL_API_URL,oldTrust=process.env.OIL_TRUST_PROXY;
  let now=1_000_000,calls=0;
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
