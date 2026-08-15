"""Contrato de indicador — a sistemática de adoção de métricas.

Cada métrica tem peculiaridade própria, e isso não é exceção: é a norma. Uma
cobre 5 anos, outra tem um ponto só. Uma existe para os 5.570 municípios, outra
só onde há rede municipal. Uma é confiável em qualquer cidade, outra vira ruído
onde o denominador é pequeno. Tratar caso a caso multiplica condicional pelo
código e garante que a próxima métrica repita o erro da anterior.

Aqui a peculiaridade vira **declaração**. Quem adiciona indicador preenche três
coisas — o que já cobre, onde se aplica, quando não é confiável — e o resto sai
de graça: a lacuna aparece no gráfico, "não se aplica" se separa de "não
declarou", e o valor instável é suprimido com motivo escrito.

O que **não** está aqui de propósito: nada decide se a métrica é relevante. Isso
é julgamento editorial, mora em docs/INDICADORES.md, e não deve virar código.
"""

from dataclasses import dataclass, field

# marcador para "vale para os 5.570" — distingue de uma lista que por acaso
# contém todos, e evita carregar 5.570 códigos em memória por indicador
TODOS_MUNICIPIOS = "todos"

PERIODICIDADES = ("mensal", "bimestral", "quadrimestral", "anual", "bienal")

# Dado anual sai com cerca de um ano de atraso — isso é o normal do serviço
# público, e avisar sempre viraria ruído que o leitor aprende a ignorar. O card
# já mostra ano de referência e data de coleta lado a lado. O aviso extra só
# aparece quando a defasagem foge do esperado.
DEFASAGEM_NOTAVEL_MESES = 18


@dataclass(frozen=True)
class Cobertura:
    """Onde e quando a métrica existe."""

    anos: tuple[int, ...]
    periodicidade: str
    defasagem_meses: int
    universo: str | tuple[str, ...] = TODOS_MUNICIPIOS

    def cobre(self, ano: int) -> bool:
        return ano in self.anos

    def tem_serie(self) -> bool:
        """Com um ponto não há evolução — o card não pode prometer tendência."""
        return len(self.anos) >= 2

    def lacunas(self, inicio: int, fim: int) -> tuple[int, ...]:
        """Anos do intervalo que a fonte não cobre.

        Existe para o gráfico mostrar buraco em vez de ligar os pontos: IDEB é
        bienal, e uma linha reta entre 2021 e 2023 inventaria 2022.
        """
        return tuple(ano for ano in range(inicio, fim + 1) if ano not in self.anos)

    def alcanca(self, codigo_municipio: str) -> bool:
        if self.universo == TODOS_MUNICIPIOS:
            return True
        return codigo_municipio in self.universo

    def explicar_defasagem(self) -> str:
        return (
            f"Dado {self.periodicidade}, publicado cerca de {self.defasagem_meses} meses "
            "depois do período de referência."
        )


@dataclass(frozen=True)
class Confiabilidade:
    """Quando o número não merece ser publicado como se fosse preciso."""

    denominador_minimo: int | None = None
    motivo_supressao: str = ""
    campo_ignorado: str | None = None
    # ano → o que mudou. A série não atravessa a quebra.
    quebras: dict[int, str] = field(default_factory=dict)

    def avaliar(self, denominador: int | None) -> tuple[bool, str | None]:
        """Suprimir este valor? Devolve (suprimir, motivo)."""
        if self.denominador_minimo is None:
            return False, None
        if denominador is None:
            # sem saber o denominador não dá para afirmar que a taxa é estável
            return True, f"{self.motivo_supressao} (base de cálculo não informada)"
        if denominador < self.denominador_minimo:
            return True, self.motivo_supressao
        return False, None

    def comparavel(self, ano_a: int, ano_b: int) -> bool:
        """Há quebra metodológica entre os dois anos?"""
        inicio, fim = sorted((ano_a, ano_b))
        return not any(inicio < ano <= fim for ano in self.quebras)

    def explicar_quebra(self, ano_a: int, ano_b: int) -> str:
        inicio, fim = sorted((ano_a, ano_b))
        motivos = [texto for ano, texto in sorted(self.quebras.items()) if inicio < ano <= fim]
        return "; ".join(motivos)

    def exige_publicar_ignorado(self) -> bool:
        """Campo com 'ignorado' alto engana se o percentual não vier junto."""
        return self.campo_ignorado is not None


@dataclass(frozen=True)
class Contrato:
    """O que um indicador precisa declarar antes de virar página."""

    cobertura: Cobertura
    confiabilidade: Confiabilidade

    def avisos_para_o_leitor(self) -> list[str]:
        """As ressalvas que a página precisa exibir — em português, não em código."""
        avisos = []

        if self.cobertura.defasagem_meses >= DEFASAGEM_NOTAVEL_MESES:
            avisos.append(self.cobertura.explicar_defasagem())

        if not self.cobertura.tem_serie():
            avisos.append(
                "Só há um ano de dado publicado até agora, então ainda não dá para "
                "mostrar se está melhorando ou piorando."
            )

        if self.cobertura.universo != TODOS_MUNICIPIOS:
            avisos.append(
                "Esta informação não existe para todos os municípios do país; "
                "onde ela não existe, a página diz isso."
            )

        if self.confiabilidade.denominador_minimo is not None:
            avisos.append(
                f"Em cidades com menos de {self.confiabilidade.denominador_minimo} casos "
                "no período, o número não é publicado: "
                f"{self.confiabilidade.motivo_supressao}."
            )

        if self.confiabilidade.exige_publicar_ignorado():
            avisos.append(
                f"Parte dos registros vem sem a informação de "
                f"{self.confiabilidade.campo_ignorado}; o percentual aparece ao lado."
            )

        for ano, motivo in sorted(self.confiabilidade.quebras.items()):
            avisos.append(
                f"A partir de {ano} o dado mudou de forma ({motivo}), então a "
                "comparação com os anos anteriores não é direta."
            )

        return avisos


def motivo_ausencia(cobertura: Cobertura, codigo_municipio: str, *, declarou: bool) -> str | None:
    """Por que este município não tem este número?

    A distinção que o leitor precisa e que quase nenhum painel faz: "não se
    aplica à sua cidade" é diferente de "a sua prefeitura não enviou o dado".
    A primeira não é falha de ninguém; a segunda é informação pública.
    """
    if not cobertura.alcanca(codigo_municipio):
        return "fora_do_universo"
    if not declarou:
        return "nao_declarou"
    return None
