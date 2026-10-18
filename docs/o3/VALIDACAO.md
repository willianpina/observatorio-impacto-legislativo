# Validação O3 e correção O3-R

PR #3, branch `codex/o3-lei-caged`, sempre em rascunho. Base da revisão: `491220808dd4bd89011c075ad479667fa17fcc36`. Sem merge, rebase, force push, GitHub Actions, publicação ou serviço pago.

## Retificação do registro O3

A contagem original da O2 incluía indevidamente os 39 testes da PoC na invocação do backend. A O2 isolada tem 131 aprovações e 2 testes ao vivo pulados; a O3 acrescentou 53 aprovações. Portanto, o backend da O3 tinha 184 aprovações e 2 pulados. A PoC, com 39 aprovações, deve ser apresentada separadamente. A duração antiga de 55,99 s correspondia à invocação que também coletava a PoC e não é uma medição isolada do backend.

Causa confirmada no pytest 9.0.3 instalado: `_decide_args` usa `testpaths` somente quando o diretório de invocação coincide com `rootdir`. O script era invocado da raiz com configuração em `backend/`; sem argumentos de caminhos, havia fallback para a raiz e coleta recursiva de `poc/`. O script agora passa explicitamente `backend/tests`. A conferência usou coleta detalhada e o código da biblioteca instalada, além de um teste da invocação do script.

As 11 mutações anteriores da O3 eram somente de tela (O4 e sobras autorizadas), não uma matriz de backend. A comparação contra o staging naquela rodada foi manual. A partir da O3-R, os scripts criam worktrees descartáveis e executam `git diff --exit-code` automaticamente após cada restauração e no repositório principal antes de copiar as evidências.

## Testes anteriores às correções

Commit exclusivamente de testes: `2899f1dc5c2b72fc5d50bdd8d3f6763d900ce086`, executado sobre a implementação `49122080`.

| Grupo novo | Total | Falhas esperadas | Aprovados |
|---|---:|---:|---:|
| Segurança | 24 | 21 | 3 |
| QA backend | 9 | 5 | 4 |
| Backend novo, total | 33 | 26 | 7 |
| Frontend novo | 14 | 14 | 0 |
| PoC, controle separado | 39 | 0 | 39 |

Os testes que já passavam conferem comportamento correto existente e são usados pelas mutações. Foram ajustadas duas fixtures de teste sem relaxar regras: `caption` passou a estar dentro de uma tabela válida, e o identificador de download no teste da trava de recorte passou a corresponder à URL sintética. A checagem de caminhos não confunde bytes comprimidos de PNG ou sequências de escape JSON com caminhos de arquivos.

## Resultado final O3-R

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

Resumos literais das execuções:

```text
217 passed, 2 skipped, 1 warning in 59.49s
39 passed, 1 warning in 4.18s
  86 passed (2.8m)
```

Evidências: `evidencias/o3r-pytest.txt`, `evidencias/o3r-testes.json`, `evidencias/o3r-tdd.json` e `frontend/evidencias/o3r-resumo-testes.json`.

Mutações de backend: 27 executadas, 26 detectadas; sobreviventes: BM. Mutações de frontend: 15 executadas e detectadas, sem sobreviventes. As duas execuções do backend preservam os 13 casos anteriores e os 14 restantes, sem duplicação. Bases sem mutação passaram; erros de infraestrutura não foram contados. Evidências: `evidencias/o3r-mutacoes-backend.json`, `frontend/evidencias/o3r-mutacoes.json` e `frontend/evidencias/o3r-mutacoes-ui.json`.

## Segurança S1–S7

Limitação operacional da execução: o Git removeu o checkout temporário do backend, mas encontrou permissão negada nos metadados ReadOnly do OneDrive. Os dois resíduos órfãos, sem registro ativo, foram inspecionados e removidos individualmente; a lista final contém apenas os três worktrees permanentes. As restaurações por caso e o diff final retornaram zero. Essa falha de limpeza não foi contada como detecção de mutação.

- Hash obrigatório e hexadecimal de 64 caracteres antes do download. ZIP limitado a 200 MiB descompactados, razão máxima de 100 por membro e proibição de membro não vazio com tamanho comprimido zero. A tabela aceita no máximo 1000 linhas de dados, com leitura limitada por `max_row`. `defusedxml==0.7.1` fixado e ativo no openpyxl. Conferência no [PyPI oficial](https://pypi.org/project/defusedxml/): versão estável 0.7.1; versões 0.8.0 existentes são de pré-lançamento.
- Removidos os seis arquivos de `docs/o3/fixtures/` e o manifesto duplicado. As duas planilhas, os dois JSON e o gerador foram conferidos byte a byte contra os arquivos preservados em `backend/tests/fixtures/o3/`. O manifesto também era idêntico. O README não tinha texto exclusivo: diferia somente na referência relativa ao manifesto, já correta no backend. A restrição de não redistribuição permanece no README dos testes.
- Removida a tabela de valores de revisão da seção 5 da spec B4. Restam apenas citações de valores esperados de teste na seção 2, seção 10 e regra de versionamento da mesma spec; precisam da confirmação final da Segurança. A tabela de arquivos da seção 1 contém metadados de download e hashes, não observações da série. As demais ocorrências do Caged em contrato, operação, validação e OpenAPI descrevem campos e procedimentos. Não há planilha, recorte ou CSV em `docs/`.
- Deputados: o corpo persistido contém somente id, nome, partido e UF; CPF, nascimento, email e endereço sintéticos foram excluídos e não aparecem na API. O hash SHA-256 escolhido continua sendo o do corpo original recebido, anterior à minimização; portanto não é o hash do JSON reduzido persistido. Essa escolha precisa de confirmação da Segurança. Não houve consulta ao banco persistente de desenvolvimento nem leitura de arquivos de ambiente: só bancos descartáveis dos testes, encerrados pelo script. Eventuais dados antigos de outro banco não foram verificados e não há migração de limpeza nesta missão.
- Evidências com caminhos locais foram sanitizadas, mantendo resultados e mensagens. A checagem usa inventário Git da documentação e das evidências e identifica caminhos em conteúdo textual. Arquivos PNG comprimidos não são tratados como texto.
- Câmara e Senado usam streaming com teto de 5 MiB, por cabeçalho e por soma dos chunks. Excesso retorna `resposta_invalida` 502, sem retry e sem snapshot; a tentativa fica inválida. Norma gerada só aceita HTTPS com fronteira correta dos domínios oficiais autorizados; um link recusado deixa a norma nula e registra o motivo, mantendo a coleta válida. A seleção de situação exclui casas sem snapshot e responde com erro padrão 503 quando não há candidato utilizável.

## QA e preservação

As datas e os rótulos dos dois marcos são comparados aos campos das fixtures do Senado, sem datas digitadas nas asserções. A guarda de linguagem examina os blocos adicionais, incluindo `summary`, e detecta as três sondas novas sem alterar `FORBIDDEN` ou `bannedPhrases`. A documentação é inventariada com `git ls-files`, exige os quatro documentos conhecidos e falha sem Git. Os scripts de mutação usam somente worktrees locais descartáveis; o script de backend adotou o caminho sugerido `backend/scripts/check_mutations_o3.py`.

O diff da PoC contra `49122080` é vazio. Os arquivos de vigência e da fixture legislativa da tela não foram alterados; os textos dos artigos 3º e 9º permanecem iguais. Missões continuam fora de `docs/`. As evidências novas têm prefixo `o3r`; evidências anteriores só mudaram na remoção dos caminhos locais autorizada em S4.

## Commits da revisão

```text
2899f1dc5c2b72fc5d50bdd8d3f6763d900ce086 test(o3r): regressoes de Seguranca e QA antes das correcoes
8e2a13ea86ffcee94dd9d9a910b9a3bf9586d125 fix(o3r): seguranca S1-S7 e minimizacao de dados
8684d3abbcf4a149dea1d2f56ec79c902722b01b fix(o3r): guarda de linguagem e escopo dos testes QA
9317d1f5bbb26ea23403a2e3ca7ae3a0a4e9af52 chore(o3r): mutacoes de backend e frontend em worktrees
7218778fa2125de24ef8083f26f3fac77789374a fix(o3r): manter worktree de tela no volume das dependencias
```

O commit posterior de documentação e evidências não altera código de produção; seu SHA final consta na descrição do PR e na entrega.

## Gitleaks

Staging e histórico completo (`--all`) verificados antes do commit final, zero achados: `evidencias/o3r-gitleaks-staging.json` e `evidencias/o3r-gitleaks-history.json`. Após o último commit, as duas verificações são repetidas antes do push; os resultados finais e o SHA são registrados na entrega e no PR. Nenhuma allowlist foi acrescentada.

## Pendências para a próxima missão

- P1: permanece o partido atual com referência explícita `atual`. Confirmar a disponibilidade e o critério de partido na apresentação antes de mudar essa informação; nenhuma nova requisição nem mudança contratual foi introduzida nesta revisão.
- P2: o marco de promulgação permanece derivado da situação e de sua data. Avaliar fonte direta para esse marco.
- P3: a mutação BM sobreviveu: o filtro de validade é redundante com as outras barreiras. Permanece registrada, sem ampliação do escopo.
- B2b (votos e placares, base sobre presentes e sigla na data do voto ou nula com motivo), tela no contrato v1.4, coleta real pelo CLI e conferência dos artigos 3º e 9º ficam fora desta missão.
- Confirmações da Segurança: hash original com corpo minimizado de deputado, eventuais registros antigos em banco persistente não consultado e as citações de valores esperados que ficaram na spec B4.

As validações novas usam transporte simulado e fixtures identificadas, em PostgreSQL local real descartável. Não foi feita coleta real pelo CLI ou nova conferência jurídica. Os dois testes ao vivo do IBGE permanecem desligados por padrão. Há o aviso conhecido de depreciação Starlette/HTTPX nas invocações do pytest.

## O3-C — licença dos dados, QA e tela no contrato v1.4.1

PR #4 em rascunho, branch `codex/o3c-licenca-tela-real`, base `cb8f9b23c6776fd84d5d05a08a6e3a8836bc352d`. Sem merge, rebase, force push, CI, deploy ou serviço pago.

### Resultado e limites

A API e a tela usam o contrato v1.4.1, com ementa literal, autoria histórica, situações, norma ou motivo, marcos e linhagem. A atribuição do Caged usa a base legal e a data da coleta em BRT. Os exemplos de vigência e votos permanecem isolados em `/api/oil/exemplo`, que só serve dados no modo de teste; `/api/oil/lei` serve o contrato canônico, com id fixo no servidor. Não se apresenta resumo legislativo ausente do contrato.

**Validação real parcial:** IBGE e lei disponíveis, não simulados. Os dois arquivos do Caged responderam HTTP 200 e tiveram hashes idênticos aos do manifesto, mas foram recusados como `arquivo_invalido`, sem observações. O motivo interno detalhado não foi preservado pelo erro genérico do parser e fica a confirmar. Não se repetiu o job nem o download, não se mudou o manifesto e não se relaxaram as proteções. A captura real retorna código 1 e registra essa pendência; não se declara a integração real do Caged aprovada.

A coleta manual foi executada uma vez em banco novo, com porta aleatória diferente de 5432 e credenciais somente na memória. API e contêiner foram encerrados. Para a captura final, restaurou-se o backup privado desse mesmo banco em outro contêiner próprio, sem executar jobs; ele também foi encerrado. O backup não foi versionado. Não foi inspecionado banco persistente antigo, nem arquivo de ambiente.

### Testes anteriores ao código

| Commit de testes | Grupo na base original | Resultado |
|---|---|---|
| `3cd9673` | A backend inicial | 3 falhas, 0 aprovações |
| `7554ddd` | A backend e sonda adicional | 3 falhas, 1 aprovação |
| `3cd9673` | A frontend | 1 falha |
| `865ba43 / a6619dd` | B backend, setup final | 6 falhas, 1 aprovação |
| `865ba43` | B frontend | 1 falha, 1 aprovação |
| `09a6d6a` | F histórico | 2 falhas |
| `85f459a` | D evidência ausente | 7 falhas |
| `c629f88` | C proxy e tela | 17 falhas, 1 aprovação |
| `f3832bf` | C detalhes adicionais | 4 falhas |
| `a7c3c7e / 7dbc527` | C matriz de estados e selo, fixture final | 4 falhas, 12 aprovações |

A PoC de controle passou separadamente com 39 testes. A primeira configuração temporária do Playwright apagou o próprio arquivo; foi descartada como falha de infraestrutura. O setup do teste de publicação foi corrigido antes do código para conferir escrita indevida, e o stub de Git foi depois limitado ao comando de hash exato. A primeira base do mutador falhou nesse stub e não gerou detecções aceitas. As mutações finais só começaram depois de uma base verde.

### Contagens finais sem duplicar a PoC

| Suíte | Total | Aprovados | Falhas | Pulados |
|---|---:|---:|---:|---:|
| O2 | 133 | 131 | 0 | 2 |
| O3 | 53 | 53 | 0 | 0 |
| O3-R | 33 | 33 | 0 | 0 |
| O3-C | 19 | 19 | 0 | 0 |
| Backend (`backend/tests`) | 238 | 236 | 0 | 2 |
| PoC separada | 39 | 39 | 0 | 0 |
| Playwright | 126 | 126 | 0 | 0 |

Axe: 26 cenários automáticos e 2 larguras reais, zero violações graves/críticas. Typecheck e build aprovados. Mutações: backend 27/27 detectadas (incluindo BM), frontend 17/17 detectadas, nenhum sobrevivente. A injeção no div foi executada separadamente da sonda do summary. Os dois scripts gravaram externamente por padrão e terminaram com `git status --porcelain` vazio no checkout principal; os artefatos foram copiados para versionamento somente neste passo explícito de documentação.

Resumos literais:
```text
236 passed, 2 skipped, 1 warning in 89.69s (0:01:29)
39 passed, 1 warning in 4.22s
  126 passed (4.0m)
```

A invocação pela raiz agora coleta 238 testes, exatamente os de `backend/tests`, sem PoC. A conferência em checkout limpo de `cb8f9b23` coletou 258 (219 backend e 39 PoC), não os 256 citados na revisão. O script continua passando `backend/tests` explicitamente. A guarda documental exige oito arquivos: os quatro antigos e os quatro adicionais listados na missão.

### Investigação F

- Câmara `/proposicoes/2233802/autores`: HTTP 200, URI principal de deputado 74161. `/deputados/74161/historico`: HTTP 200, 18 registros com data, partido e UF; registro de 01/02/2019 cobre a apresentação em 11/12/2019. A seleção usa o registro mais recente anterior à apresentação, recusa empate com siglas divergentes e preserva o fallback atual com motivo. P1 implementado com fixture gravada e minimizada.
- [Documentação Câmara](https://dadosabertos.camara.leg.br/api/v2/api-docs) confirma o endpoint. O corpo persistido do histórico contém somente id, nome, partido, UF e data; o hash continua sendo do corpo original recebido.
- [Processo Senado](https://legis.senado.leg.br/dadosabertos/processo/9056435?v=1): HTTP 200, `normaGerada={}`. A Câmara informa transformação em norma no status/despacho, sem campo estruturado direto de publicação confirmado.
- [Referência DOU](https://www.in.gov.br/web/dou/-/emenda-constitucional-n-141-738818165): conexão encerrada sem resposta (`RemoteProtocolError`, sem código HTTP). P2 permanece derivado da situação e de sua data; não se inventou fonte direta.

### Coleta manual por job

Hashes completos, horários UTC/BRT, URLs e respostas locais com hashes estão em `evidencias/o3c-coleta-real.json`. Na tabela, o hash é abreviado apenas para leitura. Registros de metadados do IBGE têm `valida=false` por não representarem observações, sem indicar falha do job.

| Job | HTTP | SHA-256 (prefixo) | coleta_id | válida | pontos / snapshots |
|---|---:|---|---:|---|---|
| migracao | — | — | — | saída 0 | 0 / 0 |
| ibge | 200 | `6d1f3602c89d` | 1 | false | 0 / 0 |
| ibge | 200 | `a5526f05e523` | 2 | true | 174 / 0 |
| ibge | 200 | `1e121ac94001` | 3 | false | 0 / 0 |
| ibge | 200 | `4f10d93c6788` | 4 | true | 174 / 0 |
| lei | 200 | `5957d71bd1e8` | 5 | true | 0 / 1 |
| lei | 200 | `287c91b8d7a5` | 6 | false | 0 / 0 |
| lei | 200 | `5322cd4d24fc` | 7 | false | 0 / 0 |
| lei | 200 | `2f569f32119c` | 8 | true | 0 / 1 |
| caged-2026-07 | 200 | `367b66f4af87` | 9 | false | 0 / 0 |
| caged-2026-08 | 200 | `d36c8ebe54e3` | 10 | false | 0 / 0 |
| calendario-caged | — | — | — | saída 0 | 0 / 0 |

### Segurança, preservação e pendências

- Base legal: [Decreto nº 8.777/2016, art. 4º e §1º](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm), com redação do Decreto nº 9.903/2019, conforme instrução do Engenheiro de Dados. Não se trata de parecer jurídico. A referência anterior foi corrigida, mantendo a restrição dos recortes ao repositório privado e aos testes.
- A guarda mantém exatamente duas exclusões congeladas. Por aprovação expressa do usuário, somente a designação isolada usa fronteiras de palavra para preservar dois IDs técnicos históricos; há teste que continua detectando o termo solto. As outras buscas permanecem literais. A saída equivalente à guarda está em `evidencias/o3c-guarda-inventario.json`.
- `poc/`, `frontend/components/vigencia.tsx` e `frontend/mocks/lei.ts` têm diff vazio contra a base; os artigos 3º/9º não foram alterados. Missões ficam fora de `docs/`. Não se modificaram as listas de frases proibidas.
- A verificação móvel detectou URLs de linhagem sem quebra; corrigida a quebra sem ocultar conteúdo. O layout e os cenários foram reexecutados.
- No OneDrive, a cópia descartável antiga exigiu retirada das junções antes da remoção dos arquivos. Os destinos compartilhados foram preservados. O runner prepara os atributos de sua própria cópia e metadados para remoção, com conferência do caminho.
- O contrato legislativo não publica calendário de divulgação: a tela não estima atraso da lei. Os indicadores exibem o sinal de calendário recebido da API, independentemente da disponibilidade.
- A integração real do Caged e a causa detalhada de `arquivo_invalido` ficam pendentes; uma nova investigação com download ou alteração dos limites requer decisão própria. P2 e a conferência jurídica dos artigos permanecem fora desta entrega. Votações reais/B2b, hospedagem, CI e agendador não foram implementados.
- O nome adotado para a publicação explícita é `--publicar-evidencia`; o tipo legislativo é `contrato-lei-v14.ts`. Não há item de nomenclatura pendente.

### Gitleaks e commits

Staging e histórico completo (`--all`) verificados antes do commit documental final, zero achados, sem allowlist nova; evidências `evidencias/o3c-gitleaks-staging.json` e `evidencias/o3c-gitleaks-history.json`. Após o último commit, as duas verificações são repetidas antes do push e o resultado final consta na entrega e no PR.

Commits anteriores ao relatório:
```text
3cd9673e29aaaa598ac28cdaca87cbb1a51194f4 test(o3c): atribuicao do Caged e guarda de licenca antes do codigo
7554ddd3e474e9dc36ab9035c9221e57e981364f test(o3c): detectar designacao isolada sem alterar IDs historicos
edc5f0cdebdc33b6f775d59f64e283ef2fd1cf5e fix(o3c): base legal do Caged e contrato v1.4.1
865ba43e47a468f309278dc9a64b734864054573 test(o3c): regressao de QA e defesa BM antes do codigo
a6619dd71afc003956d7356181cbba4bbb00b748 test(o3c): preparar destino para verificar publicacao indevida
f61e5e2eb5f9d30946d6d5ace9567f0bd932863c fix(o3c): guardas de QA e mutacoes com evidencia externa
09a6d6a32c29e0a2e99618af748b877002fce088 test(o3c): partido na apresentacao com historico oficial minimizado
85f459a21fc959e7f4343837328172424e7c1f73 test(o3c): evidencia da coleta manual sem rede automatizada
f5ae3af3580f91a8c9d5873c4e79a6f34ab1801e fix(o3c): partido e UF na apresentacao pelo historico oficial
c629f88e7b5d18144b323f9bc785dacef110f61a test(o3c): contrato legislativo real e estados da tela antes do codigo
ebb4cee614d152e82af2e28359edd06230676779 docs(o3c): evidencia da coleta real unica e falha validada do Caged
f3832bf841bf6dd5dc6f39bcb63dbd4ca9e2bb92 test(o3c): carregamento e detalhes de linhagem antes da tela
65213d579b0eaf6310e0088e11154f5ca2577a7e feat(o3c): tela no contrato v1.4.1 com linhagem e estados reais
3b0cfc01bdb4842419f2bf438bcc11567c3d70e7 test(o3c): limitar stub Git ao hash solicitado pela orquestracao
023361715ba45c43b837e31d218ff2bcd681d96c fix(o3c): quebrar URLs de linhagem no celular e isolar sonda do div
a7c3c7ee0af9de85a0008f5b79cc5c50469e6d98 test(o3c): matriz dos estados por indicador e selo do payload
7dbc5278eb8de111bdf00c93d56b31944400e9e5 test(o3c): preservar simulacao declarada apos montar fixture Caged
```

O SHA do commit documental final é registrado no PR e na entrega para evitar autorreferência do arquivo.

Conferência final após consolidar os documentos: 46 testes de guardas de linguagem, atribuição, segurança e evidência aprovados em 29,48 s; PoC separada, 39 aprovados em 4,03 s. Resumos literais em `evidencias/o3c-guardas-finais.txt`. O commit documental também normaliza quebras de linha de arquivos desta missão; não modifica o comportamento testado.
