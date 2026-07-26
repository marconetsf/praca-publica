"""TDD: promoção JSON → parquet como função reutilizável."""

import json

import duckdb
import pytest

from pipelines.common.parquet import json_para_parquet


def test_roundtrip_de_um_arquivo(tmp_path):
    origem = tmp_path / "dados.json"
    origem.write_text(json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]), encoding="utf-8")
    destino = tmp_path / "saida" / "dados.parquet"

    linhas = json_para_parquet(origem, destino)

    assert linhas == 2
    lido = duckdb.sql(f"SELECT a, b FROM '{destino.as_posix()}' ORDER BY a").fetchall()
    assert lido == [(1, "x"), (2, "y")]


def test_glob_de_varios_arquivos(tmp_path):
    for i in range(3):
        (tmp_path / f"parte{i}.json").write_text(json.dumps([{"n": i}]), encoding="utf-8")
    destino = tmp_path / "tudo.parquet"

    linhas = json_para_parquet(tmp_path / "*.json", destino)

    assert linhas == 3


def test_cria_diretorio_de_destino(tmp_path):
    origem = tmp_path / "d.json"
    origem.write_text(json.dumps([{"a": 1}]), encoding="utf-8")
    destino = tmp_path / "nao" / "existe" / "ainda" / "d.parquet"

    json_para_parquet(origem, destino)

    assert destino.exists()


def test_origem_sem_arquivos_levanta_erro(tmp_path):
    with pytest.raises(duckdb.Error):
        json_para_parquet(tmp_path / "*.json", tmp_path / "vazio.parquet")
