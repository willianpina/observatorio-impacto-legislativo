'use client';
import {BookOpen,FileCheck2} from 'lucide-react';
import type {DataState,Window} from '../lib/types';
import type {LawResponse} from '../lib/contrato-lei-v14';
import {date,TITLES} from '../lib/types';
import {csvCell} from '../lib/csv';
import {SourceLink} from './source-link';

function download(name:string,rows:unknown[][]){
  const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(row=>row.map(csvCell).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function EvidenceSources({codes,states,lawData,window}:{codes:string[];states:Record<string,DataState>;lawData:LawResponse|null;window:Window}){
  const references=lawData?[
    ...lawData.situacao.map(s=>({nome:s.casa==='camara'?'Câmara dos Deputados':'Senado Federal',fornece:'Situação da proposição',id:s.casa==='camara'?String(lawData.id_camara):String(lawData.id_senado),situacao:s.disponivel?s.situacao:(s.motivo||'Dado ainda não disponível'),link:s.link,coletado_em:s.coletado_em})),
    ...lawData.fontes_norma.map(r=>({nome:r.rotulo,fornece:'Texto da norma e referência de publicação',id:lawData.norma_gerada?.rotulo||r.link.split('/').filter(Boolean).at(-1)||'Não informado',situacao:'Referência consultada',link:r.link,coletado_em:r.coletado_em}))
  ]:[];
  return <div className="evidence-grid">{codes.map(code=>{
    const state=states[code],data=state?.status==='ready'?state.data:null;
    const status=state?.status==='error'?'Fonte indisponível':!state||state.status==='loading'?'Carregando dados…':!data?.disponivel?'Dado ainda não disponível':data.desatualizado?'Última coleta válida':'Coleta disponível';
    return <article key={code} className="evidence-card"><BookOpen size={19}/><h3>{TITLES[code]}</h3>
      <dl><dt>Fonte</dt><dd>{data?.fonte||(code==='caged-saldo'?'MTE / Novo Caged':'IBGE / SIDRA')}</dd><dt>O que fornece</dt><dd>{TITLES[code]}</dd><dt>Tabela/ID</dt><dd>{data?.tabela_ou_arquivo||'Não informado'}</dd><dt>Situação</dt><dd>{status}</dd><dt>Data da coleta</dt><dd>Coletado em {date(data?.coletado_em,true)}{data?.coletado_em?' (BRT)':''}</dd></dl>
      {data?.link&&<SourceLink href={data.link}>Abrir fonte oficial</SourceLink>}
      {data?.disponivel&&data.pontos.length>0&&<button onClick={()=>download(`${code}-${window}.csv`,[['periodo','valor','unidade','lacuna','coleta_id','coletado_em'],...data.pontos.map(p=>[p.periodo,p.valor,p.unidade,p.valor===null,p.coleta_id,p.coletado_em])])}>Baixar CSV — {TITLES[code]}</button>}
    </article>;
  })}{references.map((s,i)=><article className="evidence-card" key={i}><FileCheck2 size={19}/><h3>{s.nome}</h3>{lawData?.simulada&&<span className="test-badge">Dado de teste</span>}
    <dl><dt>O que fornece</dt><dd>{s.fornece}</dd><dt>Tabela/ID</dt><dd>{s.id}</dd><dt>Situação</dt><dd>{s.situacao}</dd><dt>Data da coleta</dt><dd>Coletado em {date(s.coletado_em,true)} (BRT)</dd></dl>
    <SourceLink href={s.link}>Consultar referência oficial</SourceLink>
    <button onClick={()=>download(`fonte-legislativa-${i+1}.csv`,[['fonte','o_que_fornece','tabela_id','situacao','link','coletado_em','simulada'],[s.nome,s.fornece,s.id,s.situacao,s.link,s.coletado_em,lawData?.simulada]])}>Baixar CSV — {s.nome}</button>
  </article>)}</div>;
}
