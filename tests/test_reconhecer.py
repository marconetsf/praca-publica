"""Reconhecimento: medir a fonte nova ANTES de decidir se ela entra.

A pergunta "precisamos baixar isso?" tinha resposta caso a caso, de cabeça.
Aqui ela é uma função de três medidas — tamanho, se dá para pedir por recorte, e
se a fonte tem precedente de sumir — e devolve o modo de guarda com o motivo
escrito, pronto para colar no `fontes.yaml`.

Os limiares não são gosto: saem de restrições reais. O teto de 6 h do runner do
Actions, os 10 GB do plano do R2 e o fato de o acervo ainda ter cópia única.
"""

import pytest

from pipelines import reconhecer

TETO_RUNNER_H = 6


def _medida(**campos):
    base = {
        "bytes_por_unidade": 100_000,
        "unidades_para_cobrir_o_pais": 1,
        "requisicoes": 1,
        "throttle_s": 1.0,
        "risco_sumico": "baixo",
        "tem_filtro": True,
    }
    return reconhecer.Medida(**{**base, **campos})


# ------------------------------------------------------------ o teto do runner


def test_estima_o_tempo_de_uma_varredura_nacional():
    """5.570 municípios × 12 meses a 1 req/s não cabem em 6 h — e é o caso do PNCP."""
    medida = _medida(requisicoes=5570 * 12, throttle_s=1.0)
    assert reconhecer.horas(medida) > 18
    assert not reconhecer.cabe_no_runner(medida)


def test_consulta_em_lote_cabe_com_folga():
    """O SIDRA aceita vários municípios por chamada: o país sai em centenas delas."""
    assert reconhecer.cabe_no_runner(_medida(requisicoes=300, throttle_s=1.0))


# ------------------------------------------------------------ a sugestão de modo


def test_fonte_que_ja_sumiu_e_guardada_inteira_mesmo_sem_indicador():
    """Risco de sumiço decide sozinho: é o único motivo aceito para gastar bytes
    sem uso imediato. O INEP apagou o Ideb de 2019 e 2021 antes de espelharmos."""
    modo, motivo = reconhecer.sugerir(
        _medida(risco_sumico="alto", bytes_por_unidade=35_000_000, unidades_para_cobrir_o_pais=6)
    )
    assert modo == "integral"
    assert "sum" in motivo.lower()


def test_acervo_gigante_sem_risco_vira_recorte():
    """66 GB do SIH são 6,6× o teto do plano, e a fonte não corre risco de sumir."""
    modo, motivo = reconhecer.sugerir(
        _medida(
            bytes_por_unidade=66 * 1024**3,
            unidades_para_cobrir_o_pais=1,
            risco_sumico="baixo",
            tem_filtro=False,
        )
    )
    assert modo == "recorte"
    assert "GB" in motivo


def test_arquivo_pequeno_e_guardado_inteiro():
    modo, _ = reconhecer.sugerir(_medida(bytes_por_unidade=200 * 1024**2))
    assert modo == "integral"


def test_api_com_filtro_e_payload_pequeno_vira_colheita_nacional():
    """621 bytes por município dão 3,5 MB para o país inteiro: colher tudo é trivial."""
    modo, motivo = reconhecer.sugerir(
        _medida(
            bytes_por_unidade=621,
            unidades_para_cobrir_o_pais=5570,
            requisicoes=800,
            tem_filtro=True,
        )
    )
    assert modo == "colheita"
    assert "MB" in motivo or "KB" in motivo


def test_payload_grande_por_municipio_nao_vira_varredura_nacional():
    """PNCP: 863 KB por município-mês são 57,7 GB/ano. Recorte, e só com pacto."""
    modo, motivo = reconhecer.sugerir(
        _medida(
            bytes_por_unidade=863_000,
            unidades_para_cobrir_o_pais=5570 * 12,
            requisicoes=5570 * 12,
            tem_filtro=True,
        )
    )
    assert modo == "recorte"
    assert "runner" in motivo or "h de" in motivo


# ------------------------------------------------------------ o bloco pronto para o YAML


def test_devolve_bloco_yaml_pronto_para_colar():
    """A etapa termina num artefato, não numa conclusão: o texto a colar no catálogo."""
    bloco = reconhecer.bloco_yaml(_medida(bytes_por_unidade=200 * 1024**2), medido_em="2026-08-16")
    assert "guarda:" in bloco
    assert "modo: integral" in bloco
    assert "medido_em: 2026-08-16" in bloco
    assert "motivo:" in bloco


def test_o_bloco_gerado_passa_na_validacao_da_guarda():
    """O que o reconhecimento sugere tem que ser aceito pelo validador — senão a
    etapa seguinte trava com um bloco que a própria ferramenta escreveu."""
    import yaml

    from pipelines.common import guarda

    for medida in (
        _medida(risco_sumico="alto"),
        _medida(bytes_por_unidade=66 * 1024**3, tem_filtro=False),
        _medida(bytes_por_unidade=621, unidades_para_cobrir_o_pais=5570, requisicoes=800),
    ):
        bloco = yaml.safe_load(reconhecer.bloco_yaml(medida, medido_em="2026-08-16"))
        guarda.ler(bloco)  # não pode levantar


@pytest.mark.parametrize("risco", ["alto", "medio", "baixo"])
def test_todo_risco_declarado_produz_sugestao(risco):
    modo, motivo = reconhecer.sugerir(_medida(risco_sumico=risco))
    assert modo in reconhecer.MODOS_COM_COPIA
    assert motivo


# ------------------------------------------------------------ quando a medição falha


def test_falha_de_rede_vira_dica_e_nao_stack_trace():
    """A primeira tentativa real morreu em 100 linhas de traceback do urllib3.

    Uma ferramenta de reconhecimento que responde com stack trace é uma
    ferramenta que ninguém usa na segunda vez — e o procedimento inteiro depende
    de ela ser o passo mais barato.
    """
    dica = reconhecer.dica_de_falha(ConnectionResetError("conexão abortada"))
    assert "residencial" in dica or "--fonte" in dica
    assert "urllib3" not in dica


def test_dica_de_tls_aponta_o_bundle_do_catalogo():
    import ssl

    dica = reconhecer.dica_de_falha(ssl.SSLCertVerificationError("unable to get local issuer"))
    assert "--fonte" in dica, "o catálogo já declara `tls_ca` para essas fontes"
