# Validação O4 — 17/10/2026

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
