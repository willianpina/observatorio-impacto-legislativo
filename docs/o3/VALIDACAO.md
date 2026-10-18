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
