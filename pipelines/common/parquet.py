"""Promoção JSON → parquet (zstd), o passo padrão raw → staging.

Origem e destino são URIs do storage: caminho local ou `s3://` (R2). Quando algum
lado é s3, o duckdb precisa do httpfs configurado com as credenciais do R2.
"""

from collections.abc import Iterable
from pathlib import Path

import duckdb

from pipelines.common import storage

Origem = str | Path | Iterable[str | Path]


def _posix(caminho: str | Path) -> str:
    """Nunca passar URI s3 por Path: no Windows ele colapsa `s3://` em `s3:/`."""
    if isinstance(caminho, Path):
        return caminho.as_posix()
    return str(caminho).replace("\\", "/")


def pragmas_s3(destino: str) -> list[str]:
    """SQL que ensina o duckdb a falar com o R2 (path-style, sem região)."""
    if not destino.startswith("s3://"):
        return []
    opcoes = storage.opcoes_fs(destino)
    endpoint = opcoes["client_kwargs"]["endpoint_url"].removeprefix("https://")
    return [
        "INSTALL httpfs",
        "LOAD httpfs",
        f"SET s3_endpoint='{endpoint}'",
        f"SET s3_access_key_id='{opcoes['key']}'",
        f"SET s3_secret_access_key='{opcoes['secret']}'",
        "SET s3_url_style='path'",
        "SET s3_region='auto'",
    ]


def conectar(*uris: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    s3 = next((uri for uri in uris if uri.startswith("s3://")), None)
    if s3:
        for pragma in pragmas_s3(s3):
            con.execute(pragma)
    return con


def json_para_parquet(origem: Origem, destino: str | Path) -> int:
    """Converte JSON (arquivo, glob ou lista) em parquet zstd e devolve o nº de linhas."""
    caminhos = [origem] if isinstance(origem, str | Path) else list(origem)
    origens = [_posix(caminho) for caminho in caminhos]
    destino = _posix(destino)

    if not destino.startswith("s3://"):
        Path(destino).parent.mkdir(parents=True, exist_ok=True)

    fonte_sql = (
        f"'{origens[0]}'" if len(origens) == 1 else "[" + ", ".join(f"'{o}'" for o in origens) + "]"
    )
    con = conectar(destino, *origens)
    con.execute(
        f"""
        COPY (SELECT * FROM read_json_auto({fonte_sql}))
        TO '{destino}' (FORMAT parquet, COMPRESSION zstd)
        """
    )
    (linhas,) = con.sql(f"SELECT count(*) FROM '{destino}'").fetchone()
    return linhas
