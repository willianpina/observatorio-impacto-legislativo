// Espelho de backend/oil/law_schemas.py, sem vigência, resumo ou votações.
export interface Situation {casa:'camara'|'senado';situacao:string;data:string|null;link:string;fonte:string;coleta_id:number|null;coletado_em:string|null;disponivel:boolean;motivo:string|null}
export interface Marker {tipo:string;rotulo:string;data:string;prevista:boolean;fonte:string;link:string;origem:'fonte'|'calculado';artigo:string|null}
export interface LawResponse {
  id_camara:number;id_senado:number;sigla_tipo:string|null;numero:number|null;ano:number|null;ementa:string|null;
  autor:string|null;partido:string|null;uf:string|null;coautores:number|null;partido_referencia:'atual'|'apresentacao'|null;autoria_motivo:string|null;data_apresentacao:string|null;
  situacao:Situation[];situacao_atual:Situation&{regra:'mais_recente'|'unica_disponivel';divergencia:boolean};
  norma_gerada:{rotulo:string;data:string;link:string;fonte:string}|null;norma_gerada_motivo:string|null;
  marcos:Marker[];fontes_norma:{rotulo:string;link:string;coletado_em:string}[];
  nivel_evidencia:'descritivo';desatualizado:boolean;simulada:boolean;fonte:string;coleta_id:number;coletado_em:string;
}
