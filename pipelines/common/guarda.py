"""O que se guarda de cada fonte — a declaração que o `fontes.yaml` passa a exigir.

Integrar base nova sempre esbarra na mesma pergunta: *"precisamos baixar isso?"*.
A resposta curta é que **computar não exige cópia, publicar exige** — e o que
precisa estar guardado é o insumo do número publicado, não o acervo do órgão.
Confundir os dois é o que faz o storage virar gargalo: guardar o PNCP inteiro
custaria 57,7 GB por ano para sustentar zero indicadores.

Daí os cinco modos. Quatro guardam alguma coisa e podem sustentar publicação; um
não guarda nada e por isso **não pode publicar**:

    integral   os bytes originais inteiros           (fonte que pode sumir)
    recorte    só a fatia que alimenta um indicador  (acervo grande demais)
    colheita   as respostas de cada execução da API  (fonte com filtro)
    remota     nada — leitura por httpfs             (só reconhecimento)
    nenhuma    nada, e o motivo escrito              (inacessível, ou sem uso)

A fronteira de `remota` é o que fecha a conta da auditoria: como ela nunca
publica, não existe número cujo insumo esteja fora do nosso alcance. Ler um
parquet remoto para decidir se a fonte serve custa zero byte e é legítimo; ler
para publicar seria vender auditabilidade por economia de disco.

O motivo é obrigatório em tudo que não é `integral`: recusa sem motivo escrito
volta como proposta nova a cada seis meses.
"""

from dataclasses import dataclass, field

MODOS_COM_COPIA = ("integral", "recorte", "colheita")
MODOS_SEM_COPIA = ("remota", "nenhuma")
MODOS = MODOS_COM_COPIA + MODOS_SEM_COPIA

RISCOS = ("alto", "medio", "baixo")
ONDE = ("actions", "brasil", "vps", "nenhum")


@dataclass(frozen=True)
class Guarda:
    """A declaração lida do YAML, já validada."""

    modo: str
    medido_em: str
    motivo: str
    risco_sumico: str = "baixo"
    onde: str = "actions"
    volume_gb: float | None = None
    recorte: dict = field(default_factory=dict)


def ler(config: dict) -> Guarda:
    """Lê e valida o bloco `guarda:` de uma fonte. Levanta ValueError se inválido."""
    bruto = (config or {}).get("guarda") or {}

    modo = bruto.get("modo")
    if modo not in MODOS:
        raise ValueError(f"modo de guarda inválido: {modo!r} (esperado um de {MODOS})")

    medido_em = bruto.get("medido_em")
    if not medido_em:
        # volume sem data de medição é chute com aparência de fato
        raise ValueError("guarda sem `medido_em`: medida sem data não é medida")

    motivo = (bruto.get("motivo") or "").strip()
    if modo != "integral" and not motivo:
        raise ValueError(f"guarda em modo {modo!r} exige `motivo:` escrito")

    risco = bruto.get("risco_sumico", "baixo")
    if risco not in RISCOS:
        raise ValueError(f"risco_sumico inválido: {risco!r}")

    onde = bruto.get("onde", "actions")
    if onde not in ONDE:
        raise ValueError(f"onde inválido: {onde!r}")

    return Guarda(
        modo=modo,
        medido_em=str(medido_em),
        motivo=motivo,
        risco_sumico=risco,
        onde=onde,
        volume_gb=bruto.get("volume_gb"),
        recorte=bruto.get("recorte") or {},
    )


def pode_publicar(declarada: Guarda) -> bool:
    """Esta fonte pode sustentar um número no site?

    Só se guardamos o insumo. `remota` e `nenhuma` servem para decidir e para
    documentar — nunca para publicar.
    """
    return declarada.modo in MODOS_COM_COPIA


def pode_colher(declarada: Guarda) -> bool:
    """O pipeline está autorizado a buscar dado desta fonte agora?

    `recorte` só colhe com indicador pactuado: é a decisão editorial de
    16/08/2026 — não escalar coleta sem métrica que responda "a cidade
    melhorou?" — virando condição que o código lê, em vez de exortação em
    documento.
    """
    if declarada.modo in MODOS_SEM_COPIA:
        return False
    if declarada.modo == "recorte":
        return bool(declarada.recorte.get("pactuado_em"))
    return True
