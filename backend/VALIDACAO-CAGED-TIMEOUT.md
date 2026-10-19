# Caged — timeout de leitura configurável, 19/10/2026

Branch codex/caged-timeout-leitura a partir da main 8de4af8. Nenhuma coleta real executada. Agosto e julho não foram consultados, nenhum arquivo baixado da rede. PR em rascunho, sem merge, CI ou deploy.

## Resultado

O timeout é aplicado somente à requisição do job Caged: conexão 5 s, leitura pela variável OIL_CAGED_READ_TIMEOUT (120 s por padrão, teto 300 s), escrita e pool 10 s. Valores inválidos são rejeitados antes da requisição. O cliente compartilhado e as rotas não foram alterados.

O streaming em arquivo temporário, SHA-256 incremental, teto de download de 100 MiB e teto de descompactação de 512 MiB foram preservados. Um bloco que excede o teto encerra o download e não valida a coleta. O hash parcial acompanha os bytes efetivamente recebidos, inclusive o bloco que disparou o corte, sem gravá-lo além do teto no temporário. Redirecionamentos habilitados somente nesta requisição, com confirm=t na URL do Drive; manifesto intacto.

Coleta.erro distingue timeout_conexao, timeout_primeiro_byte e timeout_leitura. Antes do corpo inclui espera por cabeçalhos; depois do primeiro byte inclui status, tamanho e hash parcial. A resposta pública continua timeout_fonte/504. Não houve migração nem mudança no versionamento. O teste de revisão verifica valores, versões e coleta_id das duas versões de um mesmo mês.

## Testes antes do código e validação final

- Base: 16 falhas e 2 aprovações nos 18 testes novos; PoC 39 aprovações.
- Teste adicional do hash parcial no corte: 1 falha de asserção, 17 deselecionados; correção anterior à suíte final.
- Final backend: 261 aprovados e 2 testes ao vivo pulados, zero falhas.
- Final PoC: 39 aprovados, zero falhas. Aviso de depreciação preexistente do Starlette/HTTPX.
- Todos os transportes do Caged são MockTransport. O atraso de 30 s é virtual: o transporte compara o atraso com request.extensions['timeout']; nenhum sleep real de 30 s, nenhum socket externo. Com leitura 120 s passa; com 20 s falha e registra timeout_primeiro_byte.
- Testes cobrem três fases, limites e configurações inválidas, fechamento dos recursos, mais de 100 MiB sem Content-Length, hash da fixture e persistência de revisões.

Banco de teste criado pelo executor existente em porta host aleatória, credenciais apenas em memória, removido ao concluir. A saída literal de docker ps -a --filter name=oil- após a limpeza está na evidência. Nenhuma API foi iniciada.

Gitleaks staging e histórico completo --all antes e depois do commit: zero é condição do push, sem exceções novas. O JSON pós-commit externo e o corpo do PR registram o SHA final verificado; o arquivo não entra no próprio commit para evitar autorreferência. Resumo do pytest e diff integral de caged.py no PR. Frontend, PoC, cliente comum, rotas e manifesto sem alterações.

Limitação: testes com transporte falso validam a configuração e as fases de forma determinística; não comprovam disponibilidade do Drive nem sucesso futuro de agosto. Não há nova autorização de coleta real nesta tarefa.
