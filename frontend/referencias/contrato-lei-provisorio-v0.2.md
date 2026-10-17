# Contrato legislativo provisório 0.2 — O4-R2

Versão anterior: 0.1, `vigencia` era texto livre. Na 0.2, `Lei.vigencia` é o objeto `Vigencia` de `lib/contrato-lei-provisorio.ts`, com `data_publicacao`, `regra_geral`, `etapas` e `fontes`. A alteração é restrita ao adaptador frontend e às fixtures; não muda nem implementa a O3.

Cada etapa guarda ID, descrição, dispositivos, base legal, prazo em meses, marco de origem, data de início e tipo da data (`calculada` ou `expressa`). A tela lê a data informada, não reinterpreta o prazo. O sufixo de previsão só aparece para data calculada posterior ao dia corrente em Brasília; não se aplica à publicação.

O resumo é derivado desses campos. Os artigos e as fontes ficam nos detalhes. O texto explicativo exigido pela missão esclarece os dois prazos e não apresenta as datas por extenso como citação do texto da emenda.

Os valores da fixture foram fornecidos na missão O4-R2 como conferidos pelo Especialista Legislativo. Continuam identificados como dados de teste, sem validação legal independente nesta tarefa. O modo normal continua sem integração legislativa e não serve a fixture.
