import type {DataState} from '../lib/types';
import {Classification,CollectionStatus,Reading,Source} from './indicator';

export function IndicatorSummary({state}:{state:DataState|undefined}){
  if(!state||state.status==='loading')return <p>Carregando dados…</p>;
  if(state.status==='error')return <p>Não conseguimos obter dados de {state.source} agora. Consulte o aviso no card para tentar de novo.</p>;
  const data=state.data;
  return <>
    {data.simulada&&<span className="test-badge">Dado de teste · simulado</span>}
    <CollectionStatus data={data}/>
    {!data.disponivel?<><p>Dado ainda não disponível</p><p>{data.motivo||'Não informado'}</p></>:data.pontos.length===0?<p>Ainda não há dados de {data.fonte} para este período.</p>:<><Reading data={data} summary/><Classification data={data}/></>}
    <Source data={data}/>
  </>;
}
