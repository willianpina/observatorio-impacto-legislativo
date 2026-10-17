import type { EtapaVigencia, Vigencia } from './contrato-lei-provisorio';
import { date } from './types';

export function todayInBrasilia(): string {
  const parts = new Intl.DateTimeFormat('en-CA', {timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
  const part=(type:string)=>parts.find(p=>p.type===type)!.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

export function etapaPrevista(etapa:EtapaVigencia, hoje=todayInBrasilia()):boolean {
  return etapa.data_tipo === 'calculada' && etapa.data_inicio > hoje;
}

export function vigenciaText(vigencia:Vigencia, hoje=todayInBrasilia()):string {
  const geral=`Em vigor desde ${date(vigencia.data_publicacao)}, data da publicação`;
  const etapas=vigencia.etapas.map(e=>`${e.descricao} a partir de ${date(e.data_inicio)}${etapaPrevista(e,hoje)?' (prevista)':''}`);
  return `${geral}${etapas.length?`, exceto: ${etapas.join('; ')}`:''}.`;
}
