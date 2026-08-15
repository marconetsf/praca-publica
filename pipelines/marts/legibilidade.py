"""Mede se o texto público é legível para quem não estudou o assunto.

O PRODUTO §3 pede tom de voz nível Fundamental II, e isso vinha sendo cumprido
no olho. No olho passou uma descrição de 130 caracteres com duas subordinadas —
e contar caracteres não teria pego, porque "Quanto a prefeitura efetivamente
pagou" é curto e difícil enquanto "Escolas, merenda e transporte escolar" é
curto e fácil.

Índice: Flesch adaptado ao português (Martins et al., 1996). Ele olha duas
coisas — quão longa é a frase e quão comprida é a palavra — e nada além disso.
Não enxerga jargão, ambiguidade nem se a explicação está correta. É piso, não
teto: passar no índice não torna o texto bom, mas reprovar nele significa que
está difícil demais para o leitor que o projeto escolheu servir.
"""

import re

# O índice pressupõe texto corrido. Abaixo disto ele não vale: "Escolas, merenda
# e transporte escolar" é um fragmento nominal de 5 palavras, obviamente legível,
# e tira nota 24 porque a média de sílabas por palavra sobe sem que haja frase
# para diluí-la. Texto curto é avaliado por outro critério (tamanho e palavra
# comprida isolada), não por Flesch.
MINIMO_PALAVRAS = 12

VOGAIS = "aeiouáéíóúâêôàãõü"
# pares que formam uma sílaba só: "moradores" tem 4, não 5
DITONGOS = (
    "ai",
    "ei",
    "oi",
    "ui",
    "au",
    "eu",
    "iu",
    "ou",
    "ãe",
    "ão",
    "õe",
    "ia",
    "ie",
    "io",
    "ua",
    "ue",
    "uo",
    "áu",
    "éu",
    "ói",
    "ãi",
)


def _normalizar(palavra: str) -> str:
    return palavra.lower().strip()


def silabas(palavra: str) -> int:
    """Aproxima a contagem de sílabas por grupos vocálicos.

    Não é separação silábica de verdade — é a estimativa que o índice precisa.
    Erra em casos de hiato ("saída"), e o erro é pequeno demais para mudar a
    faixa de leitura.
    """
    texto = _normalizar(palavra)
    if not texto:
        return 0

    total = 0
    i = 0
    while i < len(texto):
        if texto[i] in VOGAIS:
            total += 1
            # consome o resto do grupo vocálico
            par = texto[i : i + 2]
            if par in DITONGOS:
                i += 2
            else:
                i += 1
            while i < len(texto) and texto[i] in VOGAIS:
                # comparar COM acento: "aú" (sa-ú-de) é hiato, "au" (au-la) é
                # ditongo. Normalizar antes tornaria os dois iguais e comeria
                # uma sílaba de toda palavra com i/u acentuado.
                if texto[i - 1 : i + 1] in DITONGOS:
                    i += 1
                else:
                    break
        else:
            i += 1

    return max(1, total)


def palavras(texto: str) -> list[str]:
    return [p for p in re.findall(r"[^\W\d_]+", texto, flags=re.UNICODE) if p]


def frases(texto: str) -> int:
    """Conta por pontuação final; texto sem ponto conta como uma frase."""
    if not texto.strip():
        return 0
    encontradas = [t for t in re.split(r"[.!?]+", texto) if t.strip()]
    return max(1, len(encontradas))


def mensuravel(texto: str) -> bool:
    """O índice vale para este texto? Fragmento curto não é medível por Flesch."""
    return len(palavras(texto)) >= MINIMO_PALAVRAS


def indice(texto: str) -> float:
    """Flesch adaptado ao português. Quanto maior, mais fácil."""
    lista = palavras(texto)
    total_frases = frases(texto)
    if not lista or not total_frases:
        return 0.0

    por_frase = len(lista) / total_frases
    por_palavra = sum(silabas(p) for p in lista) / len(lista)
    return 248.835 - 1.015 * por_frase - 84.6 * por_palavra


def diagnosticar(texto: str) -> str:
    """Diz o que está pesando, para o teste não falhar sem apontar o conserto."""
    lista = palavras(texto)
    total_frases = frases(texto)
    if not lista or not total_frases:
        return "texto vazio"

    por_frase = len(lista) / total_frases
    por_palavra = sum(silabas(p) for p in lista) / len(lista)

    problemas = []
    if por_frase > 20:
        problemas.append(f"frase longa demais ({por_frase:.0f} palavras; corte em duas)")
    if por_palavra > 2.2:
        compridas = sorted(lista, key=silabas, reverse=True)[:3]
        problemas.append(
            f"palavras compridas ({por_palavra:.1f} sílabas por palavra; "
            f"as piores: {', '.join(compridas)})"
        )
    return "; ".join(problemas) or f"{por_frase:.0f} palavras/frase, {por_palavra:.1f} sílabas"
