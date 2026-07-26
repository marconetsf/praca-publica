"""Caracterização do acesso à config de fontes."""

import pytest

from pipelines.common import config


def test_fonte_siconfi_tem_api_base():
    cfg = config.fonte("siconfi")
    assert cfg["api_base"].startswith("https://apidatalake.tesouro.gov.br")
    assert cfg["throttle_s"] > 0


def test_fonte_inexistente_levanta_keyerror_com_nome():
    with pytest.raises(KeyError, match="nao_existe"):
        config.fonte("nao_existe")


def test_todas_as_fontes_do_catalogo_carregam():
    fontes = config.fontes()
    assert "cnpj_rfb" in fontes
    assert "pncp" in fontes
