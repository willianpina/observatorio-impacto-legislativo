# OIL — Contrato da API v1.4: só os acréscimos sobre a v1.3.1
Proposta do Backend, 17/10/2026, para a O3. Tudo o que não está aqui continua como na v1.3.1. Nenhum campo da v1.3.1 é removido nem muda de sentido. As rotas da PoC e os 39 testes não mudam.

## B2 · `GET /api/v1/proposicoes/{id_camara}`
- Só os ids da lista fixa do `catalog.py` (hoje: 2233802 → Senado 9056435). Outro id → 404 `proposicao_nao_acompanhada`; id não numérico → 422.
- `situacao[]` (já existia): cada item ganha `coleta_id`, `disponivel` e `motivo`. O texto continua literal da fonte.
- **`situacao_atual`** (novo): o item de `situacao[]` escolhido, mais:
  - `regra`: `"mais_recente"` (data de situação mais recente; empate → Senado) ou `"unica_disponivel"` (só uma casa com coleta válida);
  - `divergencia` (bool): true quando as duas casas mostram estágios diferentes. A tela mostra as duas, como estão na fonte.
- **`norma_gerada`** (novo): `{rotulo, data, link, fonte}` quando a fonte trouxer; senão `null` e `norma_gerada_motivo` (ex.: «normaGerada vazio na fonte do Senado»). Nunca preenchido por constante no código.
- **`fontes_norma`** (novo): lista de links de conferência da norma (Planalto e DOU), cada um com `rotulo`, `link` e `coletado_em`. Não mudam a situação.
- `marcos[]`: cada item ganha **`origem`** (`"fonte"` | `"calculado"`) e **`artigo`** (ex.: «Art. 10, I», ou null). Na O3 só entram marcos com `origem="fonte"` e `prevista=false` (aprovação no Senado 14/10/2026 e promulgação 16/10/2026). Marco `calculado` sempre com `prevista=true` e `artigo` preenchido; os de vigência ficam fora da O3.
- Fonte fora: uma casa falha → 200 com aquela casa `disponivel=false`; as duas sem coleta válida → erro padrão (503 com Retry-After, 504, 502) com `ultima_coleta_id=null`.

## B4 · `GET /api/v1/indicadores/caged-saldo` (desbloqueada)
- Fonte: Novo Caged – MTE, **só a Tabela 5.1 (com ajustes)** da planilha mensal oficial.
- Série: `medida="saldo"`, **`tipo_valor=null`**, `tipo_periodo="mensal"`, **`unidade="postos de trabalho"`**, `cv=null`, **`classificacao=null` sempre** (e `classificacao_origem=null`), `nivel_evidencia="descritivo"`.
- Ponto: `periodo`, `valor` (saldo exatamente como na fonte; pode ser negativo), `lacuna`, `ajuste="com_ajuste"`, `competencia_coleta`, `coleta_id`.
- `variacao_anual` (diferença para o mesmo mês do ano anterior, do mesmo arquivo) e `variacao_anual_unidade="postos de trabalho"`, com **`variacao_anual_origem="calculo_observatorio"`** e o rótulo «cálculo do Observatório a partir de dados do MTE». Os valores do MTE nunca são alterados.
- **`atribuicao`**: `{texto, link, licenca: null, base_legal: {texto, link}}`, corrigido na v1.4.1. Texto: «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo <mês/ano>, coletado em DD/MM/AAAA. Elaboração: OIL.» Base legal e link do decreto em `contrato-api-v1.4.1-delta.md`; mês do manifesto e data da coleta servida, convertida para America/Sao_Paulo.
- **`nota_revisao`** (novo): «Série revisada mensalmente pelo MTE: os meses anteriores podem mudar a cada novo arquivo.»
- Sem coleta válida → **200** com `disponivel=false`, `motivo` e `pontos=[]` (nunca 404).
- `atrasado_calendario` segue o calendário oficial do MTE (29/10/2026, 30/11/2026, 30/12/2026).

## Campos comuns (acréscimo)
- `variacao_anual_origem`: `"fonte"` (IBGE 8816/8837) ou `"calculo_observatorio"` (Caged). Nas séries do IBGE vale `"fonte"`.
