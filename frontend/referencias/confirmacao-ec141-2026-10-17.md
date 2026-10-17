# Confirmação oficial da EC 141/2026
Consulta: 17/10/2026, 11:22–11:23 (BRT). Este arquivo atualiza `votacoes-e-vigencia-ec141-2026-10-16.md`.

## 1. Fontes e resultado
| Fonte | Link exato | Hora (BRT) | Resultado |
|---|---|---|---|
| Planalto | https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm | 11:22:07 | **200.** Texto completo: "EMENDA CONSTITUCIONAL Nº 141, DE 16 DE OUTUBRO DE 2026". A página diz: "Este texto não substitui o publicado no DOU 16.10.2026 - Edição extra". |
| Planalto (variações) | `.../emc/emc141-2026.htm` e `.../constituicao/quadro_emc.htm` | 11:22 | 404 nas duas |
| DOU, leitura do jornal | https://www.in.gov.br/leiturajornal?data=16-10-2026&secao=do1e | 11:22:13 | **200.** A lista traz "EMENDA CONSTITUCIONAL Nº 141": pubName DO1_EXTRA_A, edição 196-A, página 2, pubDate 16/10/2026. |
| DOU, ato | https://www.in.gov.br/web/dou/-/emenda-constitucional-n-141-738818165 | 11:22:46 | **200.** "Seção: 1 - Extra A". O texto do Art. 6º e do Art. 10 foi lido nessa página. |
| Câmara (API) | https://dadosabertos.camara.leg.br/api/v2/proposicoes/2233802/tramitacoes?dataInicio=2026-10-14&dataFim=2026-10-17 | 11:22:07 | **Atualizada.** Em 16/10/2026: "Transformação em Norma Jurídica". O despacho diz: "Transformado na Emenda Constitucional 141/2026. DOU 16/10/2026 PÁG 02 COL 02 - Edição Extra A." Situação: "Transformado em Norma Jurídica" (codSituacao 1140). |
| Senado (API) | https://legis.senado.leg.br/dadosabertos/processo/9056435?v=1 | 11:22:07 | Situação "TRANSFORMADA EM NORMA JURÍDICA" (16/10/2026). O campo **`normaGerada` continua vazio** `{}`, com última atualização em 16/10/2026, 16:23. |
| LexML | https://www.lexml.gov.br/urn/urn:lex:br:federal:emenda.constitucional:2026-10-16;141 | 11:22:55 | 200, mas só 1 KB e sem o texto da norma. Não confirma nada. |
| Câmara legin | não consultado | — | — |

**Conclusão:** a promulgação está confirmada em fonte oficial. É a **Emenda Constitucional nº 141, de 16 de outubro de 2026**, publicada no **DOU de 16/10/2026, Seção 1 – Edição Extra A (nº 196-A), p. 2**.

## 2. Comparação com a minuta do Senado
Comparei com a minuta de 15/10/2026, ignorando espaços e pontuação.
- **Art. 6º:** idêntico.
- **Art. 10:** idêntico.
- No Planalto, o inciso XV traz a marcação "(Vigência)", que é uma remissão editorial.

Texto publicado (DOU e Planalto), citação literal:
> Art. 6º A redução da duração do trabalho normal para 40 (quarenta) horas semanais será implementada de forma progressiva, observado o seguinte: I - 2 (dois) meses após a publicação desta Emenda Constitucional, a duração do trabalho normal não excederá a 42 (quarenta e duas) horas semanais; II - 1 (um) ano após o decurso do prazo de que trata o inciso I deste artigo, a duração do trabalho normal não excederá a 40 (quarenta) horas semanais.

> Art. 10. Esta Emenda Constitucional entra em vigor: I - após decorridos 2 (dois) meses de sua publicação, em relação à alteração promovida pelo art. 1º desta Emenda Constitucional no inciso XV do caput do art. 7º da Constituição Federal; II - na data de sua publicação, em relação aos demais dispositivos.

## 3. Datas calculadas a partir da publicação (16/10/2026)
O cálculo conta mês a mês: o prazo termina no dia de mesmo número do mês final. O texto não fixa as datas, então o dia exato de início pode ter interpretação jurídica diferente. A tela deve citar o artigo da EC junto com cada data.
| O quê | Base | Data calculada |
|---|---|---|
| Demais dispositivos (incluindo o novo inciso XIII: 8 h/dia e 40 h/semana como teto constitucional) | Art. 10, II | 16/10/2026 |
| Repouso semanal de 2 dias (inciso XV) | Art. 10, I | 16/12/2026 |
| Teto de 42 h semanais | Art. 6º, I | 16/12/2026 |
| Cláusulas coletivas incompatíveis ficam sem efeito | Art. 3º | 16/12/2026 |
| Teto de 40 h semanais | Art. 6º, II | 16/12/2027 |
| Prazo máximo de aditamento dos contratos públicos | Art. 9º | 16/10/2027 |

Observação: o Art. 10, II, põe o inciso XIII (40 h) em vigor na publicação, mas o Art. 6º implanta a redução de forma progressiva. A tela deve mostrar as duas informações como estão no texto, sem interpretar.

## 4. Textos para a tela
**(a) Nome da lei:**
"Emenda Constitucional nº 141, de 16 de outubro de 2026 — Redução da jornada semanal e 2 dias de repouso (fim da escala 6x1)"
Rótulo de situação: «Promulgada em 16/10/2026 · DOU 16/10/2026, Ed. Extra A». Rótulo de vigência: «Em vigor em etapas: 16/10/2026, 16/12/2026 e 16/12/2027 (ver Art. 6º e Art. 10)».

**(b) Aviso:**
«É cedo para afirmar. A emenda começa a valer em etapas, e os dados oficiais saem com atraso. Mudanças nos indicadores podem ter várias causas.»

**(c) Resumo:**
A Emenda Constitucional nº 141/2026 muda o art. 7º da Constituição. Ela fixa a duração normal do trabalho em até 8 horas por dia e 40 horas por semana e prevê 2 dias de repouso semanal remunerado, sem redução de salário. A redução será feita em etapas: 42 horas semanais a partir de 16/12/2026 e 40 horas a partir de 16/12/2027, segundo o Art. 6º. O repouso de 2 dias vale a partir de 16/12/2026, segundo o Art. 10.

Arquivos de apoio: `planalto_emc141.html` e `.txt`, `dou_emc141.html`, `texto_final.txt` (minuta).
