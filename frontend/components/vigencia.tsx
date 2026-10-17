import type { Vigencia as VigenciaData } from '../lib/contrato-lei-provisorio';
import { etapaPrevista, vigenciaText, todayInBrasilia } from '../lib/vigencia';
import { date } from '../lib/types';
import { SourceLink } from './source-link';

export function Vigencia({vigencia}:{vigencia:VigenciaData}) {
  const hoje=todayInBrasilia();
  return <div className="vigencia">
    <strong data-testid="vigencia-resumo">{vigenciaText(vigencia,hoje)}</strong>
    <details><summary>Saiba mais sobre a vigência</summary>
      <p>As datas previstas foram calculadas a partir da publicação (2 meses e mais 1 ano), conforme o Art. 6º e o Art. 10 da EC. O texto da emenda não traz as datas por extenso.</p>
      <ul><li>Publicação: {date(vigencia.data_publicacao)} · {vigencia.regra_geral.base_legal}</li>
      {vigencia.etapas.map(e=><li key={e.id}>{e.descricao}: {date(e.data_inicio)}{etapaPrevista(e,hoje)?' (prevista)':''} · {e.base_legal}<br/>{e.dispositivos.join('; ')}</li>)}</ul>
      {vigencia.fontes.map(f=><p className="source" key={f.url}><SourceLink href={f.url}>{f.nome}</SourceLink><br/>Consultado em {date(f.consultado_em,true)} (BRT)</p>)}
    </details>
  </div>;
}
