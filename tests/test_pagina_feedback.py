"""A página que explica como contestar um dado — e a promessa que ela não pode fazer.

O projeto ainda não tem domínio nem e-mail próprio, então **não existe canal de
envio**. Uma página que diga "avise a gente" sem dizer por onde é pior do que
não ter página: promete atendimento que ninguém vai prestar.

Por isso o canal mora num único lugar (`site/src/contato.js`) e estes testes
amarram a página a ele: enquanto o canal for `null`, nenhum e-mail ou `mailto:`
pode aparecer no site, e a página precisa dizer com todas as letras que o canal
ainda não existe. No dia em que houver endereço, muda-se uma linha — e o teste
passa a exigir o contrário.
"""

import re
from pathlib import Path

import pytest

from pipelines.common import RAIZ
from pipelines.marts import legibilidade

PISO_FACIL = 50

SITE = RAIZ / "site" / "src"
PAGINA = SITE / "pages" / "feedback.astro"
CONTATO = SITE / "contato.js"
BASE = SITE / "layouts" / "Base.astro"

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _fonte(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _paragrafos(astro: str) -> list[str]:
    """O texto visível dos <p> da página, sem tags, expressões nem frontmatter."""
    corpo = astro.split("---", 2)[-1]
    textos = []
    for bruto in re.findall(r"<p[^>]*>(.*?)</p>", corpo, re.S):
        limpo = re.sub(r"\{[^}]*\}", "", bruto)  # expressões do Astro
        limpo = re.sub(r"<[^>]+>", "", limpo)  # tags aninhadas (<a>, <strong>)
        limpo = re.sub(r"\s+", " ", limpo).strip()
        if limpo:
            textos.append(limpo)
    return textos


def canal_declarado() -> str | None:
    achado = re.search(r"CANAL_DE_CONTATO\s*=\s*(.+?);", _fonte(CONTATO))
    valor = achado.group(1).strip() if achado else "null"
    return None if valor == "null" else valor


def test_a_pagina_existe():
    assert PAGINA.exists(), "a rota /feedback precisa existir para o rodapé não quebrar"


def test_nenhum_endereco_de_email_escrito_a_mao_no_site():
    """O canal vem de `contato.js` ou não vem — nunca de um endereço solto numa página.

    Um `mailto:` escrito à mão sobrevive a `CANAL_DE_CONTATO = null` e vira
    promessa de atendimento que ninguém presta. Interpolar a constante é a única
    forma aceita: aí o site inteiro liga e desliga de um lugar só.
    """
    for arquivo in SITE.rglob("*.astro"):
        conteudo = _fonte(arquivo)
        assert not EMAIL.search(conteudo), f"{arquivo.name} tem endereço de e-mail no texto"
        for uso in re.findall(r"mailto:([^`\"'\s}]*)", conteudo):
            assert uso.startswith("${CANAL_DE_CONTATO"), (
                f"{arquivo.name} tem mailto: fora de CANAL_DE_CONTATO"
            )


def test_sem_canal_a_pagina_diz_que_o_canal_nao_existe():
    """A falta é informação: some da página seria o mesmo erro do dado ausente."""
    if canal_declarado():
        pytest.skip("com canal declarado, a página mostra o canal")
    texto = " ".join(_paragrafos(_fonte(PAGINA))).lower()
    assert "ainda não" in texto and "canal" in texto


def test_a_pagina_ensina_a_conferir_na_fonte():
    """Sem canal, o que sobra de útil é o leitor conferir sozinho — e ele consegue."""
    conteudo = _fonte(PAGINA)
    assert "/fontes" in conteudo


def test_o_rodape_leva_a_pagina():
    assert '/feedback"' in _fonte(BASE)


@pytest.mark.parametrize("paragrafo", _paragrafos(_fonte(PAGINA)) if PAGINA.exists() else [])
def test_texto_da_pagina_e_facil_de_ler(paragrafo):
    if not legibilidade.mensuravel(paragrafo):
        return
    nota = legibilidade.indice(paragrafo)
    assert nota >= PISO_FACIL, (
        f"nota {nota:.0f} — {legibilidade.diagnosticar(paragrafo)}\n{paragrafo[:90]}"
    )
