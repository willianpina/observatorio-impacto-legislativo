# O3 · B4 — Saldo do Novo Caged (Brasil, mensal) — especificação para o Codex
Status: 17/10/2026, sem implementação. Base: main 0e14fa69 (contrato v1.3.1, migrações 0001 e 0002). Contrato alvo: v1.4 (ver `contrato-api-v1.4-delta.md`).
Origem: verificação do Engenheiro de Dados (17/10/2026, 11h22–11h31, horário de Brasília) + regras do Cientista de Dados (17/10/2026). Este arquivo é autossuficiente.

## 1. Fonte confirmada
- Página oficial do MTE (abaixo, `{BASE}`): `https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho/novo-caged`
- Página do mês: `{BASE}/2026/agosto/pagina-inicial` (200). Lista: Sumário executivo.pdf, Apresentação.pdf, Tabelas.xlsx, Painel, Nota Técnica, Comunicado.
- O link «Tabelas.xlsx» aponta para uma pasta pública do Google Drive (`1F89h6odTPGIGMb9eDiJKCute9W89QmqN`), com subpastas por ano e por mês (`202601` … `202608`).
- Download direto (sem login): `https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t` (o Drive pede `confirm=t` porque não faz checagem de vírus em arquivo grande).

| Competência | Arquivo | file_id | Tamanho | sha256 (medido em 17/10/2026) |
|---|---|---|---|---|
| 2026-07 | `3-tabelas_Julho de 2026.xlsx` | `1zMmEU0lRboxrdGxtjP-gR1XpSeYCKdv8` | 41.885.294 B | `367b66f4af878d0c1ab5b9fc881f228976e74a2240cb5d3afdc83aef78cabe01` |
| 2026-08 | `3-tabelas_Agosto de 2026.xlsx` | `1LFiRd5cYqCLbBv7udPWtus6h4cF3GaA0` | 44.543.000 B | `d36c8ebe54e3e10ea877f5ea4dd6798a0a276c4fcff262c73102f4b9c8459e7d` |

- Agosto/2026 foi publicado em 29/09/2026. O MTE não publica hash; o sha256 é o que medimos.
- **Fora do escopo:** microdados do FTP do PDET (sem conexão, formato não confirmado), Painel Power BI, Base dos Dados.
- **Base legal:** Decreto nº 8.777/2016, art. 4º e §1º, com redação do Decreto nº 9.903/2019; uso livre e gratuito com citação da fonte. O rodapé do portal cobre o site, não os dados. O MTE não publica licença própria para estes dados.

## 2. Qual tabela usar (regra do Cientista de Dados)
- **Só a aba `Tabela 5.1` (COM AJUSTES), em todos os meses.** Nunca a `Tabela 5` (sem ajustes). O número oficial divulgado pelo MTE é o com ajustes (ago/2026 = 165.827 bate com o sumário executivo e a notícia de 29/09/2026; ago/2025 = 154.683 é o com ajustes).
- Layout da `Tabela 5.1`: B2 = título «TABELA 5.1 - EVOLUÇÃO DE ESTOQUE, ADMISSÕES, DESLIGAMENTOS E SALDO POR MÊS - COM AJUSTES»; linha 5 = cabeçalho: B=`Mês`, C=`Estoque` (fórmula), D=`Admissões`, E=`Desligamentos`, **F=`Saldos`**, G=`Variação Relativa (%)` (fórmula). Dados a partir da linha 6 (`Janeiro/2020`), um mês por linha, texto «Mês/AAAA» em português. Depois de uma linha em branco: «Fonte: Novo Caged – MTE.» e uma nota.
- Ler só a coluna F (saldo) e a B (mês). Não usar C nem G (são fórmulas).

## 3. Manifesto manual
Arquivo versionado no repo (ex.: `backend/data/caged_manifesto.json`), preenchido à mão a cada divulgação. Um item por competência:
`competencia` (AAAA-MM), `arquivo` (nome no Drive), `drive_file_id`, `url_download`, `pagina_oficial` (`{BASE}/{ano}/{mes}/pagina-inicial`), `publicado_em` (data do calendário/Drive), `sha256` (opcional; se vier, tem que bater).
O job nunca descobre arquivo por busca: só baixa o que está no manifesto.

## 4. Ingestão (job CLI separado, nunca na requisição da tela)
1. Baixar por HTTPX (mesmo retry da O2: 3 tentativas, `Retry-After` respeitado com teto de 60 s, `httpx.Limits`), limite de 100 MB, em arquivo temporário. Calcular sha256.
2. Abrir com `openpyxl.load_workbook(path, read_only=True, data_only=True)` e ler **só** a aba `Tabela 5.1`.
3. Validar o layout (seção 6). Se falhar → `coleta.valida=false`, `erro` com o motivo, **nenhuma observação gravada**.
4. Converter «Agosto/2026» → período `202608`. Saldo inteiro (pode ser negativo). Sem arredondar, sem somar, sem dessazonalizar.
5. Gravar uma `coleta` por arquivo (url, sha256, `simulada=false`, `tipo='arquivo'`, `serie_codigo='caged-saldo'`). Resposta bruta: não guardar os 45 MB no banco; guardar só o sha256 e o caminho/URL (decisão do Backend; se o Engenheiro preferir guardar, usar armazenamento fora do banco).
6. **Versionamento:** cada arquivo mensal é uma coleta nova sobre a série inteira (jan/2020 até o último mês). Para cada período, nova versão da observação só quando o saldo mudar (regra da O2). A API serve a versão mais recente. O mesmo arquivo duas vezes (mesmo sha256) não cria versão.
7. Ao ter a primeira coleta válida: `serie.disponivel=true`, `motivo=null`.

## 5. Revisões (confirmadas com dado real)
A série com ajustes é revisada todo mês. Do arquivo de julho para o de agosto (Tabela 5.1):

As diferenças entre os arquivos são conferidas exclusivamente pelas fixtures privadas de teste em `backend/tests/fixtures/o3/`, sem copiar a tabela de valores para a documentação.

A resposta traz a nota de revisão (seção 8).

## 6. Layout diferente → coleta inválida
`valida=false` se: falta a aba `Tabela 5.1`; B2 não começa com «TABELA 5.1» ou não contém «COM AJUSTES»; a linha 5 não é exatamente `Mês, Estoque, Admissões, Desligamentos, Saldos, Variação Relativa (%)` em B..G; um mês não segue o formato «Mês/AAAA»; os meses não são contínuos a partir de Janeiro/2020; um saldo não é inteiro; o último mês é diferente da `competencia` do manifesto; o sha256 não bate com o do manifesto. A rota continua servindo a última coleta válida (`desatualizado=true`).

## 7. Calendário (tabela `divulgacao`, já existente)
Calendário oficial de 2026 (página `.../estatisticas-trabalho/o-pdet/calendario-de-divulgacao-do-novo-caged`): competência 2026-09 → **29/10/2026**; 2026-10 → **30/11/2026**; 2026-11 → **30/12/2026**. O calendário só dá o dia (hora e fuso não informados): gravar 23:59 -03:00 do dia. `atrasado_calendario=true` quando passou essa hora e não há coleta válida da competência.

## 8. Resposta da API (`GET /api/v1/indicadores/caged-saldo`)
- Série: `medida=saldo`, `tipo_valor=null`, `tipo_periodo=mensal`, `unidade="postos de trabalho"`, `cv=null`, `classificacao=null` sempre, `nivel_evidencia="descritivo"`.
- Cada ponto: `periodo`, `valor` (o saldo **exatamente como na Tabela 5.1**), `lacuna`, `ajuste="com_ajuste"`, `competencia_coleta` (AAAA-MM do arquivo que gerou a versão servida), `coleta_id`.
- **Valores do MTE intactos e separados de qualquer cálculo.** `variacao_anual` (se vier) = saldo do mês − saldo do mesmo mês do ano anterior, **os dois do mesmo arquivo**, em `postos de trabalho`, com `variacao_anual_origem="calculo_observatorio"` e o rótulo «cálculo do Observatório a partir de dados do MTE». Null se faltar um dos dois.
- **`atribuicao`**: `{texto, link, licenca: null, base_legal: {texto, link}}`, corrigido na v1.4.1. Texto: «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo <mês/ano>, coletado em DD/MM/AAAA. Elaboração: OIL.» Base legal e link do decreto em `contrato-api-v1.4.1-delta.md`; mês do manifesto e data da coleta servida, convertida para America/Sao_Paulo.
- `nota_revisao`: «Série revisada mensalmente pelo MTE: os meses anteriores podem mudar a cada novo arquivo.»
- Sem coleta válida → **200** com `disponivel=false`, `motivo`, `pontos=[]` (nunca 404, nunca número inventado).
- Janela `?janela=2a|5a|desde_2020` como as outras séries.

## 9. Banco (migração 0004, sobre a 0003 do B2; sobe e desce)
- Derrubar `ck_observacao_valor` (`valor >= 0`) e trocar por um gatilho do PostgreSQL que só aceita valor negativo quando a série tem `medida='saldo'`. Assim a 6381 e a 6390 continuam barrando negativo.
- `observacao.classificacao_origem`: aceitar null (Caged não tem classificação). Check: `classificacao_origem IS NULL OR classificacao_origem='calculada'`.
- `observacao.variacao_anual_origem` (novo, null ou `'calculo_observatorio'`).
- Corrigir o cadastro do Caged que veio na 0002: `tipo_valor=NULL` (hoje está `'nominal'`), `unidade` e `unidade_variacao` = `'postos de trabalho'` (hoje `'vínculos'`), `fonte.link` = `{BASE}`, `disponivel` continua false até a 1ª coleta válida.
- Tabela `caged_arquivo` (competencia única, arquivo, drive_file_id, url_download, pagina_oficial, publicado_em, sha256, coleta_id FK) para a atribuição e a linhagem.
- Descida: não apaga se já houver observação do Caged (mesmo padrão da 0002).

## 10. Testes (antes do código)
Fixtures exclusivamente em `backend/tests/fixtures/o3/` (recortes reais e pequenos da Tabela 5.1, só para teste; ver o README e o manifesto dessa pasta). Não há planilhas nem cópia dos dados em `docs/`:
1. Recorte ago/2026 → ago/2026 = **165.827**; dez/2025 = **−635.078** (negativo grava e sai na API); jun/2026 = 136.959.
2. Revisão com dado real: carregar o recorte jul/2026 (jul = **58.568**) e depois o de ago/2026 (jul = **55.915**) → julho com versões 1 e 2, a API serve 55.915 com `competencia_coleta="2026-08"`; maio e dez/2025 também ganham versão 2; recarregar o mesmo arquivo não cria versão.
3. `variacao_anual` ago/2026 = 165.827 − 154.683 = **11.144**, com `variacao_anual_origem="calculo_observatorio"`; jul/2026 (arquivo ago) = 55.915 − 133.784 = **−77.869**; o `valor` continua igual ao da planilha.
4. Layout diferente (variações sintéticas feitas no teste a partir do recorte e rotuladas `simulada=true`: cabeçalho na linha 6, `Saldos` renomeado, só a aba `Tabela 5`, mês fora do formato, sha256 errado) → `valida=false`, nenhuma observação, a API segue com a última coleta boa e `desatualizado=true`.
5. Nunca lê a `Tabela 5`: com uma planilha que só tem `Tabela 5` → `valida=false`.
6. Sem coleta válida → 200, `disponivel=false`, `motivo`, `pontos=[]`.
7. Resposta: `tipo_valor=null`, `medida=saldo`, `tipo_periodo=mensal`, `unidade="postos de trabalho"`, `classificacao=null`, `cv=null`; atribuição com mês do arquivo e data da coleta em BRT, `licenca=null`, `base_legal={texto, link}`, link oficial e `nota_revisao`.
8. Calendário: 29/10/2026, 30/11/2026, 30/12/2026; `atrasado_calendario` true depois de 29/10 23:59 -03:00 sem a competência 2026-09.
9. Gatilho: valor negativo na 6381/6390 é recusado; no `caged-saldo` é aceito. Migração 0004 sobe, desce e sobe.
10. Download: 429/503 com `Retry-After` (teto 60 s), arquivo > 100 MB recusado (com `httpx.MockTransport`, sem rede).


### Versionamento do Caged (confirmado pelo Engenheiro de Dados, 17/10/2026; obrigatório)
1. A coleta grava `mes_referencia` do arquivo (ex.: 2026-08) e o `periodo_inicio` e o `periodo_fim` contidos nele.
2. Para cada mês, o valor é comparado sempre com a versão mais recente daquele mês, na ordem do `mes_referencia` (não do `coletado_em`). Qualquer mudança gera uma versão nova, inclusive a volta a um valor antigo.
3. Reconstruir o arquivo X: para cada mês entre o `periodo_inicio` e o `periodo_fim` de X, pegar a última versão vinda de coleta válida com `mes_referencia` ≤ o de X, ordenando pelo `mes_referencia`. Coletas com `valida=false` ficam fora. Carregar um arquivo antigo depois não pode alterar a série.
4. Testes: (a) carregar julho e depois agosto; a série reconstruída de cada arquivo é idêntica ao recorte da planilha dele (jul/2026 = 58.568 no de julho e 55.915 no de agosto; dez/2025 = −634.374 e −635.078; ago/2026 = 165.827); (b) a mesma checagem carregando agosto antes de julho (fora de ordem); (c) uma coleta inválida não entra na reconstrução; (d) a rota pública mostra a reconstrução do `mes_referencia` mais recente.
