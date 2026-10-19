# O4 — correção do PR #5, 19/10/2026

Branch codex/o4-tela-lei, base 9387bd31. PR continua em rascunho, sem merge, CI ou deploy. Alterações somente em frontend/; backend, PoC e API real preservados.

## Correções

- Aprovação exige resultado exato após normalizar espaços externos, Unicode e caixa: aprovada/aprovado. A negação não passa. PEC usa os limites locais 308 na Câmara e 49 no Senado; divergência do quórum recebido bloqueia o selo e avisa conferência. Os demais tipos não recebem a regra de PEC.
- O B8 usa cartões com dl/dt/dd em desktop e celular. Todos têm O que fornece, Tabela/ID, Situação e coleta. Câmara e Senado usam nomes legíveis. As três séries têm CSV de observações; as quatro referências legislativas têm CSV de seus metadados (não são planilhas de votações inexistentes). Links oficiais continuam validados.
- Barras sem dado mostram s/d, inclusive quando um ajuste incompatível é omitido; não viram zero. A identificação da PEC no cabeçalho leva ao link oficial da proposição recebido da API.

## Validação

Testes escritos antes das correções: 7 falhas e 4 aprovações contra a base. Duas tentativas de inicialização local tiveram bloqueio/porta ocupada e foram descartadas como infraestrutura. A contagem vermelha considera exclusivamente asserções válidas. Os 11 novos testes passaram. A primeira matriz completa teve 163 aprovações e um seletor legado ambíguo, porque a situação aparece também no B8. O seletor foi limitado a #lei e a matriz completa refeita. Uma execução adicional iniciada no diretório incorreto foi interrompida e descartada como infraestrutura.

M4 (limiar de aprovação menos um voto): morto. Os testes de 307 na Câmara e 48 no Senado falharam por asserção; os outros seis casos passaram. Nenhum erro de infraestrutura foi contado como detecção. Fonte restaurada byte a byte, build refeito antes da matriz final.

- Playwright completo: 164 aprovados, zero falhas/pulados/flaky.
- Axe: 38 cenários, zero violações graves/críticas, incluindo B8 em 360 e 1280 px.
- Typecheck e build: aprovados.
- PoC: 39 aprovados, 1 aviso, 4,27 s. Primeira execução bloqueada no sandbox foi encerrada e descartada.
- Backend não repetido nesta rodada somente de frontend; resultado da entrega anterior: 243 aprovados e 2 opcionais pulados. Nenhum código backend ou PoC alterado.

As duas novas capturas do B8 são fixtures controladas, não coleta oficial. Conferidas visualmente. O TXT docker-ps-apos-limpeza.txt preserva a saída de docker ps -a --filter name=oil- após a limpeza: somente cabeçalho. API e banco da tentativa real de agosto foram encerrados; não houve nova tentativa.

Gitleaks staging e histórico completo --all antes e depois do commit: zero como condição do push, sem allowlist nova. O JSON pré-commit é versionado. O JSON pós-commit externo registra o SHA final verificado e será anexado por link na entrega; mantê-lo fora do commit evita autorreferência do hash. Checkout limpo ao concluir.

Agosto segue timeout_fonte, coleta 1 inválida e zero pontos. A evidência foi enviada separadamente na branch codex/caged-validacao-real, commit 5149a93f30a8defc6531dc7d77b912d8ecca7cbd. Julho não foi consultado. Não houve alteração de manifesto, teto, timeout ou código do coletor.
