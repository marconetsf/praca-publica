"""TDD: transformações puras do SICONFI (validação e filtro de municípios)."""

import json

import duckdb
import pytest

from pipelines.siconfi.transform import municipios_da_uf, validar_minimo

ENTES_EXEMPLO = [
    {"cod_ibge": 2611101, "ente": "Petrolina", "uf": "PE", "esfera": "M"},
    {"cod_ibge": 2607901, "ente": "Jaboatão dos Guararapes", "uf": "PE", "esfera": "M"},
    {"cod_ibge": 1400100, "ente": "Boa Vista", "uf": "RR", "esfera": "M"},
    {"cod_ibge": 26, "ente": "Pernambuco", "uf": "PE", "esfera": "E"},
    {"cod_ibge": 1, "ente": "União", "uf": "BR", "esfera": "U"},
]


@pytest.fixture
def entes_parquet(tmp_path):
    origem = tmp_path / "entes.json"
    origem.write_text(json.dumps(ENTES_EXEMPLO), encoding="utf-8")
    destino = tmp_path / "entes.parquet"
    duckdb.sql(
        f"COPY (SELECT * FROM read_json_auto('{origem.as_posix()}')) "
        f"TO '{destino.as_posix()}' (FORMAT parquet)"
    )
    return destino


def test_municipios_da_uf_filtra_esfera_municipal(entes_parquet):
    assert municipios_da_uf(entes_parquet, "PE") == [2607901, 2611101]


def test_municipios_da_uf_aceita_minusculas(entes_parquet):
    assert municipios_da_uf(entes_parquet, "rr") == [1400100]


def test_municipios_da_uf_sem_resultado(entes_parquet):
    assert municipios_da_uf(entes_parquet, "SP") == []


def test_validar_minimo_passa_no_limite():
    itens = [{"x": i} for i in range(10)]
    assert validar_minimo(itens, minimo=10, contexto="entes") is itens


def test_validar_minimo_falha_abaixo_do_limite():
    with pytest.raises(RuntimeError, match="entes"):
        validar_minimo([{"x": 1}], minimo=2, contexto="entes")
