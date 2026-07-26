"""TDD: o .env precisa carregar em qualquer entrada do pacote.

Bug real: `load_dotenv` morava só em config.py, então um módulo que não
importasse config (dadosgov) rodava sem as credenciais e acusava chave ausente
mesmo com ela no .env. Carregar no __init__ do pacote elimina a classe inteira
do problema, em vez de remendar módulo a módulo.
"""

import importlib

import dotenv

import pipelines.common


def test_importar_o_pacote_carrega_o_env(monkeypatch):
    chamadas = []
    # patch na origem: o reload refaz `from dotenv import load_dotenv` e
    # desfaria um patch aplicado no próprio pipelines.common
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: chamadas.append(a))

    importlib.reload(pipelines.common)

    assert chamadas, "importar pipelines.common precisa carregar o .env"
    assert str(chamadas[0][0]).endswith(".env")


def test_todo_modulo_executavel_alcanca_o_env():
    """Qualquer `python -m pipelines.*` passa pelo __init__ do pacote common."""
    for caminho in (
        "pipelines.espelho.dadosgov",
        "pipelines.espelho.espelhar",
        "pipelines.watcher.sonda",
        "pipelines.siconfi.ingest_entes",
        "pipelines.siconfi.ingest_dca",
    ):
        modulo = importlib.import_module(caminho)
        assert modulo is not None
