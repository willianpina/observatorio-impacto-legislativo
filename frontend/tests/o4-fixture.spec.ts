import {test,expect,type Page,type Route} from '@playwright/test';
import {intercept} from './fixtures';
import type {Series} from '../lib/types';

test('O4 fixture Caged preserva metadados mensais sem erro amostral',async()=>{
  let handler:((route:Route)=>Promise<void>)|undefined;
  const page={route:async(pattern:string,callback:(route:Route)=>Promise<void>)=>{if(pattern==='**/api/oil/indicadores/**')handler=callback;}} as unknown as Page;
  let received:unknown;
  await intercept(page,'caged');
  const route={request:()=>({url:()=> 'http://localhost/api/oil/indicadores/caged-saldo/serie?janela=5a'}),fulfill:async(body:{json:unknown})=>{received=body.json;}} as unknown as Route;
  expect(handler).toBeDefined();await handler!(route);
  const data=received as Series;
  expect(data.simulada).toBe(true);expect(data.pontos.length).toBeGreaterThan(0);
  for(const point of data.pontos as (Series['pontos'][number]&Record<string,unknown>)[]){
    expect(point.cv).toBeNull();expect(point.classificacao).toBeNull();expect(point.tipo_periodo).toBe('mensal');
    expect(point.medida).toBe('saldo');expect(point.unidade).toBe('postos de trabalho');
  }
});
