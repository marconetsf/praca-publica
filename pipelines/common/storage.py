"""Abstração de storage local ↔ Cloudflare R2.

A raiz vem de PRACA_DATA_ROOT (`data/` local por padrão; `s3://bucket` na cloud).
Nenhum pipeline monta caminho na mão — sempre via `uri()`.
"""

import os

import fsspec

from pipelines.common.config import RAIZ


def raiz() -> str:
    return os.environ.get("PRACA_DATA_ROOT") or str(RAIZ / "data")


def uri(camada: str, *partes: str) -> str:
    return "/".join([raiz().rstrip("/\\"), camada, *partes])


def opcoes_fs(destino: str) -> dict:
    """Storage options do fsspec para o destino; R2 exige credenciais no ambiente."""
    if not destino.startswith("s3://"):
        return {}
    conta = os.environ.get("R2_ACCOUNT_ID")
    chave = os.environ.get("R2_ACCESS_KEY_ID")
    segredo = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not (conta and chave and segredo):
        raise RuntimeError(
            "Destino s3:// exige R2_ACCOUNT_ID, R2_ACCESS_KEY_ID e R2_SECRET_ACCESS_KEY "
            "no ambiente (ver .env.example)"
        )
    return {
        "key": chave,
        "secret": segredo,
        "client_kwargs": {"endpoint_url": f"https://{conta}.r2.cloudflarestorage.com"},
    }


def _fs(destino: str):
    return fsspec.core.url_to_fs(destino, **opcoes_fs(destino))


def escrever_bytes(destino: str, dados: bytes) -> None:
    fs, caminho = _fs(destino)
    fs.makedirs(fs._parent(caminho), exist_ok=True)
    with fs.open(caminho, "wb") as f:
        f.write(dados)


def ler_bytes(destino: str) -> bytes:
    fs, caminho = _fs(destino)
    with fs.open(caminho, "rb") as f:
        return f.read()


def existe(destino: str) -> bool:
    fs, caminho = _fs(destino)
    return fs.exists(caminho)
