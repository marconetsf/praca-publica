"""Acesso centralizado a config/fontes.yaml e aos caminhos do projeto."""

from functools import lru_cache

import yaml

from pipelines.common import RAIZ  # importar o pacote já carrega o .env

CONFIG = RAIZ / "config" / "fontes.yaml"
# Caminhos de dados vivem em storage.py (uri/caminho_raw): montar Path aqui faria
# o pipeline escrever no disco local mesmo com PRACA_DATA_ROOT apontando para o R2.


@lru_cache(maxsize=1)
def fontes() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def fonte(nome: str) -> dict:
    try:
        return fontes()[nome]
    except KeyError:
        raise KeyError(f"Fonte '{nome}' não existe em {CONFIG}") from None
