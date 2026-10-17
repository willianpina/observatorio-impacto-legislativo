'use client';
import {useState} from 'react';
import {BarChart,Bar,ResponsiveContainer,XAxis,YAxis,Tooltip} from 'recharts';
import type {Lei,Votacao} from '../lib/contrato-lei-provisorio';
import {date} from '../lib/types';

function Vote({vote}:{vote:Votacao}){
  const [count,setCount]=useState(1);
  const p=vote.placar;
  const checked=vote.placar_conferido&&p!==null&&!vote.inconsistencia;
  const validTotals=!!p&&p.total===p.sim+p.nao+p.abstencao;
  const parties=vote.votos_por_partido;
  const partyMatch=!!p&&!!parties&&(['sim','nao','abstencao'] as const).every(key=>parties.reduce((n,x)=>n+x[key],0)===p[key])&&parties.every(x=>x.presentes===x.sim+x.nao+x.abstencao&&x.base_percentual==='presentes');
  const approved=checked&&validTotals&&(!parties||partyMatch)&&p.sim>=vote.quorum_exigido&&vote.resultado.toLocaleLowerCase('pt-BR').includes('aprovad');
  return <article className="vote" data-testid={`vote-${vote.id_votacao}`}><h4>{vote.casa==='camara'?'Câmara':'Senado'} — {vote.turno}º turno · {date(vote.data)}</h4><p className="small muted">ID da votação: {vote.id_votacao}</p>
    <span className="evidence-badge">Descritivo</span><span className="test-badge">Dado de teste</span>
    {vote.tipo==='simbolica'?<p>Votação simbólica, sem placar nominal (sem registro de votos individuais).</p>:!checked?<p>Placar em conferência</p>:<>
      {(!validTotals||vote.inconsistencia)&&<p className="notice">O resultado informado pela fonte não bate com o placar; em conferência.</p>}
      {validTotals&&<><dl className="score"><div><dt>Sim</dt><dd>{p.sim}</dd></div><div><dt>Não</dt><dd>{p.nao}</dd></div><div><dt>Abstenção</dt><dd>{p.abstencao}</dd></div></dl><p>Total: {p.total}</p><p>Obstrução: {p.obstrucao} (fora do total)</p><p>Ausentes: {p.ausentes??'Não informado'} (fora do total)</p></>}
      <p>Quórum exigido: {vote.quorum_exigido} votos sim (3/5).</p>{approved&&<strong className="result-label">Aprovada</strong>}
      {vote.casa==='senado'&&<p>Placar calculado a partir dos votos individuais registrados pelo Senado.</p>}
      {parties&&partyMatch?<><p>Porcentagem calculada sobre os presentes. Partido registrado na data do voto.</p><div className="party-chart"><ResponsiveContainer width="100%" height={150}><BarChart data={[...parties].sort((a,b)=>b.presentes-a.presentes)} layout="vertical"><XAxis type="number"/><YAxis type="category" dataKey="partido"/><Tooltip/><Bar dataKey="sim" fill="#1e5abd" isAnimationActive={false}/></BarChart></ResponsiveContainer></div><table><caption>Votos por partido</caption><thead><tr><th>Partido</th><th>Sim</th><th>Não</th><th>Abstenção</th><th>% sim / presentes</th></tr></thead><tbody>{parties.map(x=><tr key={x.partido}><th>{x.partido}</th><td>{x.sim}</td><td>{x.nao}</td><td>{x.abstencao}</td><td>{x.base_percentual==='presentes'?`${x.percentual_sim}%`:'Não informado'}</td></tr>)}</tbody></table></>:<p>{vote.motivo || 'Divisão por partido indisponível ou em conferência.'}</p>}
      {vote.votos&&<details><summary>Ver votos individuais</summary><ul>{vote.votos.slice(0,count).map((v,i)=><li key={i}>{v.parlamentar}: {v.voto} · <span>{v.sigla_ausente?'sigla não informada pela fonte':`${v.partido} / ${v.uf}`}</span></li>)}</ul>{count<vote.votos.length&&<button onClick={()=>setCount(vote.votos!.length)}>Carregar mais votos</button>}</details>}
    </>}
    <p className="source"><a href={vote.link}>Fonte: {vote.fonte}</a><br/>Coletado em {date(vote.coletado_em,true)} (BRT)</p>
  </article>;
}
export function Voting({lei}:{lei:Lei|null}){
  const [events,setEvents]=useState(5);
  return <section className="panel" id="votacao"><h2>Quem propôs e como foi a votação</h2>{!lei?<p className="unavailable"><strong>Dado ainda não disponível</strong><br/>A integração legislativa será disponibilizada na O3.</p>:<><p>Proposta por {lei.autor??'Não informado'} · {lei.partido??'Não informado'} / {lei.uf??'Não informado'}.</p><p>Apresentada em {date(lei.data_apresentacao)}</p>
    {(['camara','senado'] as const).map(casa=><div key={casa}><h3>{casa==='camara'?'Câmara dos Deputados':'Senado Federal'}</h3>{lei.votacoes.filter(v=>v.casa===casa&&v.principal).map(v=><Vote key={v.id_votacao} vote={v}/>)}<details><summary>Outras votações — {casa==='camara'?'Câmara':'Senado'}</summary>{lei.votacoes.filter(v=>v.casa===casa&&!v.principal).map(v=><Vote key={v.id_votacao} vote={v}/>)}</details></div>)}
    <h3>Tramitação</h3><ol className="timeline">{lei.tramitacoes.slice(0,events).map((event,i)=><li key={i}><strong>{date(event.data)} · {event.casa==='camara'?'Câmara':'Senado'}</strong><p>{event.descricao}</p><a href={event.link}>{event.fonte}</a><small>Coletado em {date(event.coletado_em,true)} (BRT)</small></li>)}</ol>{events<lei.tramitacoes.length&&<button onClick={()=>setEvents(lei.tramitacoes.length)}>Carregar mais tramitações</button>}</>}
  </section>;
}
