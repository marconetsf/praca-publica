"""Acesso centralizado a config/fontes.yaml e aos caminhos do projeto."""

from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")  # credenciais locais (gitignored); no CI vêm de Secrets
CONFIG = RAIZ / "config" / "fontes.yaml"
RAW = RAIZ / "data" / "raw"
STAGING = RAIZ / "data" / "staging"
MARTS = RAIZ / "data" / "marts"


@lru_cache(maxsize=1)
def fontes() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def fonte(nome: str) -> dict:
    try:
        return fontes()[nome]
    except KeyError:
        raise KeyError(f"Fonte '{nome}' não existe em {CONFIG}") from None
