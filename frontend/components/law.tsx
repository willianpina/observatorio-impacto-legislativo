'use client';
import {useEffect,useState} from 'react';
import type {LawResponse} from '../lib/contrato-lei-v14';
import type {Lei as ExampleLaw} from '../lib/contrato-lei-provisorio';
import {date} from '../lib/types';
import {SourceLink} from './source-link';
import {Vigencia} from './vigencia';
type State={status:'loading'}|{status:'error';seconds:number;message:string}|{status:'unavailable';reason:string}|{status:'ready';data:LawResponse};
export function Law({testMode,example,onData}:{testMode:boolean;example:ExampleLaw|null;onData:(data:LawResponse)=>void}){
  const [state,setState]=useState<State>({status:'loading'});
  useEffect(()=>{
    const controller=new AbortController();
    fetch('/api/oil/lei',{signal:controller.signal,cache:'no-store'}).then(async response=>{
      const body=await response.json();
      if(!response.ok)throw Object.assign(new Error(body?.erro?.mensagem||'Fonte indisponível.'),{seconds:Number(body?.erro?.tentar_novamente_em||response.headers.get('Retry-After'))||60});
      if(body.simulada&&!testMode)return {status:'unavailable',reason:'Resposta de teste recusada no modo normal.'} as State;
      if(body.disponivel===false)return {status:'unavailable',reason:body.motivo||'Dado ainda não disponível'} as State;
      if(body.id_camara!==2233802||!Array.isArray(body.situacao)||!Array.isArray(body.marcos)||!Array.isArray(body.fontes_norma))throw Error('Resposta inesperada da API local.');
      return {status:'ready',data:body} as State;
    }).then(next=>{if(!controller.signal.aborted){setState(next);if(next.status==='ready')onData(next.data);}}).catch(error=>{if(!controller.signal.aborted)setState({status:'error',seconds:error.seconds||60,message:error.message});});
    return()=>controller.abort();
  },[testMode,onData]);
  const data=state.status==='ready'?state.data:null;
  return <section className="panel law-panel" id="lei" data-testid="lei-v14" aria-busy={state.status==='loading'}>
    <h2><span className="section-number">1</span> O que mudou na lei?</h2>
    {state.status==='loading'&&<p role="status">Carregando dados da lei…</p>}
    {state.status==='error'&&<div role="alert"><strong>Não foi possível consultar a lei.</strong><p>{state.message}</p><p>Tente novamente em {state.seconds} segundos.</p></div>}
    {state.status==='unavailable'&&<div className="unavailable"><strong>Dado ainda não disponível</strong><p>{state.reason}</p></div>}
    {data&&<>
      {data.simulada&&<span className="test-badge">Dado de teste</span>}{data.desatualizado&&<p role="status">Última coleta válida</p>}
      <h3>Ementa (texto da fonte)</h3><p className="law-summary">{data.ementa||'Não informado'}</p>
      <SourceLink className="text-link" href={data.norma_gerada?.link||data.fontes_norma[0]?.link||data.situacao_atual.link}>Ver texto da lei completo</SourceLink>
      <p>Situação atual ({data.situacao_atual.casa==='camara'?'Câmara':'Senado'}): {data.situacao_atual.situacao}</p>
      <p className="source">Fonte: {data.fonte} · Coletado em {date(data.coletado_em,true)} (BRT)</p>
      {data.situacao.map(item=><div key={item.casa}><SourceLink href={item.link}>Situação ({item.casa==='camara'?'Câmara':'Senado'}, {date(item.data)}): <span>{item.situacao}</span></SourceLink><small>Fonte: {item.fonte} · Coletado em {date(item.coletado_em,true)} (BRT)</small></div>)}
      <p>Autor: {data.autor??'Não informado'} · {data.partido??'Não informado'} / {data.uf??'Não informado'}</p>
      <p>Referência do partido: {data.partido_referencia??'Não informada'}. {data.autoria_motivo}</p><p>Apresentada em {date(data.data_apresentacao)}</p>
      {data.norma_gerada?<p><SourceLink href={data.norma_gerada.link}>{data.norma_gerada.rotulo}</SourceLink> · {date(data.norma_gerada.data)} · {data.norma_gerada.fonte}</p>:<p>{data.norma_gerada_motivo||'Norma gerada não informada pela fonte.'}</p>}
      {data.situacao_atual.divergencia&&<p>As casas informam situações diferentes.</p>}
      <details><summary>Saiba mais sobre a lei</summary><p>Regra de situação: {data.situacao_atual.regra}. Coleta: {data.coleta_id}. Nível de evidência: descritivo.</p>
        {data.situacao.map(item=><p key={item.casa}>{item.motivo}</p>)}
        <h3>Marcos de calendário</h3>{data.marcos.map(marker=><div key={marker.tipo}><strong>{marker.rotulo}</strong><p>{date(marker.data)}{marker.prevista?' (prevista)':''} · Origem: {marker.origem}</p><p><SourceLink href={marker.link}>{marker.fonte}</SourceLink> · Coletado em {date(data.coletado_em,true)} (BRT)</p></div>)}
        <h3>Fontes da norma</h3>{data.fontes_norma.map(reference=><p key={reference.link}><SourceLink href={reference.link}>{reference.rotulo}</SourceLink> · Coletado em {date(reference.coletado_em,true)} (BRT)</p>)}
      </details>
      <div className="law-meta"><h3>Vigência</h3>{testMode&&data.simulada&&example?<Vigencia vigencia={example.vigencia}/>:<div className="unavailable"><strong>Dado ainda não disponível</strong><p>A fonte integrada não fornece as regras de vigência neste contrato.</p></div>}</div>
      {testMode&&data.simulada&&example&&<div className="law-milestones">{example.marcos.filter(m=>m.prevista).map(m=><div key={m.tipo}><strong>{m.rotulo}</strong><p>{date(m.data)} · {m.artigo}</p><span>{m.nota}</span> · <SourceLink href={m.link}>{m.fonte}</SourceLink></div>)}</div>}
    </>}
  </section>;
}
