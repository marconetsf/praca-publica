"""Smoke test contra a API real — roda só com `pytest -m live` (nunca no CI)."""

import pytest

from pipelines.siconfi.api import paginar


@pytest.mark.live
def test_primeira_pagina_de_entes_responde():
    itens = paginar("entes")
    assert len(itens) > 5000
    assert any(e["ente"] == "Petrolina" for e in itens)
