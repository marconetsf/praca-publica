"""GET com retry exponencial e throttle — servidores governamentais caem com frequência."""

import time

import requests

TIMEOUT_PADRAO = 60
UA = "praca-publica/0.1 (projeto de dados abertos; contato via repositório)"


def get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    tentativas: int = 5,
    backoff: float = 2.0,
    throttle_s: float = 0.0,
    timeout: int = TIMEOUT_PADRAO,
) -> requests.Response:
    headers = {"User-Agent": UA, **(headers or {})}
    ultima_exc: Exception | None = None
    for tentativa in range(tentativas):
        if throttle_s:
            time.sleep(throttle_s)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # 4xx (exceto 429) não melhora repetindo
            if status is not None and 400 <= status < 500 and status != 429:
                raise
            ultima_exc = exc
            time.sleep(backoff**tentativa)
    raise ultima_exc  # type: ignore[misc]
