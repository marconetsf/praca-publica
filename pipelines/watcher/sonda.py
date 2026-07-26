"""Watcher v1: vigia disponibilidade e mudança de conteúdo das fontes do YAML.

Nunca acoplado aos ingests (OPERACAO §1): o watcher precisa continuar rodando
justamente quando um pipeline está quebrado. Por isso ele não importa nada de
`pipelines/siconfi/` e nenhuma fonte quebrada derruba a varredura das outras.

O que ele responde: "a fonte ainda está de pé?" e "o dado mudou desde ontem?".
Fingerprint de schema e hash de listagem de diretório são o v2 (M1.8).

Uso: python -m pipelines.watcher.sonda
"""

import json
from datetime import UTC, datetime

import requests

from pipelines.common import storage, tls
from pipelines.common.alertas import alertar
from pipelines.common.config import fontes as carregar_fontes

ARQUIVO_ESTADO = "watcher_state.json"
TIMEOUT = 20
# uma indisponibilidade isolada em servidor público é rotina; alertar seria ruído
FALHAS_PARA_ALERTAR = 2


def caminho_estado() -> str:
    return storage.uri("catalog", ARQUIVO_ESTADO)


def alvos_de_sonda(fontes: dict) -> dict[str, dict]:
    """A sonda declarada de cada fonte: `{nome: {url, status_ok}}`.

    Sondar `api_base` cru não funciona: metade do catálogo são prefixos para
    montar URL (404) ou endpoints que exigem token (401). O YAML declara qual
    endereço representa a fonte e quais status significam "de pé".
    """
    alvos = {}
    for fonte, config in fontes.items():
        sonda_declarada = (config or {}).get("sonda") if isinstance(config, dict) else None
        if not sonda_declarada or not sonda_declarada.get("url"):
            continue  # sem sonda = não vigiada (FTP, ou precisa de POST autenticado)
        alvos[fonte] = {
            "url": sonda_declarada["url"],
            "status_ok": list(sonda_declarada.get("status_ok") or []),
            "detectar_mudanca": sonda_declarada.get("detectar_mudanca", True),
            # cadeia TLS incompleta na origem não pode virar "fonte caiu"
            "ca": config.get("tls_ca"),
        }
    return alvos


def _requisitar_real(metodo: str, url: str, ca: str | None = None, **kwargs) -> requests.Response:
    from pipelines.common.http import UA

    cabecalhos = {"User-Agent": UA, **kwargs.pop("headers", {})}
    return requests.request(
        metodo,
        url,
        headers=cabecalhos,
        timeout=TIMEOUT,
        allow_redirects=True,
        verify=tls.bundle(ca),
        **kwargs,
    )


def sondar(
    url: str, *, status_ok: list[int] | None = None, ca: str | None = None, requisitar=None
) -> dict:
    """Um HEAD por URL; onde HEAD é bloqueado, GET pedindo só o primeiro byte."""
    if requisitar is None:

        def requisitar(metodo, url, **kwargs):
            return _requisitar_real(metodo, url, ca=ca, **kwargs)

    try:
        resposta = requisitar("HEAD", url)
        if resposta.status_code in (403, 405, 501):
            resposta = requisitar("GET", url, headers={"Range": "bytes=0-0"})
    except Exception as exc:  # noqa: BLE001 — qualquer falha de rede vira estado, não crash
        return {
            "status": None,
            "ok": False,
            "etag": None,
            "last_modified": None,
            "content_length": None,
            "erro": f"{type(exc).__name__}: {exc}",
        }

    cabecalhos = resposta.headers
    return {
        "status": resposta.status_code,
        "ok": _status_aceito(resposta.status_code, status_ok),
        "etag": cabecalhos.get("ETag"),
        "last_modified": cabecalhos.get("Last-Modified"),
        "content_length": cabecalhos.get("Content-Length"),
        "erro": None,
    }


def _status_aceito(status: int, status_ok: list[int] | None) -> bool:
    if status_ok:
        return status in status_ok
    return 200 <= status < 400


def disponivel(sondagem: dict) -> bool:
    return bool(sondagem.get("ok"))


def assinatura(sondagem: dict) -> tuple:
    return (
        sondagem.get("etag"),
        sondagem.get("last_modified"),
        sondagem.get("content_length"),
    )


def comparar(
    nome: str, anterior: dict | None, atual: dict, *, detectar_mudanca: bool = True
) -> list[tuple[str, str]]:
    """Eventos (severidade, mensagem) desta sondagem. Função pura."""
    if anterior is None:
        return []  # linha de base: sem passado não há mudança

    falhas = anterior.get("falhas_consecutivas", 0)

    if not disponivel(atual):
        if falhas + 1 >= FALHAS_PARA_ALERTAR:
            detalhe = atual.get("erro") or f"HTTP {atual.get('status')}"
            return [("AVISO", f"{nome} indisponível há {falhas + 1} sondagens ({detalhe})")]
        return []

    if falhas >= FALHAS_PARA_ALERTAR:  # só fecha o loop de um alerta que saiu
        return [("INFO", f"{nome} voltou a responder")]

    if detectar_mudanca and disponivel(anterior) and assinatura(anterior) != assinatura(atual):
        return [("AVISO", f"{nome} mudou — dado novo disponível")]

    return []


def proximo_estado(anterior: dict | None, atual: dict) -> dict:
    falhas = 0 if disponivel(atual) else (anterior or {}).get("falhas_consecutivas", 0) + 1
    return {
        **atual,
        "falhas_consecutivas": falhas,
        "visto_em": datetime.now(UTC).isoformat(),
    }


def _carregar_estado() -> dict:
    destino = caminho_estado()
    if not storage.existe(destino):
        return {}
    return json.loads(storage.ler_bytes(destino).decode("utf-8"))


def _salvar_estado(estado: dict) -> None:
    conteudo = json.dumps(estado, ensure_ascii=False, indent=2, sort_keys=True)
    storage.escrever_bytes(caminho_estado(), conteudo.encode("utf-8"))


def executar(*, fontes: dict | None = None, requisitar=None) -> dict:
    """Sonda todas as fontes, alerta as mudanças e persiste o estado."""
    alvos = alvos_de_sonda(fontes if fontes is not None else carregar_fontes())
    estado = _carregar_estado()
    indisponiveis = 0

    for nome, alvo in alvos.items():
        atual = sondar(
            alvo["url"], status_ok=alvo["status_ok"], ca=alvo["ca"], requisitar=requisitar
        )
        eventos = comparar(nome, estado.get(nome), atual, detectar_mudanca=alvo["detectar_mudanca"])
        for severidade, mensagem in eventos:
            alertar(mensagem, severidade=severidade)
        estado[nome] = proximo_estado(estado.get(nome), atual)
        if not disponivel(atual):
            indisponiveis += 1
            print(f"  indisponível: {nome} -> {atual.get('erro') or atual.get('status')}")

    _salvar_estado(estado)
    return {"sondadas": len(alvos), "indisponiveis": indisponiveis}


def main() -> None:
    resumo = executar()
    print(f"{resumo['sondadas']} fontes sondadas, {resumo['indisponiveis']} indisponíveis")


if __name__ == "__main__":
    main()
