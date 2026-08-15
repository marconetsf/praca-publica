"""TDD: geração dos JSONs de serving — o que o site consome (ARQUITETURA §3).

Um JSON por município, com tudo que a página precisa: nenhum fetch extra, nenhum
join no navegador. É por isso que a proveniência (fonte, ano, data de coleta) e a
comparação de grupo viajam junto de cada indicador.
"""

import json

import duckdb
import pytest

from pipelines.marts import serving

DIM = [
    ("1400100", "Boa Vista", "boa-vista", "RR", "N", 413486, "100k_500k", "N|100k_500k", True),
    (
        "1100015",
        "Alta Floresta D'Oeste",
        "alta-floresta-doeste",
        "RO",
        "N",
        22728,
        "20k_50k",
        "N|20k_50k",
        False,
    ),
]

FATO = [
    ("1400100", 2024, "siconfi_despesa_saude_pc", 1, 1030.0, 1030.0, 7, 4),
    ("1400100", 2024, "siconfi_despesa_educacao_pc", 1, 1354.0, 1088.0, 7, 1),
    # município com indicador sem comparação (grupo pequeno)
    ("1100015", 2024, "siconfi_despesa_saude_pc", 1, 2500.0, None, 3, None),
]

INDICADORES = [
    (
        "siconfi_despesa_saude_pc",
        "Gasto com saúde por morador",
        "Quanto a prefeitura pagou...",
        "SICONFI/DCA",
        "Tesouro Nacional",
        "R$/morador/ano",
        "neutro",
        1,
        "formula tecnica",
        "Pegamos o total pago em saúde e dividimos pelos moradores.",
        "O valor é declarado pela prefeitura, sem auditoria.",
    ),
    (
        "siconfi_despesa_educacao_pc",
        "Gasto com educação por morador",
        "Quanto...",
        "SICONFI/DCA",
        "Tesouro Nacional",
        "R$/morador/ano",
        "neutro",
        1,
        "formula tecnica",
        "Pegamos o total pago em educação e dividimos pelos moradores.",
        "Dividimos por morador, não por aluno.",
    ),
]


@pytest.fixture
def marts(tmp_path):
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE d (codigo_municipio_ibge VARCHAR, nome VARCHAR, slug VARCHAR, uf VARCHAR,"
        " regiao VARCHAR, populacao_referencia BIGINT, faixa_porte VARCHAR,"
        " grupo_comparacao VARCHAR, eh_capital BOOLEAN)"
    )
    con.executemany("INSERT INTO d VALUES (?,?,?,?,?,?,?,?,?)", DIM)
    con.execute(
        "CREATE TABLE f (codigo_municipio_ibge VARCHAR, ano SMALLINT, indicador_id VARCHAR,"
        " versao_metodologia INT, valor DOUBLE, mediana_grupo DOUBLE, n_grupo INT,"
        " posicao_grupo INT)"
    )
    con.executemany("INSERT INTO f VALUES (?,?,?,?,?,?,?,?)", FATO)
    con.execute(
        "CREATE TABLE i (indicador_id VARCHAR, nome_exibicao VARCHAR, descricao_publica VARCHAR,"
        " fonte VARCHAR, orgao VARCHAR, unidade VARCHAR, direcao_melhor VARCHAR,"
        " versao_metodologia INT, formula_sql VARCHAR, formula_legivel VARCHAR,"
        " ressalvas VARCHAR)"
    )
    con.executemany("INSERT INTO i VALUES (?,?,?,?,?,?,?,?,?,?,?)", INDICADORES)

    caminhos = {}
    for tabela, nome in (("d", "dim"), ("f", "fato"), ("i", "dim_indicador")):
        caminho = tmp_path / f"{nome}.parquet"
        con.execute(f"COPY {tabela} TO '{caminho.as_posix()}' (FORMAT parquet)")
        caminhos[nome] = caminho
    return caminhos


@pytest.fixture
def gerados(marts, tmp_path):
    destino = tmp_path / "serving"
    serving.gerar(
        marts["dim"],
        marts["fato"],
        marts["dim_indicador"],
        destino,
        ano=2024,
        coletado_em="2026-08-15",
    )
    return destino


def _ler(destino, codigo):
    return json.loads((destino / "municipio" / f"{codigo}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- estrutura


def test_gera_um_json_por_municipio_com_dado(gerados):
    arquivos = sorted(p.name for p in (gerados / "municipio").glob("*.json"))
    assert arquivos == ["1100015.json", "1400100.json"]


def test_json_traz_identificacao_do_municipio(gerados):
    dados = _ler(gerados, "1400100")
    assert dados["nome"] == "Boa Vista"
    assert dados["uf"] == "RR"
    assert dados["slug"] == "boa-vista"
    assert dados["populacao"] == 413486
    assert dados["codigo_ibge"] == "1400100"


def test_indicadores_vem_com_nome_legivel_e_unidade(gerados):
    saude = next(
        i for i in _ler(gerados, "1400100")["indicadores"] if i["id"] == "siconfi_despesa_saude_pc"
    )
    assert saude["nome"] == "Gasto com saúde por morador"
    assert saude["unidade"] == "R$/morador/ano"
    assert saude["valor"] == 1030.0


# ---------------------------------------------------------------- as regras do produto


def test_todo_indicador_carrega_proveniencia(gerados):
    """Regra 1: fonte + data de referência + data de coleta em todo número."""
    for indicador in _ler(gerados, "1400100")["indicadores"]:
        assert indicador["fonte"]
        assert indicador["ano_referencia"] == 2024
        assert indicador["coletado_em"] == "2026-08-15"


def test_comparacao_viaja_junto_do_indicador(gerados):
    """Regra 3: nenhum card sem referência — e o site não calcula mediana."""
    educacao = next(
        i
        for i in _ler(gerados, "1400100")["indicadores"]
        if i["id"] == "siconfi_despesa_educacao_pc"
    )
    assert educacao["comparacao"]["mediana_parecidos"] == 1088.0
    assert educacao["comparacao"]["n_parecidos"] == 7
    assert educacao["comparacao"]["posicao"] == 1
    assert educacao["comparacao"]["grupo"] == "N|100k_500k"


def test_sem_comparacao_o_campo_e_nulo_e_nao_ausente(gerados):
    """O site precisa distinguir 'não comparável' de 'esqueci de gerar'."""
    saude = _ler(gerados, "1100015")["indicadores"][0]
    assert saude["comparacao"] is None
    assert saude["valor"] == 2500.0


def test_posicao_relativa_ao_grupo_e_textual(gerados):
    """Regra 6: posição sempre com denominador, nunca 'melhor/pior'."""
    educacao = next(
        i
        for i in _ler(gerados, "1400100")["indicadores"]
        if i["id"] == "siconfi_despesa_educacao_pc"
    )
    assert educacao["comparacao"]["texto"] == "1º entre os 7 parecidos"


# ------------------------------------------------- "como esse cálculo foi feito?"


def test_todo_indicador_traz_o_bloco_de_procedencia(gerados):
    """Feature de todo número, não de alguns: o bloco é obrigatório no JSON."""
    for arquivo in (gerados / "municipio").glob("*.json"):
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        for indicador in dados["indicadores"]:
            p = indicador["procedencia"]
            assert p["orgao"]
            assert p["formula_legivel"]
            assert p["ressalvas"]
            assert p["url_dado_bruto"].startswith("https://")


def test_link_do_dado_bruto_aponta_para_o_proprio_municipio(gerados):
    """De nada adianta linkar a fonte genérica — o leitor quer a linha dele."""
    dados = _ler(gerados, "1400100")
    for indicador in dados["indicadores"]:
        assert "1400100" in indicador["procedencia"]["url_dado_bruto"]
        assert "2024" in indicador["procedencia"]["url_dado_bruto"]


def test_procedencia_inclui_a_formula_tecnica_para_auditoria(gerados):
    """Duas fórmulas: a legível para o leitor, a técnica para quem audita."""
    indicador = _ler(gerados, "1400100")["indicadores"][0]
    assert indicador["procedencia"]["formula_sql"]
    assert indicador["procedencia"]["versao_metodologia"] == 1


def test_indice_de_busca_lista_os_municipios(gerados):
    indice = json.loads((gerados / "busca.json").read_text(encoding="utf-8"))
    assert {m["codigo_ibge"] for m in indice} == {"1400100", "1100015"}
    assert all(m["slug"] and m["uf"] and m["nome"] for m in indice)
