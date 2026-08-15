"""TDD: dim_municipio — a dimensão que ancora todo o mart (M2.1).

Aqui a regra 2 do projeto é finalmente cumprida: `codigo_municipio_ibge` é
VARCHAR(7), nunca INT. O SICONFI devolve o código como número, e é nesta
fronteira que ele vira texto — depois disso, nenhum município perde zero à
esquerda (Alta Floresta d'Oeste é 1100015, não 1100015 lido como int e
reimpresso sem o zero em fontes que usam 6 dígitos).
"""

import duckdb
import pytest

from pipelines.marts import dim_municipio

# A API do SICONFI devolve `capital` com padding de espaços à direita — o valor
# real é "1  " (hex 312020), não "1". A fixture reproduz isso de propósito:
# comparar sem trim marcava as 27 capitais do país como não-capitais.
ENTES = [
    # (cod_ibge, ente, capital, regiao, uf, esfera, populacao)
    (1100015, "Alta Floresta D'Oeste", "0  ", "N", "RO", "M", 22728),
    (1400100, "Boa Vista", "1  ", "N", "RR", "M", 413486),
    (1600303, "Macapá", "1  ", "N", "AP", "M", 442933),
    (2611101, "Petrolina", "0  ", "NE", "PE", "M", 386000),
    (3550308, "São Paulo", "1  ", "SE", "SP", "M", 11451245),
    (26, "Pernambuco", "0  ", "NE", "PE", "E", 9058931),  # estado: não entra
    (1, "União", "0  ", "BR", "BR", "U", 203080756),  # união: não entra
]


@pytest.fixture
def entes_parquet(tmp_path):
    caminho = tmp_path / "entes.parquet"
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE e (cod_ibge BIGINT, ente VARCHAR, capital VARCHAR, "
        "regiao VARCHAR, uf VARCHAR, esfera VARCHAR, populacao BIGINT)"
    )
    con.executemany("INSERT INTO e VALUES (?,?,?,?,?,?,?)", ENTES)
    con.execute(f"COPY e TO '{caminho.as_posix()}' (FORMAT parquet)")
    return caminho


@pytest.fixture
def dim(entes_parquet, tmp_path):
    destino = tmp_path / "dim_municipio.parquet"
    dim_municipio.construir(entes_parquet, destino)
    return duckdb.sql(f"SELECT * FROM '{destino.as_posix()}'")


# ---------------------------------------------------------------- regra 2


def test_codigo_ibge_e_varchar_de_7_digitos(dim):
    tipos = {c: t for c, t in zip(dim.columns, dim.types, strict=True)}
    assert str(tipos["codigo_municipio_ibge"]) == "VARCHAR"


def test_codigo_com_zero_a_esquerda_preservado(dim):
    """1100015 tem 7 dígitos; o risco é fonte que entrega 6 e perde o zero."""
    codigos = [linha[0] for linha in dim.project("codigo_municipio_ibge").fetchall()]
    assert all(len(c) == 7 for c in codigos), codigos
    assert "1100015" in codigos


# ---------------------------------------------------------------- conteúdo


def test_so_entra_esfera_municipal(dim):
    assert dim.aggregate("count(*)").fetchone()[0] == 5


def test_capital_vira_booleano(dim):
    linhas = dict(dim.project("codigo_municipio_ibge, eh_capital").fetchall())
    assert linhas["1400100"] is True
    assert linhas["1100015"] is False


def test_capital_sobrevive_ao_padding_da_fonte(dim):
    """O SICONFI manda "1  ", não "1" — sem trim, as 27 capitais somem."""
    capitais = dim.filter("eh_capital").project("codigo_municipio_ibge").fetchall()
    assert {c[0] for c in capitais} == {"1400100", "1600303", "3550308"}


def test_slug_sem_acento_e_com_hifen(dim):
    slugs = dict(dim.project("codigo_municipio_ibge, slug").fetchall())
    assert slugs["1600303"] == "macapa"
    assert slugs["3550308"] == "sao-paulo"
    assert slugs["1100015"] == "alta-floresta-doeste"


def test_slug_e_unico_dentro_da_uf(dim):
    duplicados = dim.aggregate("uf, slug, count(*) AS n").filter("n > 1").fetchall()
    assert duplicados == []


# ---------------------------------------------------------------- faixa de porte


@pytest.mark.parametrize(
    ("populacao", "esperado"),
    [
        (3908, "ate_5k"),
        (5000, "5k_10k"),
        (10030, "10k_20k"),
        (22728, "20k_50k"),
        (50000, "50k_100k"),
        (386000, "100k_500k"),
        (500000, "acima_500k"),
        (11451245, "acima_500k"),
    ],
)
def test_faixa_de_porte_cobre_as_7_faixas(populacao, esperado):
    assert dim_municipio.faixa_porte(populacao) == esperado


def test_faixa_de_porte_sem_populacao_e_desconhecida():
    """População ausente não pode virar faixa 'até 5 mil' — ausência ≠ zero (regra 4)."""
    assert dim_municipio.faixa_porte(None) is None
    assert dim_municipio.faixa_porte(0) is None


def test_grupo_de_comparacao_e_regiao_mais_porte(dim):
    """A régua do projeto (PRODUTO §2 regra 3): mesma faixa, mesma Grande Região."""
    grupos = dict(dim.project("codigo_municipio_ibge, grupo_comparacao").fetchall())
    assert grupos["1400100"] == "N|100k_500k"
    assert grupos["1600303"] == "N|100k_500k"
    assert grupos["2611101"] == "NE|100k_500k"  # mesma faixa, região diferente
