/** Links externos publicados pelas fontes: HTTPS e fronteira exata de domínio. */
export function safeHref(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return undefined;
    const domains = ['ibge.gov.br', 'camara.leg.br', 'senado.leg.br', 'planalto.gov.br', 'in.gov.br'];
    const official = domains.some(domain => url.hostname === domain || url.hostname.endsWith(`.${domain}`));
    const mte = ['gov.br', 'www.gov.br'].includes(url.hostname) &&
      (url.pathname === '/trabalho-e-emprego' || url.pathname.startsWith('/trabalho-e-emprego/'));
    return official || mte ? url.href : undefined;
  } catch {
    return undefined;
  }
}
