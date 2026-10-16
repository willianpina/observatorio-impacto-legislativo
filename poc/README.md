# Observatório de Impacto Legislativo — prova de conceito

API local em Python 3.13+, FastAPI, HTTPX e Pydantic. Sem chaves de API, banco ou serviços pagos. Todos os arquivos desta entrega estão nesta pasta; o ambiente de execução usado pelo Codex está em `../../work/.venv`.

## Instalar no Windows (PowerShell)

Abra o PowerShell nesta pasta (`outputs/poc`) e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Não é necessário ativar o ambiente nem alterar a política de execução do PowerShell. Dependências diretas fixadas; o arquivo não constitui um lock completo das dependências transitivas. Para reprodução estrita, gere e revise um lock antes da implantação.

## Iniciar e consultar a API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Em outro PowerShell:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/legislacao?limite=3&ano=2026' | ConvertTo-Json -Depth 10
Invoke-RestMethod 'http://127.0.0.1:8000/api/indicadores/desemprego' | ConvertTo-Json -Depth 10
Start-Process 'http://127.0.0.1:8000/docs'
```

Encerre o servidor com Ctrl+C. O teste real inicia seu próprio servidor na porta 8765 e o encerra ao terminar; não deixa serviço instalado.

## Testes separados

Testes simulados, sem consultas externas:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --junitxml=evidencias/testes-simulados.xml
```

O isolamento de plugins evita interferência de plugins globais do computador. O comando produz 39 testes cobrindo campos obrigatórios, envelope, valores e dimensões, situação opcional, divergência entre listagem/detalhe, limites de parâmetros, JSON inválido, conexões, timeout, HTTP 404/429/503, recuperação após falha, limite de três tentativas e bloqueio de consulta quando metadados divergem. O aviso de depreciação do TestClient/HTTPX da versão instalada está documentado no relatório.

Integração real, requer internet e acesso HTTPS aos domínios oficiais:

```powershell
.\.venv\Scripts\python.exe validate_live.py
```

Retorna código 0 somente se as duas fontes e as duas rotas HTTP locais passarem. Usa IDs recebidos da listagem da Câmara. Sobrescreve a última rodada em `evidencias`; copie essa pasta antes de uma nova execução se desejar preservar o histórico. O arquivo `resultado.json` registra sucesso/falha por fonte. `consultas-reais.json` contém payloads brutos, URL, horário UTC, status HTTP, tentativa e duração. O manifesto SHA-256 permite detectar alterações locais; não é assinatura digital. Os JSON normalizados e as respostas da API local são evidências complementares. A amostra legislativa adicional de 2025 é informativa e registrada separadamente.

## Contrato para o frontend

Ambas as rotas entregam `{ "dados": [...], "meta": {...} }`. `meta` inclui fonte, URLs consultadas, quantidade, instante ISO 8601 UTC e duração em milissegundos. A série inclui também tabela, variável e periodicidade.

- Legislação: `id`, `tipo`, `numero`, `ano`, `ementa`, `situacao` (texto ou null), `origem`. Consulta PL por ano, limite padrão 3 e máximo 5; enriquece todos os resultados com consulta detalhada. Lista vazia é válida quando não existem resultados. Não segue URLs arbitrárias retornadas pela fonte.
- Desocupação: oito trimestres nacionais consecutivos, ordenados por `periodo` (`AAAATT`, por exemplo `202602`), `rotulo`, `valor` numérico em porcentagem, `unidade`, `territorio`, `status`, `valor_original` e `origem`. Use `rotulo` no eixo X e `valor` no eixo Y. `5.4` significa **5,4%**. Símbolos oficiais de ausência (`...`, `..`, `-`, `X`) produzem null, nunca zero. O frontend deve deixar lacunas nesses pontos. Outras strings ou dimensões inesperadas são rejeitadas.

Erros entregam `{ "erro": { "codigo": "...", "fonte": "camara|ibge" } }`: 502 para resposta inválida ou HTTP definitivo da fonte; 503 para conexão/fonte indisponível; 504 para timeout. Parâmetros locais inválidos usam o erro padrão 422 do FastAPI. Uma falha em qualquer detalhe da Câmara impede a entrega de resultado parcial.

## Fontes e operação

- [Documentação Câmara](https://dadosabertos.camara.leg.br/swagger/api.html) e [OpenAPI oficial](https://dadosabertos.camara.leg.br/api/v2/api-docs).
- [APIs IBGE](https://servicodados.ibge.gov.br/api/docs/) e [documentação de agregados v3](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3).
- [Metadados oficiais 4099](https://servicodados.ibge.gov.br/api/v3/agregados/4099/metadados): tabela **4099**, variável **4099**, taxa de desocupação de pessoas de 14 anos ou mais na semana de referência, **trimestral**, **%**. Validados antes da implementação e novamente antes de cada extração.
- [Tabela SIDRA 4099](https://sidra.ibge.gov.br/tabela/4099), [API SIDRA](https://apisidra.ibge.gov.br/) e [consulta nacional usada](https://apisidra.ibge.gov.br/values/t/4099/n1/all/v/4099/p/last%208). `last 8` significa oito períodos disponíveis; o ano/trimestre é fornecido pela fonte, sem datas fabricadas. O portal de documentação SIDRA retornou 403 nesta rede; a confirmação semântica veio dos metadados oficiais de agregados e da resposta real do SIDRA.

HTTPS validado pelo armazenamento de certificados do sistema via `truststore`; nunca usa `verify=False`. Timeout por operação HTTP de 20 s e conexão de 5 s; até três tentativas por requisição GET, pausas de 0,25 e 0,5 s, apenas para falhas transitórias. Não há prazo global da rota: múltiplas consultas podem somar seus timeouts. Retentativas não implementam ainda o cabeçalho Retry-After. URLs são fixas e não há entrada de credenciais. Logs operacionais podem ser habilitados configurando o logger `observatorio` no host; evidências completas são persistidas apenas pelo validador explícito. API sem autenticação, adequada apenas ao loopback local.

Leia `RELATORIO.md` para resultados e limitações desta execução.
