# Séries IBGE — decisões executáveis da O2

Recorte da nota metodológica fornecida por Willian em 16/10/2026, com suas correções finais. Nível de evidência exclusivamente descritivo.

| Série Brasil N1 | Tabela | Nível | CV | Variação anual na API | Diferença para classificação |
| --- | --- | --- | --- | --- | --- |
| Desocupação | 6381 | 4099, % | 4103, % | 8816, p.p. | 8816, p.p. |
| Rendimento médio mensal real habitual de todos os trabalhos | 6390 | 5933, R$ | 5941, % | 8837, % | 8838, R$ |

As duas séries são trimestres móveis. Não usar 8819/8841, não misturar com a tabela trimestral 4099 da PoC e não deflacionar a variável 5933 novamente. `base_precos=null` enquanto a base publicada pelo IBGE não estiver confirmada.

Para o nível atual e o mesmo trimestre móvel no ano anterior:

```text
ep_atual = cv_atual / 100 × valor_atual
ep_anterior = cv_anterior / 100 × valor_anterior
ep_dif = sqrt(ep_atual² + ep_anterior²)
margem = 1,96 × ep_dif
estavel se abs(dif) <= margem
subiu se dif > margem
caiu se dif < -margem
```

`dif` precisa estar na unidade dos níveis: p.p. para a taxa, reais para rendimento. Usar 8837 (%) na classificação do rendimento seria incorreto. Se faltar qualquer CV, um dos níveis ou a diferença anual, a classificação é null. A origem permanece `calculada`. O código usa Decimal e testa a fronteira inclusiva.

O QA recalcula a diferença a partir dos dois níveis e a confronta com 8816/8838. Tolerância de arredondamento: até 0,1 p.p. na taxa e R$ 1 no rendimento, pois os níveis publicados têm uma casa decimal e reais inteiros. Usa os níveis e CVs do mesmo snapshot de resposta, sem misturar coletas. Uma revisão no ano anterior também provoca recálculo das classificações afetadas.

A fórmula não modela a covariância da amostra entre anos, podendo favorecer o rótulo estável. Trimestres móveis vizinhos compartilham meses; comparações no produto são exclusivamente com o mesmo período do ano anterior. O rendimento médio também sofre efeitos de composição. Nada disso identifica efeito de uma lei.

Calendário: datas são cadastradas manualmente em `divulgacao`, com período esperado, instante de divulgação com fuso, fonte e link oficial. Se a data já passou e o período não está nas observações da fonte, o campo de atraso é true. Não há data aproximada ou defasagem presumida. Sem cadastro é false. Falha de coleta e calendário são estados distintos.

Metadados oficiais conferidos na implementação:

- [Tabela 6381 — metadados](https://servicodados.ibge.gov.br/api/v3/agregados/6381/metadados)
- [Tabela 6390 — metadados](https://servicodados.ibge.gov.br/api/v3/agregados/6390/metadados)
- [Documentação oficial de agregados](https://servicodados.ibge.gov.br/api/docs/agregados?versao=3)

Os metadados e os valores recebidos foram gravados como fixtures. No teste, o replay é explicitamente simulado, mesmo tendo origem em uma resposta oficial. Nenhum resultado de replay é descrito como aprovação de conectividade ao vivo.
