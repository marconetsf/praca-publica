"""Manifesto de downloads: dá idempotência aos pipelines.

Cada item baixado/processado é registrado por chave; re-execuções pulam o que já consta.

Registro **completo** (o dado veio) vale para sempre. Registro **incompleto** (a fonte
não tinha o dado ainda) vale só durante a *janela de captura*: passada a janela, a chave
volta a ser consultada. Sem isso, um município que entrega a DCA com atraso ficaria
marcado como processado para sempre e nunca entraria no staging.

O manifesto mora na raiz do storage (`PRACA_DATA_ROOT`), então acompanha o dado quando
o pipeline roda na cloud. Como é um arquivo só, ele é lido uma vez por execução e
mantido em cache; laços longos devem usar `registrar(..., salvar=False)` e chamar
`salvar()` no fim, para não fazer um PUT por município.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipelines.common import storage

JANELA_PADRAO_DIAS = 30

_cache: dict[str, dict] = {}


def caminho() -> str:
    return storage.uri("catalog", "manifest.json")


def recarregar() -> None:
    """Descarta o cache — use se o manifesto foi alterado por fora."""
    _cache.clear()


def _carregar() -> dict:
    destino = caminho()
    if destino not in _cache:
        if storage.existe(destino):
            _cache[destino] = json.loads(storage.ler_bytes(destino).decode("utf-8"))
        else:
            _cache[destino] = {}
    return _cache[destino]


def salvar() -> None:
    destino = caminho()
    conteudo = json.dumps(_carregar(), ensure_ascii=False, indent=2)
    storage.escrever_bytes(destino, conteudo.encode("utf-8"))


def ja_processado(
    chave: str,
    *,
    janela_dias: int = JANELA_PADRAO_DIAS,
    agora: datetime | None = None,
) -> bool:
    registro = _carregar().get(chave)
    if registro is None:
        return False
    if registro.get("completo", True):  # registros antigos não tinham o campo
        return True
    idade = (agora or datetime.now(UTC)) - datetime.fromisoformat(registro["registrado_em"])
    return idade < timedelta(days=janela_dias)


def registrar(chave: str, *, completo: bool = True, salvar_agora: bool = True, **meta) -> None:
    """Registra a chave. `completo=False` marca lacuna provisória (ver janela de captura)."""
    _carregar()[chave] = {
        "registrado_em": datetime.now(UTC).isoformat(),
        "completo": completo,
        **meta,
    }
    if salvar_agora:
        salvar()


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def sha256_arquivo(caminho_arquivo: Path) -> str:
    h = hashlib.sha256()
    with open(caminho_arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()
