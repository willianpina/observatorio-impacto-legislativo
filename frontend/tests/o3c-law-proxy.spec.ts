import {test,expect} from '@playwright/test';
import {NextRequest} from 'next/server';
import {GET} from '../app/api/oil/lei/route';
import fixture from '../mocks/lei-v14.json';

let sequence=0;
async function normal(run:(get:()=>Promise<Response>)=>Promise<void>,upstream:(...args:Parameters<typeof fetch>)=>Promise<Response>){
  const oldFetch=globalThis.fetch,mode=process.env.OIL_TEST_MODE,base=process.env.OIL_API_URL,trust=process.env.OIL_TRUST_PROXY;
  sequence++;process.env.OIL_TEST_MODE='0';process.env.OIL_API_URL=`http://127.0.0.1:${19000+sequence}`;process.env.OIL_TRUST_PROXY='1';globalThis.fetch=upstream;
  const get=()=> (GET as unknown as (r:NextRequest)=>Promise<Response>)(new NextRequest('http://localhost/api/oil/lei?id=999',{headers:{'x-forwarded-for':`192.0.2.${sequence}`}}));
  try{await run(get);}finally{globalThis.fetch=oldFetch;for(const [key,value]of Object.entries({OIL_TEST_MODE:mode,OIL_API_URL:base,OIL_TRUST_PROXY:trust}))if(value===undefined)delete process.env[key];else process.env[key]=value;}
}
const real=()=>({...fixture,simulada:false});
test('O3C proxy lei fixa ID no servidor e serve contrato plano',async()=>{
  const urls:string[]=[];await normal(async get=>{const response=await get();expect(response.status).toBe(200);expect((await response.json()).id_camara).toBe(2233802);expect(urls).toHaveLength(1);expect(urls[0]).toMatch(/\/api\/v1\/proposicoes\/2233802$/);expect(response.headers.get('cache-control')).toBe('no-store');},async input=>{urls.push(String(input));return Response.json(real());});
});
test('O3C proxy lei recusa simulada em modo normal',async()=>{
  await normal(async get=>expect((await get()).status).toBe(502),async()=>Response.json(fixture));
});
test('O3C proxy lei cacheia sucesso somente por quinze segundos',async()=>{
  let calls=0,now=100000;const oldNow=Date.now;Date.now=()=>now;
  try{await normal(async get=>{expect((await get()).status).toBe(200);expect((await get()).headers.get('x-oil-cache')).toBe('HIT');expect(calls).toBe(1);now+=15001;await get();expect(calls).toBe(2);},async()=>{calls++;return Response.json(real());});}finally{Date.now=oldNow;}
});
test('O3C proxy lei preserva Retry-After e não cacheia erro',async()=>{
  let calls=0;await normal(async get=>{for(let i=0;i<2;i++){const r=await get();expect(r.status).toBe(503);expect(r.headers.get('retry-after')).toBe('45');}expect(calls).toBe(2);},async()=>{calls++;return Response.json({erro:{mensagem:'Fonte indisponível',tentar_novamente_em:45}},{status:503,headers:{'Retry-After':'45'}});});
});
test('O3C proxy lei limita sessenta consultas por minuto',async()=>{
  await normal(async get=>{for(let i=0;i<60;i++)expect((await get()).status).toBe(200);const response=await get();expect(response.status).toBe(429);expect(response.headers.get('retry-after')).toBeTruthy();},async()=>Response.json(real()));
});
test('O3C proxy lei timeout tem erro e prazo de nova tentativa',async()=>{
  await normal(async get=>{const response=await get();expect(response.status).toBe(503);expect(response.headers.get('retry-after')).toBe('60');expect((await response.json()).erro.tentar_novamente_em).toBe(60);},async(_input,init)=>{expect(init?.signal).toBeTruthy();throw new DOMException('Timeout simulado','TimeoutError');});
});
