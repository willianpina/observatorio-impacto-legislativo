# Adendo O3 (17/10/2026): nova base e sobras da O4

1. **Base nova.** Crie a branch `codex/o3-lei-caged` a partir da `main` em `345af863`, que já tem a O4 (PR #2) mergeada. Preserve tudo o que a O4 entregou e não reescreva o histórico (sem rebase de main, sem force push).
2. **Arquivos de missão fora de `docs/`.** Os arquivos `missao-*.md` citam frases proibidas como exemplo e fazem o `test_language.py` falhar. Coloque-os em `frontend/referencias/o3/`, não em `docs/o3/`. Os demais anexos (specs, contrato, manifesto, confirmação EC 141) vão em `docs/o3/` normalmente. Não mexa na lista de frases proibidas.
3. **Sobras da O4 a incluir nesta rodada (não bloqueantes):**
   - Linguagem: bloquear também data em formato BR (ex.: 14/10/2026) junto de variação; evento genérico («Com a promulgação, ... caiu»); generalizar «antes e depois d(a|o)».
   - Marco do calendário: fechar ao perder o foco (Tab).
   - axe no conteúdo do «Saiba mais» em mais cenários; teste card = resumo também no rendimento com valor não inteiro.
   - `tests/check-mutations.mjs`: rodar em cópia/worktree, ou checar `git diff --exit-code` antes de commit.
4. **Fora desta rodada:** a conferência do art. 3º e do Art. 9º da EC está com o Especialista Legislativo; não altere esses textos agora.
5. **Entrega:** PR em rascunho, sem merge. Relatório com commit, números de testes (backend, PoC, Playwright, mutações), gitleaks e pendências.
