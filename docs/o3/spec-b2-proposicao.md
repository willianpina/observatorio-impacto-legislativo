# O3 · B2 — Lei acompanhada (proposição Câmara + Senado) — especificação Backend para o Codex
Status: proposta 17/10/2026, sem implementação. Base: main 0e14fa69 (contrato v1.3.1, migrações 0001 e 0002). Contrato alvo: v1.4 (só acréscimos).

## 1. Rota (contrato v1.4)
`GET /api/v1/proposicoes/{id_camara}` (ex.: 2233802). Lista fixa da Fase 1 em `catalog.py`: `{2233802: {"id_senado": 9056435, "norma": "EC 141/2026"}}` (vínculo conferido pelo Especialista Legislativo, nunca descoberto por busca). Outro id → 404 `proposicao_nao_acompanhada`.

Resposta 200:
- `id_camara`, `id_senado`, `sigla_tipo`, `numero`, `ano`, `ementa`: da Câmara (`/api/v2/proposicoes/{id}`).
- `autor`, `partido`, `uf`: autor principal da Câmara (`/autores` com `ordemAssinatura=1` + `/deputados/{id}` para partido e UF **na data de apresentação** se disponível; senão o atual, com `partido_referencia="atual"`). `coautores` = total de autores menos 1. `data_apresentacao`.
- `situacao`: lista, um item por casa: `casa` (camara|senado), `situacao` (texto literal da fonte), `data` (data da situação na fonte), `link` (página pública da matéria), `fonte` (URL da API consultada), `coleta_id`, `coletado_em`, `disponivel`, `motivo`.
- `situacao_atual` (novo v1.4): o item escolhido pela regra da seção 3, mais `regra` ("mais_recente" | "unica_disponivel") e `divergencia` (bool).
- `norma_gerada` (novo v1.4): `{rotulo, data, link, fonte}` quando a fonte trouxer; hoje o `normaGerada` do Senado vem vazio → `null` com `motivo="normaGerada vazio na fonte do Senado"`. **Nunca digitar "EC 141/2026" à mão** no campo; o catálogo só serve para o teste conferir.
- `marcos`: como na v1.3.1 (`tipo, rotulo, data, prevista, fonte, link`) + `origem` (v1.4: `fonte` | `calculado`) e `artigo`. Na O3 entram só `aprovacao_senado` (14/10/2026) e `promulgacao` (16/10/2026, EC 141/2026), com `origem=fonte`, `prevista=false` e links para a Câmara/Senado, o [Planalto](https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc141.htm) e o [DOU](https://www.in.gov.br/web/dou/-/emenda-constitucional-n-141-738818165) (Ed. Extra A, p. 2). Os marcos de vigência (42 h, 40 h, 2º repouso) **ficam fora da O3**: as datas seriam cálculo do Observatório, não estão no texto. Se um dia entrarem, vêm com `prevista=true`, `origem=calculado` e o artigo citado (art. 6º/10).
- `fontes_norma` (v1.4): links fixos de conferência da norma (Planalto e DOU), cada um com `coletado_em` da conferência; não alimentam a situação.
- Comuns: `nivel_evidencia="descritivo"`, `desatualizado`, `simulada`.

## 2. Modelo de dados (migração 0003, sobre a 0002_contract_131 da main 0e14fa69; sobe e desce)
- `proposicao` (id, id_camara único, id_senado, sigla_tipo, numero, ano).
- `proposicao_snapshot` (id, proposicao_id FK, casa, coleta_id FK `coleta`, ementa, autor_json, situacao_texto, situacao_data, norma_json, link, versao; único (proposicao_id, casa, versao)). Nova versão só quando algum campo mudar, como na O2.
- `marco` (id, proposicao_id, tipo, rotulo, data, prevista, coleta_id FK, fonte, link; único (proposicao_id, tipo)).
- Reaproveita `fonte` (novas linhas `camara-dados-abertos`, `senado-dados-abertos`) e `coleta` (resposta bruta, hash, http, simulada). `coleta.serie_codigo` passa a aceitar `proposicao:2233802:camara|senado` (ou renomear para `alvo`, com FK opcional: decisão do Engenheiro de Dados).
- Integração com o B4: a migração 0004 (Caged) derruba `ck_observacao_valor` (saldo negativo); `tipo_valor` null já existe desde a 0002. Ordem: 0003 = B2, 0004 = B4.

## 3. Reconciliação Câmara × Senado
1. Coletar as duas casas sempre (Câmara: ficha `/api/v2/proposicoes/2233802`; Senado: `/dadosabertos/processo/9056435?v=1`).
2. `situacao_atual` = item com a **data de situação mais recente**; empate → Senado (casa revisora/promulgação). Se uma casa estiver sem coleta válida → a outra, com `regra="unica_disponivel"`.
3. `divergencia=true` quando os textos indicam estágios diferentes (ex.: Câmara "Aguardando Apreciação pelo Senado" × Senado "TRANSFORMADA EM NORMA JURÍDICA"). A tela mostra as duas, como estão na fonte. Nada de normalizar ou reescrever o texto.
4. Datas da fonte em ISO; `coletado_em` com fuso (UTC aceito, v1.3.1).

## 4. Fonte fora
- Coleta por job separado (CLI), nunca na requisição da tela. Retry igual à O2 (3 tentativas, Retry-After respeitado com teto 60 s, `httpx.Limits`).
- Uma casa falha, outra ok → 200; a casa falha vem com `disponivel=false`, `motivo`, e o último snapshot bom se existir (`desatualizado=true`).
- As duas sem nenhuma coleta válida → erro padrão `{erro:{codigo, mensagem, fonte, tentar_novamente_em, ultima_coleta_id:null}}`, 503 (+Retry-After) / 504 timeout / 502 resposta inválida.
- Resposta com esquema inesperado (ex.: campo de situação ausente) → coleta inválida (`valida=false`), sem gravar snapshot.

## 5. Testes (fixtures reais gravadas com URL e data no manifesto)
1. Fixture **real** de 17/10 (Câmara 2233802 «Transformado em Norma Jurídica», codSituacao 1140; Senado 9056435 «TRANSFORMADA EM NORMA JURÍDICA») → convergência: `divergencia=false`, `situacao_atual` pela regra de data/desempate (Senado). E uma fixture **sintética, rotulada `simulada=true`** (Câmara «Aguardando Apreciação pelo Senado» × Senado norma jurídica) → `divergencia=true`, as duas situações literais na resposta.
2. `norma_gerada` null com motivo quando `normaGerada` vazio; preenchido quando a fixture alterada trouxer o campo.
3. Regra de data mais recente e desempate pelo Senado (fixtures sintéticas, só em `OIL_TEST_MODE=1`).
4. Senado fora (timeout) → 200, Senado `disponivel=false`, `regra="unica_disponivel"`; ambas fora → 503/504 com `ultima_coleta_id=null`.
5. Versionamento: a mesma resposta duas vezes não cria versão; a situação mudada cria a versão 2.
6. 404 para id não acompanhado; 422 para id não numérico.
7. Nenhum campo de texto vem de constante no código (o teste procura "EC 141" e "Promulgada" fora das fixtures).
8. Frases causais proibidas também nas respostas da rota nova.
9. Migração 0003 sobe, desce e sobe; os 39 testes da PoC e os da O2 continuam passando; resumo do pytest no PR.

## 6. Fora da O3 · B2
Tramitação paginada, votações e votos (B2b), marcos de vigência calculados. Caged = especificação do Engenheiro de Dados (B4), a ser integrada.
