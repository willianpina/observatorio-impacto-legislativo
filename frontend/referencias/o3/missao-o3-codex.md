# Missão O3 (OIL) — Lei acompanhada (B2) + saldo do Novo Caged (B4)

**Repo:** `willianpina/observatorio-impacto-legislativo` (privado). **Base:** `main` em `345af863` (já com a O4 mergeada). **Branch:** `codex/o3-lei-caged`.
**Entrega:** PR em **rascunho**, sem merge. Contrato sobe de v1.3.1 para **v1.4** (só acréscimos).

## Regras
1. **Testes antes do código.** Primeiro commit só com os testes (falhando); depois a implementação.
2. Não mexer em `poc/` nem em `frontend/`. Os **39 testes da PoC** e todos os testes da O2 continuam passando.
3. Tudo privado: nada de deploy, publicação, serviço pago ou chave nova. Testes sem rede (`httpx.MockTransport` + fixtures).
4. Nenhum número ou texto de situação digitado à mão no código. Dado simulado só em `OIL_TEST_MODE=1` e com `simulada=true`.
5. Erros no formato padrão: `{"erro": {"codigo", "mensagem", "fonte", "tentar_novamente_em", "ultima_coleta_id"}}` (503 com `Retry-After`, 504, 502; 404 id inexistente; 422 parâmetro inválido).
6. Coleta: 3 tentativas, `Retry-After` respeitado com **teto de 60 s**, `httpx.Limits`. Coleta é job CLI, nunca na requisição da tela.
7. Frases causais proibidas: o teste da O2 passa a cobrir as rotas novas.
8. **Resumo do pytest no PR** (total, passou, falhou, pulou, separado: PoC, O2, O3).

## Passo 0
Copiar a pasta `docs/o3/` deste pacote para `docs/o3/` no repo. Copiar `docs/o3/fixtures/*` para `backend/tests/fixtures/o3/` (junto com o `README.md`). As fixtures são só para teste e não podem ir para nenhum artefato publicado.

## B2 — Lei acompanhada (detalhe: `spec-b2-proposicao.md`, `confirmacao-ec141.md`)
- Rota `GET /api/v1/proposicoes/{id_camara}`; lista fixa no `catalog.py` (2233802 → Senado 9056435). Outro id → 404; não numérico → 422.
- **Migração 0003** (`down_revision='0002'`): `proposicao`, `proposicao_snapshot` (versionada por coleta), `marco` (com `origem` e `artigo`); fontes `camara-dados-abertos` e `senado-dados-abertos`. Sobe, desce e sobe.
- Reconciliação: coleta as duas casas; `situacao_atual` = data de situação mais recente, empate → Senado; uma casa só → `regra="unica_disponivel"`; `divergencia` quando os estágios diferem. Texto sempre literal da fonte.
- `norma_gerada` só da fonte (hoje o Senado traz `normaGerada` vazio → null com motivo). `fontes_norma` = links do Planalto e do DOU. Marcos na O3: só aprovação no Senado (14/10/2026) e promulgação (16/10/2026), `origem="fonte"`, `prevista=false`. Vigência calculada fica fora.
- Fonte fora: uma casa falha → 200 com `disponivel=false` nela; as duas → erro padrão com `ultima_coleta_id=null`. Esquema inesperado → `valida=false`.
- **9 testes** da seção 5 da spec B2. Fixtures reais: `camara_2233802_2026-10-17.json` e `senado_9056435_2026-10-17.json` (convergência: as duas «norma jurídica», data 16/10/2026 → empate → Senado, `divergencia=false`). A divergência usa fixture sintética derivada, `simulada=true`.

## B4 — Saldo do Novo Caged (detalhe: `spec-b4-caged.md`)
- **Só a aba `Tabela 5.1` (com ajustes)**, em todos os meses. Nunca a `Tabela 5`.
- Manifesto manual (`backend/data/caged_manifesto.json`: competência, arquivo, `drive_file_id`, URL de download, página oficial, publicação, sha256). Download HTTPX (limite 100 MB). Leitura `openpyxl.load_workbook(..., read_only=True, data_only=True)`, cabeçalho na linha 5, B=Mês, F=Saldos.
- **Migração 0004** (`down_revision='0003'`): troca `ck_observacao_valor` por gatilho que só aceita negativo quando `medida='saldo'`; `classificacao_origem` aceita null; nova `observacao.variacao_anual_origem`; corrige o cadastro do Caged da 0002 (`tipo_valor` NULL, unidade `postos de trabalho`); tabela `caged_arquivo`. Sobe, desce e sobe.
- Cada arquivo = coleta nova com **sha256**; observação ganha versão nova só quando o saldo muda; mesmo arquivo de novo não cria versão. Guardar só sha256, tamanho e URL do xlsx (o arquivo não vai para o banco).
- Layout diferente → `valida=false`, nada gravado, a rota segue com a última coleta boa (`desatualizado=true`).
- Calendário (`divulgacao`): 2026-09 → **29/10/2026**, 2026-10 → **30/11/2026**, 2026-11 → **30/12/2026** (23:59 -03:00, convenção do Observatório documentada: o MTE não informa hora).
- Rota `GET /api/v1/indicadores/caged-saldo`: `medida=saldo`, `tipo_valor=null`, `tipo_periodo=mensal`, `unidade="postos de trabalho"`, `classificacao=null`, `cv=null`, `ajuste="com_ajuste"`, `competencia_coleta`; `atribuicao` («Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo <mês/ano>, licença CC BY-ND 3.0» + link da página oficial); `nota_revisao`; `variacao_anual` com `variacao_anual_origem="calculo_observatorio"`, separada do valor do MTE. Sem coleta válida → **200** com `disponivel=false`, `motivo`, `pontos=[]`.
- Testes com os recortes reais `caged_t51_2026-07_recorte.xlsx` e `caged_t51_2026-08_recorte.xlsx`: ago/2026 = **165.827**; dez/2025 = **−635.078**; revisão de jul/2026 **58.568 → 55.915** (versões 1 e 2); `variacao_anual` ago/2026 = **11.144** e jul/2026 = **−77.869**; layout diferente → `valida=false`; só `Tabela 5` → `valida=false`; sem coleta → 200 `disponivel=false`; atribuição e nota presentes; calendário; gatilho (negativo recusado na 6381/6390). Lista completa: seção 10 da spec B4.


### Versionamento do Caged (confirmado pelo Engenheiro de Dados, 17/10/2026; obrigatório)
1. A coleta grava `mes_referencia` do arquivo (ex.: 2026-08) e o `periodo_inicio` e o `periodo_fim` contidos nele.
2. Para cada mês, o valor é comparado sempre com a versão mais recente daquele mês, na ordem do `mes_referencia` (não do `coletado_em`). Qualquer mudança gera uma versão nova, inclusive a volta a um valor antigo.
3. Reconstruir o arquivo X: para cada mês entre o `periodo_inicio` e o `periodo_fim` de X, pegar a última versão vinda de coleta válida com `mes_referencia` ≤ o de X, ordenando pelo `mes_referencia`. Coletas com `valida=false` ficam fora. Carregar um arquivo antigo depois não pode alterar a série.
4. Testes: (a) carregar julho e depois agosto; a série reconstruída de cada arquivo é idêntica ao recorte da planilha dele (jul/2026 = 58.568 no de julho e 55.915 no de agosto; dez/2025 = −634.374 e −635.078; ago/2026 = 165.827); (b) a mesma checagem carregando agosto antes de julho (fora de ordem); (c) uma coleta inválida não entra na reconstrução; (d) a rota pública mostra a reconstrução do `mes_referencia` mais recente.

## Anexos (`docs/o3/`)
- `missao-o4-adendo2.md`: vale junto da O3 para a tela (ver nota no topo do arquivo)
- `missao-o3-codex.md` (este arquivo)
- `spec-b2-proposicao.md`, `spec-b4-caged.md`, `confirmacao-ec141.md`, `contrato-api-v1.4-delta.md`
- `manifesto-fixtures.json` (origem, URL/file_id, data de coleta e sha256 do original e do recorte)
- `fixtures/README.md`, `fixtures/gerar_recortes.py`, `fixtures/caged_t51_2026-07_recorte.xlsx`, `fixtures/caged_t51_2026-08_recorte.xlsx`, `fixtures/camara_2233802_2026-10-17.json`, `fixtures/senado_9056435_2026-10-17.json`

## Critérios de aceite
- [ ] PR rascunho de `codex/o3-lei-caged` para `main`, sem merge; histórico mostra os testes antes do código.
- [ ] `poc/` e `frontend/` sem nenhuma mudança no diff.
- [ ] 39 testes da PoC + O2 + O3 passando; resumo do pytest no PR.
- [ ] Migrações 0003 e 0004 sobem, descem e sobem; `alembic heads` com uma cabeça só.
- [ ] `/api/v1/proposicoes/2233802` com a fixture real: `divergencia=false`, `situacao_atual.casa="senado"`, `norma_gerada=null` com motivo, 2 marcos `origem="fonte"`, `fontes_norma` com Planalto e DOU.
- [ ] `/api/v1/indicadores/caged-saldo` devolve os números da Tabela 5.1 sem nenhuma mudança, com `atribuicao`, `nota_revisao`, `classificacao=null` e `tipo_valor=null`.
- [ ] Nenhum «EC 141», «Promulgada» ou número do Caged como constante fora das fixtures.
- [ ] Fixtures só em `backend/tests/fixtures/o3/` e `docs/o3/`, com o README de «não redistribuir».
- [ ] Contrato v1.4 documentado no repo (OpenAPI e `docs/o3/contrato-api-v1.4-delta.md`).
