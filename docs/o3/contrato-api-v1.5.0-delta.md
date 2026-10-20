# Contrato da API v1.5.0 — atribuição do Novo Caged

A v1.4.1 descrevia `atribuicao` com mês, data e `base_legal` aninhada. A v1.5.0 substitui só esse objeto em `GET /api/v1/indicadores/caged-saldo`. Números, `medida`, `tipo_valor`, `unidade`, `classificacao`, `nota_revisao`, `variacao_anual` e as outras rotas não mudam. Não há migração de banco.

- `texto`: «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes). Série revisada mensalmente. Elaboração: OIL.» Texto fixo, sem data, sem mês e sem licença.
- `link`: com coleta válida, continua sendo a `pagina_oficial` do manifesto da coleta servida. Sem coleta válida, é a página oficial do Novo Caged (`https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho/novo-caged`).
- `licenca`: chave removida.
- `base_legal`: «Decreto 8.777/2016, art. 4º».
- `arquivo_referencia`: competência `AAAA-MM` do arquivo da coleta servida, lida de `caged_arquivo` (gravada a partir do manifesto). Nunca a data de hoje. Sem coleta válida: `null`.
- `coletado_em`: instante da coleta servida, ISO 8601 em UTC com zona explícita, dentro de `atribuicao`. Sem coleta válida: `null`.

Sem coleta válida a resposta continua **200**, com `disponivel=false`, `motivo` e `pontos=[]`.
