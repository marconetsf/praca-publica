"""Promoção JSON → parquet (zstd), o passo padrão raw → staging."""

from pathlib import Path

import duckdb


def json_para_parquet(origem: Path | str, destino: Path) -> int:
    """Converte JSON (arquivo ou glob) em parquet zstd e devolve o nº de linhas."""
    origem = Path(origem)
    destino.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (SELECT * FROM read_json_auto('{origem.as_posix()}'))
        TO '{destino.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
        """
    )
    (linhas,) = con.sql(f"SELECT count(*) FROM '{destino.as_posix()}'").fetchone()
    return linhas
