import { NextRequest, NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';

// Limites locais ao processo, para uma única instância local.
const WINDOW_MS = 60_000, MAX_REQUESTS = 60, CACHE_MS = 15_000;
const clients = new Map<string, { count: number; expires: number }>();
const cache = new Map<string, { body: unknown; expires: number }>();

export async function GET(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const now = Date.now();
  // Sem proxy confiável, os clientes compartilham o limite local. Nunca aceitar
  // IP arbitrário do navegador. O proxy habilitado deve sobrescrever este header.
  const ip = process.env.OIL_TRUST_PROXY === '1'
    ? (request.headers.get('x-forwarded-for')?.split(',')[0].trim().slice(0,64) || 'local') : 'local';
  for (const [key, client] of clients) if (client.expires <= now) clients.delete(key);
  if (!clients.has(ip) && clients.size >= 1024) return limited(60);
  const client = clients.get(ip) || { count: 0, expires: now + WINDOW_MS };
  clients.set(ip, client);
  if (++client.count > MAX_REQUESTS) return limited(Math.max(1, Math.ceil((client.expires - now) / 1000)));

  const { path = [] } = await context.params;
  const code = path[0];
  if (path.length && (path.length !== 2 || path[1] !== 'serie' || !['desocupacao','rendimento-real','caged-saldo'].includes(code)))
    return NextResponse.json({ erro: { fonte: 'API local', mensagem: 'Indicador não cadastrado.' } }, { status: 404 });
  const janela = request.nextUrl.searchParams.get('janela') || '5a';
  if (!['2a','5a','desde_2020'].includes(janela))
    return NextResponse.json({ erro: { fonte: 'API local', mensagem: 'Parâmetro janela inválido.' } }, { status: 422 });
  const base = process.env.OIL_API_URL;
  if (!base) return NextResponse.json({ erro: { fonte: 'API local', mensagem: 'API local ainda não configurada.' } }, { status: 503 });
  const key = `${path.join('/')}?janela=${janela}`;
  const hit = cache.get(key);
  if (hit && hit.expires > now) return NextResponse.json(hit.body, { headers: { 'Cache-Control': 'no-store', 'X-OIL-Cache': 'HIT' } });
  try {
    const response = await fetch(`${base.replace(/\/$/,'')}/api/v1/indicadores${path.length ? `/${code}/serie` : ''}?janela=${janela}`, {
      cache: 'no-store', signal: AbortSignal.timeout(15000)
    });
    const body = await response.json();
    if (response.ok) cache.set(key, { body, expires: Date.now() + CACHE_MS });
    const headers: Record<string,string> = { 'Cache-Control': 'no-store', 'X-OIL-Cache': 'MISS' };
    if ([429,503].includes(response.status)) headers['Retry-After'] = response.headers.get('Retry-After') || '60';
    return NextResponse.json(body, { status: response.status, headers });
  } catch {
    return NextResponse.json({ erro: { fonte: 'API local', mensagem: 'Não foi possível consultar a API local.', tentar_novamente_em: 60 } }, {
      status: 503, headers: { 'Retry-After': '60' }
    });
  }
}

function limited(seconds: number) {
  return NextResponse.json({ erro: { fonte: 'API local', mensagem: 'Limite de consultas atingido.', tentar_novamente_em: seconds } }, {
    status: 429, headers: { 'Retry-After': String(seconds), 'Cache-Control': 'no-store' }
  });
}
