# Validação O3

Base: main `345af8638ed997daf6dd1ac88dad02cd7eeb5b82`, com O4 incorporada. Branch: `codex/o3-lei-caged`. Entrega em rascunho, sem merge, CI ou deploy.

## Backend e PoC

| Suíte | Total | Aprovados | Falhas | Pulados |
|---|---:|---:|---:|---:|
| O2 | 172 | 170 | 0 | 2 |
| O3 | 53 | 53 | 0 | 0 |
| Backend completo | 225 | 223 | 0 | 2 |
| PoC, executada separadamente | 39 | 39 | 0 | 0 |

Execução final: backend em 55,99 s; PoC em 4,12 s. Os dois testes ao vivo do IBGE foram pulados por padrão. Há um aviso de depreciação da integração Starlette/HTTPX em cada invocação. Não houve execução do validador ao vivo da PoC.

O commit `57a81b1ec5983f1967565ff38c10a66ba1b0be79` contém os testes anteriores à implementação: 35 falhas esperadas e 4 aprovações na O3. O teste sintético de setembro foi corrigido para manter a linha em branco antes do rodapé, sem relaxar a validação da planilha. O teste antigo de migração passou a solicitar o isolamento já usado pelas outras funções: evita herdar snapshots do teste anterior e mantém a recusa de descida quando há dados.

As migrações 0003 e 0004 foram testadas em PostgreSQL 17 descartável, com uma única cabeça 0004 e comparação do esquema com os modelos. Foram conferidos convergência e divergência entre casas, desempate por data, autoria e referência do partido atual, norma ausente, falhas parciais e totais, JSON inválido, versões e isolamento por modo.

No Caged, o replay validou saldos negativos, revisão entre arquivos, ingestão nas duas ordens, repetição sem versão extra, retorno a um valor antigo, reconstrução de arquivo intermediário tardio sem alterar o futuro, layout e hash inválidos, limite do streaming, calendário e variação anual calculada na mesma reconstrução. Nenhuma coleta inválida entra na série. Os valores são dos recortes fornecidos, servidos exclusivamente com identificação de simulação nos testes.

## Tela preservada

Somente as pequenas alterações autorizadas no adendo: guarda de linguagem com datas brasileiras e eventos, recolhimento do marco ao sair do foco, mais cenários de acessibilidade, rendimento fracionário igual no card e no resumo e proteção da restauração das mutações. Textos dos artigos 3º e 9º não foram alterados.

As 11 regressões intencionais foram detectadas. Após cada mutação os bytes foram restaurados, e a comparação Git contra o staging retornou zero. A tela foi recompilada depois da restauração. As evidências desta rodada usam prefixo O3 e preservam os arquivos históricos da O4.

Resultado final da tela: **72 aprovados, zero falhas, pulados ou instáveis, em 121,089 s**. Axe: **20 cenários**, sem violações graves ou críticas, incluindo detalhes abertos em 360 e 1280 px nos estados normal, Caged disponível, lacuna, desatualizado e sem classificação. Typecheck e build aprovados. Resultados estruturados em `evidencias/resultados.json` e evidências completas da tela em `frontend/evidencias/o3-*`.

Gitleaks: zero ocorrências no histórico completo disponível antes do commit e no staging; nova conferência do histórico após o commit é exigida antes do push. Os relatórios JSON vazios ficam em `evidencias/`. A main consultada continua na base informada; o merge com `origin/main` foi executado e retornou já atualizado, sem conflitos.

## Segurança, origem e limites

A PoC permanece sem alterações. Nenhum arquivo de ambiente foi lido ou enviado. Nenhuma exceção foi adicionada ao gitleaks. Não há serviço pago, chave nova, workflow ou publicação.

As consultas novas foram reproduzidas por MockTransport a partir do pacote fornecido; esta execução não confirma disponibilidade externa nem refaz a conferência jurídica dos links. Os comandos de coleta real estão documentados, separados da API. Os links de norma são referências manuais com os horários informados pelo usuário. As versões anteriores permanecem no banco e há proteção de descida com dados existentes.

A tela legislativa da O4 mantém seu contrato provisório. Sua futura adaptação ao contrato legislativo v1.4, tramitação/votos paginados e revisão de artigos ficam fora da O3. O manifesto e o calendário dependem de atualização humana a cada nova divulgação. A licença e a restrição de redistribuição dos recortes estão nos READMEs de fixtures; nenhum artefato foi publicado.
