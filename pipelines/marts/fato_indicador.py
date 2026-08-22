"""fato_indicador_municipio — o mart que a página do município consome (M2.3).

Fato longo (`município × ano × indicador`): indicador novo é INSERT, nunca
ALTER TABLE. A comparação vem junto no fato — `mediana_grupo` e `n_grupo` são
colunas, não cálculo de frontend, porque a régua do PRODUTO §2 regra 3 diz que
nenhum card existe sem valor de referência.

Três decisões que os dados reais impuseram:

1. **Anexo I-E, não I-G.** Os dois trazem "10 - Saúde", mas só o I-E tem a
   coluna "Despesas Pagas". Usar o outro publicaria número errado.
2. **Ausência não é zero** (regra 4). Município que não declarou não vira linha
   com valor 0 — não vira linha, e não entra na mediana dos outros.
3. **Grupo com menos de 5 municípios não publica mediana.** O menor grupo do
   país tem 4 (Norte acima de 500 mil); mediana de 4 não é "o típico das
   parecidas", é ruído com aparência de referência.

Uso: python -m pipelines.marts.fato_indicador --ano 2024
"""

import argparse
from dataclasses import dataclass, replace

from pipelines.common import parquet, storage
from pipelines.marts.contrato import (
    Cobertura,
    Confiabilidade,
    Contrato,
    Esfera,
    Natureza,
    Procedencia,
)

# abaixo disso a mediana do grupo é instável demais para virar referência pública
MINIMO_GRUPO = 5

# A DCA é anual e sai com cerca de um ano de atraso; o exercício 2024 foi
# publicado ao longo de 2025. Vale para todos os indicadores desta fonte.
CONTRATO_DCA = Contrato(
    cobertura=Cobertura(
        anos=(2024,),  # cresce conforme coletamos outros exercícios
        periodicidade="anual",
        defasagem_meses=12,
    ),
    confiabilidade=Confiabilidade(
        # o Tesouro publica sem auditar e ~25% das declarações têm inconsistência;
        # o gate de sanidade barra o impossível, o resto vira ressalva no card
        campo_ignorado=None,
        # o município pode retificar a DCA depois de enviada
        revisavel=True,
    ),
    procedencia=Procedencia(
        # quem informa é a própria prefeitura, que é parte interessada
        natureza=Natureza.DECLARADO,
        # orçamento municipal é responsabilidade da prefeitura, sem ambiguidade
        esfera_responsavel=Esfera.MUNICIPAL,
    ),
)


@dataclass(frozen=True)
class Conta:
    """Um endereço no DCA: o anexo, a coluna e a linha da declaração.

    Existe porque um indicador precisa apontar para **duas** dessas — a de cima
    e a de baixo da divisão — e três campos soltos por conta não caberiam mais
    na definição sem virar sopa de strings.
    """

    anexo: str
    coluna: str
    conta: str


@dataclass(frozen=True)
class Indicador:
    """Definição de um indicador — inclui a procedência, que é obrigatória.

    "Como esse cálculo foi feito?" é feature de todo número publicado, não de
    alguns. Por isso os campos de procedência moram aqui, ao lado da regra de
    cálculo: indicador novo sem eles quebra o teste antes de virar página.

    O divisor é declarado, não implícito: sem `denominador`, o valor é dividido
    pela **população** (o "por morador" do MVP); com ele, por outra conta do
    mesmo município, o que produz proporção — "de cada R$ 100 que entram, R$ 25
    são impostos da própria cidade". A segunda forma responde "isso é muito?"
    sem exigir que o leitor saiba quanto é muito.
    """

    indicador_id: str
    nome_exibicao: str
    descricao_publica: str
    unidade: str
    direcao_melhor: str  # 'maior' | 'menor' | 'neutro'
    # Em que bloco da página este número entra. Fica aqui, e não no site, porque
    # é decisão sobre o dado: 15 cards numa lista única não contam história
    # nenhuma; separados em "entra", "sai" e "por área", contam.
    grupo: str  # 'entrada' | 'saida' | 'area'
    numerador: Conta
    formula_legivel: str  # em português, para o leitor — sem jargão de banco
    ressalvas: str  # o que o leitor precisa saber antes de tirar conclusão
    # "Sem dado" tem dois sentidos que não são intercambiáveis: a prefeitura não
    # declarou, ou não houve gasto naquela área. Saneamento aparece em 244 dos
    # 443 municípios — tratar os 199 restantes como omissão acusaria metade
    # deles por engano.
    ausencia_significa: str
    # A sistemática de adoção: onde/quando a métrica existe e quando ela não é
    # confiável. Ver pipelines/marts/contrato.py — supressão, lacuna e aviso
    # saem daqui, sem `if` espalhado por indicador.
    contrato: Contrato
    # None = divide pela população. Preenchido = divide por outra conta.
    denominador: Conta | None = None
    fator: float = 1.0  # 100 transforma a razão em porcentagem
    # Teto do que é possível. Parte maior que o todo é erro de declaração, e
    # segue a regra do valor negativo: não se publica.
    valor_maximo: float | None = None
    fonte: str = "SICONFI/DCA"
    orgao: str = "Tesouro Nacional"
    # a chave da fonte em config/fontes.yaml — é o que liga este indicador à
    # ficha pública de /fontes, sem casar nomes de órgão por string
    fonte_id: str = "siconfi"
    versao_metodologia: int = 1

    @property
    def formula_sql(self) -> str:
        """A fórmula técnica, para quem quiser auditar ou reproduzir."""
        de_cima = (
            f"valor de '{self.numerador.conta}' no {self.numerador.anexo} "
            f"(coluna '{self.numerador.coluna}')"
        )
        if self.denominador is None:
            return f"{de_cima} dividido pela população do município no ano de referência"
        return (
            f"{de_cima} dividido por '{self.denominador.conta}' no "
            f"{self.denominador.anexo} (coluna '{self.denominador.coluna}')"
            + (", multiplicado por 100" if self.fator == 100 else "")
        )

    def url_dado_bruto(self, *, codigo_ibge: str, ano: int) -> str:
        """Link para o dado deste município na API pública do Tesouro.

        Abre no navegador e devolve o JSON da declaração — o leitor confere na
        origem, não numa cópia nossa. É a diferença entre "confie em nós" e
        "veja você mesmo".
        """
        return (
            "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
            f"?an_exercicio={ano}&id_ente={codigo_ibge}"
        )


# Os endereços do DCA que este módulo lê. Nomes exatos como o Tesouro publica.
# A cobertura anotada foi medida em 16/08/2026 sobre os 443 municípios do Norte
# já ingeridos — é ela que separa indicador publicável de promessa.
I_E = ("DCA-Anexo I-E", "Despesas Pagas")  # despesa por função (a área)
I_C = ("DCA-Anexo I-C", "Receitas Brutas Realizadas")  # receita por origem
I_D = ("DCA-Anexo I-D", "Despesas Pagas")  # despesa por natureza (o que se comprou)

RECEITA_TOTAL = Conta(*I_C, "TOTAL DAS RECEITAS (III) = (I + II)")  # 443/443
RECEITA_PROPRIA = Conta(  # 443 declaram, 412 com valor > 0
    *I_C, "1.1.0.0.00.0.0 - Impostos, Taxas e Contribuições de Melhoria"
)
DESPESA_TOTAL = Conta(*I_D, "Total Geral da Despesa")  # 443/443

# Saneamento é o único do conjunto cuja esfera não é só a prefeitura: no Norte,
# quem opera água e esgoto costuma ser a companhia do estado, e o dinheiro nem
# passa pelo município. Sem isso, "gasto zero" seria lido como abandono.
CONTRATO_SANEAMENTO = replace(
    CONTRATO_DCA,
    procedencia=Procedencia(natureza=Natureza.DECLARADO, esfera_responsavel=Esfera.COMPARTILHADA),
)


INDICADORES: tuple[Indicador, ...] = (
    # ---------------------------------------------- de onde vem o dinheiro
    Indicador(
        indicador_id="siconfi_receita_total_pc",
        nome_exibicao="Dinheiro que entrou, por morador",
        descricao_publica="Tudo que a prefeitura recebeu no ano.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="entrada",
        numerador=RECEITA_TOTAL,
        formula_legivel=(
            "Tudo que entrou no caixa da prefeitura no ano, dividido pelos moradores. "
            "Entra imposto da cidade, repasse da União e do estado, e receita de capital."
        ),
        ressalvas=(
            "Receber mais por morador não quer dizer gastar melhor. Cidade pequena "
            "costuma receber mais por pessoa, porque parte do repasse é fixa e o custo "
            "de manter a máquina não cai junto com o número de moradores."
        ),
        ausencia_significa="A prefeitura não declarou a receita do ano ao Tesouro.",
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_receita_propria_pct",
        nome_exibicao="Quanto a cidade arrecada sozinha",
        descricao_publica="A parte do dinheiro que vem de imposto e taxa local.",
        unidade="% da receita",
        direcao_melhor="neutro",
        grupo="entrada",
        numerador=RECEITA_PROPRIA,
        denominador=RECEITA_TOTAL,
        fator=100,
        valor_maximo=100,
        formula_legivel=(
            "De cada R$ 100 que entraram, quanto veio de imposto e taxa cobrados na "
            "própria cidade. O resto é repasse da União, do estado ou outra receita."
        ),
        ressalvas=(
            "Arrecadar pouco por conta própria não é má gestão nem culpa do prefeito: "
            "depende da economia local e do valor dos imóveis. Na maior parte das "
            "cidades brasileiras o dinheiro vem principalmente de repasse, e isso é o "
            "desenho do sistema tributário, não uma escolha da prefeitura."
        ),
        ausencia_significa="A prefeitura não declarou a receita do ano ao Tesouro.",
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_receita_impostos_pc",
        nome_exibicao="Impostos arrecadados por morador",
        descricao_publica="IPTU, ISS e outros impostos da própria cidade.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="entrada",
        numerador=Conta(*I_C, "1.1.1.0.00.0.0 - Impostos"),
        formula_legivel=(
            "Os impostos que a própria prefeitura arrecadou no ano, divididos pelos "
            "moradores. Repasses da União e do estado ficam de fora."
        ),
        ressalvas=(
            "Arrecadar pouco não significa má gestão: depende da economia local e do "
            "valor dos imóveis. Na maioria das cidades brasileiras, o dinheiro vem "
            "principalmente de repasses, não de impostos próprios."
        ),
        ausencia_significa=(
            "Ou a prefeitura não declarou, ou não arrecadou imposto próprio no ano."
        ),
        contrato=CONTRATO_DCA,
    ),
    # ---------------------------------------------- para onde o dinheiro vai
    Indicador(
        indicador_id="siconfi_despesa_pessoal_pct",
        nome_exibicao="Quanto vai para salários",
        descricao_publica="A parte do gasto que paga gente: salário e encargo.",
        unidade="% da despesa",
        direcao_melhor="neutro",
        grupo="saida",
        numerador=Conta(*I_D, "3.1.00.00.00 - Pessoal e Encargos Sociais"),
        denominador=DESPESA_TOTAL,
        fator=100,
        valor_maximo=100,
        formula_legivel=(
            "De cada R$ 100 que a prefeitura pagou, quanto foi para salário, encargo e "
            "aposentadoria de quem trabalha para ela."
        ),
        ressalvas=(
            "Gasto com pessoal alto não é desperdício: professor, médico e agente de "
            "saúde entram aqui. A lei limita esse gasto, mas o limite usa outra conta, "
            "mais estreita que a nossa — este número serve para comparar cidades "
            "parecidas, nunca para dizer que alguém passou do limite legal."
        ),
        ausencia_significa="A prefeitura não declarou a despesa do ano ao Tesouro.",
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_investimento_pct",
        nome_exibicao="Quanto virou obra e equipamento",
        descricao_publica="A parte do gasto que fica: obra, veículo, máquina.",
        unidade="% da despesa",
        direcao_melhor="neutro",
        grupo="saida",
        numerador=Conta(*I_D, "4.4.00.00.00 - Investimentos"),
        denominador=DESPESA_TOTAL,
        fator=100,
        valor_maximo=100,
        formula_legivel=(
            "De cada R$ 100 que a prefeitura pagou, quanto foi para obra, reforma, "
            "veículo, máquina e equipamento — coisas que ficam depois do ano."
        ),
        ressalvas=(
            "Investir muito num ano costuma vir de convênio ou de obra grande, e cai "
            "no ano seguinte. Investir pouco também pode ser sinal de que o dinheiro "
            "foi todo para manter escola e posto abertos. Olhe a série, não um ano só."
        ),
        ausencia_significa="A prefeitura não declarou a despesa do ano ao Tesouro.",
        contrato=CONTRATO_DCA,
    ),
    # ---------------------------------------------- quanto foi para cada área
    Indicador(
        indicador_id="siconfi_despesa_saude_pc",
        nome_exibicao="Gasto com saúde por morador",
        descricao_publica="Hospitais, postos e agentes de saúde.",
        unidade="R$/morador/ano",
        # gastar mais não é melhor nem pior por si só — composição não tem valência
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "10 - Saúde"),
        formula_legivel=(
            "O que a prefeitura pagou em saúde no ano, dividido pelos moradores. "
            "Usamos o valor pago, não o empenhado: empenhado é promessa de gasto."
        ),
        ressalvas=(
            "Quem declara é a prefeitura, e o Tesouro publica sem auditar. "
            "Cidade pequena tende a gastar mais por morador — custo fixo dividido "
            "entre menos gente. Por isso a comparação é só com cidades de porte parecido."
        ),
        ausencia_significa="A prefeitura não declarou o gasto com saúde do ano.",
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_educacao_pc",
        nome_exibicao="Gasto com educação por morador",
        descricao_publica="Escolas, merenda e transporte escolar.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "12 - Educação"),
        formula_legivel=(
            "O que a prefeitura pagou em educação no ano, dividido pelos moradores "
            "da cidade — e não pelo número de alunos."
        ),
        # A ressalva mais importante do MVP: o leitor lê "educação por morador" e
        # entende "investimento por aluno", que é outra conta. Enquanto o Censo
        # Escolar (M1.4) não entra, o texto precisa dizer isso de frente.
        ressalvas=(
            "Atenção: este número mede o esforço do orçamento, não o investimento por "
            "aluno. Saúde atende todo mundo; escola atende quem estuda. Cidade com mais "
            "crianças aparece gastando mais por morador sem gastar mais por aluno. "
            "O gasto por aluno depende do número de matrículas, que entra em versão futura."
        ),
        ausencia_significa="A prefeitura não declarou o gasto com educação do ano.",
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_assistencia_pc",
        nome_exibicao="Gasto com assistência social por morador",
        descricao_publica="CRAS, abrigo, cesta básica e auxílio a famílias.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "08 - Assistência Social"),
        formula_legivel=(
            "O que a prefeitura pagou em assistência social no ano, dividido pelos "
            "moradores. É a área que atende quem está em situação difícil."
        ),
        ressalvas=(
            "O Bolsa Família não entra aqui: ele é pago pela União direto à família. "
            "Este número é o que a prefeitura gastou com a estrutura de atendimento e "
            "com os auxílios que ela mesma paga."
        ),
        ausencia_significa=("Ou a prefeitura não declarou, ou não houve gasto nessa área no ano."),
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_urbanismo_pc",
        nome_exibicao="Gasto com a cidade por morador",
        descricao_publica="Rua, praça, iluminação e limpeza urbana.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "15 - Urbanismo"),
        formula_legivel=(
            "O que a prefeitura pagou em urbanismo no ano, dividido pelos moradores. "
            "É o que se vê na rua: calçamento, praça, iluminação e limpeza."
        ),
        ressalvas=(
            "Cidade com muita área rural concentra a despesa na sede, e o valor por "
            "morador fica parecido com o de uma cidade menor. Obra grande num ano "
            "também infla o número e some no ano seguinte."
        ),
        ausencia_significa=("Ou a prefeitura não declarou, ou não houve gasto nessa área no ano."),
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_saneamento_pc",
        nome_exibicao="Gasto com saneamento por morador",
        descricao_publica="Água tratada, esgoto e drenagem.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "17 - Saneamento"),
        formula_legivel=(
            "O que a prefeitura pagou em saneamento no ano, dividido pelos moradores. "
            "Água, esgoto e drenagem de chuva entram aqui."
        ),
        # A ressalva que evita a leitura mais provável e mais errada do card.
        ressalvas=(
            "Gasto zero aqui não quer dizer cidade sem água tratada. Na maior parte do "
            "Norte quem cuida da água e do esgoto é a companhia do estado, e o dinheiro "
            "nem passa pela prefeitura. Compare com cidades parecidas antes de concluir."
        ),
        ausencia_significa=(
            "Na maioria dos casos o serviço é da companhia estadual, e a prefeitura "
            "não tem gasto próprio na área."
        ),
        contrato=CONTRATO_SANEAMENTO,
    ),
    Indicador(
        indicador_id="siconfi_despesa_cultura_pc",
        nome_exibicao="Gasto com cultura por morador",
        descricao_publica="Festa, biblioteca, banda e casa de cultura.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "13 - Cultura"),
        formula_legivel=(
            "O que a prefeitura pagou em cultura no ano, dividido pelos moradores. "
            "Entra festa da cidade, biblioteca, banda e apoio a artista local."
        ),
        ressalvas=(
            "A festa tradicional da cidade costuma pesar muito neste número, e ela "
            "acontece em datas fixas. Um ano com festa grande fica bem acima do outro, "
            "sem que a política de cultura tenha mudado."
        ),
        ausencia_significa=("Ou a prefeitura não declarou, ou não houve gasto nessa área no ano."),
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_desporto_pc",
        nome_exibicao="Gasto com esporte e lazer por morador",
        descricao_publica="Quadra, campo, ginásio e competição local.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "27 - Desporto e Lazer"),
        formula_legivel=(
            "O que a prefeitura pagou em esporte e lazer no ano, dividido pelos "
            "moradores. Quadra, campo, ginásio e campeonato da cidade entram aqui."
        ),
        ressalvas=(
            "É uma das menores despesas do orçamento na maioria das cidades, então "
            "uma obra única muda muito o valor. Compare com cidades parecidas e olhe "
            "mais de um ano antes de concluir alguma coisa."
        ),
        ausencia_significa=("Ou a prefeitura não declarou, ou não houve gasto nessa área no ano."),
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_agricultura_pc",
        nome_exibicao="Gasto com agricultura por morador",
        descricao_publica="Apoio ao produtor, estrada rural e feira.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "20 - Agricultura"),
        formula_legivel=(
            "O que a prefeitura pagou nessa área no ano, dividido pelos moradores. "
            "Entra apoio ao pequeno produtor, estrada da roça e feira."
        ),
        ressalvas=(
            "O peso desta área muda muito com o perfil da cidade: onde quase todo mundo "
            "mora na zona urbana, gastar pouco aqui é esperado. A comparação por porte "
            "não separa cidade rural de cidade urbana."
        ),
        ausencia_significa=("Ou a prefeitura não declarou, ou não houve gasto nessa área no ano."),
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_legislativa_pc",
        nome_exibicao="Custo da Câmara por morador",
        descricao_publica="O que custou o Legislativo da cidade no ano.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "01 - Legislativa"),
        formula_legivel=(
            "O que foi pago na função Legislativa no ano, dividido pelos moradores. "
            "É o custo da Câmara de Vereadores, que a prefeitura repassa."
        ),
        ressalvas=(
            "A Câmara é outro poder: a prefeitura repassa o dinheiro, mas quem gasta é "
            "o Legislativo. A Constituição limita esse repasse por um percentual da "
            "receita, e cidade pequena costuma ficar no teto, o que faz o custo por "
            "morador parecer alto."
        ),
        ausencia_significa=(
            "Ou a prefeitura não declarou, ou o repasse à Câmara não entrou nesta função."
        ),
        contrato=CONTRATO_DCA,
    ),
    Indicador(
        indicador_id="siconfi_despesa_administracao_pc",
        nome_exibicao="Gasto com a máquina por morador",
        descricao_publica="Prédio, pessoal e serviços da administração.",
        unidade="R$/morador/ano",
        direcao_melhor="neutro",
        grupo="area",
        numerador=Conta(*I_E, "04 - Administração"),
        formula_legivel=(
            "O que a prefeitura pagou na função Administração no ano, dividido pelos "
            "moradores. É o custo de manter a estrutura que faz o resto funcionar."
        ),
        ressalvas=(
            "Cada prefeitura classifica de um jeito o que é administração e o que é "
            "da área fim. Parte do que uma cidade lança aqui, outra lança em saúde ou "
            "educação. Compare com cuidado."
        ),
        ausencia_significa=("Ou a prefeitura não declarou, ou não houve gasto nessa área no ano."),
        contrato=CONTRATO_DCA,
    ),
)


def _filtro(conta: Conta, alias: str = "", *, positivo: bool = False) -> str:
    """O WHERE que isola uma linha da declaração.

    Sempre exige valor não negativo: receita bruta ou despesa paga negativa é
    impossível, e 31 municípios do TO declararam assim em 2024. Regra 4 — dado
    suspeito não é promovido, porque "-R$ 3.827 por morador" não é interpretável
    por leitor nenhum. `positivo` aperta para "> 0", o que só faz sentido no
    divisor: dividir por zero não devolve notícia, devolve erro.
    """
    p = f"{alias}." if alias else ""
    return (
        f"{p}anexo = '{conta.anexo}' AND {p}coluna = '{conta.coluna}' "
        f"""AND {p}conta = '{conta.conta.replace("'", "''")}' """
        f"AND {p}valor IS NOT NULL AND {p}valor {'> 0' if positivo else '>= 0'}"
    )


def _sql_indicador(ind: Indicador, dca: str) -> str:
    """Uma linha por município para este indicador: numerador e divisor próprio.

    `denominador_proprio` é NULL quando a conta é dividida pela população — a
    escolha entre "por morador" e "proporção" fica declarada no indicador, e o
    SQL só obedece.
    """
    cabecalho = (
        f"'{ind.indicador_id}' AS indicador_id, {ind.versao_metodologia} AS versao_metodologia"
    )
    if ind.denominador is None:
        return f"""
        SELECT
            lpad(CAST(cod_ibge AS VARCHAR), 7, '0') AS codigo_municipio_ibge,
            {cabecalho},
            valor * {ind.fator} AS numerador,
            NULL::DOUBLE AS denominador_proprio
        FROM '{dca}'
        WHERE {_filtro(ind.numerador)}
    """

    # município que declarou o numerador mas não o divisor não vira linha: sem os
    # dois lados a divisão não existe, e ausência não é zero (regra 4)
    return f"""
        SELECT
            lpad(CAST(n.cod_ibge AS VARCHAR), 7, '0') AS codigo_municipio_ibge,
            {cabecalho},
            n.valor * {ind.fator} AS numerador,
            d.valor AS denominador_proprio
        FROM '{dca}' n
        JOIN '{dca}' d ON d.cod_ibge = n.cod_ibge
        WHERE {_filtro(ind.numerador, "n")}
          AND {_filtro(ind.denominador, "d", positivo=True)}
    """


def _minimos_declarados() -> dict[str, int | None]:
    """O denominador mínimo de cada indicador, vindo do contrato."""
    return {i.indicador_id: i.contrato.confiabilidade.denominador_minimo for i in INDICADORES}


def _sql_supressao(minimos: dict[str, int | None]) -> str:
    """CASE que zera o valor onde o denominador é pequeno demais.

    A supressão acontece **antes** da mediana: valor instável não pode sair do
    card e continuar servindo de referência para os vizinhos.
    """
    casos = " ".join(
        f"WHEN indicador_id = '{indicador}' AND denominador < {minimo} THEN TRUE"
        for indicador, minimo in minimos.items()
        if minimo is not None
    )
    return f"CASE {casos} ELSE FALSE END" if casos else "FALSE"


def _sql_teto() -> str:
    """Descarta proporção acima do máximo possível — "137% da receita" é erro."""
    casos = " ".join(
        f"WHEN indicador_id = '{i.indicador_id}' THEN valor <= {i.valor_maximo}"
        for i in INDICADORES
        if i.valor_maximo is not None
    )
    return f"CASE {casos} ELSE TRUE END" if casos else "TRUE"


def construir(
    dca_parquet, dim_parquet, destino, *, ano: int, minimos: dict[str, int | None] | None = None
) -> int:
    """Monta o fato para um exercício e devolve o nº de linhas.

    `minimos` sobrescreve os denominadores mínimos do contrato — existe para o
    teste exercitar a supressão sem depender de qual indicador a declara hoje.
    """
    dca = parquet._posix(dca_parquet)
    dim = parquet._posix(dim_parquet)
    saida = parquet._posix(destino)
    con = parquet.conectar(dca, dim, saida)

    minimos = _minimos_declarados() if minimos is None else minimos
    motivos = {i.indicador_id: i.contrato.confiabilidade.motivo_supressao for i in INDICADORES}

    bruto = "\n            UNION ALL\n".join(_sql_indicador(i, dca) for i in INDICADORES)

    con.execute(f"""
        CREATE TABLE base AS
        WITH bruto AS ({bruto}),
        com_denominador AS (
            SELECT
                b.codigo_municipio_ibge,
                {ano} AS ano,
                b.indicador_id,
                b.versao_metodologia,
                b.numerador / coalesce(b.denominador_proprio, m.populacao_referencia) AS valor,
                -- guardado para auditoria: dá para refazer a conta sem adivinhar.
                -- É a população nos indicadores "por morador" e a outra conta da
                -- declaração nas proporções — o divisor de fato usado, sempre.
                coalesce(b.denominador_proprio, m.populacao_referencia) AS denominador,
                m.grupo_comparacao
            FROM bruto b
            -- INNER JOIN: município fora da dimensão não entra; município da dimensão
            -- que não declarou simplesmente não tem linha (regra 4: ausência ≠ zero)
            JOIN '{dim}' m USING (codigo_municipio_ibge)
            WHERE m.populacao_referencia > 0
        )
        SELECT *, {_sql_supressao(minimos)} AS suprimido
        FROM com_denominador
        -- parte maior que o todo é erro de declaração, não notícia: mesma regra
        -- do valor negativo, o card falta e diz por quê
        WHERE {_sql_teto()}
    """)

    padrao = "'valor instável para esta base de cálculo'"
    motivo_sql = " ".join(
        f"WHEN indicador_id = '{indicador}' "
        f"""THEN '{motivos[indicador].replace("'", "''")}'"""
        for indicador, minimo in minimos.items()
        if minimo is not None and motivos.get(indicador)
    )
    # CASE sem WHEN é erro de sintaxe: sem motivo declarado, vai só o texto padrão
    motivo_case = f"CASE {motivo_sql} ELSE {padrao} END" if motivo_sql else padrao

    con.execute(f"""
        COPY (
            SELECT
                codigo_municipio_ibge, ano, indicador_id, versao_metodologia,
                -- suprimido publica ausência com motivo, não número
                CASE WHEN suprimido THEN NULL ELSE valor END AS valor,
                denominador,
                CASE WHEN suprimido THEN {motivo_case} END AS motivo_supressao,
                CASE WHEN n_grupo >= {MINIMO_GRUPO} THEN mediana END AS mediana_grupo,
                n_grupo,
                CASE WHEN n_grupo >= {MINIMO_GRUPO} THEN posicao END AS posicao_grupo,
                grupo_comparacao
            FROM (
                SELECT *,
                    -- as janelas ignoram o suprimido: valor instável sai do card E
                    -- sai da referência dos vizinhos, senão contaminaria a mediana
                    median(valor) FILTER (WHERE NOT suprimido)
                        OVER (PARTITION BY indicador_id, grupo_comparacao) AS mediana,
                    count(*) FILTER (WHERE NOT suprimido)
                        OVER (PARTITION BY indicador_id, grupo_comparacao) AS n_grupo,
                    rank() OVER (
                        PARTITION BY indicador_id, grupo_comparacao ORDER BY valor DESC
                    ) AS posicao
                FROM base
            )
            ORDER BY codigo_municipio_ibge, indicador_id
        ) TO '{saida}' (FORMAT parquet, COMPRESSION zstd)
    """)

    (total,) = con.sql(f"SELECT count(*) FROM '{saida}'").fetchone()
    return total


def construir_dim_indicador(destino) -> int:
    """A metodologia é dado público (ARQUITETURA §4): vira parquet junto do fato."""
    saida = parquet._posix(destino)
    con = parquet.conectar(saida)
    con.execute(
        "CREATE TABLE d (indicador_id VARCHAR, nome_exibicao VARCHAR, "
        "descricao_publica VARCHAR, fonte VARCHAR, orgao VARCHAR, unidade VARCHAR, "
        "direcao_melhor VARCHAR, versao_metodologia INT, formula_sql VARCHAR, "
        "formula_legivel VARCHAR, ressalvas VARCHAR, ausencia_significa VARCHAR, "
        "grupo VARCHAR, ordem INT)"
    )
    con.executemany(
        "INSERT INTO d VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                i.indicador_id,
                i.nome_exibicao,
                i.descricao_publica,
                i.fonte,
                i.orgao,
                i.unidade,
                i.direcao_melhor,
                i.versao_metodologia,
                i.formula_sql,
                i.formula_legivel,
                i.ressalvas,
                # o texto da falta viaja junto da definição: é ele que impede a
                # página de dizer "não declarou" onde a área é de outro ente
                i.ausencia_significa,
                i.grupo,
                # a ordem é a desta tupla: quem define o que o leitor vê primeiro
                # é quem conhece os números, não o alfabeto
                ordem,
            )
            for ordem, i in enumerate(INDICADORES)
        ],
    )
    con.execute(f"COPY d TO '{saida}' (FORMAT parquet, COMPRESSION zstd)")
    return len(INDICADORES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ano", type=int, default=2024)
    args = parser.parse_args()

    dca = storage.uri(
        "staging", "siconfi", "dca", f"an_exercicio={args.ano}", "uf=*", "dca.parquet"
    )
    dim = storage.uri("marts", "dim_municipio.parquet")
    destino = storage.uri("marts", f"fato_indicador_municipio/ano={args.ano}", "fato.parquet")

    linhas = construir(dca, dim, destino, ano=args.ano)
    construir_dim_indicador(storage.uri("marts", "dim_indicador.parquet"))
    print(f"{linhas} linhas em {destino}")


if __name__ == "__main__":
    main()
