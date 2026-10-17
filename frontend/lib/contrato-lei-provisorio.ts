// Contrato provisório, sem dados; substituir a adaptação quando a O3 for aprovada.
// Versão 0.2 (O4-R2): vigencia passa de texto para estrutura, sem mudança na O3.
export interface EtapaVigencia { id: string; descricao: string; dispositivos: string[]; base_legal: string; prazo: {meses:number; a_partir_de:string}; data_inicio:string; data_tipo:'calculada'|'expressa' }
export interface Vigencia { data_publicacao:string; regra_geral:{inicio:'publicacao';base_legal:string}; etapas:EtapaVigencia[]; fontes:{nome:string;url:string;consultado_em:string}[] }
export interface Marco { tipo: string; rotulo: string; data: string; prevista: boolean; fonte: string; link: string; artigo?: string; nota?: string }
export interface Situacao { casa: 'camara'|'senado'; situacao: string|null; data: string; link: string; fonte: string; coletado_em: string }
export interface Placar { sim: number; nao: number; abstencao: number; total: number; obstrucao: number; ausentes: number|null }
export interface Partido { partido: string; presentes: number; sim: number; nao: number; abstencao: number; percentual_sim: number; base_percentual: string }
export interface Voto { parlamentar: string; voto: string; partido: string|null; uf: string|null; sigla_ausente: boolean }
export interface Votacao { id_votacao: string; casa: 'camara'|'senado'; turno: number; data: string; tipo: 'nominal'|'simbolica'; link: string; fonte: string; coletado_em: string; principal: boolean; placar_conferido: boolean; placar: Placar|null; quorum_exigido: number; resultado: string; inconsistencia: string|null; votos_por_partido: Partido[]|null; motivo?: string; votos?: Voto[]; proxima?: number|null }
export interface Tramitacao { casa: string; data: string; descricao: string; fonte: string; link: string; coletado_em: string }
export interface Lei { nome: string; tipo: string; numero: number; ano: number; ementa: string; resumo: string; link: string; fonte: string; coletado_em: string; norma: string; situacao: Situacao[]; situacao_norma: {texto:string;link:string}; vigencia: Vigencia; autor: string|null; partido: string|null; uf: string|null; data_apresentacao: string|null; marcos: Marco[]; votacoes: Votacao[]; tramitacoes: Tramitacao[] }
