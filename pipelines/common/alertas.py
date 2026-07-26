"""Alertas via Telegram. Um alerta que falha NUNCA pode derrubar o pipeline."""

import os
import sys

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
