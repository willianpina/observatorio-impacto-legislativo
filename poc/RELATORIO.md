# Relatório de validação — 16/10/2026

Prova executada às **07:29:40 (America/Sao_Paulo)**; evidências usam UTC. Resultado: ambas as integrações aprovadas para a prova de conceito. Não é uma avaliação de disponibilidade contínua nem de desempenho sob carga.

| Fonte | Conexão | Dados extraídos | Compatibilidade com frontend |
| --- | --- | --- | --- |
| Câmara dos Deputados | Aprovada, HTTPS real | 3 PLs de 2026 com detalhes; 1 PL de 2025 adicional | Contrato JSON validado; situação opcional |
| IBGE | Aprovada, metadados e SIDRA reais | 8 trimestres nacionais, valores em % | Contrato JSON validado, série ordenada e numérica |

Compatibilidade significa validação do contrato e serialização via HTTP. Nenhum frontend foi construído ou testado visualmente.

## Tempos medidos

| Consulta | Duração |
| --- | ---: |
| Câmara, listagem + 3 detalhes | 688,52 ms |
| IBGE, metadados + série SIDRA | 347,96 ms |
| Câmara, amostra adicional de 2025 (listagem + detalhe) | 1.312,69 ms |
| GET local /api/legislacao, incluindo nova consulta externa | 410,10 ms, HTTP 200 |
| GET local /api/indicadores/desemprego, incluindo nova consulta externa | 366,42 ms, HTTP 200 |

São durações de uma execução, medidas com relógio monotônico, não médias. Cada requisição externa tem duração individual em `evidencias/consultas-reais.json`. Diferenças entre consultas diretas e endpoints incluem variação de rede, conexões reutilizadas e inicialização de conexões.

## Conteúdo conferido

Os IDs **2648300**, **2648297** e **2648293** vieram da listagem real; correspondem respectivamente aos PLs **5587/2026**, **5586/2026** e **5585/2026**. Todos tiveram identificador, tipo, número, ano e ementa validados também no detalhe. `descricaoSituacao` veio null nos três; foi preservada, sem inferência a partir do despacho. A amostra adicional retornou ID **2646600**, com situação **Aguardando Despacho do Presidente da Câmara dos Deputados (Chancela)**. Dados e origens estão nos JSON da entrega.

Os metadados oficiais confirmaram tabela **4099**, variável **4099**, PNAD Contínua **trimestral**, unidade **%**, abrangência nacional N1. A série utiliza trimestres de calendário; não deve ser rotulada como taxa mensal ou de trimestre móvel.

| Referência | Taxa de desocupação (%) |
| --- | ---: |
| 3º trimestre 2024 | 6,4 |
| 4º trimestre 2024 | 6,2 |
| 1º trimestre 2025 | 7,0 |
| 2º trimestre 2025 | 5,8 |
| 3º trimestre 2025 | 5,6 |
| 4º trimestre 2025 | 5,1 |
| 1º trimestre 2026 | 6,1 |
| 2º trimestre 2026 | 5,4 |

## Testes e rastreabilidade

**39 testes automatizados simulados passaram em 4,12 s**, separadamente das consultas reais. Relatório JUnit em `evidencias/testes-simulados.xml`. O validador real retornou código 0 e confirmou as duas fontes e ambas as rotas em servidor Uvicorn real, acessado por HTTP de loopback. O servidor foi encerrado após a validação.

Evidências: `resultado.json` resume a execução; `consultas-reais.json` registra respostas originais e tempos por tentativa; `*-normalizado.json` registra o contrato; `*-api-local.json` registra as respostas HTTP locais; `servidor.log` registra o servidor; `sha256.json` contém hashes dos arquivos de evidência. A documentação da Câmara utilizada foi extraída do OpenAPI oficial. O código não contém dados reais fixados nem fallback fictício; fixtures dos testes são explicitamente sintéticas.

## Problemas encontrados e resolução

- A rede restrita inicialmente impediu resolução DNS no processo Python. As consultas reais foram executadas com acesso de rede autorizado, sem alterar projetos externos.
- O Python padrão falhou ao validar a cadeia TLS local. O uso de `truststore` com os certificados confiáveis do Windows resolveu o problema mantendo HTTPS validado.
- A raiz e a página de ajuda do portal `apisidra.ibge.gov.br` retornaram **403**. O endpoint de valores retornou **200**. A documentação de agregados do IBGE e seus metadados oficiais permitiram confirmar tabela, variável, periodicidade e unidade antes da implementação. O leitor web também não conseguiu acessar algumas páginas IBGE; a leitura direta por HTTPS funcionou.
- A execução inicial do pytest não concluiu normalmente neste ambiente; a rodada isolando plugins globais concluiu. O comando documentado desabilita descoberta automática de plugins. Não foi atribuída causa definitiva ao travamento.
- A versão instalada do Starlette emitiu aviso de depreciação do TestClient com HTTPX; todos os testes passaram. O runtime da API permanece em HTTPX conforme solicitado. Avaliar atualização do mecanismo de testes ao atualizar o conjunto de dependências.

## Limitações e ajustes para uma próxima fase, sujeitos à aprovação

A Câmara está limitada a uma página de PLs por ano, com no máximo cinco itens, e faz uma consulta adicional por item. Não há coleta histórica completa, paginação, filtro temático ou definição automática de impacto. Situação pode estar ausente e precisa de tratamento visual. Para escala, avaliar cache e atualização incremental, respeitando limites das fontes.

IBGE retorna os oito últimos trimestres disponíveis, com revisão potencial dos dados. A PoC não mantém versões históricas de revisões nem calendário de publicação. O cabeçalho SIDRA e a semântica esperada são validados; mudança de contrato provoca erro explícito. Ausências viram null e falham no critério de aprovação do teste real, embora sejam representáveis na API.

Não há SLA medido, testes de carga, cache, prazo global da rota ou controle global de requisições concorrentes. Antes de uso compartilhado, definir essas políticas e suporte a Retry-After; fixar dependências transitivas e revisar atualizações. Não há CORS habilitado: preferir frontend na mesma origem ou configurar origens locais explícitas quando existir frontend. Hospedagem pública exige uma decisão posterior sobre autenticação e operação. Evidências são uma fotografia local, não assinatura oficial.

Nenhum dashboard, módulo de IA, notícias ou serviço pago foi desenvolvido. A próxima fase permanece aguardando aprovação do responsável pelo projeto.
