"""TDD: Gate 2 de sanidade (ESCOPO M2.4).

O mantenedor não precisa saber avaliar se R$ 5.371 por morador em saúde é
plausível — o gate precisa. São checagens objetivas, com âncora externa ao
nosso próprio cálculo:

- a soma das funções não pode exceder a despesa total declarada;
- valor negativo em despesa ou receita não existe;
- percentuais aplicados em saúde e educação abaixo do piso constitucional são
  sinal de que o número está errado (nosso ou do declarante);
- valor muito distante da mediana do grupo merece olhar antes de publicar.

**Importante**: o percentual aqui é indicador de sanidade, não aferição legal.
A base de cálculo do piso real exclui várias transferências que somamos, então
nosso denominador é maior e o percentual sai menor que o oficial. Serve para
achar erro, nunca para afirmar que um município descumpriu a Constituição.
"""

import duckdb
import pytest

from pipelines.marts import sanidade


def _dca(tmp_path, linhas):
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE d (cod_ibge BIGINT, anexo VARCHAR, coluna VARCHAR, "
        "conta VARCHAR, valor DOUBLE)"
    )
    con.executemany("INSERT INTO d VALUES (?,?,?,?,?)", linhas)
    caminho = tmp_path / "dca.parquet"
    con.execute(f"COPY d TO '{caminho.as_posix()}' (FORMAT parquet)")
    return caminho


DESPESA = ("DCA-Anexo I-E", "Despesas Pagas")
RECEITA = ("DCA-Anexo I-C", "Receitas Brutas Realizadas")


def _municipio_saudavel(cod=1400100):
    """Município com contas coerentes: total maior que as partes, pisos atendidos."""
    return [
        (cod, *DESPESA, "Despesas Exceto Intraorçamentárias", 1000.0),
        (cod, *DESPESA, "10 - Saúde", 300.0),
        (cod, *DESPESA, "12 - Educação", 400.0),
        (cod, *RECEITA, "1.1.0.0.00.0.0 - Impostos, Taxas e Contribuições de Melhoria", 200.0),
        (cod, *RECEITA, "1.7.0.0.00.0.0 - Transferências Correntes", 800.0),
    ]


# ---------------------------------------------------------------- soma das partes


def test_municipio_coerente_nao_gera_achado(tmp_path):
    achados = sanidade.verificar(_dca(tmp_path, _municipio_saudavel()))
    assert achados == []


def test_soma_das_funcoes_acima_do_total_e_critico(tmp_path):
    linhas = _municipio_saudavel()
    linhas[1] = (1400100, *DESPESA, "10 - Saúde", 900.0)  # 900 + 400 > 1000

    achados = sanidade.verificar(_dca(tmp_path, linhas))

    assert any(a["check"] == "soma_funcoes_excede_total" for a in achados)
    assert all(a["severidade"] == "CRITICO" for a in achados if a["check"].startswith("soma"))


def test_valor_negativo_e_critico(tmp_path):
    linhas = _municipio_saudavel()
    linhas[1] = (1400100, *DESPESA, "10 - Saúde", -50.0)

    achados = sanidade.verificar(_dca(tmp_path, linhas))

    assert any(a["check"] == "valor_negativo" for a in achados)


# ---------------------------------------------------------------- pisos


def test_educacao_muito_abaixo_do_piso_vira_aviso(tmp_path):
    """25% é o piso da CF art. 212; 4% denuncia erro no dado, não economia."""
    linhas = _municipio_saudavel()
    linhas[2] = (1400100, *DESPESA, "12 - Educação", 40.0)  # 4% de 1000

    achados = sanidade.verificar(_dca(tmp_path, linhas))

    educacao = [a for a in achados if a["check"] == "educacao_abaixo_do_piso"]
    assert len(educacao) == 1
    assert educacao[0]["severidade"] == "AVISO"


def test_saude_muito_abaixo_do_piso_vira_aviso(tmp_path):
    linhas = _municipio_saudavel()
    linhas[1] = (1400100, *DESPESA, "10 - Saúde", 20.0)  # 2% de 1000

    achados = sanidade.verificar(_dca(tmp_path, linhas))

    assert any(a["check"] == "saude_abaixo_do_piso" for a in achados)


def test_achado_de_piso_explica_que_nao_e_afericao_legal(tmp_path):
    """O texto precisa impedir que isto vire acusação de descumprimento."""
    linhas = _municipio_saudavel()
    linhas[2] = (1400100, *DESPESA, "12 - Educação", 40.0)

    achado = next(
        a
        for a in sanidade.verificar(_dca(tmp_path, linhas))
        if a["check"] == "educacao_abaixo_do_piso"
    )

    assert "aproxima" in achado["detalhe"].lower()


def test_sem_base_de_calculo_nao_avalia_piso(tmp_path):
    """Município sem receita declarada não pode ser acusado de nada (regra 4)."""
    linhas = [linha for linha in _municipio_saudavel() if linha[1] != RECEITA[0]]
    linhas[1] = (1400100, *DESPESA, "10 - Saúde", 1.0)

    achados = sanidade.verificar(_dca(tmp_path, linhas))

    assert not any("piso" in a["check"] for a in achados)


# ---------------------------------------------------------------- relatório


def test_relatorio_agrupa_por_severidade(tmp_path):
    linhas = _municipio_saudavel() + [
        (1400200, *DESPESA, "Despesas Exceto Intraorçamentárias", 100.0),
        (1400200, *DESPESA, "10 - Saúde", 900.0),
    ]

    achados = sanidade.verificar(_dca(tmp_path, linhas))
    resumo = sanidade.resumir(achados)

    assert resumo["CRITICO"] >= 1
    assert resumo["total"] == len(achados)


def test_verificar_lista_o_municipio_em_cada_achado(tmp_path):
    linhas = _municipio_saudavel()
    linhas[1] = (1400100, *DESPESA, "10 - Saúde", -1.0)

    achado = sanidade.verificar(_dca(tmp_path, linhas))[0]

    assert achado["codigo_municipio_ibge"] == "1400100"
    assert achado["detalhe"]


@pytest.mark.parametrize("severidade", ["CRITICO", "AVISO"])
def test_severidades_sao_as_do_projeto(severidade):
    assert severidade in sanidade.SEVERIDADES
