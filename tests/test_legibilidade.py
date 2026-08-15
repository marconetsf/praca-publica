"""TDD: o texto público precisa ser legível para quem não estudou o assunto.

O PRODUTO §3 pede "tom de voz nível Fundamental II". Isso vinha sendo respeitado
no olho — e no olho passou uma descrição de 130 caracteres com duas orações
subordinadas. Contagem de caracteres não resolve: "Quanto a prefeitura
efetivamente pagou" é curto e difícil; "Escolas, merenda e transporte escolar"
é curto e fácil.

O índice é o Flesch adaptado ao português (Martins et al., 1996):

    248,835 − 1,015 × (palavras/frase) − 84,6 × (sílabas/palavra)

    75–100  muito fácil     (1ª a 4ª série)
    50–75   fácil           (5ª a 8ª série)  ← nosso alvo
    25–50   difícil         (ensino médio/superior)
     0–25   muito difícil

Não é medida perfeita — não enxerga jargão nem ambiguidade. Serve para pegar o
deslize óbvio: frase longa demais e palavra comprida demais.
"""

import pytest

from pipelines.marts import fato_indicador, legibilidade

# Fundamental II. Abaixo disso o texto exige mais escolaridade do que o
# projeto pode supor do leitor típico.
PISO_FACIL = 50


def test_conta_silabas_de_palavras_conhecidas():
    assert legibilidade.silabas("casa") == 2
    assert legibilidade.silabas("prefeitura") == 4
    assert legibilidade.silabas("saúde") == 3
    assert legibilidade.silabas("a") == 1


def test_ditongo_conta_como_uma_silaba():
    """'moradores' tem 4; 'cidade' tem 3. Ditongo não pode inflar a conta."""
    assert legibilidade.silabas("moradores") == 4
    assert legibilidade.silabas("cidade") == 3


def test_conta_frases_por_pontuacao_final():
    assert legibilidade.frases("Uma frase. Outra frase!") == 2
    assert legibilidade.frases("Sem pontuação final") == 1
    assert legibilidade.frases("Pergunta? Sim. Não!") == 3


def test_texto_simples_pontua_alto():
    facil = "O prefeito gasta o dinheiro. A cidade tem escolas."
    assert legibilidade.indice(facil) > 70


def test_texto_rebuscado_pontua_baixo():
    dificil = (
        "A execução orçamentária consubstanciada na declaração encaminhada "
        "evidencia a materialização das despesas empenhadas e subsequentemente "
        "liquidadas no exercício financeiro correspondente."
    )
    assert legibilidade.indice(dificil) < 30


def test_indice_de_texto_vazio_nao_estoura():
    assert legibilidade.indice("") == 0.0
    assert legibilidade.indice("   ") == 0.0


# ------------------------------------------------- o texto que vai ao ar


def test_fragmento_curto_nao_e_medivel_por_flesch():
    """Limite honesto do instrumento, descoberto ao aplicá-lo.

    "Escolas, merenda e transporte escolar" tira 24 no índice e é obviamente
    legível: são 5 palavras nominais, sem frase que dilua a média de sílabas.
    Flesch pressupõe texto corrido. Reprovar isso seria o instrumento mandando
    no texto, e não o contrário.
    """
    assert not legibilidade.mensuravel("Escolas, merenda e transporte escolar.")
    assert legibilidade.mensuravel(
        "O que a prefeitura pagou em saúde no ano, dividido pelos moradores da cidade."
    )


@pytest.mark.parametrize("indicador", fato_indicador.INDICADORES, ids=lambda i: i.indicador_id)
def test_descricao_publica_e_curta_ou_facil(indicador):
    """Descrição é fragmento: vale o tamanho; se crescer, passa a valer o índice."""
    texto = indicador.descricao_publica
    if legibilidade.mensuravel(texto):
        nota = legibilidade.indice(texto)
        assert nota >= PISO_FACIL, (
            f"{indicador.indicador_id}: {nota:.0f} — {legibilidade.diagnosticar(texto)}"
        )
    else:
        assert len(texto) <= 80, f"{indicador.indicador_id}: fragmento longo demais"


@pytest.mark.parametrize("indicador", fato_indicador.INDICADORES, ids=lambda i: i.indicador_id)
def test_formula_legivel_e_facil(indicador):
    nota = legibilidade.indice(indicador.formula_legivel)
    assert nota >= PISO_FACIL, (
        f"{indicador.indicador_id}: fórmula com nota {nota:.0f} — "
        f"{legibilidade.diagnosticar(indicador.formula_legivel)}"
    )


@pytest.mark.parametrize("indicador", fato_indicador.INDICADORES, ids=lambda i: i.indicador_id)
def test_ressalvas_sao_faceis(indicador):
    nota = legibilidade.indice(indicador.ressalvas)
    assert nota >= PISO_FACIL, (
        f"{indicador.indicador_id}: ressalva com nota {nota:.0f} — "
        f"{legibilidade.diagnosticar(indicador.ressalvas)}"
    )


def test_diagnostico_diz_o_que_consertar():
    """Falhar não basta: o teste precisa dizer se é frase longa ou palavra difícil."""
    longa = "A " + "palavra " * 40 + "final."
    assert "frase" in legibilidade.diagnosticar(longa).lower()
