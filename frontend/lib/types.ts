export type Window = '2a'|'5a'|'desde_2020';
export interface Point { periodo: string; valor: number|null; lacuna: boolean; unidade: string; cv: number|null; variacao_anual: number|null; coleta_id?: number|null; coletado_em?: string|null; versao?: number|null; ajuste?: string; competencia_coleta?: string }
/** Atribuição do Caged no contrato v1.5.0. base_legal é texto; não há licenca. */
export interface Atribuicao { texto: string; link: string; base_legal: string; arquivo_referencia: string|null; coletado_em: string|null }
export interface Series { codigo: string; nome: string; valor: number|null; periodo: string|null; unidade: string; cv: number|null; variacao_anual: number|null; variacao_anual_unidade: string; classificacao: 'subiu'|'caiu'|'estavel'|null; classificacao_origem: string; tipo_valor: 'real'|'nominal'|null; tipo_periodo: string; medida: string; base_precos: string|null; fonte: string; tabela_ou_arquivo: string|null; link: string|null; coletado_em: string|null; coleta_id: number|null; disponivel: boolean; motivo: string|null; desatualizado: boolean; atrasado_calendario: boolean; simulada: boolean; pontos: Point[]; ajuste?: string; atribuicao?: Atribuicao|null; nota_revisao?:string|null; variacao_anual_origem?:'fonte'|'calculo_observatorio' }
export type DataState = {status:'loading'} | {status:'error'; source:string; retryAfter?:number} | {status:'ready'; data:Series};
export const TITLES:Record<string,string> = {desocupacao:'Taxa de desocupação','caged-saldo':'Saldo de empregos formais','rendimento-real':'Rendimento médio real'};
export const WARNING='É cedo para afirmar. A emenda começa a valer em etapas, e os dados oficiais saem com atraso. Mudanças nos indicadores podem ter várias causas.';
export const LEGEND='Marcos de calendário. Não indicam efeito da lei.';
export function number(value:number|null|undefined) { return value == null ? 'sem dado' : new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(value); }
export function date(value:string|null|undefined, time=false) { if(!value) return 'Não informado'; const d=new Date(value.length===10?value+'T12:00:00Z':value); if(Number.isNaN(d.valueOf())) return 'Não informado'; return new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',day:'2-digit',month:'2-digit',year:'numeric',...(time?{hour:'2-digit',minute:'2-digit'}:{})}).format(d); }
const MESES_ARQUIVO=['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
/** Competência AAAA-MM do arquivo. Fora desse formato, ou nula, vira s/d. */
export function mesArquivo(referencia:string|null|undefined) {
  const match=/^(\d{4})-(0[1-9]|1[0-2])$/.exec(referencia??'');
  if(!match) return 's/d';
  return `${MESES_ARQUIVO[Number(match[2])-1]}/${match[1]}`;
}
/** Data da coleta em Brasília (dd/mm/aaaa). Nula ou inválida vira s/d, sem usar o dia de hoje. */
export function dataColetaBrasilia(iso:string|null|undefined) {
  if(!iso) return 's/d';
  const rotulo=date(iso);
  return rotulo==='Não informado'?'s/d':rotulo;
}
/** Frase da tela. O texto fixo da API continua sem data; o mês e o dia entram aqui. */
export function fraseFonteCaged(arquivo:string|null|undefined, coletado:string|null|undefined) {
  return `Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo ${mesArquivo(arquivo)}, coletado em ${dataColetaBrasilia(coletado)}. Série revisada mensalmente. Elaboração: OIL.`;
}
export function periodType(value:string) { return value==='trimestre_movel'?'Trimestre móvel':value==='trimestral'?'Trimestral':'Mensal'; }
export function valueLabel(value:number|null|undefined,unit:string) { return unit==='R$'?`R$ ${number(value)}`:`${number(value)} ${unit}`; }
export function period(value:string|null|undefined,type='mensal') {
  if (!value || !/^\d{6}$/.test(value)) return 'Não informado';
  const year=Number(value.slice(0,4)),month=Number(value.slice(4))-1;
  if(month<0||month>11)return 'Não informado';
  if(type==='trimestral')return `${Math.floor(month/3)+1}º trimestre de ${year}`;
  const end=new Date(Date.UTC(year,month,1));
  if(type==='trimestre_movel') {
    const start=new Date(Date.UTC(year,month-2,1));
    const name=(d:Date)=>new Intl.DateTimeFormat('pt-BR',{month:'short',timeZone:'UTC'}).format(d);
    return `${name(start)}${start.getUTCFullYear()!==year?` de ${start.getUTCFullYear()}`:''}–${name(end)} de ${year}`;
  }
  return new Intl.DateTimeFormat('pt-BR',{month:'short',year:'numeric',timeZone:'UTC'}).format(end);
}
