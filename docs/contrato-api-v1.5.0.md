# Contrato da API v1.5.0

Consolida o contrato vigente. Continuam valendo `docs/contrato-api-v1.3-indicadores.md`, `docs/o3/contrato-api-v1.4-delta.md` e `docs/o3/contrato-api-v1.4.1-delta.md`, exceto o objeto `atribuicao` de `GET /api/v1/indicadores/caged-saldo`, que esta versão substitui. Números, `medida`, `tipo_valor`, `unidade`, `classificacao`, `nota_revisao`, `variacao_anual` e as outras rotas não mudam. Não há migração.

## `atribuicao` de `caged-saldo`

- `texto`: «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes). Série revisada mensalmente. Elaboração: OIL.» Texto fixo, sem data, sem mês e sem licença.
- `link`: com coleta válida, a `pagina_oficial` do manifesto da coleta servida. Sem coleta válida, a página oficial do Novo Caged.
- `licenca`: removido.
- `base_legal`: string "Decreto 8.777/2016, art. 4º" (antes era objeto).
- `arquivo_referencia`: competência `AAAA-MM` do arquivo da coleta servida, vinda do manifesto (`caged_arquivo`). Nunca a data de hoje. Sem coleta válida: `null`.
- `coletado_em`: ISO 8601 em UTC com zona explícita, igual ao da coleta servida, dentro de `atribuicao`. Sem coleta válida: `null`.

Sem coleta válida a resposta continua 200, com `disponivel=false`.

## Diferenças de `atribuicao`

| Campo | v1.4.1 | v1.5.0 |
|---|---|---|
| `texto` | mês do arquivo e data da coleta em BRT | «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes). Série revisada mensalmente. Elaboração: OIL.» |
| `licenca` | licenca=null | removido |
| `base_legal` | base_legal=objeto | string "Decreto 8.777/2016, art. 4º" |
| `arquivo_referencia` | ausente | `AAAA-MM`, do manifesto |
| `coletado_em` | ausente em `atribuicao` | ISO 8601 UTC com zona |
