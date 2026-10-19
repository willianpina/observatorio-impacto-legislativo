import {NextRequest,NextResponse} from 'next/server';
export const dynamic='force-dynamic';
const clients=new Map<string,{count:number;expires:number}>();
const cache=new Map<string,{body:unknown;expires:number}>();
function error(status:number,mensagem:string,seconds=60){return NextResponse.json({erro:{fonte:'API local',mensagem,tentar_novamente_em:seconds}},{status,headers:{'Retry-After':String(seconds),'Cache-Control':'no-store'}});}
export async function GET(request:NextRequest){
  if(process.env.OIL_TEST_MODE==='1'){
    const {default:data}=await import('../../../../mocks/lei-v14.json');
    return NextResponse.json(data,{headers:{'Cache-Control':'no-store'}});
  }
  const now=Date.now();
  const ip=process.env.OIL_TRUST_PROXY==='1'?(request.headers.get('x-forwarded-for')?.split(',')[0].trim().slice(0,64)||'local'):'local';
  for(const [key,client]of clients)if(client.expires<=now)clients.delete(key);
  if(!clients.has(ip)&&clients.size>=1024)return error(429,'Limite de consultas atingido.');
  const client=clients.get(ip)||{count:0,expires:now+60000};clients.set(ip,client);
  if(++client.count>60)return error(429,'Limite de consultas atingido.',Math.max(1,Math.ceil((client.expires-now)/1000)));
  const base=process.env.OIL_API_URL;
  if(!base)return error(503,'API local ainda não configurada.');
  const key=base.replace(/\/$/,'')+'/api/v1/proposicoes/2233802';
  const hit=cache.get(key);
  if(hit&&hit.expires>now)return NextResponse.json(hit.body,{headers:{'Cache-Control':'no-store','X-OIL-Cache':'HIT'}});
  try{
    const response=await fetch(key,{cache:'no-store',signal:AbortSignal.timeout(15000)});
    let body;try{body=await response.json();}catch{return error(502,'Resposta inesperada da API local.');}
    if(response.ok&&(!body||body.simulada!==false))return error(502,'Resposta de teste ou inesperada recusada no modo normal.');
    if(response.ok)cache.set(key,{body,expires:Date.now()+15000});
    const headers:Record<string,string>={'Cache-Control':'no-store','X-OIL-Cache':'MISS'};
    if([429,503].includes(response.status))headers['Retry-After']=response.headers.get('Retry-After')||'60';
    return NextResponse.json(body,{status:response.status,headers});
  }catch{return error(503,'Não foi possível consultar a API local.');}
}
