# Contrato v1.3.1 — recorte de indicadores para O2-R

Especificação fornecida por Willian em 16/10/2026, com as correções explícitas da tarefa O2-R para v1.3.1. Este arquivo registra somente o recorte de indicadores; os demais blocos do contrato não foram implementados nesta tarefa.

Rotas: `GET /api/v1/indicadores` e `GET /api/v1/indicadores/{codigo}/serie`. Códigos: `desocupacao`, `rendimento-real` e `caged-saldo`. O alias genérico sem `/serie` foi removido. A única exceção explícita é `GET /api/v1/indicadores/caged-saldo`: HTTP 200, série cadastrada como indisponível, motivo e `pontos=[]`.

Janela: `2a`, `5a` (padrão) e `desde_2020`. O filtro recorta os pontos, sem agregar períodos nem alterar a comparação anual. O índice tem `indicadores` e metadados de fonte, data de coleta, desatualização e atraso; cada item e cada ponto carregam os campos comuns.

Campos comuns: `valor`, `lacuna`, `unidade`, `periodo`, `tipo_periodo`, `tipo_valor`, `medida`, `base_precos`, `cv`, `variacao_anual`, `classificacao`, `classificacao_origem`, `fonte`, `tabela_ou_arquivo`, `link`, `coleta_id`, `coletado_em`, `desatualizado`, `atrasado_calendario`, `nivel_evidencia`, `disponivel`, `motivo` e `comparacao`.

- Ausência: `valor=null`, nunca zero; `lacuna=true`. Período móvel: código SIDRA `AAAAMM`, mês final do trimestre, mantido sem transformação em trimestre de calendário.
- PNAD usa `tipo_periodo=trimestre_movel`; Caged indisponível usa `mensal`. `tipo_valor=null` nas taxas, `real` no rendimento; `medida` distingue taxa/valor/saldo. `base_precos=null` nesta tarefa.
- CV vem de 4103/5941. Classificação calculada: `subiu`, `caiu`, `estavel` ou null. Origem sempre `calculada`.
- Variação anual exposta: 8816 (p.p.) na desocupação; 8837 (%) no rendimento. A diferença 8838 (R$), usada na fórmula, fica no banco e na resposta bruta.
- `coletado_em` usa ISO 8601 com fuso. Fonte, tabela/variáveis, link e coleta dão linhagem. Cada ponto inclui `versao`.
- `desatualizado=true` somente ao servir a última coleta boa após falha posterior da fonte. Calendário vencido sem período esperado: `atrasado_calendario=true`. Sem data cadastrada: false.
- `nivel_evidencia=descritivo` e `comparacao=mesmo_periodo_ano_anterior`. Nenhuma afirmação causal.
- Série sem coleta: `disponivel=false`, motivo explícito e `pontos=[]`. Falha conhecida sem coleta boa produz erro 502/503/504. Não há fallback fictício em produção.

Campos de rastreabilidade: `variacao_anual_unidade` (`p.p.` na desocupação e `%` no rendimento), `variaveis` (códigos de nível, CV, variação e diferença) e `simulada` (identificação explícita do replay em testes). `pontos` contém a série histórica; os campos de nível no topo representam o último ponto da janela. Períodos intermediários faltantes aparecem como pontos nulos, com `lacuna=true`; não se cria coleta ou versão fictícia para eles.

Erros v1: `{"erro":{"codigo","mensagem","fonte","tentar_novamente_em","ultima_coleta_id"}}`; 503 tem `Retry-After`. `ultima_coleta_id` pode referenciar somente coleta válida e fica null quando nenhuma existe. Erros HTTP são mapeados pelo status dentro de `/api/v1/indicadores`; fora desse prefixo, mantém-se o tratamento padrão. 404 para código inexistente; 422 informa o nome real do parâmetro inválido. As duas rotas da PoC conservam seu contrato anterior.
