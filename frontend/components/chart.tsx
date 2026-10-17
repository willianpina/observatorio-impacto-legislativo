'use client';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Marco } from '../lib/contrato-lei-provisorio';
import type { Series } from '../lib/types';
import { date, LEGEND, number, period } from '../lib/types';

function stamp(p:string){ return Date.UTC(Number(p.slice(0,4)),Number(p.slice(4)),0); }
export function Chart({series,marcos}:{series:Series;marcos:Marco[]}) {
  const income=series.codigo==='rendimento-real', bars=series.medida==='saldo';
  const points=series.pontos.map(p=>({...p,time:stamp(p.periodo),valor:bars && series.ajuste && p.ajuste!==series.ajuste?null:p.valor}));
  const start=points[0]!.time,end=points.at(-1)!.time;
  const common=<><CartesianGrid vertical={false} stroke="#e2e8f0"/><XAxis dataKey="time" type="number" domain={['dataMin','dataMax']} tickFormatter={t=>new Intl.DateTimeFormat('pt-BR',{month:'short',year:'2-digit',timeZone:'UTC'}).format(t)} tick={{fontSize:11,fill:'#475569'}} minTickGap={28}/><YAxis width={54} tickFormatter={v=>number(v)} tick={{fontSize:11,fill:'#475569'}}/><Tooltip labelFormatter={t=>date(new Date(Number(t)).toISOString())} formatter={v=>[`${number(v==null?null:Number(v))} ${series.unidade}`,'Valor']}/>{marcos.filter(m=>Date.parse(m.data)>=start && Date.parse(m.data)<=end).map(m=><ReferenceLine key={m.tipo} x={Date.parse(m.data)} stroke="#64748b" strokeWidth={1} strokeDasharray={m.prevista?'4 4':undefined}/>)}</>;
  return <figure className="chart-figure"><figcaption className="sr-only">{series.nome}, {series.tipo_periodo}, de {period(series.pontos[0]?.periodo)} a {period(series.pontos.at(-1)?.periodo)}. Unidade: {series.unidade}. A tabela de dados está em Saiba mais.</figcaption>
    <div className="chart" role="img" aria-label={`${series.nome}. Valores em ${series.unidade}; série histórica e tabela alternativa em Saiba mais.`}>
      <span className="axis-unit" aria-hidden="true">{series.unidade}</span>
      <ResponsiveContainer width="100%" height={220}>
        {bars?<BarChart data={points} accessibilityLayer>{common}<ReferenceLine y={0} stroke="#475569"/><Bar dataKey="valor" isAnimationActive={false}>{points.map((p,i)=><Cell key={i} fill={p.valor!=null&&p.valor<0?'#475569':'#176952'}/>)}</Bar></BarChart>:<LineChart data={points} accessibilityLayer>{common}<Line type="linear" dataKey="valor" stroke={income?'#6d40ab':'#1e5abd'} strokeWidth={2.5} connectNulls={false} dot={false} activeDot={{r:4}} isAnimationActive={false}/></LineChart>}
      </ResponsiveContainer>
    </div>
    {marcos.length>0&&<div className="marker-list" aria-label="Marcos de calendário">{marcos.map(m=><details key={m.tipo}><summary data-marker data-prevista={String(m.prevista)} style={{borderLeftStyle:m.prevista?'dashed':'solid'}}>{m.rotulo}{m.prevista?' (prevista)':''}<small>{date(m.data)}</small></summary><div className="marker-info">{date(m.data)} · {m.fonte}<br/>{m.artigo}{m.nota&&<p>{m.nota}</p>}<a href={m.link} rel="noreferrer">Fonte do marco: {m.fonte}</a></div></details>)}</div>}
    <p className="chart-legend">{LEGEND}</p>
    {marcos.some(m=>Date.parse(m.data)>end)&&<p className="muted small">Marcos posteriores ao último dado são referências no eixo, sem extensão da série.</p>}
  </figure>;
}
