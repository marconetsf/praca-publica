"""Manifesto de downloads: dá idempotência aos pipelines.

Cada item baixado/processado é registrado por chave; re-execuções pulam o que já consta.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pipelines.common.config import RAIZ

CAMINHO = RAIZ / "data" / "manifest.json"


def _carregar() -> dict:
    if CAMINHO.exists():
        return json.loads(CAMINHO.read_text(encoding="utf-8"))
    return {}


def ja_processado(chave: str) -> bool:
    return chave in _carregar()


def registrar(chave: str, **meta) -> None:
    manifesto = _carregar()
    manifesto[chave] = {"registrado_em": datetime.now(UTC).isoformat(), **meta}
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()
