"""Abstração de storage local ↔ Cloudflare R2.

A raiz vem de PRACA_DATA_ROOT (`data/` local por padrão; `s3://bucket` na cloud).
Nenhum pipeline monta caminho na mão — sempre via `uri()`.
"""

import os
from datetime import date

import fsspec

from pipelines.common.config import RAIZ


def raiz(camada: str | None = None) -> str:
    """Raiz da camada. A raw tem raiz própria porque mora em outro bucket.

    Topologia da ARQUITETURA §2: `praca-raw` guarda só `raw/` (token de escrita
    escopado nele) e `praca-dados` guarda staging/marts/serving. Local, sem
    PRACA_RAW_ROOT, tudo compartilha a mesma pasta.
    """
    if camada == "raw":
        propria = os.environ.get("PRACA_RAW_ROOT")
        if propria:
            return propria
    return os.environ.get("PRACA_DATA_ROOT") or str(RAIZ / "data")


def uri(camada: str, *partes: str) -> str:
    return "/".join([raiz(camada).rstrip("/\\"), camada, *partes])


def caminho_raw(fonte: str, *partes: str, coleta: date | None = None) -> str:
    """`raw/{fonte}/{AAAA-MM-DD}/...` — cada coleta em sua pasta (regra 6: raw é imutável)."""
    return uri("raw", fonte, (coleta or date.today()).isoformat(), *partes)


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


def listar(padrao: str) -> list[str]:
    """Expande um glob e devolve URIs completas (o fsspec devolve o caminho sem esquema)."""
    fs, caminho = _fs(padrao)
    prefixo = "s3://" if padrao.startswith("s3://") else ""
    return sorted(prefixo + achado for achado in fs.glob(caminho))


def coletas_mais_recentes(fonte: str, *partes: str) -> list[str]:
    """A versão mais nova de cada arquivo da raw, varrendo todas as datas de coleta.

    A raw acumula uma pasta por dia; o staging precisa do último estado de cada
    arquivo — sem perder o que foi coletado antes e não voltou a aparecer.
    """
    marcador = f"/raw/{fonte}/"
    recentes: dict[str, tuple[str, str]] = {}
    for achado in listar(uri("raw", fonte, "*", *partes)):
        _, _, resto = achado.replace("\\", "/").partition(marcador)
        coleta, _, chave = resto.partition("/")
        if not chave:
            continue
        if chave not in recentes or coleta > recentes[chave][0]:
            recentes[chave] = (coleta, achado)
    return [recentes[chave][1] for chave in sorted(recentes)]
