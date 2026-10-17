# Tela local — O4

Next.js App Router, TypeScript, Tailwind e Recharts. Uso local e privado, sem publicação, analytics ou serviços pagos. O navegador consulta somente o adaptador `/api/oil`; a URL do backend fica no servidor. Não há consulta do navegador ao IBGE.

## Windows / PowerShell

Com Node.js e o backend da O2 disponíveis:

```powershell
cd frontend
npm ci
$env:NEXT_TELEMETRY_DISABLED='1'
$env:OIL_API_URL='http://127.0.0.1:8000'
$env:OIL_TEST_MODE='0'
npm run build
npm start
```

Abrir http://127.0.0.1:3100. O backend usa banco e ingestão separados, conforme seu README. Nenhum arquivo `.env` é necessário: configure as variáveis no processo. `frontend/.env.example` enumera as opções.

## Testes locais

Os testes usam respostas gravadas do backend e cenários explicitamente simulados. O servidor normal recusa respostas com `simulada: true`. Os dados legislativos de demonstração só são habilitados no servidor por `OIL_TEST_MODE=1`, com faixa e selos visíveis.

```powershell
$env:NEXT_TELEMETRY_DISABLED='1'
$env:OIL_BROWSER_CHANNEL='msedge'
npm run build
npm run typecheck
npm run test:e2e
```

Os testes iniciam e encerram dois servidores próprios nas portas 3101 e 3102. Usam Edge instalado; sem Edge, instale um navegador Playwright e omita `OIL_BROWSER_CHANNEL`. Relatório temporário em `test-results/`, ignorado pelo Git.

A verificação real é separada: com backend real em 8766, frontend normal em 3100 e `OIL_API_URL=http://127.0.0.1:8766`, execute `node tests/capture-real.mjs`. Ela falha se receber dados simulados, indisponíveis ou menos de oito pontos, confere os valores renderizados e executa axe em 360 e 1280 px. Não executa `validate_live.py`.

## Contrato e precedência

Referências recebidas preservadas em `referencias/`. O adendo 1 substitui os pontos conflitantes da missão O4; o adendo 2 substitui a nota antiga do Caged. A única exceção à expressão proibida é a legenda literal obrigatória dos marcos, autorizada pelo usuário.

`lib/contrato-lei-provisorio.ts` concentra os tipos legislativos. A O3 ainda precisa fornecer a integração real. Em modo normal, lei, marcos e votações ficam indisponíveis; o mock não é fallback. A paginação da demonstração recorta listas simuladas; será conectada à paginação do contrato O3 quando existir.

O Caged normal continua indisponível. O adaptador visual já aceita `ajuste`, `arquivo_origem`, `licenca` e `competencia_coleta`: a O3 deve fornecer esses metadados a partir do arquivo, além da comparação anual. A tela não calcula o saldo nem presume mês de origem. Meses de outro ajuste ficam fora do gráfico, mas permanecem na tabela.

## Proteções da O4-R

Links externos passam por `safeHref()`: somente HTTPS das famílias IBGE, Câmara, Senado, Planalto, Imprensa Nacional e do caminho oficial MTE em `gov.br/trabalho-e-emprego`. Links recusados viram texto. URLs com credenciais ou porta alternativa também são recusadas. O CSV prefixa os caracteres de fórmula sem apagar o conteúdo original.

O proxy limita 60 consultas por minuto, inclusive hits do cache, com 429 e `Retry-After`. O cache em memória guarda somente sucessos, por 15 segundos, separado por série e janela. Erros não entram no cache. O estado é local ao processo e é reiniciado junto ao servidor; uma implantação com várias instâncias exigiria armazenamento compartilhado, fora do escopo local.

Sem proxy confiável, todos os acessos pertencem ao cliente local e compartilham o limite: cabeçalhos de IP do navegador são ignorados. Somente atrás de um proxy que remova e sobrescreva `X-Forwarded-For`, use `OIL_TRUST_PROXY=1` para separar limites por IP. A configuração padrão permanece `0` e o servidor continua restrito ao endereço de loopback.

Os cabeçalhos CSP, `nosniff` e política de referência são enviados pelo Next.js. A CSP mantém as origens locais e permite scripts inline para o bootstrap do Next.js e estilos inline para o Recharts; não permite scripts de terceiros, objetos nem incorporação em frames. Uma política sem `unsafe-inline` requer nonces e é uma melhoria futura, além dos cabeçalhos solicitados nesta revisão.

## Evidências e limites

Consulte `VALIDACAO.md` e `evidencias/`. Axe automatizado complementa a conferência visual e por teclado; não representa certificação integral de acessibilidade. As capturas simuladas têm faixa de teste. As capturas `real-*` usam coletas reais da API local e não apresentam dados legislativos de teste.
