"""TDD: alertas Telegram — nunca podem derrubar um pipeline."""

import pytest
import requests

from pipelines.common import alertas


class _RespostaFake:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


@pytest.fixture(autouse=True)
def _credenciais(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")


def test_sem_credenciais_retorna_false_sem_tocar_a_rede(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    monkeypatch.delenv("TELEGRAM_CHAT_ID")
    chamadas = []
    monkeypatch.setattr(alertas.requests, "post", lambda *a, **k: chamadas.append(1))
    assert alertas.alertar("oi") is False
    assert chamadas == []


def test_envia_com_prefixo_de_severidade(monkeypatch):
    capturado = {}

    def post_fake(url, json=None, timeout=None):
        capturado["url"] = url
        capturado["json"] = json
        return _RespostaFake(200)

    monkeypatch.setattr(alertas.requests, "post", post_fake)
    assert alertas.alertar("pipeline falhou", severidade="CRITICO") is True
    assert "bottok123/sendMessage" in capturado["url"]
    assert capturado["json"]["chat_id"] == "999"
    assert capturado["json"]["text"].startswith("🔴 CRITICO")
    assert "pipeline falhou" in capturado["json"]["text"]


def test_severidade_padrao_e_info(monkeypatch):
    capturado = {}
    monkeypatch.setattr(
        alertas.requests,
        "post",
        lambda url, json=None, timeout=None: capturado.update(json=json) or _RespostaFake(),
    )
    alertas.alertar("resumo diário")
    assert capturado["json"]["text"].startswith("ℹ️ INFO")


def test_severidade_invalida_levanta_valueerror():
    with pytest.raises(ValueError, match="URGENTE"):
        alertas.alertar("x", severidade="URGENTE")


def test_falha_de_rede_nao_estoura(monkeypatch):
    def post_explosivo(*a, **k):
        raise requests.ConnectionError("telegram fora do ar")

    monkeypatch.setattr(alertas.requests, "post", post_explosivo)
    assert alertas.alertar("mensagem") is False


def test_resposta_nao_200_retorna_false(monkeypatch):
    monkeypatch.setattr(alertas.requests, "post", lambda *a, **k: _RespostaFake(status_code=401))
    assert alertas.alertar("mensagem") is False
