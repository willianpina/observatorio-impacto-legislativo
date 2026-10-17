# OIL — Especificação da tela da Fase 1 (Frontend) — v1.5 (CONGELADA), 16/10/2026 (referência: contrato v1.3 gravado em `contrato-api-v1.md`, com `marcos`/`prevista`, `medida`, `atrasado_calendario` e `classificacao_origem`)
Só especificação, sem código. Stack: Next.js, Tailwind e Recharts, tudo gratuito. A tela só fala com a nossa API (`/api/v1/...`, ver `contrato-api-v1.md`) e nunca chama a fonte oficial direto.
**Regra de ouro:** nenhum número é escrito neste documento nem na tela à mão. Onde aparece `[valor]`, `[data]` etc., é um marcador que vem da API.

Base: `prototipo-aprovado.png`, `fase1-proposta.md`, `contrato-api-v1.md`, `metodologia-v1.md` e `legislativo/parecer-6x1-2026-10-16.md`. `fontes-verificadas.md` (Engenheiro de Dados, 16/10/2026): 6381/v4099 e 6390/v5933 confirmadas; Senado confirmado em `GET /dadosabertos/votacao`; **Novo Caged não confirmado (B4 bloqueado)**.

---
## 1. O que muda em relação ao protótipo
| Protótipo | Fase 1 |
|---|---|
| Seção 4 «O que dizem as fontes» (notícias) | **Sai.** A seção 4 vira o **bloco de evidências B8** (fontes oficiais, links e datas). |
| Aba «Notícias e estudos» | **Sai.** |
| «Pergunte ao Observatório» (IA) | **Sai.** No lugar entra o bloco «Quem propôs e como foi a votação» (ver §6). |
| Etiqueta «Situação: Aprovada» | Mostra **só o texto da fonte** (§3). |
| Etiqueta «Vigência: 2026» e card «Vigência Jan/2026» | Marcos de vigência lidos da lista `marcos` (§3.1): «42 h (prevista)» e «40 h (prevista)». Sem data digitada. |
| Linha vermelha «Início da lei Jan/2026» | **Substituída** pelos marcos de calendário (§4.3): linhas finas, cinza e neutras, nunca vermelhas, sem sombrear antes ou depois. |
| Setas verde/vermelha no resumo («Leve aumento após a vigência») | Saem. Ficam «subiu / caiu / estável em relação ao mesmo período do ano anterior», com ícone neutro (§4.1 e §5). |
| «Setores mais afetados», «Milhões de trabalhadores» | Só aparecem se vierem de fonte com link. Senão, o item fica oculto (nada de texto à mão). |
| Filtro «Região» | **Oculto** na Fase 1 (só Brasil). Vai como texto fixo: «Brasil». |
| Menus de tema (Saúde, Educação, Segurança, Economia, Meio Ambiente, Outros) | **Ocultos** no celular e **desabilitados** no desktop, com `aria-disabled` e dica «Em breve». Só «Trabalho» fica ativo. |
| Busca do topo | Desabilitada, com dica «Em breve» (só há uma lei na Fase 1). |
| Abas | «Visão geral», «Indicadores» e «Metodologia e dados». |

## 2. Estrutura da página (de cima para baixo)
1. Topo: marca, menus Temas, Sobre, Metodologia, Dados e Fale conosco (os que não tiverem página ficam desabilitados) e a faixa de temas.
2. Trilha: Início > Trabalho > `[titulo da proposição]`.
3. **Cabeçalho da lei** (§3) e, à direita, «O que você vai ver nesta página» com âncoras para as 4 seções: 1 O que mudou na lei, 2 O que os dados mostram, 3 Já existem evidências de impacto?, 4 Fontes e dados (B8).
4. Abas.
5. Coluna principal: seções 1, 2 (3 gráficos), 4 (B8). Coluna lateral: «Resumo da análise» (§5), seção 3 e o bloco de votação (§6).
6. Rodapé: versão da metodologia, data da última coleta geral e link para o repositório (quando ficar público).

**Celular (< 768 px):** uma coluna, nesta ordem: cabeçalho, resumo da análise (com o aviso), seção 1, seção 2 (um gráfico por vez, empilhados), seção 3, votação, B8. O índice da página vira um menu recolhível. Tablet (768–1023 px): gráficos em 2 colunas e lateral abaixo. Desktop (≥ 1024 px): como o protótipo.

## 3. Cabeçalho e seção 1 «O que mudou na lei?»
- **Título:** texto fixo de produto («Redução da jornada de trabalho (escala 6x1)») e, logo abaixo, `[tipo] [numero]/[ano]` e a ementa da fonte, com link.
- **Etiquetas:** «Tema: Trabalho» · uma etiqueta de situação **por item da lista `situacao`** · «Vigência: ver marcos» · «Norma: `[norma]`» (só se a fonte trouxer).
  - `situacao` é uma lista por casa: cada item tem `casa`, `situacao`, `data`, `link`, `fonte` e `coletado_em`. A etiqueta mostra **exatamente** o texto da fonte: «Situação (`[casa]`, `[data]`): `[situacao]`», com link. Item sem texto: «Situação (`[casa]`): não informado».
  - **Câmara e Senado divergem hoje** (o parecer mostra a Câmara ainda com «Aguardando Apreciação pelo Senado Federal» e o Senado com «Transformada em norma jurídica»). A tela mostra as duas, cada uma com casa, data e link, e uma nota: «As casas atualizam em datas diferentes.» Nunca escolhe nem reescreve uma delas.
  - Cor da etiqueta de situação: neutra (cinza/azul). Verde não é usado, para não sugerir juízo.
- **Seção 1:** resumo do que a norma prevê, texto revisado pelo Especialista Legislativo, com link «Ver texto da lei completo» para a fonte oficial. Card lateral: «Vigência: prevista em 2 etapas (ver §3.1)», «Autor: `[autor] ([partido]-[UF])`», «Apresentada em `[data]`».

### 3.1 Vigência e marcos (lista `marcos` do contrato v1.3)
- A rota `GET /api/v1/proposicoes/{id_camara}` traz a lista `marcos`, com um item por marco de calendário: aprovação no Senado (14/10/2026), promulgação (16/10/2026), 2º dia de repouso e 42 h, e 40 h.
- Cada item traz `data`, `tipo`, `rotulo`, `prevista` (true/false), `fonte` e `link`. A tela usa `rotulo` como está e não calcula datas.
- No cabeçalho e no card da seção 1, os marcos de vigência aparecem como «`[rotulo]` — `[data]`» com o link da fonte; com `prevista: true`, o selo «Prevista (ainda não conferida no DOU)». Hoje as 42 h e as 40 h vêm só da minuta do Senado.
- Nos gráficos, os mesmos itens seguem o §4.3.

## 4. Seção 2 «O que os dados mostram?» — os 3 gráficos
Filtro **Período** (no topo da seção): «2 anos», «5 anos», «Desde 2020» → `?janela=2a|5a|desde_2020`. Padrão: **5 anos** (`5a`). Aviso fixo ao lado do filtro: «A série do Novo Caged começa em jan/2020; antes disso não há dado comparável.» Com «5 anos», o gráfico do Caged começa onde a série começa, sem preencher meses anteriores. O filtro **só muda a janela**. Cada série mantém a sua frequência; a tela nunca soma nem tira média de meses.

| Gráfico | Rota | Fonte e tabela | Tipo | Período |
|---|---|---|---|---|
| Taxa de desocupação | `GET /api/v1/indicadores/desocupacao` | IBGE, PNAD Contínua, SIDRA 6381 | linha | trimestre móvel |
| Saldo de empregos formais | `GET /api/v1/indicadores/caged-saldo` | Novo Caged (MTE), Brasil | barras (positivo acima, negativo abaixo do zero) | mensal, desde jan/2020 |
| Rendimento médio real | `GET /api/v1/indicadores/rendimento-real` | IBGE, PNAD Contínua, SIDRA 6390, v5933 | linha | trimestre móvel |

**Cada card de gráfico mostra (de cima para baixo):**
1. Título e ícone de ajuda (?) com a definição curta da metodologia.
2. **Insight primeiro:** «Último dado: `[valor] [unidade]` (`[periodo]`). Variação em relação ao mesmo período do ano anterior: `[variacao_anual]`.» Se `classificacao` não for null, acrescenta o rótulo «`subiu|caiu|estável`» **exatamente como vem da API**. O filtro Período não muda esse texto.
3. Linha de metadados: `[unidade]` · `medida` (`taxa` → «Taxa (%)», `saldo` → «Saldo de vagas», `valor` → «Valor em R$») · `tipo_valor` (`real` → «Real (preços de [base_precos])»; se `base_precos` vier null num valor real: «Real, base de preços do IBGE em verificação»; `nominal` → «Nominal») · `tipo_periodo` (`mensal` → «Mensal», `trimestral` → «Trimestral», `trimestre_movel` → «Trimestre móvel») · selo **«Descritivo»** (de `nivel_evidencia`).
4. O gráfico (Recharts), com eixos rotulados com unidade, dica ao passar o mouse ou focar (período, valor e unidade) e os marcos de calendário (§4.3).
5. Rodapé: «Fonte: `[fonte]`, `[tabela_ou_arquivo]`» (link de `link`) · «Coletado em `[coletado_em DD/MM/AAAA HH:mm]` (BRT)». `coleta_id` fica no «Saiba mais», para auditoria.
6. «Saiba mais»: abre a **tabela de dados** (período, valor, unidade, lacuna sim/não), a nota de método e o botão «Baixar CSV» (gerado no navegador com os mesmos dados da API).

Regras dos gráficos:
- **Rendimento:** a tela usa o valor real da 6390/v5933 como veio. Não deflaciona de novo e não converte.
- **Lacuna** (`valor: null` e `lacuna: true`): a linha **quebra** (sem ligar os pontos); nas barras, o mês fica vazio com a marca «s/d». Na tabela aparece «sem dado». Nunca vira zero.
- Cores: uma cor por série, com contraste ≥ 3:1 contra o fundo. Barras negativas do Caged têm cor diferente **e** ficam abaixo do zero (posição é o sinal principal).
- Os 3 gráficos nunca dividem um eixo e não são normalizados uns contra os outros.


### 4.1 Regra única de comparação (cards, resumo, texto alternativo)
- **A tela não calcula nada.** Ela lê `variacao_anual` e `classificacao` (`subiu`, `caiu`, `estável` ou `null`) direto da API. A comparação é sempre com o mesmo período do ano anterior (`comparacao`), e o filtro Período muda **só a janela do gráfico**.
- O `cv` vem das variáveis **4103 (6381)** e **5941 (6390)**. A API calcula a `classificacao` com a fórmula do contrato (margem de 1,96 × erro padrão da diferença). No Caged, `cv` e `classificacao` são sempre null. O `cv` aparece no «Saiba mais» e na tabela de dados.
- A `classificacao` é lida como vier. `classificacao_origem` é `calculada` por padrão na Fase 1 (CV das variáveis 4103 e 5941). A nota junto ao rótulo segue `classificacao_origem`: `calculada` → «calculado pelo Observatório com a margem de erro do IBGE»; `ibge` → «classificação publicada pelo IBGE». Nos dois casos, o «Saiba mais» tem link para a metodologia. Com `classificacao: null`, não há rótulo nem nota.
- Valores da API: `subiu`, `caiu`, `estavel` (sem acento); a tela escreve «subiu», «caiu», «estável».
- **`classificacao: null`** (Caged, ou falta de algum CV): mostra só o valor, o sinal e a `variacao_anual` (ex.: «`[valor]` · `+|−[variacao_anual]` em relação a `[periodo do ano anterior]`»), **sem rótulo** e sem ícone. O sinal vem do número, não de cor.
- Rótulo, ícone e frase nunca são inventados pela tela a partir dos números.

### 4.2 Série indisponível (`disponivel: false`) e o Caged bloqueado
A tela lê `disponivel` e `motivo` em cada série. Com `disponivel: false` (e `pontos: []`), o card mostra o texto abaixo com o `motivo` da API. A fonte do Novo Caged não foi confirmada (`fontes-verificadas.md`). Enquanto isso, o card mostra o título, a fonte prevista e o texto «**Dado ainda não disponível.** A fonte oficial do Novo Caged ainda está em verificação.», **sem gráfico**, sem eixo, sem número e sem esqueleto de carregamento. O resumo da análise mostra a mesma frase no item do Caged. Não é estado de erro nem de lacuna. Quando o B4 for liberado, o card passa a seguir as regras do §4, e cada ponto mostra **«saldo sem ajuste, competência MM/AAAA»** (ou «com ajuste», conforme `ajuste`) (de `ajuste` e `competencia_coleta`) no «Saiba mais» **e** numa coluna da tabela de dados. **Regra do Cientista:** uma linha (ou série de barras) do gráfico do Caged **nunca mistura meses com e sem ajuste**. Se a série tiver os dois, a tela desenha só um tipo (o que a API indicar para a série) e mostra os meses do outro tipo apenas na tabela, com a nota «Meses com outro tipo de ajuste não entram no gráfico.» Nunca liga os dois tipos na mesma linha.


### 4.3 Marcos de calendário nos gráficos (pedido do Willian: efeito de antecipação)
- **Origem:** lista `marcos` da rota `GET /api/v1/proposicoes/{id_camara}` (contrato v1.3). Cada item tem `data`, `tipo`, `rotulo`, `prevista`, `fonte` e `link`. A tela não calcula nem digita datas.
- **Marcos da Fase 1:** aprovação no Senado (14/10/2026), promulgação (16/10/2026), início previsto das 42 h e início previsto das 40 h (datas vindas da API).
- **Desenho:** linha vertical fina, **cinza e neutra, nunca vermelha nem cor de alerta**, sem sombrear o antes nem o depois e sem setas.
  - `prevista: false` → linha contínua. `prevista: true` → linha tracejada; o texto é o `rotulo` da API (ex.: «42 h (prevista)»).
  - Rótulo curto em cada linha («Senado», «Promulgação», «42 h (prevista)»). Data, fonte e link aparecem no foco do teclado (cada marco é focável) ou no toque, e o leitor de tela lê «Marco de calendário: `[rótulo]`, `[data]`, fonte `[fonte]`».
  - **Legenda fixa** em todo gráfico: «Marcos de calendário. Não indicam efeito da lei.»
  - Marco **depois do último dado** da série aparece só como **referência no eixo** (marca curta no eixo do tempo, com o rótulo e foco/toque iguais aos outros), **sem estender a linha dos dados** nem desenhar pontos vazios até ele. Também entra na legenda.
  - Rótulos que se sobrepõem (ex.: 14/10 e 16/10 num gráfico de 5 anos) se juntam num só rótulo («Senado / Promulgação»), com os dois no foco.
- Os mesmos marcos aparecem nos três gráficos e na tabela de dados (coluna «Marco» no período correspondente). Nenhum texto diz «antes» ou «depois» da lei.

## 5. Resumo da análise e seção 3
- Um item por indicador, com a **mesma regra do §4.1** (lido da API, independente do filtro): nome e frase «`[Indicador]`: `[variacao_anual]` em relação a `[periodo do ano anterior]`», mais o rótulo «`subiu|caiu|estável`» e o ícone neutro (▲, ▼ ou =, mesma cor) **só quando `classificacao` não for null**. A palavra é o sinal; o ícone só repete. O Caged mostra «dado ainda não disponível» enquanto o B4 estiver bloqueado.
- **Aviso fixo, sempre visível** (sem fechar e sem recolher): «É cedo para afirmar que as mudanças observadas se devem a esta lei. Outros fatores também influenciam. Nível de evidência: descritivo.»
- Seção 3 «Já existem evidências de impacto?»: texto revisado à mão, que diz que a Fase 1 é descritiva e que não há estudo de impacto com método publicado. Link para a metodologia.
- **Proibido** em qualquer texto da tela: «depois da aprovação», «desde a promulgação», «causou», «graças a», «por causa da lei», «efeito da lei», «após a vigência, X subiu», setas verdes/vermelhas de efeito, comparação «antes × depois». O QA tem uma lista de termos bloqueados que vira teste (§10). **Nenhum texto liga um marco a uma variação** (ex.: «desde a promulgação, a desocupação caiu»).

## 6. Bloco «Quem propôs e como foi a votação»
Rotas: `GET /api/v1/proposicoes/{id_camara}` (2233802; `id_senado` 9056435), `GET /api/v1/proposicoes/{id}/tramitacao?pagina=&por_pagina=` e `GET /api/v1/proposicoes/{id}/votacoes`. **O Senado entra** (a PEC foi votada lá em 14/10/2026): as duas casas são obrigatórias, separadas pelo campo `casa` (`camara`|`senado`). Nível de evidência: descritivo. O bloco não liga voto a indicador.

**6.1 Topo:** «Proposta por `[autor]` (`[partido]`-`[uf]`) em `[data_apresentacao]`.» Linha de resultado só com texto da fonte. Link para a página oficial.

**6.2 Câmara e Senado separados:** duas abas (desktop) ou duas seções empilhadas (celular): «Câmara dos Deputados» e «Senado Federal». Cada uma com a sua fonte, link e `coletado_em`.

**6.3 Uma votação por turno:** cada turno da PEC é um cartão próprio: «`[casa]` — `[turno]`º turno — `[data]`», com «ID da votação: `[id_votacao]`» e link. As votações com `principal: true` aparecem abertas: **Câmara 2233802-424 (1º turno) e 2233802-438 (2º turno), de 27/05/2026; Senado, sessões 7106 (1º turno) e 7107 (2º turno), de 14/10/2026**. As demais vão para a lista recolhida «Outras votações», na casa correspondente. Nunca soma turnos.

**6.4 Placar (votação nominal):**
- No Senado, a API do Senado não traz os totais (`totalVotosSim` e os outros vêm nulos). O `placar` que a nossa API entrega é a **soma dos votos individuais**, e cada voto traz o partido e a UF **da data do voto** (`siglaPartidoParlamentar`, `siglaUFParlamentar`). A tela mostra a nota «Placar calculado a partir dos votos individuais registrados pelo Senado» com o link da votação. **O placar só aparece com `placar_conferido: true`** (conferência do QA contra a página oficial), nas duas casas. Com `false`, o cartão mostra «Placar em conferência», com o link oficial, sem números, sem barra e sem «Aprovada». Na Câmara, o placar segue o contrato.
- Barra única empilhada: Sim, Não, Abstenção, Obstrução e Ausentes (obstrução e ausentes à parte, **fora do total** de votos), com os números escritos ao lado de cada parte e uma legenda em texto. Cada parte tem cor **e** padrão/rótulo, e a ordem é sempre a mesma.
- «Quórum exigido: `[quorum_exigido]` votos sim (3/5).»
- A palavra **«Aprovada»** (só com `placar_conferido: true`; sim ≥ 308 na Câmara e ≥ 49 no Senado) só aparece quando `resultado` da fonte diz isso **e** `placar.sim ≥ quorum_exigido` (308 na Câmara, 49 no Senado) e `inconsistencia` está vazia. Se houver `inconsistencia`: aviso «O resultado informado pela fonte não bate com o placar; em conferência», e a palavra não aparece.
- Se a soma por partido não bater com o `placar`, a API marca `inconsistencia` e a tela não mostra o gráfico por partido nem «Aprovada» (metodologia §8, regra 6).
- Tabela no «Saiba mais» com os mesmos números.
- «Ver votos individuais» no «Saiba mais»: lista paginada de `GET /api/v1/votacoes/{id}/votos?pagina=&por_pagina=` (padrão 50), com parlamentar, voto, partido e UF da data do voto. Voto com `sigla_ausente: true` aparece como «sigla não informada pela fonte» e **nunca** recebe o partido atual. Botão «Carregar mais» enquanto `proxima` não for null.

**6.5 Votação simbólica** (`tipo: "simbolica"`, `placar: null`): texto «Votação simbólica, sem placar nominal (sem registro de votos individuais).» Sem barra, sem zero, sem estimativa.

**6.6 Votos por partido:**
- Barras horizontais (Recharts), ordenadas pelo tamanho da bancada presente, com o número e a porcentagem escritos em cada barra. Nota fixa: «Porcentagem calculada sobre os deputados (ou senadores) presentes. Partido registrado na data do voto.» Tabela no «Saiba mais».
- Se `votos_por_partido: null`: o gráfico **não aparece**. A tela mostra só o `placar` e o texto de `motivo` («A fonte não informa o partido na data do voto, então não mostramos a divisão por partido.»). **Sigla ausente nunca vira partido «atual»**: não existe rótulo «atual», nem aviso de «atual», nem gráfico parcial. Se faltar a sigla em parte dos votos, vale a mesma regra: sem gráfico por partido.
- Porcentagem = votos do partido ÷ **presentes desse partido**, com `base_percentual: "presentes"`, em que **presentes = sim + não + abstenção** (o mesmo `total` do `placar`). **Obstrução e ausência ficam fora da base** e aparecem à parte. Se vier outro valor em `base_percentual`, a tela não mostra porcentagem, só números.

**6.7 Tramitação:** linha do tempo vertical com data, órgão e descrição da fonte. As **últimas 5** visíveis; o resto em «Saiba mais», paginado pela API (`pagina`, `por_pagina`, `total`, `proxima`; o botão «Carregar mais» some quando `proxima` é null). Cada evento traz `casa`, e cada casa tem a sua linha.

## 7. Seção 4 — Bloco de evidências B8 «Fontes e dados»
Lista em tabela (no celular, cartões): Fonte · O que fornece · Tabela/arquivo/ID · Link oficial · Data da coleta · Situação (`ok` / «dado de DD/MM» / «fonte indisponível»). Entram: IBGE SIDRA 6381, IBGE SIDRA 6390 (v5933), Novo Caged (MTE), API da Câmara (proposição, tramitação, votações), API do Senado (matéria, votações) e o DOU da EC (se houver link). Sem notícias e sem estudos de terceiros. Link para a metodologia v1 e para o CSV de cada série.

## 8. Estados (todos os blocos)
| Estado | Quando | O que a tela mostra |
|---|---|---|
| Carregando | aguardando a API | esqueleto cinza do tamanho final (sem pular layout), `aria-busy="true"`, texto «Carregando dados de `[fonte]`…» para leitor de tela. Nunca mostra número provisório. |
| Vazio | série ou lista sem itens | «Ainda não há dados de `[fonte]` para este período.» Para votações: «Nenhuma votação registrada na fonte» com o motivo da API. Nunca gráfico zerado. |
| Erro | 502/503/504 sem coleta anterior (corpo `erro.codigo`, `erro.mensagem`, `erro.fonte`, `erro.tentar_novamente_em`; 503 com `Retry-After`) | caixa de aviso: «Não conseguimos obter dados de `[erro.fonte]` agora. Tente de novo `[erro.tentar_novamente_em]`.» Botão «Tentar de novo». Só aquele bloco falha; o resto da página continua. 404: «Proposição não encontrada.» 422 (janela inválida): volta ao padrão e avisa. |
| Lacuna | `valor: null` | falha na linha / «s/d» / «sem dado» na tabela, e nota «Há períodos sem dado na fonte». |
| Desatualizado | `desatualizado: true` (200, a API está servindo a última coleta boa) | selo amarelo com ícone e texto «Dado de `[DD/MM]`» e a dica «A fonte não respondeu; mostramos a última coleta válida.» |
| Atrasado na fonte | `atrasado_calendario: true` (a fonte ainda não publicou o período esperado pelo calendário) | selo cinza «A fonte ainda não publicou `[periodo esperado]`». Não é erro e não usa amarelo. |
| Modo de teste | só com a variável do modo de teste ligada | faixa fixa no topo «MODO DE TESTE — dados simulados, não são reais» em todas as páginas, e o selo «simulado» em cada gráfico. Em modo normal, a tela recusa dado marcado como simulado. |

## 9. Acessibilidade (WCAG 2.1 AA)
- Contraste de texto ≥ 4,5:1 (≥ 3:1 em texto grande e em elementos de gráfico). Cor nunca é o único sinal: palavras, números, padrões e posição.
- Teclado: tudo alcançável com Tab, foco visível, ordem lógica, abas com setas (padrão ARIA tabs), «Saiba mais» como `button` com `aria-expanded`. Link «Pular para o conteúdo».
- Cada gráfico tem texto alternativo curto gerado dos dados («Taxa de desocupação, trimestre móvel, de `[inicio]` a `[fim]`; último valor `[valor] [unidade]`, `[subiu|caiu|estável, ou só os valores se não houver classificação]` em relação ao ano anterior») e a tabela de dados como alternativa completa.
- Estados de carregando, erro e desatualizado anunciados com `aria-live="polite"`.
- Idioma `pt-BR`, títulos em ordem (h1 → h2 → h3), zoom de 200% sem perder conteúdo, alvo de toque ≥ 44 px, respeita «reduzir movimento».
- Datas em DD/MM/AAAA e números no formato brasileiro (vírgula decimal).

## 10. Testes de tela (Playwright + axe, gratuitos, locais)
Rodam contra a API em modo de teste (dados simulados com rótulo). Cenários mínimos:
1. Página carrega com os 3 gráficos, cada um com fonte, link, coleta, unidade, real/nominal, tipo de período e selo «Descritivo».
2. Filtro Período: o padrão é 5 anos, com o aviso do Caged; trocar a janela (2a, 5a, desde 2020) não muda a frequência nem o texto dos cards e do resumo. A tela mostra `variacao_anual` e `classificacao` exatamente como vêm (teste com dados simulados que conferem o texto); com `classificacao: null` não aparece rótulo nem ícone.
2b. Série com `disponivel: false` mostra o `motivo` e nenhum gráfico nem número (caso atual do Caged).
2c. `classificacao` calculada mostra o rótulo com a nota «calculado pelo Observatório…» e o link no «Saiba mais»; `null` não mostra rótulo.
2d. Marcos: quatro itens de `marcos` lidos com `rotulo`, sem «Início da lei»; marcos desenhados como linhas finas e cinza; `prevista: false` contínuo, `prevista: true`, previsto tracejado com «42 h (prevista)»; legenda «Marcos de calendário. Não indicam efeito da lei.» sempre visível; marco após o último dado aparece só como referência no eixo, sem estender a linha dos dados; data, fonte e link aparecem com Tab e com toque; **nenhum marco usa cor de alerta** (o teste lê a cor calculada de cada linha e reprova vermelho, laranja ou amarelo de aviso) e nenhuma área sombreada.
2f. Obstrução: aparece como item à parte no placar e **fora do total** (o total e a soma de sim + não + abstenção não incluem a obstrução); a porcentagem por partido não a conta como sim nem como não.
2g. Frases proibidas: varredura do texto renderizado (incluindo dicas, texto alternativo e tabelas) reprova «depois da aprovação», «desde a promulgação» e o resto da lista do §5, e reprova qualquer frase que cite um marco (rótulo ou data) junto com subiu, caiu, aumentou, diminuiu ou variação.
2h. Caged (dado simulado, modo de teste): «saldo sem ajuste, competência MM/AAAA» aparece no «Saiba mais» e na tabela de dados.
2i. Caged com meses `com_ajuste` e `sem_ajuste` em dado simulado: o gráfico nunca liga os dois tipos na mesma linha; a tabela mostra todos, com o tipo de ajuste.
2e. Votação: só as 4 principais abertas; o resto em «Outras votações»; com `placar_conferido: false` aparece «Placar em conferência» e nenhum número; lista de votos pagina e mostra «sigla não informada pela fonte».
3. Lacuna: ponto `null` quebra a linha e aparece «sem dado» na tabela; nenhum «0» no lugar.
4. Desatualizado mostra «Dado de DD/MM»; erro mostra o aviso e o botão; uma fonte com erro não derruba as outras.
5. Não existe linha «Início da lei» em nenhum estado; só os marcos do §4.3.
6. Aviso «É cedo para afirmar» visível em todas as larguras; varredura de termos proibidos na página inteira.
7. Votação: turnos separados com ID e link; simbólica mostra o texto certo e nenhum número; «Aprovada» some quando o placar não bate o quórum ou há `inconsistencia`; `votos_por_partido: null` esconde o gráfico e mostra o motivo; nota «sobre os presentes» visível; soma por partido = placar.
8. Tramitação mostra 5 itens e carrega mais pela paginação.
9. Faixa «MODO DE TESTE» aparece só no modo de teste.
10. axe sem violação séria ou crítica em desktop e celular, nos estados normal, erro e vazio; navegação só por teclado; captura de tela em 375 px (uma coluna) e 1280 px.
11. Menus de tema sem conteúdo ocultos/desabilitados; nada de notícias nem de IA na página.

## 11. Critérios de aceite da tela
- Fiel ao protótipo, com as mudanças do §1; sem notícias, sem IA.
- Todo número tem fonte, link e data da coleta; nenhum número escrito à mão; o QA confere 100% contra a fonte numa rodada real.
- Situação só da fonte (por casa); marcos de vigência com `prevista: true` até a conferência no DOU; marcos de calendário neutros (§4.3), sem linha «Início da lei».
- Lacuna nunca vira zero; desatualizado e erro sempre visíveis.
- Nenhuma frase causal; aviso sempre visível; selo «Descritivo» em todos os gráficos e no bloco de votação.
- Regras de votação do §6 cumpridas (turnos, quórum, simbólica, partido na data do voto, base dos presentes).
- Todos os testes do §10 passam; os 39 da PoC continuam passando.
- Roda localmente sem custo; nada publicado sem o OK do Willian.

## 12. Esforço (Cursor, a partir de 16/11)
| Parte | Dias |
|---|---|
| B7 + B8: layout, cabeçalho, 3 gráficos, filtro, resumo, estados, responsivo, acessibilidade e testes | 5–6 |
| Bloco de votação (Câmara e Senado, turnos, placar, partidos, tramitação, estados e testes) | 2–2,5 |
| **Total** | **7–8,5** |

## 13. Pendências
- `fontes-verificadas.md` (Engenheiro de Dados): já saiu; falta o Caged (B4) e a `base_precos` da 6390.
- ORCHESTRATOR: OK da proposta de contrato v1.2 do Backend.
- Especialista Legislativo: conferir no DOU as datas dos dois marcos de vigência e o texto da seção 1.

## 14. Divergências (v1.5 congelada, 16/10/2026)
Só itens abertos; os resolvidos saíram.
Ainda abertas:
1. **Datas das 42 h e das 40 h:** só da minuta do Senado, sem DOU (`prevista: true`).
2. **`metodologia-v1.md` §6.2:** resolvido em 16/10 (alinhada com o contrato, marcos, antecipação e regra do Caged).
3. **Caged:** o contrato não diz qual tipo de `ajuste` é o principal da série no gráfico. B4 segue bloqueado.
4. **Votos do 1º turno da Câmara** (2233802-424) não testados; **`base_precos` da 6390** pendente; **orientação de bancada** fora da tela na Fase 1.

## Adendo 16/10 (revisão do PR #1)
- A tela não mostra `tipo_valor` quando `medida = taxa` (vale para `nominal` ou null no contrato v1.4).
- Critérios para ligar a tela: o `caged-saldo` devolve 200 com `disponivel: false`, `motivo` e `pontos: []`; um período que falta vem como ponto com `valor: null` e `lacuna: true`.
- A tela usa `variacao_anual_unidade` para a unidade da variação anual.
