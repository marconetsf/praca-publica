"""TDD: fato_indicador_municipio — o mart que a página consome (M2.3).

Duas regras do projeto viram código aqui:
- **regra 3 do PRODUTO §2**: nenhum card sem comparação. `mediana_grupo` e
  `n_grupo` são colunas do fato, não cálculo de frontend.
- **regra 4**: ausência ≠ zero. Município que não declarou não vira linha com
  valor 0 — não vira linha nenhuma, e não entra na mediana dos outros.

E uma que os dados reais impuseram: o menor grupo de comparação do país tem 4
municípios (Norte acima de 500 mil). Mediana de 4 é frágil demais para virar
"o típico das parecidas", então grupo pequeno publica valor sem comparação.
"""

import duckdb
import pytest

from pipelines.marts import fato_indicador

# (cod_ibge, uf, anexo, coluna, conta, valor, populacao)
DCA = [
    # grupo NE|100k_500k — 5 municípios, comparação válida
    (2611101, "PE", "DCA-Anexo I-E", "Despesas Pagas", "10 - Saúde", 400_000_000.0, 400_000),
    (2607901, "PE", "DCA-Anexo I-E", "Despesas Pagas", "10 - Saúde", 200_000_000.0, 200_000),
    (2604106, "PE", "DCA-Anexo I-E", "Despesas Pagas", "10 - Saúde", 300_000_000.0, 300_000),
    (2609600, "PE", "DCA-Anexo I-E", "Despesas Pagas", "10 - Saúde", 150_000_000.0, 150_000),
    (2610707, "PE", "DCA-Anexo I-E", "Despesas Pagas", "10 - Saúde", 250_000_000.0, 250_000),
    # grupo N|100k_500k — 2 municípios, pequeno demais para mediana
    (1400100, "RR", "DCA-Anexo I-E", "Despesas Pagas", "10 - Saúde", 400_000_000.0, 400_000),
    (1600303, "AP", "DCA-Anexo I-E", "Despesas Pagas", "10 - Saúde", 440_000_000.0, 400_000),
    # anexo errado: não pode ser confundido com despesa paga
    (2611101, "PE", "DCA-Anexo I-G", "Despesas Empenhadas", "10 - Saúde", 999.0, 400_000),
]

DIM = [
    ("2611101", "Petrolina", "PE", "NE", 400_000, "100k_500k", "NE|100k_500k"),
    ("2607901", "Jaboatão", "PE", "NE", 200_000, "100k_500k", "NE|100k_500k"),
    ("2604106", "Caruaru", "PE", "NE", 300_000, "100k_500k", "NE|100k_500k"),
    ("2609600", "Olinda", "PE", "NE", 150_000, "100k_500k", "NE|100k_500k"),
    ("2610707", "Paulista", "PE", "NE", 250_000, "100k_500k", "NE|100k_500k"),
    ("1400100", "Boa Vista", "RR", "N", 400_000, "100k_500k", "N|100k_500k"),
    ("1600303", "Macapá", "AP", "N", 400_000, "100k_500k", "N|100k_500k"),
    # município na dimensão que NÃO declarou DCA — não pode virar zero
    ("2600054", "Abreu e Lima", "PE", "NE", 100_000, "100k_500k", "NE|100k_500k"),
]


@pytest.fixture
def fato(tmp_path):
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE d (cod_ibge BIGINT, uf VARCHAR, anexo VARCHAR, coluna VARCHAR, "
        "conta VARCHAR, valor DOUBLE, populacao BIGINT)"
    )
    con.executemany("INSERT INTO d VALUES (?,?,?,?,?,?,?)", DCA)
    dca = tmp_path / "dca.parquet"
    con.execute(f"COPY d TO '{dca.as_posix()}' (FORMAT parquet)")

    con.execute(
        "CREATE TABLE m (codigo_municipio_ibge VARCHAR, nome VARCHAR, uf VARCHAR, "
        "regiao VARCHAR, populacao_referencia BIGINT, faixa_porte VARCHAR, "
        "grupo_comparacao VARCHAR)"
    )
    con.executemany("INSERT INTO m VALUES (?,?,?,?,?,?,?)", DIM)
    dim = tmp_path / "dim.parquet"
    con.execute(f"COPY m TO '{dim.as_posix()}' (FORMAT parquet)")

    destino = tmp_path / "fato.parquet"
    fato_indicador.construir(dca, dim, destino, ano=2024)
    return duckdb.sql(f"SELECT * FROM '{destino.as_posix()}'")


def _linha(fato, codigo, indicador="siconfi_despesa_saude_pc"):
    achados = fato.filter(
        f"codigo_municipio_ibge = '{codigo}' AND indicador_id = '{indicador}'"
    ).fetchall()
    colunas = fato.columns
    return dict(zip(colunas, achados[0], strict=True)) if achados else None


# ---------------------------------------------------------------- cálculo


def test_valor_e_per_capita(fato):
    """R$ 400 mi para 400 mil moradores = R$ 1.000 por morador."""
    assert _linha(fato, "2611101")["valor"] == pytest.approx(1000.0)


def test_usa_apenas_o_anexo_correto(fato):
    """I-G também tem '10 - Saúde'; usar o anexo errado publicaria número errado."""
    assert _linha(fato, "2611101")["valor"] == pytest.approx(1000.0)  # não 999/400000


def test_codigo_ibge_continua_varchar_de_7(fato):
    codigos = [linha[0] for linha in fato.project("codigo_municipio_ibge").fetchall()]
    assert all(isinstance(c, str) and len(c) == 7 for c in codigos)


# ---------------------------------------------------------------- ausência


def test_municipio_sem_declaracao_nao_vira_zero(fato):
    """Regra 4: ausência não é linha com valor 0 — é ausência de linha."""
    assert _linha(fato, "2600054") is None


def test_ausencia_nao_entra_na_mediana_do_grupo(fato):
    """O grupo NE tem 5 declarantes + 1 ausente; a mediana é dos 5."""
    linha = _linha(fato, "2611101")
    assert linha["n_grupo"] == 5
    assert linha["mediana_grupo"] == pytest.approx(1000.0)


# ---------------------------------------------------------------- comparação


def test_mediana_do_grupo_e_a_mediana_dos_declarantes(fato):
    """Valores per capita do grupo NE: 1000, 1000, 1000, 1000, 1000 → 1000."""
    assert _linha(fato, "2607901")["mediana_grupo"] == pytest.approx(1000.0)


def test_grupo_pequeno_nao_publica_mediana(fato):
    """Mediana de 2 municípios não é 'o típico das parecidas' — é ruído."""
    linha = _linha(fato, "1400100")
    assert linha["n_grupo"] == 2
    assert linha["mediana_grupo"] is None


def test_grupo_pequeno_ainda_publica_o_valor_do_municipio(fato):
    """Sem comparação o card existe; o que falta é a referência, não o número."""
    assert _linha(fato, "1400100")["valor"] == pytest.approx(1000.0)


def test_posicao_no_grupo_tem_denominador(fato):
    """Regra 6: posição sempre com o tamanho do grupo, nunca 'melhor/pior'."""
    linha = _linha(fato, "1600303")
    assert linha["posicao_grupo"] is None, "grupo pequeno não ranqueia"

    petrolina = _linha(fato, "2611101")
    assert 1 <= petrolina["posicao_grupo"] <= petrolina["n_grupo"]


# ---------------------------------------------------------------- metodologia


def test_indicadores_declarados_tem_metodologia_completa():
    """A fórmula é dado público (ARQUITETURA §4) — nenhum indicador sem ela."""
    for definicao in fato_indicador.INDICADORES:
        assert definicao.nome_exibicao
        assert definicao.descricao_publica
        assert definicao.unidade
        assert definicao.direcao_melhor in ("maior", "menor", "neutro")


def test_dim_indicador_e_gerada_a_partir_da_mesma_fonte(tmp_path):
    destino = tmp_path / "dim_indicador.parquet"
    fato_indicador.construir_dim_indicador(destino)
    linhas = duckdb.sql(f"SELECT * FROM '{destino.as_posix()}'").fetchall()
    assert len(linhas) == len(fato_indicador.INDICADORES)
