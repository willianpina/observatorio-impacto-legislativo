# O2 — banco local e séries IBGE

## Timeout exclusivo do download do Caged

`OIL_CAGED_READ_TIMEOUT` configura em segundos o prazo de leitura de cada operação de rede do job Caged: padrão 120, máximo 300. Valores positivos fracionários são aceitos; zero, negativos, valores não numéricos e não finitos são rejeitados antes do download. No PowerShell, configure apenas o ambiente do processo:

```powershell
$env:OIL_CAGED_READ_TIMEOUT='120'
```

O job usa `connect=5`, `write=10` e `pool=10`, com `follow_redirects=False` e `confirm=t` no endereço do Drive. Um 302 registra a coleta com `valida=false`, sem consultar o endereço de `Location`. Não altera o cliente compartilhado, outras fontes ou as rotas. O timeout de leitura é por espera de dados, não um limite total da duração do arquivo.

O download é em streaming para arquivo temporário, com contagem de bytes e SHA-256 incremental. O teto existente permanece em `100 * 1024 * 1024` bytes (100 MiB); excedê-lo interrompe o fluxo e mantém a coleta inválida. O teto de descompactação também permanece inalterado. Arquivo temporário e resposta são fechados mesmo em erro.

`Coleta.erro` distingue `timeout_conexao` (conexão ou espera pelo pool), `timeout_primeiro_byte` (antes do primeiro byte do corpo, incluindo espera pelos cabeçalhos) e `timeout_leitura` (após receber bytes do corpo). Quando disponíveis, preserva status HTTP, quantidade recebida e hash parcial; esse hash não valida um arquivo incompleto. O erro público continua `timeout_fonte`/504 e as tentativas continuam limitadas a três. Revisões mantêm as versões anteriores e a ligação de cada observação com sua coleta.

Os testes de timeout usam `httpx.MockTransport` e atrasos virtuais: não dormem 30 segundos nem fazem requisições reais. O transporte falso compara o atraso ao timeout enviado na requisição, pois o MockTransport não aplica deadlines de socket. A suíte usa banco descartável e não autoriza baixar arquivos reais:

```powershell
.\.venv\Scripts\python.exe backend/scripts/test_postgres.py backend/tests/test_caged_timeout.py
```

Executar a partir da raiz do repositório com Python 3.13 e PostgreSQL 17 local. A pasta `poc/` permanece intacta. Nenhum arquivo `.env` é lido automaticamente. A URL do banco vem exclusivamente da variável de ambiente `DATABASE_URL`; `.env.example` é só um exemplo, sem credenciais reais.

## Instalação (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Configure `DATABASE_URL` no ambiente do processo com sua conexão PostgreSQL/psycopg. O formato está em `.env.example`. Não há URL padrão nem fallback SQLite. Para um PostgreSQL local dedicado via Docker, configure `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` no ambiente e execute:

```powershell
docker run --name oil-postgres --detach --publish 127.0.0.1:5432:5432 --env POSTGRES_USER --env POSTGRES_PASSWORD --env POSTGRES_DB --volume oil-postgres-data:/var/lib/postgresql/data postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
```

O banco de aplicação é persistente no volume local. Não aponta para bancos de outros projetos. O comando de downgrade remove as tabelas da O2 e seus dados; use somente em banco dedicado:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini downgrade base
```

## Ingestão separada da API

```powershell
.\.venv\Scripts\python.exe -m backend.oil.cli desocupacao rendimento-real
.\.venv\Scripts\python.exe -m uvicorn backend.oil.main:app --host 127.0.0.1 --port 8000
```

O job consulta metadados oficiais antes dos valores, guarda cada tentativa e ingere a série nacional completa (`n1/all`, `p/all`), incluindo os períodos anteriores necessários para a comparação anual. Não usa valores fixados nem fixtures. Se a fonte falhar, o job registra a falha e retorna código 1. GETs novos leem exclusivamente o banco; nunca fazem coleta.

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/indicadores'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/indicadores/desocupacao/serie?janela=2a'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/indicadores/rendimento-real/serie?janela=desde_2020'
```

A rota de séries é somente `/api/v1/indicadores/{codigo}/serie`, conforme a O2-R e o contrato v1.3.1. A exceção explícita `/api/v1/indicadores/caged-saldo` retorna HTTP 200 com `disponivel=false`, motivo e `pontos=[]`, sem inventar valores ou arquivo de origem. Caged também aparece no índice e em `/caged-saldo/serie`. `/docs` mostra o OpenAPI. As rotas legadas `/api/legislacao` e `/api/indicadores/desemprego` usam o código original da PoC, incluindo suas consultas externas; também é possível continuar iniciando a aplicação da PoC como antes.

## Testes reproduzíveis, sem banco existente e sem fontes externas

Com Docker local disponível:

```powershell
.\.venv\Scripts\python.exe backend/scripts/test_postgres.py
```

O script cria um PostgreSQL descartável exclusivo, com nome aleatório, senha efêmera em memória e porta dinâmica em loopback. Ignora qualquer `DATABASE_URL` preexistente, injeta a conexão somente no ambiente dos testes e encerra apenas o contêiner que criou. Os testes de migração executam upgrade, downgrade e novo upgrade reais. Testes recusam banco não marcado como descartável. Não há reset/clean/stash nem alteração de outros bancos. O script executa a suíte nova e, separadamente, os 39 testes originais da PoC, desabilitando plugins globais e gravação de bytecode.

As fixtures contêm respostas **gravadas da fonte real**, cujo replay é sempre **simulado**. `tests/fixtures/manifesto.json` registra URLs, horário e hashes. Mutações para testes de revisão/erro são explicitamente sintéticas e não são servidas em modo normal. `OIL_TEST_MODE=1` é obrigatório para ingestão simulada; o servidor normal exclui essas coletas e observações. Não configure essa variável no uso normal.

Teste ao vivo opcional, desligado por padrão:

```powershell
$env:RUN_LIVE_IBGE='1'
.\.venv\Scripts\python.exe backend/scripts/test_postgres.py -m live
Remove-Item Env:RUN_LIVE_IBGE
```

Confere a referência jun–ago/2026: desocupação 5,3%, CV 1,3%; rendimento R$ 3.777, CV 0,7%. Se a fonte falhar, executa replay gravado com `simulada=true` e aviso explícito, sem aprovar disponibilidade real. Uma resposta válida com valor/período diferente falha, para revisão humana da expectativa. A suíte normal deixa esses dois casos como skipped. O `poc/validate_live.py` não é executado pelo script.

## Calendário manual

`divulgacao` começa vazia. Cadastre somente uma data/hora conferida no calendário público do IBGE, usando período `AAAAMM` do mês final, instante ISO com fuso, nome da fonte e link HTTPS do IBGE:

```powershell
.\.venv\Scripts\python.exe -m backend.oil.calendar --help
```

Argumentos: `codigo --periodo AAAAMM --prevista-em INSTANTE_COM_FUSO --fonte NOME --link URL_OFICIAL`. Fonte e link aceitam até 500 caracteres, tanto na CLI quanto na função de cadastro. Nenhuma data aproximada é cadastrada automaticamente. Sem calendário, `atrasado_calendario=false`. Atraso é uma data prevista já passada sem o período esperado entre as observações da fonte. Falha de coleta é outro estado: `desatualizado=true` quando há dados anteriores válidos; sem coleta boa, um erro estruturado 502/503/504 é devolvido, com `ultima_coleta_id=null`. Tentativa falha nunca é identificada como coleta válida. 503 inclui Retry-After.

## Persistência e limitações

- `fonte`, `coleta`, `serie`, `observacao` e `divulgacao` têm migração inicial explícita. A migração `0002` mantém observações existentes, torna `tipo_valor` nulo nas taxas e cadastra Caged como indisponível. Nenhuma tabela é criada automaticamente no startup.
- `coleta` conserva corpo da resposta em bytes, URL, fuso UTC, HTTP e SHA-256. O hash é de `response.content` (corpo entregue pelo HTTPX, após descompressão HTTP), não dos bytes de transporte. Falha de conexão não tem corpo/HTTP/hash; isso fica null, nunca fabricado. Metadados também são auditados.
- Cada revisão de nível, CV, variação ou classificação gera nova versão por série/período. Repetição idêntica só gera coleta, sem duplicar observação. Um lock da linha da série serializa revisões concorrentes. Versões anteriores e o corpo que as originou permanecem guardados. Cada ponto referencia sua coleta de origem; o topo da série referencia a última coleta validada.
- Variável 8838 é guardada como `diferenca_anual` e identificada em `variaveis.diferenca_anual`; a resposta bruta completa permanece na linhagem. A API expõe 8837 como `variacao_anual` do rendimento. `base_precos=null`; não há nova deflação.
- Janela padrão: 60 períodos móveis, terminando no último período disponível; `2a`: 24 períodos; `desde_2020`: a partir de 202001. É recorte mensal, sem agregação. A coleta guarda histórico anterior para não mudar a classificação ao recortar o gráfico.
- Conforme o contrato v1.3.1, `tipo_valor=null` quando `medida=taxa`, no banco e na resposta. Rendimento usa `tipo_valor=real` e `medida=valor`. `variacao_anual_unidade` vem em cada série e ponto: `p.p.` na desocupação e `%` no rendimento.
- A leitura também materializa períodos intermediários ausentes do banco com valor/CV/classificação nulos, `lacuna=true` e sem inventar um ID de coleta ou versão para o ponto ausente.
- Timeout por requisição: 20 s, conexão: 5 s, até 5 conexões HTTP e no máximo 3 tentativas. Para HTTP 429/503, respeita Retry-After em segundos ou data HTTP, limitado a 60 s. Sem cabeçalho válido, aplica pausas de 0,25/0,5 s. HTTP 500/502/504 também são transitórios. Ainda não há prazo global do job, scheduler ou autenticação pública. A API é destinada ao loopback local.
- A guarda parametrizada de linguagem verifica todas as strings das respostas exercitadas (inclusive nomes, motivos, erros e rotas legadas) e todos os arquivos de `docs/`.
- A O3 acrescenta ingestão do Caged e detalhe legislativo: consulte [operação O3](../docs/o3/operacao.md). Votações, IA, deploy, serviços pagos e GitHub Actions continuam fora do escopo.

Referências e regras: [contrato para indicadores](../docs/contrato-api-v1.3-indicadores.md), [metodologia O2](../docs/metodologia-o2.md).
