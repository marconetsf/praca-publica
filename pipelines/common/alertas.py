"""Alertas via Telegram. Um alerta que falha NUNCA pode derrubar o pipeline."""

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import requests

ICONES = {"CRITICO": "🔴", "AVISO": "🟡", "INFO": "ℹ️"}


def alertar(mensagem: str, severidade: str = "INFO") -> bool:
    """Envia alerta ao canal de operações. Devolve False (sem levantar) se não conseguir."""
    if severidade not in ICONES:
        raise ValueError(f"Severidade inválida: {severidade} (use {sorted(ICONES)})")

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    texto = f"{ICONES[severidade]} {severidade} — {mensagem}"

    if not (token and chat_id):
        print(f"[alerta não enviado: Telegram não configurado] {texto}", file=sys.stderr)
        return False

    try:
        resposta = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": texto},
            timeout=10,
        )
        return resposta.status_code == 200
    except requests.RequestException as exc:
        print(f"[alerta não enviado: {exc}] {texto}", file=sys.stderr)
        return False


@contextmanager
def falhas_alertadas(contexto: str) -> Iterator[None]:
    """Avisa no canal de operações quando o bloco falha, sem engolir a exceção.

    Só alerta em falha: alerta de rotina vira ruído e o operador para de olhar o canal.
    KeyboardInterrupt fica de fora — é o operador desistindo, não incidente.
    """
    try:
        yield
    except KeyboardInterrupt:
        raise
    except BaseException as exc:  # inclui SystemExit, com que os pipelines abortam
        try:
            alertar(f"{contexto} falhou: {type(exc).__name__}: {exc}", severidade="CRITICO")
        except Exception as falha_do_alerta:  # noqa: BLE001 — o erro original é o que importa
            print(f"[alerta não enviado: {falha_do_alerta}]", file=sys.stderr)
        raise
