"""TDD: promoção JSON → parquet como função reutilizável."""

import json

import duckdb
import pytest

from pipelines.common import storage
from pipelines.common.parquet import json_para_parquet, pragmas_s3


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


def test_aceita_uris_de_string_do_storage(monkeypatch, tmp_path):
    """Os pipelines passam URIs do storage, não Path — precisa funcionar igual."""
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    origem = storage.uri("raw", "fonte", "d.json")
    storage.escrever_bytes(origem, json.dumps([{"a": 1}]).encode("utf-8"))
    destino = storage.uri("staging", "fonte", "d.parquet")

    assert json_para_parquet(origem, destino) == 1
    assert storage.existe(destino)


def test_pragmas_s3_vazio_para_destino_local(tmp_path):
    assert pragmas_s3(str(tmp_path / "x.parquet")) == []


def test_pragmas_s3_configura_endpoint_e_credenciais_do_r2(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "abc123")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "chave")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "segredo")

    sql = " ".join(pragmas_s3("s3://praca-dados/x.parquet"))

    assert "httpfs" in sql
    # o endpoint do duckdb é host puro, sem esquema
    assert "s3_endpoint='abc123.r2.cloudflarestorage.com'" in sql
    assert "https://" not in sql
    assert "s3_access_key_id='chave'" in sql
    assert "s3_secret_access_key='segredo'" in sql
    # o R2 só atende path-style e não tem região
    assert "s3_url_style='path'" in sql
    assert "s3_region='auto'" in sql
