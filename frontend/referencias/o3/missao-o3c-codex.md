# Missão O3-C (OIL): licença do Caged, sobras do QA, coleta real e tela no contrato v1.4 com dados reais

**Repo:** `willianpina/observatorio-impacto-legislativo` (privado).
**Base:** `main` em `cb8f9b23c6776fd84d5d05a08a6e3a8836bc352d`, o merge do PR #3 (O3 + O3-R), de 18/10/2026.
**Entrega:** branch nova `codex/o3c-licenca-tela-real`, criada a partir de `cb8f9b23`, e um PR novo **em rascunho** para `main`. Não há merge.
**Origem:** vereditos finais da O3-R (18/10/2026). Segurança: «APROVADO COM RESSALVAS», com a ressalva da licença do Caged. QA: «APROVADO COM GAPS», com 4 achados baixos novos. Verificação do Engenheiro de Dados sobre a licença do Novo Caged (18/10/2026). Pendências P1, P2 e P3 do PR #3.
**Nome:** «O3-C» é um nome descritivo. Nenhum documento do repo define o rótulo seguinte: a O4 foi a tela com dados de exemplo, a O3 foi o backend da lei e do Caged, e a O3-R foi a revisão dela. Esta missão continua a O3 e liga a tela a ela.
**Linhas:** todos os números de linha citados se referem à `main` em `cb8f9b23`. Antes de editar, confira cada um.

## Regras fixas
1. Não faça merge nem force push. Não use rebase de commits já publicados.
2. Não use `git stash`, `git reset --hard` nem `git clean`.
3. Rode os testes à mão, no Docker local: `backend/scripts/test_postgres.py` (Postgres descartável) e Playwright local. Não rode o CI do GitHub e não dispare workflow.
4. Não leia nem commite `.env` ou segredos. Nunca use a porta 5432 do host. O script de testes publica em `127.0.0.1::5432`, o que dá uma porta aleatória; mantenha assim. Qualquer outro Postgres desta missão usa porta aleatória ou fixa, sempre diferente de 5432.
5. Não mexa no art. 3º, no Art. 9º nem em nada dentro de `poc/`; eles esperam a conferência do Especialista Legislativo. Os 39 testes da PoC continuam passando. Não altere `frontend/components/vigencia.tsx` nem `frontend/mocks/lei.ts`, a não ser que seja indispensável; se for, justifique no relatório.
6. Os arquivos de missão não entram em `docs/`. Esta missão vai para `frontend/referencias/o3/missao-o3c-codex.md`.
7. «efeito da lei» só pode aparecer na legenda literal (`frontend/lib/types.ts:7`, `LEGEND`). Não crie frase causal nova em código, docs ou evidência. Não mexa nas listas `FORBIDDEN` (`backend/tests/test_language.py:18`) e `bannedPhrases` (`frontend/tests/linguagem.ts:4`). Pode reforçar as regras das guardas.
8. Tudo fica privado: sem deploy, sem publicação, sem hospedagem, sem serviço pago, sem chave nova e sem workflow de CI. A suíte automática roda sem rede (`httpx.MockTransport`, fixtures e `page.route`). A única exceção é o Bloco D, que é manual e roda uma vez só.
9. Rode o gitleaks no staging e no histórico (`--all`) antes do push e de novo depois do último commit. Guarde a evidência e não acrescente allowlist.
10. Testes antes do código. Cada bloco tem primeiro um commit só com os testes novos, que precisam falhar em `cb8f9b23`. A correção vem num commit seguinte. O relatório diz quantos testes falharam e quantos passaram em cada commit de testes.
11. Não invente números, caminhos nem fatos. Toda contagem do relatório sai de uma execução real, com o resumo do pytest ou do Playwright colado. O que você não conseguir confirmar fica marcado «confirmar».
12. Mutações sempre em worktree descartável, como na O3-R. Nenhuma evidência pode ter caminho local absoluto (`D:\`, `C:\Users\`, `/home/`, `/Users/`).
13. Fora do escopo: B2b (votações), que vai para missão própria; o art. 3º e o Art. 9º; a hospedagem; workflows de CI; agendador ou coleta automática.

## Passo 0
- Rode `git fetch` e confirme que `origin/main` está em `cb8f9b23`. Se não estiver, pare e informe no relatório.
- Crie `codex/o3c-licenca-tela-real` a partir de `cb8f9b23`.
- Copie esta missão para `frontend/referencias/o3/missao-o3c-codex.md`.

## Bloco A: licença do Caged (obrigatório antes de hospedar)
**Fato verificado** pelo Engenheiro de Dados em 18/10/2026 (isto não é parecer jurídico): o MTE não publica licença própria para as tabelas do Novo Caged. O rodapé «CC BY-ND 3.0» do gov.br vale para o conteúdo do site, não para os dados. A base é o Decreto nº 8.777/2016, art. 4º e §1º, com a redação do Decreto nº 9.903/2019: uso livre e gratuito, com citação da fonte.

### A1. Testes primeiro
- Em `backend/tests/test_o3_caged.py:55-56`, troque as asserções da atribuição por:
  - `data['atribuicao']['licenca'] is None`;
  - `data['atribuicao']['base_legal']['texto']` igual, caractere por caractere, a: «Uso livre e gratuito, com citação da fonte (Decreto nº 8.777/2016, art. 4º e §1º, com a redação do Decreto nº 9.903/2019). O MTE não publica licença própria para estes dados.»
  - `data['atribuicao']['base_legal']['link'] == 'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm'`;
  - `data['atribuicao']['texto']` igual a «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo agosto/2026, coletado em DD/MM/AAAA. Elaboração: OIL.». A data vem do `coletado_em` da coleta servida, convertida para America/Sao_Paulo. Leia a data da coleta no próprio teste; não digite à mão.
  - O mês/ano continua vindo de `mes_referencia`, como hoje (`caged.py:247`), nunca fixo no código.
- Crie uma guarda nova, por exemplo `backend/tests/test_licenca_caged.py` (**confirmar** o nome). Ela usa `git ls-files` em todo o repo (sem git, falha) e faz o teste falhar se aparecer, sem diferenciar maiúsculas:
  - `cc[\s_-]*by` (cobre «CC BY», «CC-BY» e «CC BY-ND»), `by-nd` ou `semderiva`;
  - `cc0` ou `domínio público` / `dominio publico`.
  - Exclusões, numa lista congelada no próprio teste e só estas duas: `frontend/package-lock.json`, onde aparece a licença `CC-BY-4.0` de uma dependência npm e não de dado; e `frontend/referencias/o3/missao-o3c-codex.md`, porque esta missão cita o termo para removê-lo. Arquivos binários ficam fora.
- No Playwright, `frontend/tests/tela.spec.ts:147` hoje espera «arquivo 08/2026, licença CC BY-ND 3.0». Troque por asserções do texto novo da atribuição e da base legal com o link do decreto (o card passa a ler o contrato no Bloco C, então este teste fecha junto com o C).
- O commit de testes precisa falhar em `cb8f9b23`.

### A2. Código e documentos
- `backend/oil/caged.py:252-253`: `atribuicao` passa a ser `{texto, link, licenca: null, base_legal: {texto, link}}`, com os textos de A1. O `link` da atribuição continua sendo `metadata['pagina_oficial']`.
- `backend/oil/schemas.py:25` hoje tem `atribuicao: dict[str,str] | None`, que não aceita `null` nem objeto aninhado. Troque por um modelo explícito, por exemplo `Atribuicao` e `BaseLegal`, com `extra='forbid'`.
- Troque o texto «CC BY-ND» nestes lugares. Todos foram conferidos em `cb8f9b23`:
  - `backend/tests/fixtures/o3/README.md:7`: tire «Licença da fonte: CC BY-ND 3.0 (sem derivações)». Ponha a base legal e mantenha o resto da regra de uso. Os recortes continuam só para os testes, no repo privado, e fora de publicação até decisão própria (o Engenheiro de Dados recomenda trechos pequenos, com URL, data da coleta e sha256).
  - `docs/o3/spec-b4-caged.md:18`: a linha «Licença» vira «Base legal», com o decreto e a nota de que o rodapé do gov.br cobre o site, não os dados.
  - `docs/o3/spec-b4-caged.md:56` (formato de `atribuicao`) e `:77` (critério 7 da resposta): texto e campos novos. A Segurança citou a linha 79; em `cb8f9b23` o trecho está na 77. **Confira.**
  - `docs/o3/contrato-api-v1.4-delta.md:20`: troque pelo formato novo e acrescente «corrigido na v1.4.1».
  - `frontend/referencias/o3/missao-o3r-codex.md:36` («A licença é CC BY-ND 3.0…»): troque por uma nota de correção com a base legal. Na linha 188, o critério «README de "não redistribuir"» ganha uma nota de que a regra continua, mas a justificativa agora é a base legal.
  - Também tinham o termo em `cb8f9b23`, fora da lista da Segurança: `frontend/referencias/o3/missao-o3-codex.md:34`, `frontend/referencias/o3/missao-o4-adendo2.md:9` e `:16`, `frontend/referencias/missao-o4-adendo2.md:7` e `:14`, `frontend/tests/fixtures.ts:46` e `frontend/tests/tela.spec.ts:147`. Nas missões históricas, troque só a licença por uma nota curta de correção e preserve o resto do texto. As linhas `:16` e `:14` dizem que «a licença CC BY-ND não permite apresentar uma obra derivada como se fosse do MTE»: mantenha a regra de identificar o cálculo do Observatório e troque a justificativa pela citação da fonte.
  - Na tela, `frontend/components/indicator.tsx:11` (`licença ${data.licenca ?? 'Não informada'}`) e `frontend/lib/types.ts:3` (campo `licenca`): no Bloco C, o card passa a mostrar `atribuicao.texto` e a base legal com link. A palavra «licença» sai do card.
- Não use CC0 nem «domínio público» em lugar nenhum.

### A3. Contrato v1.4.1
O repo já seguiu o padrão de correção com versão de patch (v1.3 → v1.3.1). Siga o mesmo:
- Crie `docs/o3/contrato-api-v1.4.1-delta.md`, só com o que muda: `atribuicao.licenca` passa a ser sempre `null` no Caged, entra `atribuicao.base_legal {texto, link}` e muda o formato de `atribuicao.texto`. Explique em uma frase que a v1.4 trazia uma licença que não se aplica aos dados.
- `backend/oil/main.py:36`: `version='1.4.1'`. Gere `docs/o3/openapi-v1.4.1.json` e mantenha `openapi-v1.4.json` como histórico.
- Inclua `docs/o3/contrato-api-v1.4.1-delta.md` na lista de documentos exigidos da guarda (veja B4).

## Bloco B: achados baixos do QA e P3

### B1. Guarda de linguagem em `div` e na página inteira
- Hoje `frontend/tests/tela.spec.ts:214` chama `languageViolations(text+' '+attributes,[],false)`, com a checagem por frase desligada. O seletor de `scanLanguageBlocks` (`frontend/tests/linguagem.ts:22`) não inclui `div`.
- O QA injetou «Em 14/10/2026, a desocupação caiu.» num `<div>` solto da vigência em `frontend/components/dashboard.tsx`, e a guarda não pegou.
- Correção sugerida:
  - Inclua os `div` na varredura por bloco usando só os nós de texto próprios de cada `div`, para não juntar frases de filhos diferentes.
  - Ligue a checagem por frase também no texto da página inteira. Use `innerText`, que separa os blocos com quebra de linha, e não `textContent`. Assim a regra de data com variação (`linguagem.ts:13-15`) se aplica sem juntar blocos.
- Teste novo, que precisa falhar em `cb8f9b23`: a mesma injeção no `<div>` da vigência do `dashboard.tsx` é detectada. Junte uma mutação equivalente ao `check-mutations.mjs`.
- Não pode haver falso positivo nos textos reais da tela, nem nos novos do Bloco C. Se aparecer um, corrija o texto da tela, nunca a regra.

### B2. Scripts de mutação sem regravar evidência versionada
- `frontend/tests/check-mutations.mjs:40` copia os JSON do diretório externo para `frontend/evidencias/` do checkout principal. `backend/scripts/check_mutations_o3.py:135` grava direto em `docs/o3/evidencias/o3r-mutacoes-backend.json`. Por isso o repo não termina limpo.
- Por padrão, os dois scripts passam a gravar só fora do git: o diretório externo que já existe ao lado do repo, ou outro caminho ignorado pelo `.gitignore`. Imprimem o caminho relativo da saída.
- Versionar a evidência passa a ser um passo explícito: por exemplo, a opção `--publicar-evidencia` (**confirmar** o nome), usada só no commit de documentos. Sem ela, o script termina com `git status --porcelain` vazio no checkout principal; teste isso.
- Documente `OIL_BROWSER_CHANNEL` em `frontend/README.md` (linhas 27 e 33) e em `docs/o3/operacao.md:27`. No Windows o padrão é `msedge`; no Linux use `OIL_BROWSER_CHANNEL=chromium`. Hoje `check-mutations.mjs:47` e `capture-real.mjs:5` caem em `msedge` quando a variável falta, e `playwright.config.ts:6` cai no Chromium do Playwright. Documente essa diferença; não é preciso mudar o padrão.

### B3. `pytest -c backend/pytest.ini` a partir da raiz não pode coletar a PoC
- A causa já está registrada no PR #3: no pytest 9.0.3, `testpaths` é ignorado quando o diretório de invocação é diferente do rootdir. Hoje só o script contorna isso (`backend/scripts/test_postgres.py`, que injeta `backend/tests`).
- Corrija na configuração (`backend/pytest.ini`), por exemplo com `norecursedirs` incluindo `poc`, ou outra opção equivalente que você confirmar na documentação do pytest. Mantenha o argumento explícito do script.
- Teste que precisa falhar em `cb8f9b23`: a partir da raiz, `python -m pytest -c backend/pytest.ini --collect-only -q` não lista nenhum item de `poc/`, e o total coletado é igual ao de `backend/tests`. Na raiz, isso dava 256 segundo o QA; confira.

### B4. Documentos exigidos pela guarda
- `backend/tests/test_language.py:30-31` exige só os quatro documentos da O3. Acrescente `docs/README.md`, `docs/contrato-api-v1.3-indicadores.md`, `docs/metodologia-o2.md` e o novo `docs/o3/contrato-api-v1.4.1-delta.md`.
- O teste precisa falhar se um deles sair do `git ls-files`.

### B5. Teste barato da BM (P3)
- Insira à mão, no banco de teste, uma observação ligada a uma coleta com `valida=false` (mesma série, competência e período dentro da janela) e confira que `reconstruct` (`backend/oil/caged.py:85-95`) a ignora e que a API não mostra o valor.
- A mutação BM (tirar `Coleta.valida.is_(True)` de `caged.py:91`) passa a ser DETECTADA no `check_mutations_o3.py`. Atualize a regra do script que tolera a BM como sobrevivente (linha 137): depois desta missão, nenhuma sobrevivente é aceita.

## Bloco F: P1 e P2, investigar antes de implementar
Implemente só com campo oficial confirmado na fonte. Sem isso, deixe `null` com motivo. Não invente partido nem data.

### F1. P1: partido na data da apresentação
- Hoje `legislation.py:152-153` grava `partido_referencia='atual'`, com o motivo «Partido e UF atuais; referência histórica não publicada nesta consulta».
- Investigue se a API de Dados Abertos da Câmara publica o partido do deputado numa data. Um candidato é `GET /deputados/{id}/historico` (**confirmar**: existência, campos e data de cada registro).
- Se houver campo oficial, com data, que cubra a `dataApresentacao`: grave `partido` e `uf` daquela data, com `partido_referencia='apresentacao'` (valor que o contrato já prevê em `law_schemas.py`). A nova resposta segue a mesma minimização da S3: só id, nome, partido, UF e datas, nada além disso. Use fixture gravada nova, com teste antes do código.
- Se não houver: mantenha `atual` com motivo claro, e registre no relatório a URL consultada e o que ela devolveu.

### F2. P2: fonte direta da promulgação
- Hoje o marco é inferido de «TRANSFORMADA EM NORMA JURÍDICA» com `dataSituacaoAtual`. Na resposta do Senado conferida pelo QA em 18/10, `normaGerada` estava vazio (`{}`).
- Investigue, só em fontes oficiais, um campo direto com a data da promulgação ou da publicação. Candidatos: `normaGerada` do Senado preenchido depois; algum campo da proposição ou da tramitação na Câmara; o DOU, já listado em `backend/data/fontes_norma.json` (**confirmar** se há um endpoint estruturado).
- Se houver: o marco passa a usar esse campo e cita a fonte, com teste e fixture. Se não houver: mantenha a derivação atual e registre a investigação no relatório.

## Bloco D: coleta real pelo CLI, local e manual
Rode **uma vez**, à mão, sem agendador, sem laço de nova tentativa e sem fallback de fixture.
- **Banco:** use um Postgres local próprio desta missão (contêiner novo), em porta diferente de 5432. Ponha `DATABASE_URL` só no ambiente do processo. Não leia `.env` e não reaproveite banco persistente antigo.
- Se você souber de um banco de desenvolvimento persistente que já recebeu coleta real de autoria antes do commit `8e2a13ea` (corpo bruto de deputado), informe no relatório e **não apague nada**. A limpeza é decisão do Willian.
- **Comandos** (de `docs/o3/operacao.md` e `backend/README.md:28`):
  1. `python -m alembic -c backend/alembic.ini upgrade head`
  2. `python -m backend.oil.cli desocupacao rendimento-real`
  3. `python -m backend.oil.o3_cli lei`
  4. `python -m backend.oil.o3_cli caged 2026-07` e `python -m backend.oil.o3_cli caged 2026-08`
  5. `python -m backend.oil.o3_cli calendario-caged`
- Só use competências que já estão em `backend/data/caged_manifesto.json` (hoje 2026-07 e 2026-08). Não acrescente entrada sem conferência humana.
- O sha256 do arquivo baixado tem de bater com o do manifesto. Se não bater, a coleta fica inválida e você registra isso; não troque o hash.
- Se alguma fonte falhar, registre a falha como ela veio (código, HTTP), sem repetir em laço.
- **Evidência:** `docs/o3/evidencias/o3c-coleta-real.json`. Para cada job, registre o comando, o início e o fim (UTC e BRT), a URL, o status HTTP, o sha256 do corpo, o `coleta_id`, `valida`, `simulada=false` e a contagem de pontos ou snapshots.
  - Não entram: corpo de resposta, dado pessoal, `DATABASE_URL`, senha, nem caminho absoluto.
  - Acrescente as respostas reais de `GET /api/v1/indicadores/{desocupacao,rendimento-real,caged-saldo}/serie` e `GET /api/v1/proposicoes/2233802` servidas por esse banco, com o sha256 de cada resposta.
  - Os números do Caged em 2026-08 devem bater com os valores já conferidos nos testes (`test_o3_caged.py:48-50`). Se não baterem, registre e não «corrija» a fonte.
- A API sobe em `127.0.0.1:8766` contra esse banco para a validação real do Bloco C. No fim, pare o contêiner e diga no relatório que ele foi parado.

## Bloco C: tela no contrato v1.4.1 com dados reais
**Estado atual em `cb8f9b23`:** os indicadores já passam pelo proxy `frontend/app/api/oil/indicadores/[[...path]]/route.ts`. A lei não: `frontend/app/api/oil/lei/route.ts` devolve o mock no modo de teste e `disponivel:false` no modo normal. Os tipos da lei ainda são os do contrato provisório v0.2 (`frontend/lib/contrato-lei-provisorio.ts`). O card do Caged lê `licenca` e `arquivo_origem` no nível de cima, mas o backend entrega `atribuicao`.

### C1. Testes primeiro (Playwright e axe)
- Os testes rodam com respostas gravadas no formato v1.4.1, todas marcadas `simulada:true` no modo de teste. No modo normal, use respostas com `simulada:false` servidas por um backend falso local, seguindo o padrão de `frontend/tests/proxy.spec.ts`. Nada de rede.
- Casos mínimos:
  - O servidor normal recusa `simulada:true` também na lei.
  - O selo «Dado de teste» aparece só quando a resposta traz `simulada:true`. Hoje ele está fixo no bloco da lei em `dashboard.tsx` e em `voting.tsx`.
  - A lei real mostra ementa, autor, partido e UF, `partido_referencia` com o motivo, data de apresentação, `situacao_atual` (e as duas casas quando há `divergencia`), `norma_gerada` ou o motivo, marcos com `origem` e `fontes_norma`, cada um com fonte, link e «Coletado em … (BRT)».
  - O card do Caged mostra `atribuicao.texto` uma vez só (sem «Fonte: Fonte:»), a base legal com link e a `nota_revisao`.
  - Estados de carregando, erro (com `Retry-After`), indisponível (`disponivel:false` com `motivo`), desatualizado e atrasado pelo calendário, para lei, Caged e IBGE.
  - O número do card e o do «Resumo da análise» são iguais para cada conceito.
  - axe a 360 e 1280 px nos estados normal, indisponível e erro, também com o «Saiba mais» aberto: zero violações graves ou críticas.
  - A guarda de linguagem do B1 passa nas telas novas.

### C2. Código
- **Proxy da lei:** no modo normal, `/api/oil/lei` consulta `${OIL_API_URL}/api/v1/proposicoes/2233802`, com o id fixo no servidor e nunca vindo do navegador. Use as mesmas proteções do proxy de indicadores: 60 consultas por minuto, cache de 15 s só para sucesso, timeout de 15 s, `no-store` e `Retry-After`. Pode extrair o código comum para `frontend/lib/`. No modo de teste, sirva uma fixture v1.4.1 com `simulada:true`.
- **Tipos:** crie `frontend/lib/contrato-lei-v14.ts` (**confirmar** o nome), espelhando `LawResponse` de `backend/oil/law_schemas.py`, e troque o tipo `Series` (`frontend/lib/types.ts:3`) para refletir `atribuicao`, `nota_revisao` e `variacao_anual_origem`. Ajuste `frontend/tests/fixtures.ts:46` para o formato do backend, com `unidade='postos de trabalho'` e `arquivo` vindo de `atribuicao`.
- **Princípios da tela:**
  - O insight vem primeiro; o detalhe fica no «Saiba mais».
  - Um número só por conceito.
  - Texto da fonte sempre literal.
  - Nenhum resumo inventado: a v1.4 não tem `resumo`, então a tela mostra a `ementa` como «Ementa (texto da fonte)». O resumo revisado pelo Especialista Legislativo fica para depois.
- **O que a v1.4 não entrega:**
  - **Vigência:** no modo normal, o bloco mostra «Dado ainda não disponível» com uma frase neutra. No modo de teste, continua como está. Não mexa em `vigencia.tsx` nem em `mocks/lei.ts`.
  - **Votações e tramitação:** no modo normal ficam indisponíveis, com o motivo «As votações entram numa próxima etapa». Troque o texto antigo «A integração legislativa será disponibilizada na O3.» (`voting.tsx`), que ficou desatualizado.
- **«efeito da lei»** só na legenda literal. Nenhuma frase liga marco ou data a variação de indicador.
- **Links:** todos passam por `safeHref`. O domínio do decreto (`planalto.gov.br`) já está na lista de `frontend/lib/safe-href.ts`; confira.
- **Validação real:** com a API do Bloco D em 8766, rode `frontend/tests/capture-real.mjs`, estendido para a lei e para o Caged.
  - Ele falha se receber `simulada:true`, `disponivel:false` ou atribuição com «licença».
  - Evidência em `frontend/evidencias/o3c-validacao-real.json`, sem caminho absoluto, e capturas em 360 e 1280 px.

## Ordem sugerida de commits
1. `test(o3c): licença do Caged e guarda CC` (A1) — falha em `cb8f9b23`
2. `fix(o3c): base legal do Caged e contrato v1.4.1` (A2, A3)
3. `test(o3c): sobras do QA e BM` (B1, B3, B4, B5) — falha em `cb8f9b23`
4. `fix(o3c): guardas, pytest.ini e scripts de mutação` (B1–B5)
5. `test(o3c): P1/P2` e `fix(o3c): P1/P2` — só se houver fonte confirmada (F)
6. `test(o3c): tela v1.4.1` (C1) — falha em `cb8f9b23`
7. `feat(o3c): tela no contrato v1.4.1` (C2)
8. `docs(o3c): coleta real, VALIDACAO e evidências` (D e relatório)

Pode juntar ou separar commits, desde que os testes de cada bloco venham antes do código daquele bloco.

## Relatório final (colar no PR e entregar ao Willian)
- SHAs de todos os commits e o head final.
- Para cada commit de testes, quantos falharam e quantos passaram em `cb8f9b23`.
- Tabela com contagens reais, sem somar a PoC no backend: O2, O3, O3-R, O3-C, Backend (`backend/tests`), PoC (39), Playwright, axe (cenários), typecheck e build.
- Saída de `pytest -c backend/pytest.ini --collect-only -q` a partir da raiz (B3).
- Mutações de backend e de frontend: total, detectadas e sobreviventes (a meta é zero, inclusive a BM).
- Saída de `git grep -niE "cc[ _-]*by|by-nd|cc0|dom[ií]nio p[uú]blico"` com só as duas exceções da guarda.
- Gitleaks no staging e no histórico, antes e depois do último commit: quantidade de achados e caminho da evidência.
- `git diff cb8f9b23..HEAD --stat -- poc/ frontend/components/vigencia.tsx frontend/mocks/lei.ts` vazio, ou justificado.
- Bloco D: tabela por job (HTTP, sha256, `coleta_id`, `valida`, pontos) e confirmação de que o contêiner foi parado.
- Bloco F: URLs consultadas, o que cada uma devolveu e a decisão (implementado ou `null` com motivo).
- `git status --porcelain` vazio depois de rodar os dois scripts de mutação sem `--publicar-evidencia`.
- Itens «confirmar» que ficaram em aberto.

## Critérios de aceite
- [ ] PR novo em rascunho, a partir de `cb8f9b23`, sem merge e sem force push. Os commits de teste vêm antes dos de código em cada bloco.
- [ ] Nenhum «CC BY», «BY-ND», «CC0» ou «domínio público» no repo fora das duas exceções congeladas. A guarda falha se o termo voltar.
- [ ] O Caged na API tem `licenca: null`, `base_legal` com o texto e o link do decreto e o texto de atribuição novo. O contrato v1.4.1 e a OpenAPI v1.4.1 estão versionados.
- [ ] B1 a B5 fechados: injeção em `div` detectada, scripts terminam com o repo limpo, `pytest.ini` não coleta a PoC, guarda exige os 7 docs e BM detectada.
- [ ] P1 e P2 implementados só com fonte oficial confirmada, ou `null`/derivação mantida com motivo e investigação registrada.
- [ ] Coleta real feita uma vez, à mão, fora da porta 5432, com evidência e hashes, sem corpo nem dado pessoal na evidência.
- [ ] Tela consome a API local (lei, Caged e IBGE), com o selo de simulado só quando `simulada:true`, os estados completos e o axe sem violações graves ou críticas.
- [ ] `poc/`, o art. 3º e o Art. 9º sem mudança; «efeito da lei» só na legenda literal; nenhum `missao-*.md` em `docs/`; nenhum caminho local absoluto nas evidências.
- [ ] Gitleaks com zero achados antes do push, sem allowlist nova. Nenhum CI do GitHub disparado.
