# Adendo 1 à Missão O4 (17/10/2026) — correção para o Codex

Fonte: confirmação do Especialista Legislativo (`legislativo/confirmacao-ec141-2026-10-17.md`), feita no DOU de 16/10/2026, Seção 1, Edição Extra A, p. 2, e no Planalto. Este adendo substitui os pontos da O4 que conflitarem com ele.

## 1. Aviso (troca o texto fixo da O4)
Use exatamente este texto: «É cedo para afirmar. A emenda começa a valer em etapas, e os dados oficiais saem com atraso. Mudanças nos indicadores podem ter várias causas.» Logo abaixo, mantenha o selo «Nível de evidência: descritivo».
O aviso é texto fixo da tela, não é dado: aparece sempre, em modo normal e em modo teste, sem botão de fechar. O teste procura esse texto exato.

## 2. Resumo da lei (só no mock por enquanto)
Pela spec §3, o resumo é texto revisado à mão pelo Especialista Legislativo, com o link «Ver texto da lei completo» para a fonte oficial. Até existir a rota da lei, ele entra só no mock (`OIL_TEST_MODE=1`), com o selo «Dado de teste». Em modo normal, aparece «Dado ainda não disponível». Texto:
> A Emenda Constitucional nº 141/2026 muda o art. 7º da Constituição. Ela fixa a duração normal do trabalho em até 8 horas por dia e 40 horas por semana e prevê 2 dias de repouso semanal remunerado, sem redução de salário. A redução será feita em etapas: 42 horas semanais a partir de 16/12/2026 e 40 horas a partir de 16/12/2027, segundo o Art. 6º. O repouso de 2 dias vale a partir de 16/12/2026, segundo o Art. 10.
Link: https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm

## 3. Nome e situação (no mock)
- Nome: «Emenda Constitucional nº 141, de 16 de outubro de 2026 — Redução da jornada semanal e 2 dias de repouso (fim da escala 6x1)».
- Situação: «Promulgada em 16/10/2026 · DOU 16/10/2026, Ed. Extra A», com link para https://www.in.gov.br/web/dou/-/emenda-constitucional-n-141-738818165.
- Vigência: «Em vigor em etapas: 16/10/2026, 16/12/2026 e 16/12/2027 (ver Art. 6º e Art. 10)».
- A lista `situacao` por casa continua como na spec §3. No mock, vão os dois itens: Câmara, «Transformado em Norma Jurídica» (16/10/2026), e Senado, «TRANSFORMADA EM NORMA JURÍDICA» (16/10/2026), cada um com o seu link, mostrados como a fonte escreve.

## 4. Marcos no mock (lista `marcos`)
| data | rótulo | prevista | base |
|---|---|---|---|
| 14/10/2026 | Aprovação no Senado | false | Senado |
| 16/10/2026 | Promulgação e publicação no DOU | false | DOU |
| 16/12/2026 | Repouso de 2 dias e teto de 42 h | true | Art. 10, I e Art. 6º, I |
| 16/12/2027 | Teto de 40 h | true | Art. 6º, II |

- As datas com `prevista: true` levam a nota «data calculada pelo Observatório a partir da publicação», junto do artigo da EC (por exemplo, «Art. 6º, I»). Essa nota troca o selo antigo «ainda não conferida no DOU».
- A tela não calcula nenhuma data, só mostra a que vem no dado.
- Nos gráficos, as linhas continuam cinza, tracejadas quando `prevista: true`, com a legenda «Marcos de calendário. Não indicam efeito da lei.»

## 5. Testes a acrescentar
- O aviso exato do item 1 aparece nos dois modos.
- Resumo, nome e situação só aparecem com `OIL_TEST_MODE=1` e com o selo «Dado de teste». Em modo normal, aparece «Dado ainda não disponível».
- Cada marco com `prevista: true` mostra o traço tracejado, a nota e o artigo.
- O teste de frases proibidas cobre também o resumo e os rótulos dos marcos.
