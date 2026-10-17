// REPLAY SIMULADO: valores gravados do SIDRA na O2; nunca usado pela aplicação.
import fs from 'node:fs';
import path from 'node:path';
import type { Page } from '@playwright/test';

export function fixture(code: string) {
  if (code === 'caged-saldo') return { codigo: code, nome: 'Saldo de empregos formais', disponivel: false,
    motivo: 'Fonte oficial do Novo Caged em verificação.', pontos: [], fonte: 'MTE / Novo Caged', simulada: true };
  const income = code === 'rendimento-real';
  const table = income ? '6390' : '6381';
  const rows = JSON.parse(fs.readFileSync(path.join(process.cwd(), '../backend/tests/fixtures', `sidra-${table}.json`), 'utf8')) as Record<string,string>[];
  const level = income ? '5933' : '4099', cv = income ? '5941' : '4103', variation = income ? '8837' : '8816';
  const meta = { codigo: code, nome: income ? 'Rendimento médio real' : 'Taxa de desocupação',
    fonte: 'IBGE / PNAD Contínua / SIDRA', tabela_ou_arquivo: table, link: `https://sidra.ibge.gov.br/tabela/${table}`,
    coletado_em: '2026-10-17T14:22:00+00:00', coleta_id: 1, unidade: income ? 'R$' : '%', medida: income ? 'valor' : 'taxa',
    tipo_valor: income ? 'real' : null, tipo_periodo: 'trimestre_movel', base_precos: null, nivel_evidencia: 'descritivo',
    comparacao: 'mesmo_periodo_ano_anterior', classificacao: income ? 'subiu' : 'caiu', classificacao_origem: 'calculada',
    variacao_anual_unidade: income ? '%' : 'p.p.', simulada: true, disponivel: true, desatualizado: false, atrasado_calendario: false };
  const points = rows.filter(r => r.D2C === level).slice(-60).map(r => {
    const get = (id: string) => Number(rows.find(v => v.D3C === r.D3C && v.D2C === id)?.V);
    return { ...meta, periodo: r.D3C, valor: Number(r.V), cv: get(cv), variacao_anual: get(variation), lacuna: false, versao: 1 };
  });
  return { ...meta, ...points.at(-1), pontos: points };
}

export async function intercept(page: Page, state = 'normal') {
  await page.route('**/api/oil/indicadores/**', async route => {
    const code = new URL(route.request().url()).pathname.split('/')[4];
    if (state === 'error' && code === 'desocupacao') return route.fulfill({ status: 503, json: { erro: { fonte: 'IBGE', mensagem: 'Fonte temporariamente indisponível.', tentar_novamente_em: 60 } } });
    const data = fixture(code);
    if ('desatualizado' in data && state === 'stale') data.desatualizado = true;
    if ('pontos' in data && data.pontos.length && state === 'gap') data.pontos[20] = { ...data.pontos[20], valor: null as unknown as number, lacuna: true };
    if (state === 'empty') data.pontos = [];
    if ('classificacao' in data && state === 'unclassified') data.classificacao = null as unknown as string;
    if (code === 'caged-saldo' && state === 'caged') {
      const reference = fixture('desocupacao');
      Object.assign(data, { ...reference, codigo: code, nome: 'Saldo de empregos formais', valor:-10, cv:null, classificacao:null, variacao_anual:2, variacao_anual_unidade:'vínculos', unidade:'vínculos',fonte:'Novo Caged – MTE',tabela_ou_arquivo:'Tabela 5.1 (com ajustes)',arquivo_origem:'08/2026',licenca:'CC BY-ND 3.0', medida: 'saldo', tipo_periodo: 'mensal', ajuste: 'com_ajuste',
        pontos: reference.pontos.slice(-3).map((p,i) => ({ ...p, valor: i === 1 ? -10 : 20, unidade: 'vínculos', ajuste: i === 1 ? 'com_ajuste' : 'sem_ajuste', competencia_coleta: '202608' })) });
    }
    await route.fulfill({ json: data });
  });
}
