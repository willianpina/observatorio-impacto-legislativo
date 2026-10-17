import { NextRequest, NextResponse } from 'next/server';
export const dynamic='force-dynamic';
export async function GET(request:NextRequest,context:{params:Promise<{path?:string[]}>}) {
  const {path=[]}=await context.params;
  const code=path[0];
  if(path.length && (path.length!==2 || path[1]!=='serie' || !['desocupacao','rendimento-real','caged-saldo'].includes(code))) return NextResponse.json({erro:{fonte:'API local',mensagem:'Indicador não cadastrado.'}},{status:404});
  const janela=request.nextUrl.searchParams.get('janela') || '5a';
  if(!['2a','5a','desde_2020'].includes(janela)) return NextResponse.json({erro:{fonte:'API local',mensagem:'Parâmetro janela inválido.'}},{status:422});
  const base=process.env.OIL_API_URL;
  if(!base) return NextResponse.json({erro:{fonte:'API local',mensagem:'API local ainda não configurada.'}},{status:503});
  try {
    const response=await fetch(`${base.replace(/\/$/,'')}/api/v1/indicadores${path.length?`/${code}/serie`:''}?janela=${janela}`,{cache:'no-store',signal:AbortSignal.timeout(15000)});
    const body=await response.json();
    return NextResponse.json(body,{status:response.status,headers:response.status===503?{'Retry-After':response.headers.get('Retry-After') || '60'}:undefined});
  } catch { return NextResponse.json({erro:{fonte:'API local',mensagem:'Não foi possível consultar a API local.'}},{status:503}); }
}
