# O4 — revisão da tela atual, 19/10/2026

Branch `codex/o4-tela-lei`, base `main` `c000ee67401493998ffe2ce14f743dc14b304272`. Entrega em novo PR rascunho, sem merge, CI, deploy, analytics ou serviço pago. O usuário confirmou a revisão da tela existente, preservando a API real. A branch local da primeira O4 foi preservada com o nome `codex/o4-tela-lei-historico-973a8d8`; o push desta revisão é normal, sobre histórico ancestral.

## Problemas corrigidos

- O resumo agora mostra a origem, o link oficial seguro e a coleta em BRT de cada indicador; o selo de teste depende do payload. Reutiliza a leitura dos valores e a classificação recebida da API, sem cálculos novos.
- Série indisponível mostra o motivo no resumo; série vazia não mantém o número do último dado. Avisos de última coleta válida e calendário acompanham os cards também no resumo.
- Fontes e dados distingue falha de conexão, carregamento e ausência de dados. Campo sem informação usa «Não informado».
- O rodapé escolhe a data mais recente entre índice, séries e fontes legislativas (proposição, casas e referências da norma), comparando os instantes completos. O teste adicional a0c7d85 reproduziu três falhas e uma aprovação; os quatro casos passaram após a correção seguinte, antes da matriz final.
- Fontes e dados encerra a ordem móvel e a ordem do documento, após seção 3 e votação. Mantidos o resumo na lateral no desktop e antes da seção 1 no celular.

## Testes antes do código

`2f439c7`: testes novos contra a base, **12 falhas e 10 aprovações**. `bb63352`: teste de ordem móvel, **1 falha**. Falhas de comportamento confirmadas, sem contar erro de infraestrutura. Correção `f4700bd`: **23 novos testes aprovados (1,2 min)**. O teste adicional b40a3ea comprovou a fixture do Caged com CV indevido (1 falha de asserção); a correção 2df5bff mantém metadados mensais, CV e classificação nulos nos pontos. A primeira execução dessa sonda falhou por diretório de trabalho incorreto e foi descartada como infraestrutura, antes da reprodução válida. A suíte intermediária passou com 149; a matriz final foi executada novamente com 153.

| Suíte | Aprovados | Falhas | Pulados |
|---|---:|---:|---:|
| Backend da base (sem PoC) | 243 | 0 | 2 |
| PoC separada | 39 | 0 | 0 |
| Playwright completo | 153 | 0 | 0 |

Axe: **36 cenários**, zero violações graves/críticas. Typecheck e build aprovados. Os dois testes ao vivo opcionais do backend continuam desligados. O backend e a PoC foram testados com PostgreSQL descartável em porta aleatória; contêiner encerrado. Nada em `backend/` ou `poc/` foi alterado.

Resumos literais do pytest:
```text
243 passed, 2 skipped, 1 warning in 96.61s (0:01:36)
39 passed, 1 warning in 4.48s
```

Asserções legadas continuam cobrindo lacuna, filtro sem agregação, fonte fora do ar, 503 e nova tentativa, cores e linhas previstas, linguagem, links seguros, selo de simulação e placar do exemplo 2233802-424 (472/22/0, total 494 e obstrução 1 fora do total). Não há votações reais inventadas.

## Capturas e rastreabilidade

Há dez capturas, 360 e 1280 px, nos estados normal, lacuna (`gap`), Caged indisponível (`unavailable`), fonte fora do ar (`stale`) e modo de teste (`test`), em `evidencias/o4-revisao-2026-10-19/`. Todas são **fixtures de teste**, identificadas no nome e no JSON; as capturas do modo normal verificam o comportamento com payload não simulado, porém continuam sendo respostas controladas de teste. Nenhuma dessas imagens comprova nova coleta oficial. Os detalhes ficam abertos para axe e tabela de dados. Os demais 26 cenários de axe legados também passaram.

## Contrato e diferenças da missão histórica

- Stack Next.js App Router, TypeScript, Tailwind e Recharts já existia na main; foi preservada, sem reinstalação ou troca de dependência.
- A missão histórica dizia que a rota legislativa não existia. Agora ela existe: a tela normal mantém o proxy com id fixo e o contrato [v1.4.1](../docs/o3/contrato-api-v1.4.1-delta.md), com os tipos [contrato-lei-v14.ts](lib/contrato-lei-v14.ts). Não se voltou ao envelope antigo nem a texto legislativo simulado no modo normal.
- O [contrato provisório v0.2](lib/contrato-lei-provisorio.ts) já existia e foi preservado somente para os exemplos de vigência, votação e tramitação em modo de teste. A v1.4.1 não fornece esses três blocos completos nem resumo revisado: no modo normal, continuam indisponíveis com motivo. A ementa permanece literal da fonte, na seção da lei; nenhum resumo é inventado.
- Mantidos o aviso do Adendo 1, as atribuições e a separação entre saldo do MTE e comparação do Observatório do Adendo 2. Não foram reintroduzidos conteúdo de notícias, IA, busca ativa ou módulos pagos do protótipo.
- As referências oficiais e tabelas usam os dados recebidos da API; os marcos não são recalculados no frontend. Nenhum número econômico de produção foi digitado no código. As séries continuam com sua frequência original.
- A conferência nova não abrange parecer jurídico dos artigos, nova ingestão ou aprovação de placares reais; QA e Segurança farão a revisão do PR, coordenada pelo Willian.
- Desvios visuais preservados da interface existente: a ementa e as situações literais ficam na seção 1, em vez de repetidas integralmente no cabeçalho; B8 usa cartões também no desktop, em vez da tabela indicada na spec. A revisão mantém esses componentes já entregues e registra as diferenças para a decisão de QA e Frontend. Não se declara equivalência pixel a pixel com o protótipo, que continha módulos retirados pelos adendos. O axe automático não substitui a auditoria manual completa de acessibilidade.

## Caged real — execução anterior, separada desta revisão

A coleta única solicitada foi executada primeiro, na base c000ee67, e enviada **só como evidência** na branch `codex/caged-validacao-real`, commit `c00b563d0dd27963f74a3d7b8de0b9d52ef2f5aa`. Julho: HTTP 200, hash exato do manifesto, coleta 1 válida, 79 pontos. Agosto: `timeout_fonte` antes de status HTTP/hash, coleta 2 inválida, zero pontos; a reconexão foi bloqueada. Não houve novo `arquivo_invalido`, mas agosto não chegou à validação. Banco encerrado, API não iniciada. Não se repetiu download nem se alterou manifesto ou limite. Agosto segue pendente de nova decisão do Willian.

## Segurança e entrega

Gitleaks no staging e no histórico completo (`--all`) antes do commit final e novamente após ele, antes do push. Zero achados é condição para o envio; relatórios anteriores ao commit ficam nesta pasta de evidências e os posteriores na pasta externa da execução. Nenhuma allowlist nova. Arquivos de ambiente, credenciais e caminhos locais absolutos não entram na evidência. Backend, PoC, vigência e mock legislativo permanecem com diff vazio contra a base. Checkout limpo ao terminar. O SHA final e o link do novo PR constam na entrega para evitar autorreferência do documento.

Commits anteriores ao relatório:
```text
2f439c7d5f9566fea3198d64807acaa157af2584 test(o4): revisar resumo rastreabilidade e estados antes do codigo
bb63352dff595f17000122f50494c43e0fe962fe test(o4): fixar ordem movel e de leitura antes do layout
f4700bd37cec5a277b2c2c45b95b6932b7588aa1 fix(o4): alinhar resumo fontes e ordem movel ao contrato real
b40a3ea2eaf357f6f1b2fc8f45b62f733442cc9c test(o4): conferir contrato dos pontos da fixture Caged
2df5bffa31e2ffda4c4a42548de79ba4f4a67691 fix(o4): manter fixture Caged mensal com CV nulo
a0c7d8598b2c9841b0437c6ca98e88bf6667e1a0 test(o4): incluir fontes legislativas no rodape antes da correcao
c8fe9c9e5748da79eb1cae397350e60c78f9859e fix(o4): considerar coletas legislativas na data geral
```

## Arquivos desta revisão

```text
frontend/VALIDACAO-O4-REVISAO.md
frontend/VALIDACAO.md
frontend/app/globals.css
frontend/components/dashboard.tsx
frontend/components/indicator-summary.tsx
frontend/components/indicator.tsx
frontend/evidencias/o4-revisao-2026-10-19/arquivos.txt
frontend/evidencias/o4-revisao-2026-10-19/build.txt
frontend/evidencias/o4-revisao-2026-10-19/fixture-tdd.json
frontend/evidencias/o4-revisao-2026-10-19/gitleaks-history.json
frontend/evidencias/o4-revisao-2026-10-19/gitleaks-staging.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-1280-gap-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-1280-normal-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-1280-stale-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-1280-test-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-1280-unavailable-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-360-gap-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-360-normal-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-360-stale-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-360-test-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-360-unavailable-fixture.png
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-1280-gap.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-1280-normal.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-1280-stale.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-1280-test.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-1280-unavailable.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-360-gap.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-360-normal.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-360-stale.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-360-test.json
frontend/evidencias/o4-revisao-2026-10-19/o4-revisao-axe-360-unavailable.json
frontend/evidencias/o4-revisao-2026-10-19/playwright.txt
frontend/evidencias/o4-revisao-2026-10-19/pytest.txt
frontend/evidencias/o4-revisao-2026-10-19/rodape-tdd.json
frontend/evidencias/o4-revisao-2026-10-19/testes.json
frontend/evidencias/o4-revisao-2026-10-19/typecheck.txt
frontend/tests/fixtures.ts
frontend/tests/o4-fixture.spec.ts
frontend/tests/o4-ordem.spec.ts
frontend/tests/o4-revisao.spec.ts
frontend/tests/o4-rodape.spec.ts
```
