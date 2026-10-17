# Missão O4 — Tela da lei (B7/B8) do Observatório

**Repo:** privado, base `main` (0e14fa69). **Branch:** `codex/o4-tela-lei`. **Entrega:** PR em rascunho, sem merge.
**Leia antes:** `frontend-spec.md` v1.5 (com o adendo de 16/10), `prototipo-aprovado.png`, contrato v1.3.1 (`docs/`).

## O que fazer
1. Crie `frontend/` com Next.js (App Router, TypeScript), Tailwind e Recharts, só pacotes gratuitos. Não mexa em `backend/` nem em `poc/`.
2. Monte a página da EC 141/2026 (era a PEC 221/2019) na ordem da spec §2: cabeçalho e «O que mudou na lei?» com os marcos; «O que os dados mostram?» com 3 cards e gráficos (desocupação 6381, rendimento real 6390 e Caged); o resumo; «Quem propôs e como foi a votação»; e «Fontes e dados» (B8). Sem notícias, sem IA e sem «Pergunte ao Observatório».
3. Dados reais: `GET /api/v1/indicadores` e `GET /api/v1/indicadores/{codigo}/serie?janela=2a|5a|desde_2020` (padrão `5a`), com a URL da API em variável de ambiente.
4. A lei, os marcos e as votações ainda não têm rota (vêm na O3). Crie `frontend/lib/contrato-lei-provisorio.ts` com os tipos da spec §3.1 e §6 e um mock em `frontend/mocks/`, ativo só com `OIL_TEST_MODE=1` e sempre com o selo visível «Dado de teste». Em modo normal, sem a rota, o bloco mostra «Dado ainda não disponível», e nunca o mock.
5. Escreva os testes antes do código (Playwright e axe, locais), seguindo a spec §10. Os testes usam fixtures da API e não chamam a SIDRA.

## Regras da tela (obrigatórias)
- Todo número e todo gráfico mostra a fonte, o link e a data da coleta (`coletado_em`, convertida para o horário de Brasília).
- Uma lacuna (`valor: null`) aparece como buraco no gráfico e «sem dado» na tabela. Nunca zero e nunca uma linha ligando os pontos por cima.
- Campo que a fonte não traz aparece como «Não informado». Um partido ausente aparece como «sigla não informada pela fonte».
- Aviso fixo perto dos gráficos: «É cedo para afirmar efeitos da lei. Os dados mostram só o que aconteceu, não a causa.»
- Nenhuma frase causal. Proibidas, entre outras: «causou», «graças a», «por causa da lei», «depois da aprovação», «desde a promulgação». Há um teste que procura essas frases em toda a página renderizada.
- Os marcos são linhas cinza finas, tracejadas quando `prevista: true`, nunca vermelhas e sem sombrear o antes e o depois. A legenda é: «Marcos de calendário. Não indicam efeito da lei.»
- `classificacao` null não mostra rótulo. Quando há rótulo, aparece junto a nota «calculado pelo Observatório com a margem de erro do IBGE». A tela não mostra `tipo_valor` quando `medida = taxa`.
- `disponivel: false` (Caged) mostra «Dado ainda não disponível», com o `motivo`. A tela não pode mostrar erro nesse caso.
- Se a fonte cair: com `desatualizado: true`, aparece o aviso «Fonte fora do ar. Mostrando a última coleta válida de DD/MM/AAAA». Com erro 502, 503 ou 504, aparece um aviso claro com a opção de tentar de novo, sem número inventado.
- O insight vem primeiro, e o detalhe fica em «Saiba mais». Placar: «aprovada» só com o quórum de 3/5 (308 na Câmara, 49 no Senado); a obstrução fica à parte e fora do total; «Placar em conferência» enquanto `placar_conferido` for false.
- WCAG 2.1 AA: contraste, teclado, foco visível, texto alternativo e tabela de dados em cada gráfico. Responsivo de 360 px até o desktop.
- Nada de CI pago, deploy, link público ou analytics. Tudo é privado.

## Critérios de aceite
- [ ] Os testes da spec §10 passam (Playwright e axe), com zero violações graves ou críticas do axe.
- [ ] Desocupação e rendimento renderizam com dados reais da API local, com fonte, link e data em cada card e gráfico.
- [ ] Testes de lacuna, de `disponivel: false`, de `desatualizado`, de erro 503, de frases proibidas, de marco tracejado e cinza, e de selo «Dado de teste» só em modo teste.
- [ ] Teste do placar com a votação 2233802-424: sim 472, não 22, abstenção 0, total 494, obstrução 1 à parte e «aprovada».
- [ ] `backend/` e `poc/` sem nenhuma mudança. Os testes do backend (PoC e v1) continuam passando.
- [ ] gitleaks sem ocorrências e nenhuma dependência paga.

## Relatório (no PR e para o ORCHESTRATOR)
Branch e commit; lista de arquivos; resumo do pytest e do Playwright (passou e falhou); resultado do axe; capturas da tela em desktop e em 360 px, nos estados normal, lacuna, Caged indisponível, fonte fora do ar e modo teste; o contrato provisório da lei que você criou; e cada desvio da spec, com o motivo.
