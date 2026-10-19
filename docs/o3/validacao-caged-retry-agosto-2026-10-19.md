# Retry único do Caged — agosto/2026

Execução real autorizada em 19/10/2026, sem fixture, sem coleta de julho e sem nova tentativa automática. Branch codex/caged-validacao-real, base c00b563. Nenhum código do produto, manifesto ou teto foi alterado.

| Job | HTTP | Hash recebido | coleta_id | Válida | Pontos |
|---|---|---|---:|---|---:|
| caged 2026-08 | Não recebido | Não calculado | 1 | não | 0 |

A consulta durou 20,424 s e registrou timeout_fonte. O RuntimeError externo é exclusivamente a trava que bloqueou a reconexão; não substitui a causa persistida. Houve exatamente um GET ao endereço do manifesto. Agosto não chegou à validação do arquivo, portanto não foi aprovado nem classificado como arquivo_invalido. Nenhum hash de conteúdo foi inventado.

PostgreSQL novo descartável, porta host aleatória 50737, credenciais somente em memória. Migração concluída. A API não foi iniciada. Contêiner encerrado e removido. A saída literal de docker ps -a --filter name=oil- está no TXT de evidência e no JSON: somente cabeçalho, nenhum contêiner correspondente.

Gitleaks no staging e no histórico inteiro antes e depois do commit, sem exceções novas. O JSON pós-commit externo registra o SHA final verificado; não é acrescentado ao próprio commit para evitar autorreferência. Nenhum teste simulado foi contado como validação real. Nova tentativa de agosto fica a cargo do Willian.
