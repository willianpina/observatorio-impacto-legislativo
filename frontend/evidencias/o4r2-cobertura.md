# O4-R2 — cobertura e prova de regressão

Os nomes abaixo identificam testes reais do Playwright. Os testes de helpers/proxy ficam em `tests/proxy.spec.ts`; os testes de interface em `tests/r2.spec.ts` e `tests/tela.spec.ts`. As mutações são opt-in, fora da suíte normal, e seus resultados ficam em `o4r2-mutacoes.json`, `o4r2-mutacoes-ui.json` e `o4r2-mutacoes.txt`.

| Item | Testes que protegem | Regressão injetada e detectada |
|---|---|---|
| 1 | `R2-1 modo normal recusa série simulada: sem valor nem gráfico` | Troca da condição da trava por `if(false)`: o teste falha porque a série de teste passa a aparecer no modo normal. |
| 2 | `R2-2 CSV preserva número negativo e escapa somente texto`; download em `R2-2 CSV conserva -10 numérico e neutraliza =1+1 e -x textuais` | Escapar o resultado de `String()` sem distinguir tipos faz a asserção de `-10` falhar. Os testes também conferem os dois textos protegidos. |
| 3 | `R2-3 vigência é derivada do dado, e prevista exige data calculada futura`; três testes de interface com prefixo `R2-3` | A previsão sem comparação com o dia corrente falha no teste temporal; resumo fixo falha quando a resposta muda. Também são conferidos texto exato, artigos/fontes, dia exato de início, data expressa futura e publicação sem previsão. |
| 4 | `R2-4 periodicidade trimestral não vira mensal`; `R2-4 fixture trimestral mostra Trimestral e trimestre de calendário` | Retirar o caso trimestral da função de rótulos faz o teste falhar. A fixture é sintética e explicitamente identificada, sem relabelar uma série real como trimestral. |
| 5 | Casos parametrizados `R2-5 linguagem rejeita`; `R2-5 exceção restrita à legenda literal`; varredura da página | Desativar a guarda que junta marco e variação faz os casos negativos falharem. Os testes incluem as duas frases exigidas, a legenda permitida e uma versão parcial que continua proibida. |
| 6 | `R2-6 foco por Tab no marco revela fonte e link sem clique`; teste adicional de expansão/recolhimento por clique | Impedir a abertura no foco faz o teste de Tab falhar. O link revelado recebe o próximo Tab; o foco por teclado não interfere com o clique nativo do summary. |
| 7 | `R2-7 safeHref testa domínios ambíguos e canonicalização`; demais casos de URL e UI | Retirar o ponto que delimita subdomínio faz `evilcamara.leg.br` passar e o teste falha. Domínio com credencial enganosa e domínio com ponto final são recusados; maiúsculas são normalizadas. |
| 8 | `R2-8 requisições inválidas não consomem cota`; regressão anterior de cache/limite | Contar a quota antes de validar faz as requisições inválidas atingirem 429 e falharem. O caso válido verifica exatamente 60 consultas e bloqueio da próxima. |
| 9 | `axe 1280: detalhes abertos, modo caged/normal`; dois testes `R2-9 card e resumo têm o mesmo valor` | Resumo com zero falha nas duas séries; imagem sem alternativa que só aparece nos detalhes em desktop faz o axe reprovar. Também há axe com os detalhes abertos em 360 px. |

## Como repetir

No PowerShell, dentro de `frontend/`, com Node e Edge instalados e os servidores das portas 3101/3102 parados:

```powershell
$env:NEXT_TELEMETRY_DISABLED='1'
$env:OIL_BROWSER_CHANNEL='msedge'
node tests/check-mutations.mjs
npm run build
npm run typecheck
npm run test:e2e
```

O verificador exige falha de asserção, não considera erro de compilação como detecção e restaura os bytes em `finally`. As mutações de UI são independentes e compiladas juntas; cada teste selecionado precisa reprovar sua respectiva regressão. Ao final, é necessário recompilar porque a saída intermediária do Next contém o código alterado. A execução normal após a restauração é a que define o resultado da entrega.
