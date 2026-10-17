# Adendo 2 à Missão O4 — Card do Caged (vai junto com a O3, quando a rota do Caged existir)

Este adendo substitui, na spec v1.5, a nota antiga «saldo sem ajuste, competência MM/AAAA». A série usada passa a ser o saldo **com ajustes**.

## 1. Card e gráfico do Caged
- Nota curta no card, logo abaixo do número: «Saldo com ajustes».
- Atribuição no card, no gráfico e na tabela de dados: «Fonte: Novo Caged – MTE, Tabela 5.1 (com ajustes), arquivo <mês/ano>, licença CC BY-ND 3.0». O `<mês/ano>` vem do dado (arquivo de origem da coleta), nunca da data de hoje. Junto vão o link e a data da coleta, como em todo número.
- No «Saiba mais»: «As séries do Novo Caged são revisadas mensalmente. O número de um mês pode mudar nas divulgações seguintes.»
- Uma linha do gráfico nunca mistura meses com e sem ajuste (regra do Cientista, que continua valendo). Quando o MTE revisar um mês, a tela mostra o valor da coleta mais recente, sem apagar o histórico.

## 2. Valor oficial e cálculo do Observatório, separados
- O valor oficial (o saldo do mês) aparece como o MTE publica, sem nenhuma conta da tela.
- Qualquer variação ou comparação (por exemplo, com o mesmo mês do ano anterior) aparece em linha separada, com o rótulo «Cálculo do Observatório a partir de dados do MTE». Nunca na mesma linha nem com o mesmo estilo do valor oficial.
- A licença CC BY-ND não permite apresentar uma obra derivada como se fosse do MTE. Por isso, o rótulo do cálculo é obrigatório e a tabela oficial não é alterada.
- Enquanto a rota não existir ou vier `disponivel: false`, o card continua com «Dado ainda não disponível» e o `motivo`.

## 3. Testes a acrescentar
- O card mostra «Saldo com ajustes» e a atribuição completa, com o mês e o ano do arquivo vindos da fixture.
- O «Saiba mais» contém «revisadas mensalmente».
- Toda variação do Caged tem o rótulo «Cálculo do Observatório a partir de dados do MTE» e fica num elemento separado do valor oficial.
- Um teste com meses de ajustes diferentes na fixture falha se eles forem para a mesma linha.
- O teste de frases proibidas também cobre os textos do Caged.
