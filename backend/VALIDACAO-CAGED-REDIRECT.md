# PR #6 — correção de redirecionamento, 19/10/2026

Achado Alto corrigido na mesma branch codex/caged-timeout-leitura, base 23ea09f. A única alteração funcional em caged.py é follow_redirects=True para follow_redirects=False. Não há implementação de seguimento seletivo, allowlist ou limite futuro de saltos nesta rodada.

302 gera uma única requisição, Coleta.codigo_http=302, valida=false e erro=http_fonte, sem hash nem observações. Location não é consultado, mesmo quando usa o próprio host HTTPS. Os outros testes cobrem host fora da lista e HTTP. O teste de hash da fixture continua com resposta direta 200, streaming, confirm=t e fechamento do temporário.

## Testes locais, antes e depois do código

- Antes: três falhas de asserção contra a versão com redirecionamento habilitado; 18 testes fora do filtro.
- Depois, bateria executada manualmente com python backend/scripts/test_postgres.py -k caged: 48 aprovados, 218 deselecionados, 1 aviso em 5,51 s.
- PoC executada separadamente pelo mesmo executor: 39 aprovados, 1 aviso em 3,99 s.
- Aviso preexistente de depreciação do Starlette/HTTPX. Esta rodada é a bateria Caged, não uma nova execução integral de todos os testes backend.
- MockTransport em todos os downloads de teste; RUN_LIVE_IBGE=0. Nenhuma coleta real, agosto/julho não consultados.

PostgreSQL descartável local em porta host aleatória e credenciais apenas em memória, removido ao terminar. Nenhuma API iniciada. A saída de docker ps -a --filter name=oil- está na evidência. Sem merge e sem CI. Timeout configurável, tetos, manifesto, outras fontes, rotas, frontend e PoC intactos.

Gitleaks no staging e histórico completo --all antes e depois do commit: zero é condição do push, sem exceções novas. O JSON pós-commit externo registra o SHA final e também é publicado no corpo do PR, evitando autorreferência do arquivo dentro do próprio commit. Resumo literal do pytest e diff integral desta correção em caged.py no PR. Checkout limpo ao concluir.
