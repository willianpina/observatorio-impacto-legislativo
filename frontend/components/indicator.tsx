'use client';
import { useEffect,useState } from 'react';
import { CircleHelp, Download, ExternalLink, RefreshCw } from 'lucide-react';
import type { Marco } from '../lib/contrato-lei-provisorio';
import type { DataState, Series, Window } from '../lib/types';
import { date, description, number, period, TITLES } from '../lib/types';
import { Chart } from './chart';

export function Source({data}:{data:Series}){ const attribution=data.codigo==='caged-saldo'?`${data.fonte}, ${data.tabela_ou_arquivo??'Tabela não informada'}, arquivo ${data.arquivo_origem??'Não informado'}, licença ${data.licenca??'Não informada'}`:`${data.fonte} · ${data.tabela_ou_arquivo}`;return <p className="source">Fonte: {data.link?<a href={data.link} rel="noreferrer">{attribution}</a>:attribution}<br/>Coletado em {date(data.coletado_em,true)} {data.coletado_em?'(BRT)':''}</p>; }
export function Classification({data}:{data:Series}){ return data.classificacao?<span className="classification"><span aria-hidden="true">{data.classificacao==='subiu'?'▲':data.classificacao==='caiu'?'▼':'='}</span> {data.classificacao==='estavel'?'estável':data.classificacao}<small>{data.classificacao_origem==='ibge'?'classificação publicada pelo IBGE':'calculado pelo Observatório com a margem de erro do IBGE'}</small></span>:null; }

export function Indicator({code,window,testMode,marcos,onState,onInvalidWindow}:{code:string;window:Window;testMode:boolean;marcos:Marco[];onState:(code:string,s:DataState)=>void;onInvalidWindow:()=>void}) {
  const [state,setState]=useState<DataState>({status:'loading'}),[reload,setReload]=useState(0);
  useEffect(()=>{
    const controller=new AbortController(); setState({status:'loading'});
    fetch(`/api/oil/indicadores/${code}/serie?janela=${window}`,{signal:controller.signal}).then(async r=>{
      const body=await r.json();
      if(r.status===422){ if(window!=='5a') onInvalidWindow(); throw new Error('Parâmetro janela inválido; selecionamos 5 anos.'); }
      if(!r.ok) throw new Error(body?.erro?.fonte || 'API local');
      if(typeof body.disponivel!=='boolean'||!Array.isArray(body.pontos)) throw new Error('Resposta inesperada da API local');
      if(body.simulada&&!testMode) return {...body,disponivel:false,pontos:[],motivo:'Resposta de teste recusada no modo normal.'};
      if(body.pontos.some((p:{valor:unknown})=>p.valor!==null&&(typeof p.valor!=='number'||!Number.isFinite(p.valor)))) throw new Error('Resposta inesperada da API local');
      return body as Series;
    }).then(data=>{if(!controller.signal.aborted){const result:DataState={status:'ready',data};setState(result);onState(code,result);}}).catch(e=>{if(!controller.signal.aborted){const result:DataState={status:'error',source:e.message};setState(result);onState(code,result);}});
    return()=>controller.abort();
  },[code,window,reload,testMode,onState,onInvalidWindow]);
  const data=state.status==='ready'?state.data:null;
  function csv(){
    if(!data)return;
    const cell=(v:unknown)=>`"${String(v??'').replace(/^[=+@]/,"'").replaceAll('"','""')}"`;
    const rows=[['periodo','valor','unidade','cv','variacao_anual','variacao_anual_unidade','lacuna','coleta_id','coletado_em','ajuste','competencia_coleta'],...data.pontos.map(p=>[p.periodo,p.valor,p.unidade,p.cv,p.variacao_anual,data.variacao_anual_unidade,p.valor===null,p.coleta_id,p.coletado_em,p.ajuste,p.competencia_coleta])];
    const url=URL.createObjectURL(new Blob(['\uFEFF'+rows.map(r=>r.map(cell).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`${code}-${window}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <article className="indicator-card" data-testid={`card-${code}`} aria-labelledby={`heading-${code}`}>
    <div className="card-heading"><h3 id={`heading-${code}`}>{TITLES[code]}</h3><CircleHelp size={17} aria-label={code==='desocupacao'?'Parcela das pessoas na força de trabalho que estão desocupadas.':code==='rendimento-real'?'Rendimento habitual de todos os trabalhos, já corrigido pelo IBGE.':'Admissões menos desligamentos de vínculos formais.'}/></div>
    <div aria-live="polite" aria-busy={state.status==='loading'}>
    {state.status==='loading'&&<div className="loading"><div className="skeleton"/>Carregando dados…</div>}
    {state.status==='error'&&<div className="unavailable error"><strong>Não conseguimos obter dados de {state.source} agora.</strong><p>Tente novamente em instantes.</p><button onClick={()=>setReload(v=>v+1)}><RefreshCw size={15}/> Tentar de novo</button></div>}
    {data&&(!data.disponivel?<div className="unavailable"><strong>Dado ainda não disponível</strong><p>{data.motivo}</p><span className="muted">Fonte prevista: {code==='caged-saldo'?'MTE / Novo Caged':data.fonte}</span></div>:data.pontos.length===0?<div className="unavailable">Ainda não há dados de {data.fonte} para este período.</div>:<>
      {testMode&&<span className="test-badge">Dado de teste · simulado</span>}
      <div data-testid={`insight-${code}`}>{data.medida==='saldo'?<><p className="insight" data-testid="caged-valor-oficial">Último dado: {number(data.valor)} {data.unidade} ({period(data.periodo)}).</p><p>Saldo com ajustes</p><p className="caged-comparison" data-testid="caged-comparacao">Cálculo do Observatório a partir de dados do MTE: {number(data.variacao_anual)} {data.variacao_anual_unidade} em relação ao mesmo período do ano anterior.</p></>:<p className="insight">{description(data)}</p>}<Classification data={data}/></div>
      <p className="metadata">{data.medida==='taxa'?'Taxa (%)':data.medida==='saldo'?'Saldo de vagas':'Valor em R$'} · {data.tipo_periodo==='trimestre_movel'?'Trimestre móvel':'Mensal'}{data.medida!=='taxa'&&data.tipo_valor&&<> · {data.tipo_valor==='real'?(data.base_precos?`Real (preços de ${data.base_precos})`:'Real, base de preços do IBGE em verificação'):'Nominal'}</>}</p>
      <span className="evidence-badge">Descritivo</span>
      {data.desatualizado&&<p className="notice">Fonte fora do ar. Mostrando a última coleta válida de {date(data.coletado_em)}</p>}
      {data.atrasado_calendario&&<p className="calendar-delay">A fonte ainda não publicou o período esperado no calendário.</p>}
      <Chart series={data} marcos={marcos}/><Source data={data}/>
      <details className="more"><summary>Saiba mais</summary><p>Comparação: mesmo período do ano anterior. CV: {number(data.cv)}%. Coleta: {data.coleta_id ?? 'Não informado'}.</p><a href="#metodologia">Consultar metodologia</a>
        {data.pontos.some(p=>p.valor===null)&&<p>Há períodos sem dado na fonte.</p>}
        {data.medida==='saldo'&&<><p>As séries do Novo Caged são revisadas mensalmente. O número de um mês pode mudar nas divulgações seguintes.</p><p>Meses com outro tipo de ajuste não entram no gráfico.</p><Source data={data}/></>}
        <div className="table-scroll" tabIndex={0} role="region" aria-label={`Tabela de ${TITLES[code]}`}><table><caption>Dados de {TITLES[code]}</caption><thead><tr>{['Período','Valor','Unidade','CV (%)','Variação anual','Lacuna','Ajuste / competência','Marco'].map(h=><th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{data.pontos.map(p=><tr key={p.periodo}><th scope="row">{period(p.periodo)}</th><td>{number(p.valor)}</td><td>{p.unidade}</td><td>{number(p.cv)}</td><td>{number(p.variacao_anual)} {data.variacao_anual_unidade}</td><td>{p.valor===null?'sim':'não'}</td><td>{p.ajuste?`saldo ${p.ajuste==='sem_ajuste'?'sem ajuste':'com ajuste'}, competência ${p.competencia_coleta?.slice(4)}/${p.competencia_coleta?.slice(0,4)}`:'Não se aplica'}</td><td>{marcos.filter(m=>m.data.slice(0,7).replace('-','')===p.periodo).map(m=>m.rotulo).join('; ')||'—'}</td></tr>)}</tbody></table></div>
        <button onClick={csv}><Download size={15}/> Baixar CSV</button>
      </details>
    </>)}
    </div>
    {data?.disponivel&&<a className="card-link" href={data.link || '#fontes'}>Consultar fonte <ExternalLink size={13}/></a>}
  </article>;
}
