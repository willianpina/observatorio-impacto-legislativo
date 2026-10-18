# Fixtures da O3 — SÓ PARA TESTE

## Recortes do Novo Caged (`caged_t51_2026-07_recorte.xlsx`, `caged_t51_2026-08_recorte.xlsx`)
- São recortes pequenos da aba «Tabela 5.1» (com ajustes) das planilhas oficiais do MTE (`3-tabelas_Julho de 2026.xlsx` e `3-tabelas_Agosto de 2026.xlsx`). Origem, URL, data e sha256 estão em `../manifesto-fixtures.json`.
- Mesmo layout do original: título em B2, cabeçalho na linha 5 (B..G), dados a partir da linha 6, linha em branco, «Fonte: Novo Caged – MTE.» e a nota. Só os meses de junho/2025 até o último mês do arquivo.
- **Nenhum número foi alterado.** B, D, E e F são cópia direta. C (Estoque) e G (Variação Relativa) eram fórmulas no original; aqui vão como o valor que o próprio arquivo guardou, com o mesmo texto numérico do XML original, porque as fórmulas apontavam para linhas que não estão no recorte. A ingestão não usa C nem G.
- **Não redistribuir.** Licença da fonte: CC BY-ND 3.0 (sem derivações). Estes recortes existem só para os testes automáticos, no repositório privado. Ficam **fora de qualquer publicação**: não vão para o site, para a API, para downloads, para releases nem para imagens de deploy.
- Para gerar de novo: `python gerar_recortes.py <pasta com os xlsx originais> .`

## Respostas reais das APIs (B2)
- `camara_2233802_2026-10-17.json`: `GET https://dadosabertos.camara.leg.br/api/v2/proposicoes/2233802`, 17/10/2026 11:34 (BRT), HTTP 200.
- `senado_9056435_2026-10-17.json`: `GET https://legis.senado.leg.br/dadosabertos/processo/9056435?v=1`, 17/10/2026 11:22 (BRT), HTTP 200.
- A fixture de divergência (Câmara «Aguardando Apreciação pelo Senado») **não é real**: o teste a cria a partir da real e marca `simulada=true`.
