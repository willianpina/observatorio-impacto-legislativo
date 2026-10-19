# Caged — coleta real única em 18/10/2026 (BRT)

Base `main`: `c000ee67401493998ffe2ce14f743dc14b304272`. Branch de evidência `codex/caged-validacao-real`. Nenhum código do produto ou manifesto alterado.

**Resultado parcial:** julho entrou como dado válido, com 79 pontos. Agosto sofreu `timeout_fonte` antes de haver status HTTP ou hash registrado, com zero pontos. Não é possível comprovar agosto nesta execução. Não houve `arquivo_invalido`; o arquivo de agosto não chegou ao parser.

| Job | HTTP | SHA-256 | coleta_id | Válida | Pontos | Duração |
|---|---|---|---:|---|---:|---:|
| caged 2026-07 | 200 | 367b66f4af878d0c1ab5b9fc881f228976e74a2240cb5d3afdc83aef78cabe01 | 1 | true | 79 | 20.972 s |
| caged 2026-08 | não recebido | não calculado | 2 | false | 0 | 20.029 s |

O hash de julho bate exatamente com o manifesto. `simulada=false` nas duas coletas. O subcódigo de agosto gravado em `Coleta.erro` foi `timeout_fonte`. O orquestrador lançou uma exceção ao impedir a reconexão automática; isso não é um erro de parser e não foi contado como nova tentativa.

Cada URL teve uma única requisição HTTPX autorizada. Não houve retry, redownload, fallback de fixture, mudança de hash ou de teto. Mantido o teto da main, 512 MiB. Uma nova tentativa de agosto depende de nova autorização do Willian.

PostgreSQL novo e descartável, publicado apenas em loopback, porta aleatória `65140` (diferente de 5432), credenciais somente no ambiente/memória dos processos; sem leitura de arquivo de ambiente. Migração inicial aprovada. O contêiner próprio foi parado e removido (`--rm`). A API não foi iniciada porque os dois arquivos não passaram; não há API desta execução em funcionamento.

## Segurança e entrega

Gitleaks no staging e no histórico completo (`--all`), antes e depois do commit de evidência: resultados registrados nos relatórios da execução e na entrega. Sem allowlist nova. Push somente de evidência; sem merge, CI, deploy ou serviço pago. O checkout termina limpo.

Evidência estruturada: `evidencias/caged-real-2026-10-18.json`. O arquivo contém horários UTC/BRT, hashes, contagens e o encerramento dos recursos, sem senha, URL de banco ou corpo baixado.
