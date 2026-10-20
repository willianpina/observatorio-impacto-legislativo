# Correção do contrato v1.4.1

A atribuição descrita abaixo foi substituída no contrato v1.5.0 (`../contrato-api-v1.5.0.md`). Na tabela de diferenças, a coluna v1.4.1 é licenca=null e base_legal=objeto. Este arquivo registra o que a v1.4.1 entregou.

A v1.4 atribuía aos dados do Novo Caged uma licença do site que não se aplica a esses dados.

- `atribuicao.licenca` é sempre `null` no Caged.
- `atribuicao.base_legal` contém `texto` e `link` do Decreto nº 8.777/2016, art. 4º e §1º, com redação do Decreto nº 9.903/2019.
- `atribuicao.texto`: «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo <mês/ano>, coletado em DD/MM/AAAA. Elaboração: OIL.» O mês é da coleta servida; a data da coleta é convertida para America/Sao_Paulo.
- `atribuicao.link` continua sendo a página oficial do arquivo. O texto da base legal é: «Uso livre e gratuito, com citação da fonte (Decreto nº 8.777/2016, art. 4º e §1º, com a redação do Decreto nº 9.903/2019). O MTE não publica licença própria para estes dados.»

Fonte: [Decreto](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/decreto/d8777.htm). Nenhum valor da série muda nesta correção.
