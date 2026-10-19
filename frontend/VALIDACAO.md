# Validação O4 — 17/10/2026

## Revisão O4-R2 — PR #2

Mesma branch `codex/o4-tela-lei`, base `13b012bf44ea56a31dfb9720357cfeeebeff7309`. Código, testes e evidências alterados somente em `frontend/`; backend, PoC e O3 preservados. O documento de instruções do usuário em `docs/missao-o4-r2-codex.md` permanece intacto e não versionado. Sem merge, outro PR, force push, CI ou deploy.

A cobertura dos itens 1–9, com o nome de cada teste e a regressão que o faz reprovar, está em `evidencias/o4r2-cobertura.md`. A prova executável está em `tests/check-mutations.mjs`: são 11 mutações intencionais, com seis cenários de helpers/proxy e cinco cenários visuais (um deles cobre as duas séries). As falhas intencionais ficam separadas da execução final: `o4r2-mutacoes.json`, `o4r2-mutacoes-ui.json` e `o4r2-mutacoes.txt`.

O contrato legislativo provisório passa à versão **0.2**, documentada em `referencias/contrato-lei-provisorio-v0.2.md`. A vigência vem da estrutura do dado, com fontes, artigos e horários de consulta. Datas calculadas só recebem previsão quando posteriores ao dia corrente em Brasília; datas expressas e publicação não recebem esse rótulo. A fixture continua exclusiva do modo de teste. Os testes congelam o dia de referência para que a passagem real do tempo não invalide as asserções.

O CSV preserva números negativos e protege somente texto. O proxy valida caminho/janela antes de contar consultas; a política de IP e o limite local compartilhado continuam iguais. Os quatro casos extras de domínio já eram recusados/normalizados corretamente pelo `safeHref`, sem necessidade de mudar sua política.

### Resultados e evidências O4-R2

| Verificação | Resultado final |
|---|---|
| Playwright | 62 aprovados; 0 falhas, 0 ignorados, 0 instáveis; 109,671 s |
| Axe | 14 cenários, zero violações graves/críticas |
| Prova de mutação | 11 regressões detectadas; fontes restaurados antes da execução final |
| Typecheck e build | Aprovados |

O resumo final com contagens e duração está em `evidencias/o4r2-testes.json`; a execução integral em `o4r2-playwright.txt`. `o4r2-typecheck.txt` e `o4r2-build.txt` registram as verificações dos fontes restaurados após as mutações. As capturas `o4r2-*-fixture.png` e os JSONs `o4r2-axe-*` registram os cenários de 360 e 1280 px, incluindo todos os detalhes abertos. São fixtures, não novas coletas oficiais. Nenhum dado real anterior é substituído por simulação.

**Pytest:** a primeira execução na pasta de trabalho teve **169 aprovados, 1 falha, 2 ignorados e 1 aviso** no backend; a PoC teve **39 aprovados e 1 aviso**. A falha foi `test_no_forbidden_phrases_in_all_docs`: o próprio arquivo de instruções não versionado contém a expressão que o teste proíbe. O log original foi preservado em `o4r2-pytest.txt`. Não se alterou o teste, nem se apagou ou editou a missão para ocultar a falha.

A regressão dos arquivos versionados foi então executada numa cópia isolada obtida com `git archive HEAD backend poc docs`, usando o script de PostgreSQL descartável existente: **170 aprovados, 2 ignorados, 1 aviso em 59,67 s** no backend; **39 aprovados, 1 aviso em 4,33 s** na PoC. Evidência: `o4r2-pytest-versionados.txt`. Os fontes backend/PoC da pasta de trabalho não diferem dessa base. A execução direta continuará encontrando o documento de instruções enquanto ele permanecer em `docs/`; essa é uma ressalva do ambiente local, não um resultado omitido.

**Gitleaks:** a evidência versionada `o4r2-gitleaks-final.json` identifica o SHA do commit final de código e a varredura de todo seu histórico. Ela entra num commit posterior de evidência. O histórico incluindo esse último commit também é examinado antes do push. Um arquivo não pode conter literalmente o SHA do próprio commit, pois adicionar o SHA altera o commit; por isso o SHA do código coberto e o SHA final da branch são distinguidos na entrega. Nenhuma exceção nova é criada.

A relação de arquivos desta revisão está em `evidencias/o4r2-arquivos.txt`. Não houve nova ingestão real nem validação legal independente; a informação legislativa da missão continua identificada como fixture. Permanecem as limitações de CSP e limite/cache em memória descritas na O4-R.

## Revisão O4-R — PR #2

Mesma branch `codex/o4-tela-lei`, sobre o commit O4 `e235dfc6bb06f3ea6a739c858a1209d046752373`. Todos os itens 1–16 da revisão foram implementados exclusivamente em `frontend/`, inclusive as melhorias opcionais. Sem alteração em backend, PoC ou O3; sem merge, CI ou deploy.

| Verificação O4-R | Resultado |
|---|---|
| Playwright, execução final | 41 passaram; 0 falhas, 0 ignorados, 0 instáveis; 78,733 s |
| Axe | 12 cenários; zero violações graves/críticas |
| Axe com detalhes abertos, 360 px | Caged e modo normal: zero violações de qualquer nível |
| TypeScript (`npm run typecheck`) | Aprovado |
| Next.js (`npm run build`) | Aprovado |
| Gitleaks, histórico inteiro anterior ao novo commit | 4 commits examinados; zero ocorrências |

O teste de janela exige 60 pontos no padrão, 24 em dois anos e mais de 60 desde 2020, além da mudança da curva; último valor e comparação continuam iguais. Os novos testes cobrem a separação entre saldo oficial e comparação no resumo do Caged, a vigência literal, metadados e valor principal único por card, os cabeçalhos com a tela funcionando, links recusados, CSV com todos os prefixos solicitados, prazo de erro, marco dentro da série e ausência de setas sem classificação. A varredura inclui os dois novos termos proibidos. No gráfico, a descrição traz valor e classificação; o SVG interno é decorativo e não há elementos na ordem de tabulação dentro do contêiner `role="img"`.

Evidências desta revisão usam o prefixo `o4r-`: `o4r-testes.json` contém os 41 resultados; `o4r-playwright.txt`, `o4r-build.txt` e `o4r-typecheck.txt` guardam as execuções. Os 12 JSONs `o4r-axe-*` e `o4r-security-headers.json` registram os resultados de acessibilidade e os cabeçalhos efetivamente recebidos. As capturas `o4r-*-fixture.png` foram conferidas visualmente e são simulações de teste, inclusive as do modo normal. Elas não substituem as evidências reais da O4 abaixo. A lista da revisão está em `o4r-arquivos.txt`.

Gitleaks também é executado sobre todos os arquivos preparados para o novo commit, com o hook oficial; a evidência é `o4r-gitleaks-staging.txt`. Uma última varredura do histórico incluindo o novo commit é realizada antes do push; seu resultado é informado na entrega. Nenhuma exceção foi acrescentada à configuração existente.

### Limitações explícitas da O4-R

- Cache e limite são locais ao processo: 15 segundos para respostas bem-sucedidas e 60 consultas por minuto. O cache é separado por série e janela; respostas de erro não são armazenadas. Em várias instâncias seria necessário compartilhar o estado.
- No servidor local, sem proxy confiável, todos os acessos compartilham o limite. `OIL_TRUST_PROXY=1` habilita a separação por IP, somente atrás de um proxy que sobrescreva `X-Forwarded-For`. O padrão é `0`, para impedir que o navegador contorne o limite falsificando esse cabeçalho.
- A CSP implementa as quatro diretivas solicitadas e restringe origens externas. Permite `unsafe-inline` para bootstrap Next.js e estilos Recharts. Uma CSP baseada em nonces é uma evolução futura, além do solicitado nesta revisão.
- Os testes O4-R usam respostas gravadas e cenários simulados; não houve nova ingestão real nem nova execução de pytest. Os resultados de backend/PoC e a validação real apresentados abaixo são históricos da O4, preservados. O escopo O3 continua pendente e intocado.
- A avaliação automatizada e a conferência visual não equivalem a certificação integral de WCAG.

Nenhum item da revisão ficou sem implementação. O PR permanece para aprovação do usuário.

## Histórico da validação O4 inicial

Base `main` em `0e14fa69`, branch `codex/o4-tela-lei`. Alterações restritas a `frontend/`. Backend e PoC preservados, sem alteração de suas rotas, testes ou arquivos. Nenhum deploy ou GitHub Actions.

## Execuções

| Verificação | Resultado |
|---|---|
| Pytest backend, PostgreSQL isolado, migrações e regressões | 170 passaram, 2 ignorados, 1 aviso, 58,49 s |
| Pytest PoC | 39 passaram, 1 aviso, 4,39 s |
| Build Next.js / TypeScript | Passou |
| Playwright | Resultado final em `evidencias/resumo-testes.json` |
| Axe | Zero violações graves/críticas nas larguras e estados testados |
| npm audit na instalação | Zero vulnerabilidades |
| Gitleaks | Resultado final em `evidencias/gitleaks.txt` |

Os avisos pytest são a depreciação do uso de HTTPX pelo TestClient do Starlette. Os dois testes ignorados são os testes opt-in do backend. Os testes da interface foram escritos inicialmente antes dos componentes, e ampliados durante a validação.

## Integração real separada

PostgreSQL local isolado, migração inicial e ingestão genuína via coletor existente, com `OIL_TEST_MODE=0`. Cada série gerou 174 observações; a janela de cinco anos forneceu 60 pontos. As credenciais efêmeras ficaram somente na memória dos processos e não integram as evidências.

| Série | Referência | Valor | CV | Resultado |
|---|---|---:|---:|---|
| Desocupação, 6381 | 202608, trimestre móvel | 5,3% | 1,3% | Renderizado igual à API local |
| Rendimento real, 6390 | 202608, trimestre móvel | R$ 3.777 | 0,7% | Renderizado igual à API local |

Origem, links, IDs e horários da coleta estão em `evidencias/validacao-real.json`. Capturas reais em `real-360.png` e `real-1280.png`. Nenhum identificador de coleta dessa base descartável deve ser interpretado como ID de produção.

## Cobertura da interface

Estados normal, lacuna, vazio, erro independente, última coleta válida, classificação ausente, Caged indisponível e Caged simulado com ajustes. Validação de faixa de teste, recusa de simulação no modo normal, unidades anuais, ausência de tipo monetário na taxa, aviso literal, legenda autorizada, marcos neutros, placar nominal e obstrução separada, votação simbólica, inconsistência de partidos, paginação de demonstração, teclado e CSV. Varredura de linguagem inclui textos ocultos em detalhes e tabelas, atributos e cenário do Caged.

## Adaptações e pendências explícitas

- As referências foram preservadas em `frontend/referencias/`, em vez de `docs/`, para manter toda a O4 dentro de `frontend/`. Elas contêm instruções com exemplos de linguagem proibida e não são conteúdo servido na tela.
- A lei e as votações fornecidas são exclusivamente fixtures identificadas. Este trabalho não validou os documentos legislativos nas fontes oficiais. A confirmação enviada pelo usuário foi preservada como referência, sem ativar dados legislativos no modo normal.
- Como o último período é anterior aos quatro marcos, eles aparecem como referências interativas abaixo do eixo, sem ampliar o domínio ou prolongar a curva. Marcos que estiverem dentro do domínio usam linhas verticais. Datas previstas incluem artigos e nota de cálculo.
- A O3 fornecerá a paginação real, IDs e linhagem legislativa. Até lá, o contrato provisório e o carregamento incremental são demonstrados em listas de teste.
- Caged disponível depende da O3 e dos metadados do arquivo de origem. Base de preços do rendimento permanece em verificação; nenhum novo deflacionamento.
- A conferência visual cobre celular e desktop; axe não substitui revisão humana completa de WCAG.

A relação exata de arquivos acompanha `evidencias/arquivos.txt`. A aprovação do PR e qualquer próxima fase permanecem a cargo do usuário.


## Rodada O3 — preservação da O4

Somente as sobras autorizadas no adendo O3: guarda de linguagem com datas brasileiras, eventos e comparação antes/depois; marco recolhe ao sair do foco; rendimento fracionário é idêntico no card e no resumo; axe cobre mais estados com detalhes abertos. Artigos 3º e 9º permanecem iguais.

Resultado final: 72 testes Playwright aprovados (zero falhas, pulados ou instáveis), em 121,089 s; 20 cenários axe sem violações graves/críticas; typecheck e build aprovados. As 11 mutações de tela (O4 e sobras) foram detectadas; a comparação com o staging foi manual. Houve nova compilação e suíte completa após restaurar os fontes. Evidências desta rodada: `evidencias/o3-*`; evidências O4 anteriores preservadas.

Retificação O3: backend O2/O3 isolado com 184 aprovados e 2 testes ao vivo pulados (O2: 131 + 2; O3: 53); PoC: 39 aprovados, código intocado. Relatório detalhado em ../docs/o3/VALIDACAO.md. Sem CI, deploy ou merge do PR.


## O3-R

Os totais de backend nos registros históricos da O4 acima incluem os 39 testes da PoC. Esses registros foram preservados; a tabela corrigida abaixo separa as suítes. A partir da O3-R, as restaurações dos scripts de mutação são verificadas automaticamente com `git diff --exit-code` em worktrees descartáveis. As 11 mutações antigas eram somente de tela; as novas evidências incluem também o backend.

| Suíte | Aprovados | Pulados | Falhas |
|---|---:|---:|---:|
| O2 | 131 | 2 | 0 |
| O3 | 53 | 0 | 0 |
| O3-R backend | 33 | 0 | 0 |
| Backend total (`backend/tests`) | 217 | 2 | 0 |
| PoC, separada | 39 | 0 | 0 |
| Playwright | 86 | 0 | 0 |
| Axe | 20 cenários | — | 0 graves/críticas |
| Typecheck | aprovado | — | — |
| Build | aprovado | — | — |

Mutações de backend: 27 executadas, 26 detectadas; sobreviventes: BM. Mutações de frontend: 15 executadas e detectadas, sem sobreviventes. As duas execuções do backend preservam os 13 casos anteriores e os 14 restantes, sem duplicação. Bases sem mutação passaram; erros de infraestrutura não foram contados. Evidências: `evidencias/o3r-mutacoes-backend.json`, `frontend/evidencias/o3r-mutacoes.json` e `frontend/evidencias/o3r-mutacoes-ui.json`.

Resumos literais das execuções:

```text
217 passed, 2 skipped, 1 warning in 59.49s
39 passed, 1 warning in 4.18s
  86 passed (2.8m)
```

Evidências: `evidencias/o3r-pytest.txt`, `evidencias/o3r-testes.json`, `evidencias/o3r-tdd.json` e `frontend/evidencias/o3r-resumo-testes.json`.

Relatório de Segurança, TDD e pendências P1–P3 em `../docs/o3/VALIDACAO.md`. PoC e textos dos artigos 3º e 9º preservados.

## O3-C

Contrato legislativo v1.4.1, atribuição aninhada e base legal, selo condicionado à resposta simulada, estados de erro/indisponibilidade e linhagem. 126 testes Playwright aprovados, zero falhas/pulados/instáveis, 26 cenários axe sem violações graves/críticas; typecheck e build aprovados. Mutações frontend 17/17 e backend 27/27 detectadas. Backend: 236 aprovados e 2 pulados; PoC separada: 39 aprovados. Validação real parcial: IBGE e lei exibidos; Caged indisponível, registrado como falha, sem substituição por fixture. API e bancos próprios encerrados. Arquivos de vigência e mock legislativo preservados. Relatório completo em `../docs/o3/VALIDACAO.md`; evidências com prefixo `o3c-`.
