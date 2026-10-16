# O2 — banco local e séries IBGE

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

Os aliases `/api/v1/indicadores/desocupacao` e `/api/v1/indicadores/rendimento-real` atendem às URLs do contrato v1.3 fornecido. `/docs` mostra o OpenAPI. As rotas legadas `/api/legislacao` e `/api/indicadores/desemprego` usam o código original da PoC, incluindo suas consultas externas; também é possível continuar iniciando a aplicação da PoC como antes.

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

Argumentos: `codigo --periodo AAAAMM --prevista-em INSTANTE_COM_FUSO --fonte NOME --link URL_OFICIAL`. Nenhuma data aproximada é cadastrada automaticamente. Sem calendário, `atrasado_calendario=false`. Atraso é uma data prevista já passada sem o período esperado entre as observações da fonte. Falha de coleta é outro estado: `desatualizado=true` quando há dados anteriores válidos; sem coleta boa, um erro estruturado 502/503/504 é devolvido. 503 inclui Retry-After.

## Persistência e limitações

- `fonte`, `coleta`, `serie`, `observacao` e `divulgacao` têm migração inicial explícita. Nenhuma tabela é criada automaticamente no startup.
- `coleta` conserva corpo da resposta em bytes, URL, fuso UTC, HTTP e SHA-256. O hash é de `response.content` (corpo entregue pelo HTTPX, após descompressão HTTP), não dos bytes de transporte. Falha de conexão não tem corpo/HTTP/hash; isso fica null, nunca fabricado. Metadados também são auditados.
- Cada revisão de nível, CV, variação ou classificação gera nova versão por série/período. Repetição idêntica só gera coleta, sem duplicar observação. Um lock da linha da série serializa revisões concorrentes. Versões anteriores e o corpo que as originou permanecem guardados. Cada ponto referencia sua coleta de origem; o topo da série referencia a última coleta validada.
- Variável 8838 é guardada como `diferenca_anual` e identificada em `variaveis.diferenca_anual`; a resposta bruta completa permanece na linhagem. A API expõe 8837 como `variacao_anual` do rendimento. `base_precos=null`; não há nova deflação.
- Janela padrão: 60 períodos móveis, terminando no último período disponível; `2a`: 24 períodos; `desde_2020`: a partir de 202001. É recorte mensal, sem agregação. A coleta guarda histórico anterior para não mudar a classificação ao recortar o gráfico.
- No campo categórico `tipo_valor`, a taxa de desocupação usa `nominal`; isso não significa moeda nem deflação. `medida=taxa` e `unidade=%` definem sua interpretação. Rendimento usa `tipo_valor=real` e `medida=valor`.
- Timeout por requisição: 20 s, conexão: 5 s, no máximo 3 tentativas com pausas limitadas (0,25/0,5 s). HTTP 429 e 500/502/503/504 são transitórios. Ainda não há prazo global do job, scheduler, autenticação pública ou implementação de Retry-After da fonte. A API é destinada ao loopback local.
- Nenhum Caged, dashboard, votação, dado legislativo novo, IA, deploy, serviço pago ou GitHub Actions integra a O2.

Referências e regras: [contrato para indicadores](../docs/contrato-api-v1.3-indicadores.md), [metodologia O2](../docs/metodologia-o2.md).
