"""A declaração de guarda: o que se guarda de cada fonte, e por quê.

Integrar base nova sempre esbarrou na mesma pergunta — "precisamos baixar isso?"
— e ela vinha sendo respondida caso a caso, de cabeça. Aqui ela vira declaração
no `fontes.yaml`, com o mesmo contrato de `sonda:` e `ficha:`: **fonte sem
`guarda:` quebra o teste**, e o motivo de não guardar é obrigatório.

A regra que o resto sustenta é uma só: *todo byte que produziu um número
publicado está guardado por nós, datado e com hash*. Sem isso não existe errata
defensável — emitir errata é dizer "no dia X a fonte dizia Y", e sem o insumo
guardado isso vira palavra contra palavra.
"""

import pytest

from pipelines.common import guarda
from pipelines.common.config import fontes as fontes_reais


def _fonte(**campos):
    base = {
        "modo": "colheita",
        "medido_em": "2026-08-16",
        "risco_sumico": "baixo",
        "onde": "actions",
        "motivo": "API com filtro por município; guardamos as respostas de cada execução.",
    }
    return {"guarda": {**base, **campos}}


# ------------------------------------------------------------ o que pode publicar


def test_modo_remota_nao_sustenta_numero_publicado():
    """Leitura remota é reconhecimento, não origem.

    O arquivo remoto muda sob nossos pés e ninguém consegue provar o que lemos.
    A fronteira existe para que não exista número cujo insumo esteja fora do
    nosso alcance.
    """
    assert not guarda.pode_publicar(guarda.ler(_fonte(modo="remota", motivo="só dimensionamento")))
    assert not guarda.pode_publicar(guarda.ler(_fonte(modo="nenhuma", motivo="fonte inacessível")))


@pytest.mark.parametrize("modo", ["integral", "recorte", "colheita"])
def test_modos_com_copia_podem_publicar(modo):
    assert guarda.pode_publicar(guarda.ler(_fonte(modo=modo, espelho_declarado=True)))


# ------------------------------------------------------------ invariantes da declaração


def test_modo_desconhecido_e_recusado():
    with pytest.raises(ValueError, match="modo"):
        guarda.ler(_fonte(modo="talvez"))


def test_nao_guardar_exige_motivo_escrito():
    """Recusa sem motivo escrito volta como proposta nova de seis em seis meses."""
    with pytest.raises(ValueError, match="motivo"):
        guarda.ler(_fonte(modo="nenhuma", motivo=""))


def test_medicao_sem_data_e_chute():
    with pytest.raises(ValueError, match="medido_em"):
        guarda.ler(_fonte(medido_em=None))


def test_recorte_sem_pacto_editorial_nao_colhe():
    """Recorte é bytes com finalidade. Sem indicador pactuado, não se colhe nada.

    É a decisão editorial de 16/08/2026 virando condição que o pipeline lê:
    não escalar coleta sem indicador que responda "a cidade melhorou?".
    """
    sem_pacto = guarda.ler(_fonte(modo="recorte", recorte={"pactuado_em": None}))
    assert not guarda.pode_colher(sem_pacto)

    com_pacto = guarda.ler(_fonte(modo="recorte", recorte={"pactuado_em": "2026-08-16"}))
    assert guarda.pode_colher(com_pacto)


def test_colheita_sem_recorte_declarado_colhe_normalmente():
    """API com filtro não precisa de recorte pactuado: o custo já é por consulta."""
    assert guarda.pode_colher(guarda.ler(_fonte(modo="colheita")))


# ------------------------------------------------------------ o portão da coleta


def test_espelhador_recusa_fonte_que_decidimos_nao_espelhar():
    """A decisão escrita tem que ter dentes, senão é exortação em documento.

    Sem o portão, basta alguém rodar `--todas` numa sessão futura para copiar
    justamente o acervo que foi analisado e recusado — e o motivo escrito no
    YAML não impediria nada.
    """
    from pipelines.espelho import espelhar as espelhador

    catalogo = {
        "guardavel": {
            "espelho": ["https://exemplo.gov.br/a.zip"],
            "guarda": {
                "modo": "integral",
                "medido_em": "2026-08-16",
                "motivo": "fonte com precedente de apagão",
            },
        },
        "recusada": {
            "espelho": ["https://exemplo.gov.br/b.zip"],
            "guarda": {
                "modo": "recorte",
                "medido_em": "2026-08-16",
                "motivo": "66 GB para sustentar nenhum indicador pactuado até agora",
                "recorte": {"pactuado_em": None},
            },
        },
    }
    assert espelhador.alvos_do_catalogo(catalogo) == [("guardavel", "https://exemplo.gov.br/a.zip")]


def test_recorte_pactuado_volta_a_ser_espelhavel():
    from pipelines.espelho import espelhar as espelhador

    catalogo = {
        "pactuada": {
            "espelho": ["https://exemplo.gov.br/c.zip"],
            "guarda": {
                "modo": "recorte",
                "medido_em": "2026-08-16",
                "motivo": "acervo grande; só a fatia do indicador de abandono escolar",
                "recorte": {"pactuado_em": "2026-08-16"},
            },
        }
    }
    assert espelhador.alvos_do_catalogo(catalogo) == [("pactuada", "https://exemplo.gov.br/c.zip")]


# ------------------------------------------------------------ o catálogo real


@pytest.mark.parametrize("nome", sorted(fontes_reais()))
def test_toda_fonte_declara_o_que_se_guarda_dela(nome):
    config = fontes_reais()[nome] or {}
    assert config.get("guarda"), (
        f"'{nome}' não declara `guarda:` — sem isso ninguém sabe se o dado que "
        "sustenta um número publicado está conosco"
    )
    guarda.ler(config)  # levanta ValueError se a declaração for inválida


@pytest.mark.parametrize("nome", sorted(fontes_reais()))
def test_guarda_integral_tem_alvos_declarados(nome):
    """`integral` sem lista de alvos é intenção, não acervo."""
    config = fontes_reais()[nome] or {}
    if guarda.ler(config).modo != "integral":
        return
    assert config.get("espelho"), f"'{nome}' declara guarda integral sem `espelho:`"


@pytest.mark.parametrize("nome", sorted(fontes_reais()))
def test_fonte_que_nao_guarda_explica_por_que(nome):
    declarada = guarda.ler(fontes_reais()[nome] or {})
    if declarada.modo == "integral":
        return
    assert len(declarada.motivo) >= 40, (
        f"'{nome}': motivo curto demais para explicar por que não guardamos tudo"
    )
