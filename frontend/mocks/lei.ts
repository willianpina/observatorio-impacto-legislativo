// DADO DE TESTE. Nunca carregado no navegador nem habilitado fora de OIL_TEST_MODE=1.
import type { Lei, Votacao } from '../lib/contrato-lei-provisorio';
const collected='2026-10-17T11:23:00-03:00';
const dou='https://www.in.gov.br/web/dou/-/emenda-constitucional-n-141-738818165';
const planalto='https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm';
const camara='https://dadosabertos.camara.leg.br/api/v2/proposicoes/2233802';
const senado='https://legis.senado.leg.br/dadosabertos/processo/9056435?v=1';
const votes:Votacao[]=[
 {id_votacao:'2233802-424',casa:'camara',turno:1,data:'2026-05-27',tipo:'nominal',principal:true,link:camara,fonte:'Câmara — fixture de teste',coletado_em:collected,placar_conferido:true,placar:{sim:472,nao:22,abstencao:0,total:494,obstrucao:1,ausentes:null},quorum_exigido:308,resultado:'Aprovada',inconsistencia:null,votos_por_partido:null,motivo:'A fonte não informa o partido na data do voto nesta fixture; divisão por partido indisponível.',votos:[{parlamentar:'Parlamentar de teste A',voto:'Sim',partido:null,uf:null,sigla_ausente:true},{parlamentar:'Parlamentar de teste B',voto:'Não',partido:'TESTE',uf:'DF',sigla_ausente:false}],proxima:2},
 ...[{id:'2233802-438',casa:'camara' as const,turno:2,data:'2026-05-27'},{id:'7106',casa:'senado' as const,turno:1,data:'2026-10-14'},{id:'7107',casa:'senado' as const,turno:2,data:'2026-10-14'}].map(v=>({id_votacao:v.id,casa:v.casa,turno:v.turno,data:v.data,tipo:'nominal' as const,principal:true,link:v.casa==='camara'?camara:senado,fonte:v.casa==='camara'?'Câmara — fixture de teste':'Senado — fixture de teste',coletado_em:collected,placar_conferido:false,placar:null,quorum_exigido:v.casa==='camara'?308:49,resultado:'Não informado',inconsistencia:null,votos_por_partido:null})),
 {id_votacao:'simbolica-teste',casa:'camara',turno:1,data:'2026-05-27',tipo:'simbolica',principal:false,link:camara,fonte:'Câmara — fixture de teste',coletado_em:collected,placar_conferido:false,placar:null,quorum_exigido:308,resultado:'Não informado',inconsistencia:null,votos_por_partido:null}
];
export const lei:Lei={nome:'Emenda Constitucional nº 141, de 16 de outubro de 2026 — Redução da jornada semanal e 2 dias de repouso (fim da escala 6x1)',tipo:'PEC',numero:221,ano:2019,norma:'EC 141/2026',
 ementa:'Dado de teste: ementa da proposição ainda não integrada à rota da lei.',
 resumo:'A Emenda Constitucional nº 141/2026 muda o art. 7º da Constituição. Ela fixa a duração normal do trabalho em até 8 horas por dia e 40 horas por semana e prevê 2 dias de repouso semanal remunerado, sem redução de salário. A redução será feita em etapas: 42 horas semanais a partir de 16/12/2026 e 40 horas a partir de 16/12/2027, segundo o Art. 6º. O repouso de 2 dias vale a partir de 16/12/2026, segundo o Art. 10.',
 link:planalto,fonte:'DOU / Planalto — mock revisado',coletado_em:collected,autor:null,partido:null,uf:null,data_apresentacao:null,situacao_norma:{texto:'Promulgada em 16/10/2026 · DOU 16/10/2026, Ed. Extra A',link:dou},
 vigencia:{data_publicacao:'2026-10-16',regra_geral:{inicio:'publicacao',base_legal:'Art. 10, II'},etapas:[
 {id:'repouso_2_dias_42h',descricao:'repouso de 2 dias por semana e limite de 42 h semanais',dispositivos:['CF art. 7º, XV','EC art. 6º, I','EC art. 3º'],base_legal:'Art. 10, I; Art. 6º, I',prazo:{meses:2,a_partir_de:'publicacao'},data_inicio:'2026-12-16',data_tipo:'calculada'},
 {id:'limite_40h',descricao:'limite de 40 h semanais',dispositivos:['EC art. 6º, II'],base_legal:'Art. 6º, II',prazo:{meses:12,a_partir_de:'repouso_2_dias_42h'},data_inicio:'2027-12-16',data_tipo:'calculada'}],fontes:[
 {nome:'DOU 16/10/2026, Seção 1, Ed. Extra A, p. 2',url:dou,consultado_em:'2026-10-17T11:23-03:00'},
 {nome:'Planalto – EC 141/2026',url:planalto,consultado_em:'2026-10-17T11:22-03:00'}]},
 situacao:[{casa:'camara',situacao:'Transformado em Norma Jurídica',data:'2026-10-16',link:camara,fonte:'Câmara',coletado_em:collected},{casa:'senado',situacao:'TRANSFORMADA EM NORMA JURÍDICA',data:'2026-10-16',link:senado,fonte:'Senado',coletado_em:collected}],
 marcos:[{tipo:'senado',rotulo:'Aprovação no Senado',data:'2026-10-14',prevista:false,fonte:'Senado',link:senado},{tipo:'promulgacao',rotulo:'Promulgação e publicação no DOU',data:'2026-10-16',prevista:false,fonte:'DOU',link:dou},
 {tipo:'42h',rotulo:'Repouso de 2 dias e teto de 42 h',data:'2026-12-16',prevista:true,fonte:'DOU / Planalto',link:planalto,artigo:'Art. 10, I e Art. 6º, I',nota:'data calculada pelo Observatório a partir da publicação'},
 {tipo:'40h',rotulo:'Teto de 40 h',data:'2027-12-16',prevista:true,fonte:'DOU / Planalto',link:planalto,artigo:'Art. 6º, II',nota:'data calculada pelo Observatório a partir da publicação'}],
 votacoes:votes,tramitacoes:Array.from({length:7},(_,i)=>({casa:i%2?'senado':'camara',data:'2026-10-16',descricao:`Evento de tramitação simulado ${i+1}`,fonte:i%2?'Senado':'Câmara',link:i%2?senado:camara,coletado_em:collected}))};
