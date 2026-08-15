"""TDD: contrato de indicador — a sistemática de adoção de métricas.

Cada métrica tem peculiaridades que não são exceções, são a norma: cobre anos
diferentes, existe só para parte dos municípios, e tem faixas em que o número
é ruído. Tratar isso caso a caso multiplica `if` pelo código e garante que a
próxima métrica repita o erro da anterior.

Aqui as peculiaridades viram **declaração**. Quem adiciona indicador preenche o
contrato; supressão, lacuna e aviso saem de graça.
"""

import pytest

from pipelines.marts import contrato


def _cobertura(**kwargs):
    padrao = {
        "anos": (2020, 2021, 2022, 2023, 2024),
        "periodicidade": "anual",
        "defasagem_meses": 12,
        "universo": contrato.TODOS_MUNICIPIOS,
    }
    return contrato.Cobertura(**{**padrao, **kwargs})


def _confianca(**kwargs):
    padrao = {
        "denominador_minimo": None,
        "motivo_supressao": "",
        "campo_ignorado": None,
        "quebras": {},
    }
    return contrato.Confiabilidade(**{**padrao, **kwargs})


# ---------------------------------------------------------------- período


def test_ano_dentro_da_cobertura_e_publicavel():
    assert _cobertura().cobre(2023)


def test_ano_fora_da_cobertura_nao_e_publicavel():
    """IDEB não tem 2020; publicar valor ali seria inventar."""
    assert not _cobertura(anos=(2021, 2023)).cobre(2020)


def test_lacuna_no_meio_da_serie_e_declarada():
    """IDEB é bienal: 2021 e 2023 existem, 2022 não. O gráfico precisa saber."""
    cobertura = _cobertura(anos=(2019, 2021, 2023), periodicidade="bienal")
    assert cobertura.lacunas(2019, 2023) == (2020, 2022)


def test_serie_sem_lacuna_devolve_vazio():
    assert _cobertura().lacunas(2020, 2024) == ()


def test_um_ano_so_nao_e_serie():
    """Com um ponto não há evolução — o card não pode prometer tendência."""
    assert not _cobertura(anos=(2023,)).tem_serie()
    assert _cobertura(anos=(2022, 2023)).tem_serie()


def test_defasagem_explica_por_que_o_dado_e_velho():
    cobertura = _cobertura(defasagem_meses=18)
    assert "18 meses" in cobertura.explicar_defasagem()


def test_defasagem_normal_nao_vira_aviso():
    """Dado anual sai com ~1 ano de atraso: avisar sempre é ruído que se aprende
    a ignorar, e o card já mostra ano de referência e data de coleta."""
    normal = contrato.Contrato(
        cobertura=_cobertura(defasagem_meses=12), confiabilidade=_confianca()
    )
    assert normal.avisos_para_o_leitor() == []

    anormal = contrato.Contrato(
        cobertura=_cobertura(defasagem_meses=24), confiabilidade=_confianca()
    )
    assert any("24 meses" in a for a in anormal.avisos_para_o_leitor())


# ---------------------------------------------------------------- cobertura geográfica


def test_universo_padrao_alcanca_todo_municipio():
    assert _cobertura().alcanca("1400100")


def test_universo_restrito_a_uma_lista():
    """Métrica que só existe onde há rede municipal, ou só em capitais."""
    cobertura = _cobertura(universo=("1400100", "3550308"))
    assert cobertura.alcanca("1400100")
    assert not cobertura.alcanca("2611101")


def test_fora_do_universo_e_diferente_de_nao_declarou():
    """A distinção que o leitor precisa: 'não se aplica' ≠ 'a prefeitura não mandou'."""
    cobertura = _cobertura(universo=("1400100",))
    assert contrato.motivo_ausencia(cobertura, "2611101", declarou=False) == "fora_do_universo"
    assert contrato.motivo_ausencia(cobertura, "1400100", declarou=False) == "nao_declarou"


def test_dentro_do_universo_e_com_dado_nao_tem_ausencia():
    assert contrato.motivo_ausencia(_cobertura(), "1400100", declarou=True) is None


# ---------------------------------------------------------------- imprecisão


def test_denominador_pequeno_suprime_o_valor():
    """Mortalidade infantil em cidade de 40 nascimentos: um óbito vira 25 por mil."""
    conf = _confianca(
        denominador_minimo=100,
        motivo_supressao="poucos nascimentos para uma taxa estável",
    )
    suprimir, motivo = conf.avaliar(denominador=40)
    assert suprimir
    assert "poucos nascimentos" in motivo


def test_denominador_suficiente_publica():
    conf = _confianca(denominador_minimo=100, motivo_supressao="x")
    assert conf.avaliar(denominador=500) == (False, None)


def test_sem_regra_de_minimo_nao_suprime():
    assert _confianca().avaliar(denominador=1) == (False, None)


def test_denominador_ausente_suprime_por_precaucao():
    """Sem saber o denominador não dá para afirmar que a taxa é confiável."""
    conf = _confianca(denominador_minimo=100, motivo_supressao="x")
    suprimir, _ = conf.avaliar(denominador=None)
    assert suprimir


def test_quebra_metodologica_impede_comparar_atraves_dela():
    """RAIS mudou layout em 2024; CAGED mudou com o eSocial. Série não atravessa."""
    conf = _confianca(quebras={2024: "mudança de layout e de variáveis"})
    assert not conf.comparavel(2023, 2024)
    assert conf.comparavel(2021, 2023)


def test_quebra_explica_o_motivo():
    conf = _confianca(quebras={2020: "pandemia alterou o registro"})
    assert "pandemia" in conf.explicar_quebra(2019, 2021)


def test_sem_quebra_qualquer_par_e_comparavel():
    assert _confianca().comparavel(2015, 2024)


def test_campo_ignorado_precisa_ser_publicado_junto():
    """Pré-natal tem 'ignorado'; sem publicar o percentual, o número engana."""
    conf = _confianca(campo_ignorado="consultas de pré-natal não informadas")
    assert conf.exige_publicar_ignorado()
    assert not _confianca().exige_publicar_ignorado()


# ---------------------------------------------------------------- esfera responsável


def test_esfera_responsavel_e_declarada():
    """O prefeito não manda em escola estadual nem em hospital federal."""
    assert contrato.Natureza.DECLARADO in contrato.Natureza
    proc = contrato.Procedencia(
        natureza=contrato.Natureza.DECLARADO, esfera_responsavel=contrato.Esfera.MUNICIPAL
    )
    assert proc.esfera_responsavel is contrato.Esfera.MUNICIPAL


def test_esfera_nao_municipal_gera_aviso_de_atribuicao():
    """Erro mais comum em painel municipal: cobrar do prefeito o que não é dele."""
    proc = contrato.Procedencia(
        natureza=contrato.Natureza.MEDIDO, esfera_responsavel=contrato.Esfera.ESTADUAL
    )
    aviso = proc.aviso_de_atribuicao()
    assert aviso and "estadual" in aviso.lower()


def test_esfera_municipal_nao_precisa_de_aviso():
    proc = contrato.Procedencia(
        natureza=contrato.Natureza.MEDIDO, esfera_responsavel=contrato.Esfera.MUNICIPAL
    )
    assert proc.aviso_de_atribuicao() is None


# ---------------------------------------------------------------- natureza do dado


@pytest.mark.parametrize(
    ("natureza", "trecho"),
    [
        (contrato.Natureza.DECLARADO, "informado pela própria"),
        (contrato.Natureza.ESTIMADO, "estimativa"),
        (contrato.Natureza.RATEADO, "não foi medido"),
    ],
)
def test_natureza_nao_medida_se_explica(natureza, trecho):
    """Rateio apresentado como medição é o engano mais silencioso do gênero."""
    proc = contrato.Procedencia(natureza=natureza, esfera_responsavel=contrato.Esfera.MUNICIPAL)
    assert trecho in proc.explicar_natureza().lower()


def test_dado_medido_nao_precisa_de_ressalva_de_natureza():
    proc = contrato.Procedencia(
        natureza=contrato.Natureza.MEDIDO, esfera_responsavel=contrato.Esfera.MUNICIPAL
    )
    assert proc.explicar_natureza() is None


# ---------------------------------------------------------------- revisão e sincronia


def test_dado_revisavel_avisa_que_o_passado_muda():
    """SIM e SINASC são revistos: o valor de 2020 hoje difere do de 2021."""
    conf = _confianca(revisavel=True)
    assert conf.avisa_revisao()


def test_dado_definitivo_nao_avisa():
    assert not _confianca().avisa_revisao()


def test_taxa_exige_numerador_e_denominador_do_mesmo_ano():
    """Óbitos de 2024 com nascidos vivos de 2017 é erro que nenhum teste pega."""
    conf = _confianca(exige_mesmo_ano=True)
    assert not conf.anos_compativeis(2024, 2017)
    assert conf.anos_compativeis(2024, 2024)


def test_sem_exigencia_de_sincronia_qualquer_par_passa():
    assert _confianca().anos_compativeis(2024, 2017)


# ---------------------------------------------------------------- o contrato inteiro


def test_indicador_novo_precisa_declarar_cobertura_e_confianca():
    """A sistemática: sem contrato preenchido, o indicador não é aceito."""
    with pytest.raises(TypeError):
        contrato.Contrato(cobertura=_cobertura())  # falta confiabilidade


def test_contrato_resume_o_que_o_leitor_precisa_saber():
    c = contrato.Contrato(
        cobertura=_cobertura(anos=(2022, 2023), defasagem_meses=24),
        confiabilidade=_confianca(denominador_minimo=100, motivo_supressao="poucos casos"),
    )
    avisos = c.avisos_para_o_leitor()
    assert any("24 meses" in a for a in avisos)
    assert any("100" in a for a in avisos)


def test_contrato_sem_ressalva_nao_inventa_aviso():
    c = contrato.Contrato(cobertura=_cobertura(), confiabilidade=_confianca())
    assert c.avisos_para_o_leitor() == []
