# Operação local O3

Execute a partir da raiz do repositório. Use Python 3.13, Docker Desktop para os testes e uma variável `DATABASE_URL` já definida no ambiente para uso normal. Não há leitura de arquivo de ambiente pelo backend.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m backend.oil.o3_cli lei
.\.venv\Scripts\python.exe -m backend.oil.o3_cli caged 2026-08
.\.venv\Scripts\python.exe -m backend.oil.o3_cli calendario-caged
.\.venv\Scripts\python.exe -m uvicorn backend.oil.main:app --host 127.0.0.1 --port 8766
```

As consultas HTTP da API leem somente o banco. Os jobs acima fazem coleta real, sem fallback de fixture. O manifesto manual `backend/data/caged_manifesto.json` contém os arquivos completos informados no pacote do Engenheiro de Dados; os hashes são dos originais. A publicação de julho não foi informada no manifesto de apoio e permanece nula. Atualize o manifesto após conferência humana de cada divulgação. Redirecionamentos HTTP não são seguidos automaticamente.

O calendário do MTE é cadastrado pelo comando explícito, sem rede e sem criar coletas. Como a fonte informa apenas o dia, usa-se 23:59 no fuso -03:00 como convenção do Observatório. Não se estima atraso pela idade da coleta. Sem cadastro, o atraso fica falso.

## Testes no Windows

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe backend/scripts/test_postgres.py
Set-Location frontend
npm ci --ignore-scripts --no-audit --no-fund
$env:NEXT_TELEMETRY_DISABLED='1'
$env:OIL_BROWSER_CHANNEL='msedge'
npm run typecheck
npm run build
npm run test:e2e
```

O script de PostgreSQL cria um banco descartável exclusivo, aplica todas as migrações e roda backend e PoC separadamente. Os dois testes ao vivo do IBGE ficam desligados. Nenhum teste novo acessa rede: HTTPX MockTransport reproduz os arquivos gravados fornecidos. Replay é sempre marcado como simulado e filtrado no modo normal. Recortes de planilhas são aceitos apenas pelo coletor em modo de teste explícito; em produção, a série deve começar em janeiro de 2020. As fixtures permanecem privadas e fora de artefatos publicados.

## Linhagem e revisões

Cada tentativa tem URL, HTTP quando recebido, instante UTC e hash quando há corpo. JSON legislativo é guardado integralmente, exceto o de deputado, reduzido a id, nome, partido e UF; nesse caso, o hash continua sendo o do corpo original recebido; XLSX é baixado por streaming para arquivo temporário, com limite de 100 MB e sem guardar o corpo no banco. O metadado do manifesto fica imutável em cada coleta, além do cadastro do arquivo por competência. Assim uma coleta histórica ou simulada não substitui a atribuição de outra coleta.

A Tabela 5.1 é validada antes de qualquer observação. SHA-256 é obrigatório antes do download. Cabeçalho, título, continuidade, inteiro, competência e hash divergentes invalidam a coleta. ZIP admite no máximo 200 MiB expandidos e razão 100 por membro; a leitura fica limitada a 1000 linhas de dados, com defusedxml ativo. Respostas legislativas têm teto de 5 MiB. Falhas posteriores à última coleta boa fazem a API sinalizar desatualização. Ausência de Caged válido retorna 200, indisponível, sem pontos.

As versões registram a ordem de ingestão, enquanto a precedência dos dados usa o mês de referência da fonte. Reconstrução exclui coletas inválidas e seleciona versões até a competência pedida. Ao receber um arquivo intermediário tarde, materializam-se as fronteiras necessárias para preservar arquivos futuros já validados. Repetição idêntica não duplica observações. Variação anual usa dois valores da mesma reconstrução e é identificada como cálculo do Observatório; os saldos do MTE são preservados.

Os snapshots legislativos só ganham versão quando os campos mudam. A situação atual usa a data da situação, com desempate pelo Senado. As duas situações permanecem literais; a comparação de estágios trata as flexões de transformação em norma jurídica como equivalentes. Não há interpretação jurídica de vigência. Norma gerada ausente fica nula. Os links e datas de conferência vêm do documento fornecido pelo usuário, sem nova conferência ao vivo nesta execução.

Migrações recusam descida quando isso apagaria observações do Caged ou snapshots legislativos. O teste completo de subida/descida usa o mesmo isolamento de banco vazio das demais funções de teste. Marcos de teste têm unicidade separada dos reais, além do filtro por coleta.

## Limitações

Não há descoberta automática de arquivo, agendamento do job, autenticação pública, nova conferência de artigos da norma, tramitação paginada ou votos nesta missão. A integração da tela com o novo contrato legislativo fica para uma rodada própria; a tela O4 é preservada com as pequenas correções autorizadas no adendo. As coletas reais novas não foram executadas para validar disponibilidade externa: esta entrega valida ingestão e rotas por replay rastreável em banco PostgreSQL real.


## Regressões intencionais O3-R

Com o código rastreado sem alterações, execute separadamente:

```powershell
.\.venv\Scripts\python.exe backend/scripts/check_mutations_o3.py
Set-Location frontend
node tests/check-mutations.mjs
```

Os scripts usam worktrees descartáveis fora do repositório e conferem `git diff --exit-code` após cada restauração. A execução do backend usa somente PostgreSQL descartável em porta aleatória de loopback. O argumento `--only` permite retomar casos específicos, preservando a evidência anterior para consolidação por identificador.

## Navegador e evidência de mutações
No Windows, use `$env:OIL_BROWSER_CHANNEL='msedge'`; no Linux, `OIL_BROWSER_CHANNEL=chromium`. O Playwright principal usa Chromium quando a variável não é definida; `check-mutations.mjs` e `capture-real.mjs` usam msedge como fallback. Defina a variável explicitamente para manter as execuções consistentes.
As mutações gravam por padrão somente fora do Git e exigem checkout limpo. `--publicar-evidencia` copia o resultado para a evidência versionada, somente no passo explícito de documentação.

## Tela O3-C
A tela normal consulta a API local pelo proxy de indicadores e pelo proxy legislativo com id fixo 2233802. Configure `OIL_API_URL` no ambiente do processo. O contrato legislativo é v1.4.1: ementa literal, autoria, situações e linhagem. Ele não fornece resumo, vigência ou votos. Os exemplos de vigência e votação são servidos por `/api/oil/exemplo` somente quando `OIL_TEST_MODE=1`; no modo normal, esse caminho retorna 404.

A evidência da coleta manual única está em `docs/o3/evidencias/o3c-coleta-real.json`. Não há fallback simulado em coleta real. O verificador opt-in `node tests/capture-real.mjs`, executado dentro de `frontend/` com os serviços locais em 8766 e 3100, grava artefatos `o3c-` e retorna erro se alguma fonte estiver indisponível. Nesta rodada, o Caged foi recusado pelo validador e o resultado é parcial; o verificador não muda os hashes do manifesto.
