"""Isolamento entre testes.

O `.env` do desenvolvedor é carregado por config.py e pode apontar para o R2 —
a suíte precisa ser determinística e nunca tocar a cloud, então as raízes de
storage são neutralizadas: quem precisa delas as define explicitamente.
"""

import pytest

from pipelines.common import manifest

RAIZES = ("PRACA_DATA_ROOT", "PRACA_RAW_ROOT")


@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    for variavel in RAIZES:
        monkeypatch.delenv(variavel, raising=False)
    manifest.recarregar()  # o manifesto é cacheado em módulo
    yield
    manifest.recarregar()
