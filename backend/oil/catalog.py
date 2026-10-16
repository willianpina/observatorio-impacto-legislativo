from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    codigo: str
    nome: str
    tabela: str
    variavel: str
    cv: str
    variacao: str
    diferenca: str
    unidade: str
    unidade_fonte: str
    unidade_variacao: str
    medida: str
    tipo_valor: str

    @property
    def variaveis(self):
        return tuple(dict.fromkeys((self.variavel, self.cv, self.variacao, self.diferenca)))

    @property
    def url(self):
        return (f'https://apisidra.ibge.gov.br/values/t/{self.tabela}/n1/all/v/'
                f'{",".join(self.variaveis)}/p/all')

    @property
    def metadata_url(self):
        return f'https://servicodados.ibge.gov.br/api/v3/agregados/{self.tabela}/metadados'

    @property
    def units(self):
        return {self.variavel: self.unidade_fonte, self.cv: '%',
                self.variacao: 'Ponto percentual' if self.medida == 'taxa' else '%',
                self.diferenca: 'Ponto percentual' if self.medida == 'taxa' else 'Reais'}


SPECS = {
    'desocupacao': Spec('desocupacao', 'Taxa de desocupação — Brasil', '6381',
                       '4099', '4103', '8816', '8816', '%', '%', 'p.p.', 'taxa', 'nominal'),
    'rendimento-real': Spec('rendimento-real', 'Rendimento médio mensal real habitual — Brasil',
                           '6390', '5933', '5941', '8837', '8838', 'R$', 'Reais', '%', 'valor', 'real'),
}
