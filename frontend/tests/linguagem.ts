import { LEGEND } from '../lib/types';
import type {Page} from '@playwright/test';

export const bannedPhrases=['causou','graças a','por causa da lei','depois da aprovação','desde a promulgação','efeito da lei','após a vigência','impacto da lei','antes × depois','antes e depois da lei'];

/** Ferramenta de QA; não altera nem censura respostas das fontes. */
export function languageViolations(text:string,marcos:string[]=[],checkSentences=true):string[] {
  // A exceção vale somente para a legenda literal completa, antes de normalizar.
  const corpus=text.split(LEGEND).join(' ').normalize('NFKC').toLocaleLowerCase('pt-BR');
  const found=bannedPhrases.filter(phrase=>corpus.includes(phrase));
  if(/antes e depois d[aoe]\b/u.test(corpus))found.push('antes e depois de evento');
  if(!checkSentences)return found;
  const variation=/\b(subiu|caiu|aumentou|diminuiu|variação)\b/u;
  for(const sentence of corpus.split(/[.!?\n]+/u)) {
    if(variation.test(sentence)&&(marcos.some(m=>sentence.includes(m.toLocaleLowerCase('pt-BR')))||/\b\d{2}\/\d{2}(?:\/\d{4})?\b/u.test(sentence)||/\b(?:com [ao]|a partir d[ao]) (promulgação|aprovação|vigência|marco|lei)\b/u.test(sentence))) found.push('marco e variação na mesma frase');
  }
  return found;
}

/** Cada bloco é avaliado isoladamente; não relaciona frases de blocos distintos. */
export async function scanLanguageBlocks(page:Page,marcos:string[]=[]):Promise<string[]> {
  const blocks=await page.locator('p,h1,h2,h3,h4,figcaption,td,th,summary,li,strong,span,small,dd,dt,label,button,caption,[aria-label],[title],[alt]').evaluateAll(elements=>elements.map(element=>(element.textContent||'')+' '+['aria-label','title','alt'].map(attribute=>element.getAttribute(attribute)||'').join(' ')));
  return blocks.flatMap(block=>languageViolations(block,marcos));
}
