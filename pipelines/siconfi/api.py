"""Acesso à API do SICONFI: paginação offset/hasMore genérica."""

from collections.abc import Callable

from pipelines.common import http
from pipelines.common.config import fonte

Buscador = Callable[[str, dict], dict]


def _buscar_real(endpoint: str, params: dict) -> dict:
    cfg = fonte("siconfi")
    resposta = http.get(
        f"{cfg['api_base']}/{endpoint}", params=params, throttle_s=cfg["throttle_s"]
    )
    return resposta.json()


def paginar(
    endpoint: str, params: dict | None = None, *, buscar: Buscador | None = None
) -> list[dict]:
    """Percorre todas as páginas de um endpoint e devolve os items concatenados.

    `buscar` é injetável para testes; em produção usa a API real com throttle.
    """
    buscar = buscar or _buscar_real
    itens: list[dict] = []
    offset = 0
    while True:
        pagina = buscar(endpoint, {**(params or {}), "offset": offset})
        itens.extend(pagina["items"])
        if not pagina.get("hasMore"):
            return itens
        offset += pagina["limit"]
