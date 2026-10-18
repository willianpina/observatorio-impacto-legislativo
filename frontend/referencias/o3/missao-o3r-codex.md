# Missão O3-R (OIL): correções do QA e da Segurança no PR #3

**Repo:** `willianpina/observatorio-impacto-legislativo` (privado).
**PR:** #3, em rascunho. Branch `codex/o3-lei-caged`, head atual `491220808dd4bd89011c075ad479667fa17fcc36`, base `main` em `345af8638ed997daf6dd1ac88dad02cd7eeb5b82`.
**Entrega:** commits novos na mesma branch, com push normal. O PR continua em rascunho e não há merge.
**Vereditos de origem (18/10/2026):** QA e Auditoria «APROVADO COM GAPS»; Segurança «APROVADO COM RESSALVAS». Esta missão fecha os itens listados abaixo. Os números de linha se referem ao head `49122080`.

## Regras fixas
1. Não faça merge nem force push. Não use rebase de commits já publicados.
2. Não use `git stash`, `git reset --hard` nem `git clean`.
3. Rode os testes à mão no Docker local, com `backend/scripts/test_postgres.py` (Postgres descartável) e Playwright local, sem runner e sem programa em segundo plano. Não rode o CI do GitHub e não dispare workflow.
4. Não leia nem commite `.env` ou segredos. Não use a porta 5432 do host. O script atual publica o contêiner em `127.0.0.1::5432`, o que dá uma porta aleatória no host; mantenha assim, ou use uma porta fixa diferente de 5432.
5. Não mexa no texto do art. 3º nem do Art. 9º, nem em nada dentro de `poc/`. Os 39 testes da PoC continuam passando.
6. Os arquivos de missão não entram em `docs/`. Esta missão vai para `frontend/referencias/o3/` ou fica fora do git.
7. A expressão «efeito da lei» só pode aparecer na legenda literal (`frontend/lib/types.ts:7`). Não crie frase causal nova em código, docs ou evidência. Não mexa na lista de frases proibidas (`FORBIDDEN` / `bannedPhrases`). Pode reforçar as regras da guarda.
8. Tudo fica privado: sem deploy, sem publicação, sem serviço pago e sem chave nova. Os testes rodam sem rede (`httpx.MockTransport` + fixtures).
9. Rode o gitleaks no staging e no histórico (`--all`) antes do push e de novo depois do último commit. Guarde a evidência e não acrescente allowlist.
10. Testes antes do código. Para cada bloco, primeiro vem um commit só com os testes novos, que precisam falhar no `49122080`. A correção vem num commit seguinte. Registre no relatório quantos testes falharam e quantos passaram no commit de testes.
11. Não invente números. Toda contagem do relatório sai de uma execução real, com o resumo do pytest ou do Playwright colado.
12. Fora do escopo desta missão: B2b (votações, placar e partido na data do voto), a tela no contrato v1.4, a coleta real pelo CLI e a conferência do art. 3º e do Art. 9º. Não implemente nada disso.

## Passo 0
- Faça `git fetch` e confira que `codex/o3-lei-caged` está em `49122080`. Se o head tiver mudado, pare e informe no relatório.
- Copie esta missão para `frontend/referencias/o3/missao-o3r-codex.md`.

## Bloco S: Segurança

### S1. xlsx do Caged (médio) em `backend/oil/caged.py`
- O sha256 do manifesto passa a ser obrigatório. Hoje a linha 133 só compara quando `entry.get('sha256')` existe. Sem sha256, ou com um valor que não seja hexadecimal de 64 caracteres, a coleta é recusada antes do download, com `valida=false` e nada gravado. Hash divergente continua sendo recusado.
- Antes de chamar `openpyxl.load_workbook` (linha 29), abra o arquivo com `zipfile` e recuse se a soma de `file_size` dos membros passar de 200 MB, ou se algum membro tiver razão `file_size/compress_size` acima de 100. Recuse também membro com `compress_size` igual a 0 e `file_size` maior que 0.
- Ponha um teto de 1000 linhas de dados na leitura da `Tabela 5.1`, usando `max_row` no `iter_rows` a partir da linha 6. Se o arquivo passar disso sem encontrar o fim da tabela, recuse com `valida=false`.
- Acrescente `defusedxml==0.7.1` ao `backend/requirements.txt`. A versão 0.7.1 é a mais recente no índice em 18/10/2026; confirme. O openpyxl usa defusedxml automaticamente quando está instalado. Escreva um teste que falhe se `openpyxl.xml.DEFUSEDXML` for falso.
- Testes: manifesto sem sha256; sha256 malformado; zip com razão acima de 100 (gerado no teste, pequeno); soma descompactada acima do limite (simule pelos metadados do zip, sem criar 200 MB em disco); planilha com mais de 1000 linhas; defusedxml ativo.

### S2. Fixtures do Caged fora de `docs/` (médio)
A licença é CC BY-ND 3.0. Vale a Segurança, e não o critério antigo da O3 de manter as fixtures em `backend/tests/fixtures/o3/` e `docs/o3/`.
- Remova com `git rm` a pasta `docs/o3/fixtures/` inteira. Hoje ela tem `caged_t51_2026-07_recorte.xlsx`, `caged_t51_2026-08_recorte.xlsx`, `gerar_recortes.py`, os dois JSON das casas e um `README.md`. Os cinco primeiros são idênticos aos de `backend/tests/fixtures/o3/`; o README é diferente. Antes de remover, confira que tudo existe em `backend/tests/fixtures/o3/` e leve para o README de lá o que só existir no de `docs/`.
- Remova `docs/o3/manifesto-fixtures.json`, que é idêntico a `backend/tests/fixtures/o3/manifesto-fixtures.json`.
- Atualize as referências: `docs/o3/spec-b4-caged.md:75` (aponta para `docs/o3/fixtures/`) e `backend/tests/test_language.py:126`, a exceção de `.xlsx` em `docs/o3/fixtures`. Com a pasta fora, `docs/` não pode ter nenhum `.xlsx`; o teste deve falhar se aparecer um.
- Faça um inventário em `docs/` (por exemplo, `git ls-files docs | xargs rg -il caged`) e retire de `docs/` qualquer cópia de dados do Caged: planilha, recorte, tabela de valores copiada ou CSV. Citar um valor esperado de teste numa spec não é cópia de dados, mas liste esses casos no relatório para a Segurança confirmar.
- Crie um teste que falhe se existir em `docs/` algum arquivo `.xlsx` ou algum arquivo cujo nome contenha `caged` e `recorte`.

### S3. Dados brutos de deputado (médio) em `backend/oil/legislation.py`
Hoje `record()` (linhas 58 a 62) grava `response.content` inteiro em `Coleta.resposta_bruta`, inclusive a resposta de `/deputados/{id}` (linha 109), que traz CPF, data de nascimento e outros dados pessoais.
- Nas coletas de deputado, grave em `resposta_bruta` só um JSON reduzido com nome, partido (`siglaPartido`) e UF (`siglaUf`). Se precisar, inclua o id numérico da URI. Nada além disso.
- O `hash_sha256` pode continuar sendo o do corpo original, para a linhagem. Registre no relatório a escolha feita (**confirmar com a Segurança**).
- Teste com um payload sintético de deputado (`simulada=true`, valores falsos) que tenha `cpf`, `dataNascimento`, `email` e endereço. Depois da coleta, nenhum desses campos pode aparecer em `resposta_bruta` nem na API.
- Se o seu banco local de desenvolvimento já tiver respostas brutas de deputado, informe no relatório. Não crie migração de limpeza nesta missão.

### S4. Caminhos locais `D:\` nas evidências (baixo)
- Tire os caminhos absolutos locais de `frontend/evidencias/o3-playwright.json` (linhas 5, 8, 45, 52 e 53) e de `docs/o3/evidencias/pytest.txt` (linhas 7 e 15). Troque por caminhos relativos ao repo ou por `<local>`.
- Os arquivos herdados da O4, `frontend/evidencias/o4r2-pytest.txt` e `frontend/evidencias/o4r2-pytest-versionados.txt`, também têm `D:\`. Limpe-os da mesma forma, mexendo só nos caminhos.
- Crie um teste ou checagem que falhe se algum arquivo versionado em `docs/` ou em `frontend/evidencias/` tiver `[A-Za-z]:\\` ou `/Users/` ou `/home/`.

### S5. Teto de cerca de 5 MB nas respostas da Câmara e do Senado (baixo)
- Em `LawCollector.fetch` (linha 71), troque o `client.get` por `client.stream`. Recuse se `Content-Length` passar de 5 MiB (5 × 1024 × 1024 bytes) ou se a soma dos chunks passar disso.
- A recusa é 502 `resposta_invalida`, sem nova tentativa, com `valida=false` e nada gravado em snapshot. Não crie código de erro novo.
- Teste com o MockTransport: (a) `Content-Length` acima do teto; (b) corpo acima do teto sem `Content-Length`.

### S6. Validar o link de `normaGerada` (baixo)
- Na linha 138 de `legislation.py`, o link da `normaGerada` do Senado só passa pelo `GeneratedNorm`, que valida apenas o tipo (`backend/oil/law_schemas.py:28-32`).
- Aceite só `https`, com host igual a um destes domínios ou subdomínio deles: `planalto.gov.br`, `in.gov.br`, `senado.leg.br`, `camara.leg.br`. É a mesma lista de `frontend/lib/safe-href.ts:7`, sem o IBGE.
- Link fora da lista fica `norma_gerada=null`, com `norma_gerada_motivo` dizendo que o link estava fora das fontes oficiais. A coleta continua válida.
- Testes: `javascript:`, `http://`, host parecido (`planalto.gov.br.exemplo.com`) e um link válido.

### S7. KeyError em `snapshots[s['casa']]` (baixo), em `legislation.py:222`
- `candidates` pode ter uma casa com `coleta_id`, mas sem snapshot, e então `max(...)` quebra com KeyError.
- Filtre os candidatos para as casas com snapshot. Se não sobrar nenhum, devolva o erro padrão (503 com `ultima_coleta_id`), nunca 500.
- Teste: uma casa tem coleta válida e nenhum snapshot correspondente, e a rota não pode dar 500.

## Bloco Q: QA

### Q1. Data e rótulo dos marcos (gap médio 1)
- Em `backend/tests/test_o3_law.py:58-59`, o teste confere só `tipo`, `origem` e `prevista`.
- Acrescente asserções de `data` e `rotulo` de cada marco contra a fixture real do Senado. A aprovação usa `deliberacao.data` e `deliberacao.tipoDeliberacao`; a promulgação usa `situacaoAtual` e `dataSituacaoAtual`.
- Não digite a data à mão: leia da fixture.
- Têm de ser detectadas as mutações em `legislation.py:184`: data fixa `'2026-10-15'` e rótulo `'Aprovação'`.

### Q2. Buraco na guarda de linguagem (gap médio 2)
- Em `frontend/tests/tela.spec.ts:214`, a checagem por frase no texto inteiro está desligada (último argumento `false`). O laço por elemento (`:215`) não olha `summary`, `li`, `strong`, `span` nem `small`.
- Inclua esses elementos no seletor da linha 215 (e `dd`, `dt`, `label`, `button` e `caption` se existirem na tela). Ou troque para uma varredura por bloco que não junte frases de blocos diferentes.
- Tem de ser detectada a injeção de «Em 14/10/2026, a desocupação caiu» dentro do `<summary>` «Saiba mais sobre a vigência» (`frontend/components/vigencia.tsx`).
- Não pode haver falso positivo nos textos reais da tela.

### Q3. Linguagem: três sondas que passaram (gap baixo 5)
Reforce as regras de `frontend/tests/linguagem.ts` (`languageViolations`) e o equivalente do backend, se houver, sem mexer em `bannedPhrases`/`FORBIDDEN`. Têm de ser detectadas:
- «A partir da promulgação, a desocupação caiu.» (evento genérico com «a partir d(a|o)», junto de «com a» já coberto);
- «Em 14/10, a desocupação caiu.» (data `dd/mm` sem ano junto de variação);
- «Compare antes e depois de 16/10/2026.» (generalizar a regra `antes e depois d[ao]` para `de` e para data).

### Q4. Trava de recorte fora do modo de teste (gap baixo 1)
`caged.py:101-104` não tem teste. Crie um: `fixture_recorte=true` sem `simulada` ou sem `OIL_TEST_MODE=1` levanta erro e não grava nada. Ele precisa detectar a troca da condição por `if False:`.

### Q5. Checagem «COM AJUSTES» (gap baixo 2)
`caged.py:34` não tem teste. Crie um: uma planilha com título «TABELA 5.1 ... SEM AJUSTES» dá `valida=false` e nada gravado. Ele precisa detectar a remoção de `or 'COM AJUSTES' not in title`.

### Q6. Contagem da O2 (gap baixo 4)
- A linha «O2 172 / 170 / 0 / 2» conta a PoC duas vezes. A suíte do backend coletou também `poc/` (39), que já é rodada separadamente. A O2 real é **131 aprovados e 2 pulados**.
- O QA atribui a coleta ao `pytest.ini`. O `backend/pytest.ini` do head tem `testpaths = tests`, e o `test_postgres.py:43` roda com `-c backend/pytest.ini` a partir da raiz. **Confirme** a causa exata e corrija a invocação para coletar só `backend/tests`, por exemplo passando o caminho explícito.
- Refaça a tabela com linhas separadas, sem somar a PoC no backend: O2, O3, O3-R, Backend (`backend/tests`) e PoC.
- Corrija em `docs/o3/VALIDACAO.md:9` e na descrição do PR #3, que tem a mesma tabela.
- O registro da O4 em `frontend/VALIDACAO.md:26` e `:69` fica como está, porque é histórico. Só acrescente uma nota de que ali o total inclui a PoC.

### Q7. `rglob` no `test_language.py` (gap baixo 8)
`backend/tests/test_language.py:119` usa `(ROOT/'docs').rglob('*')`. Troque por `git ls-files docs`. O teste deve falhar se o git estiver ausente e exigir a presença dos documentos conhecidos (`docs/o3/VALIDACAO.md`, `docs/o3/spec-b2-proposicao.md`, `docs/o3/spec-b4-caged.md`, `docs/o3/contrato-api-v1.4-delta.md`).

### Q8. Testes antes do código e `check-mutations` (gap médio 4)
- Nesta rodada vale a regra 10: cada bloco tem um commit de testes que falha no `49122080`, e só depois vem o commit de código. O relatório lista os SHAs e as falhas de cada commit de testes.
- Em `frontend/tests/check-mutations.mjs`, a linha 22 (`restore()`) só confere os bytes. Mude para:
  - criar um worktree descartável (`git worktree add --detach <pasta temporária fora do repo> HEAD`);
  - aplicar e rodar as mutações só no worktree;
  - depois de cada restauração, rodar `git -C <worktree> diff --exit-code` e abortar se o código de saída não for zero;
  - no fim, rodar `git diff --exit-code` também no repo principal e tirar o worktree com `git worktree remove <pasta>`.
- Atualize o comentário do topo do arquivo, que hoje diz «Sem comandos Git». Não use `stash`, `reset` nem `clean`.

### Q9. Mutações de backend da O3 como evidência (gap médio 3)
- Crie `backend/scripts/check_mutations_o3.py` (sugestão de caminho; **confirmar**). Ele segue o mesmo padrão: worktree descartável, uma mutação por vez, Postgres descartável via Docker (porta do host diferente de 5432), `pytest backend/tests -x`, restauração e `git diff --exit-code` depois de cada mutação.
- Saída em `docs/o3/evidencias/o3r-mutacoes-backend.json`, com nome, arquivo, resultado e o teste que pegou.
- Lista mínima, que reproduz as 22 do QA. Todas precisam ser DETECTADA, exceto BM, que pode sobreviver se declarada:

| Id | Arquivo | Mutação | Antes desta missão |
|---|---|---|---|
| BA1 | legislation.py | tirar `Coleta.simulada==test_mode` das leituras | detectada |
| BA2 | caged.py | tirar `Coleta.simulada==test_mode` das leituras | detectada |
| BA3 | legislation.py | trava `OIL_TEST_MODE` do coletor vira `if False:` | detectada |
| BA4 | caged.py | trava de recorte vira `if False:` | **sobreviveu** → Q4 |
| BB | legislation.py | empate passa a favorecer a Câmara | detectada |
| BC | legislation.py | `divergencia` sempre `False` | detectada |
| BD | legislation.py | `marker.prevista=True` | detectada |
| BD2 | legislation.py | `marker.origem='calculado'` | detectada |
| BE | legislation.py | `norma_gerada` fixa | detectada |
| BF | caged.py | reconstrução ordenada por `Coleta.id` | detectada |
| BG | caged.py | compara com a versão mais antiga | detectada |
| BH | caged.py | sinal da variação anual invertido | detectada |
| BI | caged.py | calendário às 00:00 | detectada |
| BJ | legislation.py | `partido_referencia='data_apresentacao'` | detectada |
| BK | caged.py | sem a checagem «COM AJUSTES» | **sobreviveu** → Q5 |
| BL | caged.py | aceita aba `Tabela 5` | detectada |
| BM | caged.py | leitura ignora `valida` (linha 75) | sobreviveu (defesa redundante, fora do escopo) |
| BN | caged.py | saldo em valor absoluto | detectada |
| BO | caged.py | `tipo_valor='nominal'` | detectada |
| BP | caged.py | atribuição sem «(com ajustes)» | detectada |
| BQ | legislation.py:184 | data do marco fixa `'2026-10-15'` | **sobreviveu** → Q1 |
| BR | legislation.py:184 | rótulo do marco fixo `'Aprovação'` | **sobreviveu** → Q1 |

- Acrescente uma mutação para cada item S1, S3, S5, S6 e S7, que desfaça a correção. Exemplos: aceitar manifesto sem sha256, gravar o corpo bruto do deputado, tirar o teto de 5 MiB, aceitar qualquer host na norma, voltar ao `snapshots[s['casa']]`. Todas precisam ser detectadas.
- No frontend, rode o `check-mutations.mjs` já com o worktree (Q8) e acrescente as sondas de Q2 e Q3. Evidência em `frontend/evidencias/o3r-mutacoes*.json`. Não sobrescreva as evidências `o3-*` e `o4r2-*`.

### Q10. Três imprecisões do VALIDACAO
Corrija em `docs/o3/VALIDACAO.md`, em `frontend/VALIDACAO.md:110` e na descrição do PR #3:
1. A contagem «O2 172» passa para a tabela da Q6.
2. As «11 regressões» são só de tela (O4 + sobras). Diga isso e aponte para a evidência nova de backend (Q9).
3. A comparação com o staging foi manual. Diga que ela foi manual na O3 e que, a partir da O3-R, é feita com `git diff --exit-code` dentro do script (Q8).

Corrija também o erro de digitação «videncias/o3-*» em `frontend/VALIDACAO.md:110`. Acrescente uma seção «O3-R» com as contagens reais desta rodada.

## Pendências registradas, sem implementar agora
Escreva em `docs/o3/VALIDACAO.md`, seção «Pendências para a próxima missão», e na descrição do PR:
- P1 (QA baixo 6): a autoria usa o partido atual (`partido_referencia='atual'`). A spec pede o partido na data da apresentação quando existir; se não existir, `null` com motivo. Implemente nesta rodada só se for trivial, isto é, sem requisição nova à API e sem mudança de contrato. Caso contrário, deixe só registrado.
- P2 (QA baixo 7): o marco de promulgação é inferido de «TRANSFORMADA EM NORMA JURÍDICA» com `dataSituacaoAtual`. A data confere com o DOU. Avaliar uma fonte direta para o marco.
- P3: a defesa redundante do filtro `valida` em `caged.py:75` está sem teste (mutação BM).
- Para a missão seguinte: B2b (votações, com `base_percentual` sobre os presentes e a sigla do partido na data do voto ou `null` com motivo), a tela no contrato v1.4, a coleta real pelo CLI e a conferência do art. 3º e do Art. 9º pelo Especialista Legislativo.

## Ordem sugerida de commits
1. `test(o3r): segurança S1–S7` (falham no `49122080`)
2. `fix(o3r): segurança S1–S7`
3. `test(o3r): QA Q1–Q5, Q7` (falham no `49122080`)
4. `fix(o3r): QA Q1–Q5, Q7`
5. `chore(o3r): check-mutations com worktree e mutações de backend` (Q8, Q9)
6. `docs(o3r): VALIDACAO, contagens e pendências` (Q6, Q10, S2, S4)

Pode juntar ou separar commits, desde que os testes de cada bloco venham antes do código daquele bloco.

## Relatório final (colar no PR e entregar ao Willian)
- SHAs de todos os commits e o head final.
- Para cada commit de testes, quantos falharam e quantos passaram no `49122080`.
- Tabela com contagens reais, sem somar a PoC no backend: O2, O3, O3-R, Backend (`backend/tests`), PoC (39), Playwright, axe (cenários), typecheck e build.
- Mutações de backend e de frontend: total, detectadas e sobreviventes, com o nome de cada sobrevivente.
- Gitleaks no staging e no histórico, antes e depois do último commit: quantidade de achados e caminho da evidência.
- Saída de `git diff 49122080..HEAD --stat -- poc/` vazia, e confirmação de que o art. 3º e o Art. 9º não mudaram.
- Inventário de S2 (o que saiu de `docs/` e as citações de valores que ficaram).
- A escolha do sha256 em S3 e a causa confirmada da contagem dupla em Q6.
- Pendências P1 a P3 e qualquer item marcado «confirmar» que ficou em aberto.

## Critérios de aceite
- [ ] PR #3 continua em rascunho, sem merge e sem force push. Os commits de teste vêm antes dos de código em cada bloco.
- [ ] S1 a S7 corrigidos, com testes que falham no `49122080` e passam no head final.
- [ ] Nenhum `.xlsx` nem recorte do Caged em `docs/`. Fixtures só em `backend/tests/fixtures/o3/`, com o README de «não redistribuir».
- [ ] Nenhum dado pessoal de deputado além de nome, partido e UF no banco ou na API.
- [ ] Nenhum caminho `D:\` (nem outro caminho absoluto local) em `docs/` ou `frontend/evidencias/`.
- [ ] Q1 a Q10 fechados. As mutações BA4, BK, BQ e BR e as sondas FC4, FC5, FD3 e «data no summary» agora são detectadas.
- [ ] `check-mutations.mjs` e o script de backend usam worktree e `git diff --exit-code`.
- [ ] VALIDACAO.md e o PR mostram O2 = 131 aprovados + 2 pulados, PoC separada e as 3 imprecisões corrigidas.
- [ ] `poc/`, o art. 3º e o Art. 9º sem mudança; «efeito da lei» só na legenda literal; nenhum `missao-*.md` em `docs/`.
- [ ] Gitleaks com zero achados antes do push, sem allowlist nova. Nenhum CI do GitHub disparado.
