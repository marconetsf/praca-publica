"""TDD: contrato dos workflows do Actions.

Workflow quebrado só aparece em produção, às 03:00, quando ninguém está olhando —
então as convenções da OPERACAO.md viram teste.
"""

import re

import pytest
import yaml

from pipelines.common.config import RAIZ

DIRETORIO = RAIZ / ".github" / "workflows"
SHA_DE_ACTION = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}(\s+#.*)?$")


def _carregar(caminho):
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def _gatilhos(workflow: dict) -> dict:
    # PyYAML interpreta a chave `on:` como o booleano True
    return workflow.get("on") or workflow.get(True) or {}


def _passos(workflow: dict):
    for job in workflow.get("jobs", {}).values():
        yield from job.get("steps", [])


TODOS = sorted(DIRETORIO.glob("*.yml"))
AGENDADOS = [caminho for caminho in TODOS if "schedule" in _gatilhos(_carregar(caminho))]


@pytest.mark.parametrize("caminho", TODOS, ids=lambda c: c.name)
def test_workflow_e_yaml_valido_com_jobs(caminho):
    workflow = _carregar(caminho)
    assert workflow.get("jobs"), f"{caminho.name} não declara jobs"


@pytest.mark.parametrize("caminho", TODOS, ids=lambda c: c.name)
def test_actions_pinnadas_por_sha(caminho):
    """Tag móvel (@v4) é superfície de supply chain: o autor pode reapontá-la."""
    for passo in _passos(_carregar(caminho)):
        usa = passo.get("uses")
        if usa:
            assert SHA_DE_ACTION.match(usa), f"{caminho.name}: '{usa}' não está pinnada por SHA"


def test_existe_workflow_de_ingestao_siconfi_agendado():
    assert AGENDADOS, "nenhum workflow agendado — M0.6 exige o SICONFI rodando sozinho"
    nomes = " ".join(caminho.name for caminho in AGENDADOS)
    assert "ingest" in nomes


@pytest.mark.parametrize("caminho", AGENDADOS, ids=lambda c: c.name)
def test_agendado_tem_concurrency(caminho):
    """Duas execuções simultâneas corromperiam o manifesto compartilhado no R2."""
    workflow = _carregar(caminho)
    assert workflow.get("concurrency"), f"{caminho.name} não declara concurrency"
    assert workflow["concurrency"].get("cancel-in-progress") is False


@pytest.mark.parametrize("caminho", AGENDADOS, ids=lambda c: c.name)
def test_agendado_avisa_no_telegram_quando_falha(caminho):
    """OPERACAO §1: todo workflow agendado tem if: failure() → Telegram."""
    passos = list(_passos(_carregar(caminho)))
    assert any("failure()" in str(passo.get("if", "")) for passo in passos), (
        f"{caminho.name} não tem passo condicionado a failure()"
    )


@pytest.mark.parametrize("caminho", AGENDADOS, ids=lambda c: c.name)
def test_agendado_escreve_nos_buckets_de_producao(caminho):
    """Só a main via Actions escreve no R2 (OPERACAO §5) — e nos buckets certos."""
    workflow = _carregar(caminho)
    ambiente = {**workflow.get("env", {})}
    for job in workflow.get("jobs", {}).values():
        ambiente.update(job.get("env", {}))
    assert ambiente.get("PRACA_RAW_ROOT", "").startswith("s3://")
    assert ambiente.get("PRACA_DATA_ROOT", "").startswith("s3://")
    assert ambiente["PRACA_RAW_ROOT"] != ambiente["PRACA_DATA_ROOT"]


@pytest.mark.parametrize("caminho", AGENDADOS, ids=lambda c: c.name)
def test_agendado_recebe_as_credenciais_do_r2(caminho):
    conteudo = caminho.read_text(encoding="utf-8")
    for segredo in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"):
        assert f"secrets.{segredo}" in conteudo, f"{caminho.name} não recebe {segredo}"
