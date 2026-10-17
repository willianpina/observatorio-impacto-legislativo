# Validação O4 — 17/10/2026

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
