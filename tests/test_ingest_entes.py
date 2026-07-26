"""TDD: orquestração do ingest de entes sobre storage (raw datada + manifesto)."""

import json
from datetime import date

import pytest

from pipelines.common import manifest, storage
from pipelines.siconfi import ingest_entes

COLETA = date(2026, 7, 26)


def _entes(quantidade: int) -> list[dict]:
    return [
        {"cod_ibge": 2600000 + i, "ente": f"Município {i}", "uf": "PE", "esfera": "M"}
        for i in range(quantidade)
    ]


def _buscador(itens: list[dict]):
    def buscar(endpoint: str, params: dict) -> dict:
        assert endpoint == "entes"
        return {"items": itens, "hasMore": False}

    return buscar


def test_grava_raw_na_pasta_datada(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    ingest_entes.executar(buscar=_buscador(_entes(5000)), coleta=COLETA)

    raw = storage.caminho_raw("siconfi", "entes.json", coleta=COLETA)
    assert storage.existe(raw)
    assert len(json.loads(storage.ler_bytes(raw).decode("utf-8"))) == 5000


def test_promove_para_staging_e_devolve_o_destino(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    destino = ingest_entes.executar(buscar=_buscador(_entes(5000)), coleta=COLETA)

    assert destino == storage.uri("staging", "siconfi", "entes.parquet")
    assert storage.existe(destino)


def test_registra_manifesto_com_hash_e_data_de_coleta(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    ingest_entes.executar(buscar=_buscador(_entes(5000)), coleta=COLETA)

    registro = json.loads(storage.ler_bytes(manifest.caminho()).decode("utf-8"))
    chave = f"siconfi/entes/{COLETA.isoformat()}"
    assert registro[chave]["registros"] == 5000
    assert len(registro[chave]["sha256"]) == 64
    assert registro[chave]["completo"] is True


def test_resposta_truncada_nao_promove_staging(monkeypatch, tmp_path):
    """Regra 4: dado suspeito falha ruidosamente e não vira staging."""
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))

    with pytest.raises(RuntimeError, match="entes"):
        ingest_entes.executar(buscar=_buscador(_entes(12)), coleta=COLETA)

    assert not storage.existe(storage.uri("staging", "siconfi", "entes.parquet"))


def test_coleta_do_dia_seguinte_nao_sobrescreve_a_anterior(monkeypatch, tmp_path):
    monkeypatch.setenv("PRACA_DATA_ROOT", str(tmp_path))
    ingest_entes.executar(buscar=_buscador(_entes(5000)), coleta=COLETA)
    ingest_entes.executar(buscar=_buscador(_entes(5001)), coleta=date(2026, 7, 27))

    ontem = storage.caminho_raw("siconfi", "entes.json", coleta=COLETA)
    assert len(json.loads(storage.ler_bytes(ontem).decode("utf-8"))) == 5000
