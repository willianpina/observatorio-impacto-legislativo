// REPLAY SIMULADO: valores gravados do SIDRA na O2; nunca usado pela aplicação.
import fs from 'node:fs';
import path from 'node:path';
import lawFixture from '../mocks/lei-v14.json';
import type { Page } from '@playwright/test';

export function fixture(code: string, janela = '5a') {
  if (code === 'caged-saldo') return { codigo: code, nome: 'Saldo de empregos formais', disponivel: false,
    motivo: 'Fonte oficial do Novo Caged em verificação.', pontos: [], fonte: 'MTE / Novo Caged', simulada: true,
    link: 'https://www.gov.br/trabalho-e-emprego/pt-br',
    atribuicao: { texto: 'Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes). Série revisada mensalmente. Elaboração: OIL.',
      link: 'https://www.gov.br/trabalho-e-emprego/pt-br', base_legal: 'Decreto 8.777/2016, art. 4º',
      arquivo_referencia: null, coletado_em: null } };
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
  const points = rows.filter(r => r.D2C === level && (janela!=='desde_2020'||r.D3C>='202001')).slice(janela==='2a'?-24:janela==='desde_2020'?-1000:-60).map(r => {
    const get = (id: string) => Number(rows.find(v => v.D3C === r.D3C && v.D2C === id)?.V);
    return { ...meta, periodo: r.D3C, valor: Number(r.V), cv: get(cv), variacao_anual: get(variation), lacuna: false, versao: 1 };
  });
  return { ...meta, ...points.at(-1), pontos: points };
}

export async function intercept(page: Page, state = 'normal', normalMode = false,transform?:(data:Record<string,unknown>,code:string)=>void) {
  await page.route('**/api/oil/lei',route=>route.fulfill({json:{...lawFixture,simulada:!normalMode}}));
  await page.route('**/api/oil/indicadores?*',route=>route.fulfill({json:{indicadores:[],coletado_em:null,simulada:!normalMode}}));
  await page.route('**/api/oil/indicadores/**', async route => {
    const code = new URL(route.request().url()).pathname.split('/')[4];
    if (state === 'error' && code === 'desocupacao') return route.fulfill({ status: 503, json: { erro: { fonte: 'IBGE', mensagem: 'Fonte temporariamente indisponível.', tentar_novamente_em: 60 } } });
    const data = fixture(code,new URL(route.request().url()).searchParams.get('janela')||'5a');
    if ('desatualizado' in data && state === 'stale') data.desatualizado = true;
    if ('pontos' in data && data.pontos.length && state === 'gap') data.pontos[20] = { ...data.pontos[20], valor: null as unknown as number, lacuna: true };
    if (state === 'empty') data.pontos = [];
    if ('classificacao' in data && state === 'unclassified') data.classificacao = null as unknown as string;
    // Fixture sintética de apresentação: não é uma série real inferida da PNAD móvel.
    if(code==='desocupacao' && state==='trimestral' && data.pontos.length) {
      Object.assign(data,{tipo_periodo:'trimestral',nome:'Fixture trimestral simulada',fonte:'Fixture sintética — teste de periodicidade',tabela_ou_arquivo:null,link:null,valor:7.2,periodo:'202606',pontos:[
        {...data.pontos[0],tipo_periodo:'trimestral',periodo:'202603',valor:7.5},
        {...data.pontos[0],tipo_periodo:'trimestral',periodo:'202606',valor:7.2}
      ]});
    }
    if (code === 'caged-saldo' && ['caged','csv'].includes(state)) {
      const reference = fixture('desocupacao');
      Object.assign(data, { ...reference, codigo: code, nome: 'Saldo de empregos formais', valor:-10, cv:null, classificacao:null, variacao_anual:2, variacao_anual_unidade:'postos de trabalho', unidade:'postos de trabalho',fonte:'Novo Caged – MTE',link:'https://www.gov.br/trabalho-e-emprego/pt-br',tabela_ou_arquivo:'Tabela 5.1 (com ajustes)',atribuicao:{texto:'Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes). Série revisada mensalmente. Elaboração: OIL.',link:'https://www.gov.br/trabalho-e-emprego/pt-br',base_legal:'Decreto 8.777/2016, art. 4º',arquivo_referencia:'2026-08',coletado_em:'2026-10-17T14:22:00Z'},nota_revisao:'Série revisada mensalmente pelo MTE: os meses anteriores podem mudar a cada novo arquivo.',variacao_anual_origem:'calculo_observatorio' , medida: 'saldo', tipo_periodo: 'mensal', ajuste: 'com_ajuste',
        pontos: reference.pontos.slice(-3).map((p,i) => ({ ...p, codigo:code, medida:'saldo', tipo_periodo:'mensal', tipo_valor:null, cv:null, classificacao:null, classificacao_origem:null, variacao_anual:2, variacao_anual_unidade:'postos de trabalho', variacao_anual_origem:'calculo_observatorio', fonte:'Novo Caged – MTE', link:'https://www.gov.br/trabalho-e-emprego/pt-br', tabela_ou_arquivo:'Tabela 5.1 (com ajustes)', valor: i === 1 ? -10 : 20, unidade: 'postos de trabalho', ajuste: i === 1 ? 'com_ajuste' : 'sem_ajuste', competencia_coleta: '202608' })) });
    }
    if(code==='caged-saldo'&&state==='csv') {data.pontos[0].unidade='=1+1';data.pontos[1].unidade='-x';}
    if (normalMode) data.simulada=false;
    transform?.(data,code);
    await route.fulfill({ json: data });
  });
}
