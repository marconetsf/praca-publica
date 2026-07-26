"""Caracterização do GET com retry — sem tocar a rede."""

import pytest
import requests

from pipelines.common import http


class _RespostaFake:
    def __init__(self, status_code: int):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            erro = requests.HTTPError(f"{self.status_code}")
            erro.response = self
            raise erro


@pytest.fixture(autouse=True)
def _sem_sleep(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda _s: None)


def test_sucesso_apos_falhas_de_conexao(monkeypatch):
    chamadas = []

    def get_fake(url, **kwargs):
        chamadas.append(url)
        if len(chamadas) < 3:
            raise requests.ConnectionError("caiu")
        return _RespostaFake(200)

    monkeypatch.setattr(http.requests, "get", get_fake)
    resposta = http.get("http://fonte.gov.br")
    assert resposta.status_code == 200
    assert len(chamadas) == 3


def test_404_nao_e_repetido(monkeypatch):
    chamadas = []

    def get_fake(url, **kwargs):
        chamadas.append(url)
        return _RespostaFake(404)

    monkeypatch.setattr(http.requests, "get", get_fake)
    with pytest.raises(requests.HTTPError):
        http.get("http://fonte.gov.br")
    assert len(chamadas) == 1


def test_429_e_repetido(monkeypatch):
    chamadas = []

    def get_fake(url, **kwargs):
        chamadas.append(url)
        if len(chamadas) == 1:
            return _RespostaFake(429)
        return _RespostaFake(200)

    monkeypatch.setattr(http.requests, "get", get_fake)
    assert http.get("http://fonte.gov.br").status_code == 200
    assert len(chamadas) == 2


def test_erro_persistente_estoura_apos_tentativas(monkeypatch):
    chamadas = []

    def get_fake(url, **kwargs):
        chamadas.append(url)
        return _RespostaFake(500)

    monkeypatch.setattr(http.requests, "get", get_fake)
    with pytest.raises(requests.HTTPError):
        http.get("http://fonte.gov.br", tentativas=3)
    assert len(chamadas) == 3


def test_user_agent_padrao_presente(monkeypatch):
    capturado = {}

    def get_fake(url, params=None, headers=None, timeout=None):
        capturado["headers"] = headers
        return _RespostaFake(200)

    monkeypatch.setattr(http.requests, "get", get_fake)
    http.get("http://fonte.gov.br")
    assert "praca-publica" in capturado["headers"]["User-Agent"]
