# Checklist de indicadores — progresso por etapa

> Tracking dos indicadores que respondem **"minha cidade está melhorando?"**. O critério de
> admissão e o porquê da escolha estão em [INDICADORES.md](INDICADORES.md); aqui fica só o
> andamento. Atualizado em **15/08/2026**.
>
> Marcar etapa só quando ela estiver verificada contra dado real — não quando o código existir.

## Legenda das etapas

| Etapa | O que significa "pronto" |
|---|---|
| **1. Espelho** | arquivo bruto no R2, com sha256 no manifesto, cobrindo os anos necessários |
| **2. Staging** | virou parquet legível por município e ano, com contrato de schema |
| **3. Definição** | `Indicador` com fórmula legível, ressalvas, direção e link do dado bruto; passa nos testes de legibilidade |
| **4. Mart** | no `fato_indicador_municipio`, com mediana de grupo e ranking |
| **5. Página** | card renderizado, com semáforo na direção correta e "como foi calculado" |
| **6. Metodologia** | página `/metodologia/{indicador}` explicando a direção pactuada |

## Progresso

| Indicador | 1. Espelho | 2. Staging | 3. Definição | 4. Mart | 5. Página | 6. Metodologia |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| **Abandono escolar** ↓ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **Mortalidade infantil** ↓ | ⚠️ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **Pré-natal 7+ consultas** ↑ | ⚠️ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **IDEB anos iniciais** ↑ | ⚠️ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **Internações evitáveis (ICSAP)** ↓ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **Horas sem energia (DEC)** ↓ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **Saldo de empregos formais** ↑ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| *Gasto com saúde/morador* (neutro) | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ |
| *Gasto com educação/morador* (neutro) | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ |
| *Impostos por morador* (neutro) | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ |

Os três em itálico são os atuais, de composição de gasto: servem de referência do que é
"pronto" e mostram a única etapa que falta a todos — a página de metodologia.

## Bloqueios a resolver antes de processar

Descobertos ao montar este checklist, conferindo o manifesto do espelho contra o que cada
indicador exige. **Dois deles invertem a ordem de trabalho que parecia óbvia.**

### B1 — SINASC nacional só tem 2014–2017

`DNBR{ano}.dbc` existe apenas para 4 anos; os demais anos só existem por UF (`DNSP`, `DNRJ`…).
Sem nascidos vivos não há denominador, então **mortalidade infantil e pré-natal ficam presos a
2015–2017** — três anos, insuficiente para mostrar evolução.

**Ação**: espelhar o SINASC por UF, 2018–2024 → 27 arquivos × 7 anos. Estimativa ~1 GB.
Só depois disso os dois indicadores viram série.

### B2 — IDEB só tem 2023

Confirmado em 26/07: `divulgacao_anos_iniciais_municipios_2019.zip` e `_2021.zip` respondem
**404**. O INEP não mantém as edições anteriores nessas URLs. Com um ponto só, o IDEB entra
como valor, **não como evolução**.

**Ação**: procurar as edições 2019 e 2021 em outra origem (portal do INEP, Base dos Dados) ou
aceitar o IDEB como indicador sem série — decisão editorial, não técnica.

### B3 — SIH e ANEEL não foram coletados

ICSAP depende do SIH (DataSUS), horas sem luz dependem da ANEEL. Nenhum dos dois tem espelho
nem pipeline. São os dois indicadores mais distantes da fila.

### B4 — `.dbc` não é lido por nada que temos

Formato proprietário do DataSUS. Precisa de `datasus-dbc` ou `pysus` para virar parquet, e é
conversão de mão única: converter **uma vez** e guardar em staging, nunca reprocessar do
`.dbc` (FONTES §Camada 2).

## O que isso muda na ordem de ataque

A ordem proposta em INDICADORES.md §5 começava por mortalidade infantil. **O inventário
desmente**: ela está bloqueada por B1 e B4 ao mesmo tempo.

Ordem corrigida, por prontidão real:

1. **Abandono escolar** — única com espelho completo (Censo Escolar 2020–2024, 5 anos) e
   formato legível (`.zip` de CSV). Não depende de nenhum bloqueio.
2. **Mortalidade infantil** — resolver B1 (espelhar SINASC por UF) e B4 (conversor `.dbc`).
   Continua sendo o indicador mais valioso; só não é o mais barato.
3. **Pré-natal** — sai junto da mortalidade infantil, mesma fonte e mesmo conversor.
4. **IDEB** — decidir B2 antes: publicar sem série ou garimpar os anos anteriores.
5. **ICSAP e DEC** — dependem de coleta nova.

## Detalhe por indicador

### Abandono escolar ↓
- **Pergunta**: quantos alunos pararam de estudar no meio do ano?
- **Fonte**: INEP, Censo Escolar (situação do aluno ao fim do ano letivo)
- **Anos disponíveis**: 2020–2024 (5 pontos — série real)
- **Direção**: menor é melhor. Consenso sem controvérsia.
- **Ressalva obrigatória**: rede municipal vai até o 9º ano; ensino médio é estadual e não
  entra. Comparar cidade com rede pequena exige cuidado com n baixo.

### Mortalidade infantil ↓
- **Pergunta**: de cada mil bebês que nasceram, quantos não completaram 1 ano?
- **Fonte**: SIM (óbitos < 1 ano) ÷ SINASC (nascidos vivos) × 1.000
- **Anos disponíveis hoje**: 2015–2017 (interseção); 2015–2024 depois de resolver B1
- **Direção**: menor é melhor. O indicador social mais consagrado do mundo.
- **Ressalva obrigatória**: em município pequeno, um óbito muda a taxa inteira — **suprimir
  quando nascidos vivos < 100** e dizer por quê. Melhora pode ser subnotificação.

### Pré-natal adequado ↑
- **Pergunta**: quantas gestantes fizeram 7 ou mais consultas de pré-natal?
- **Fonte**: SINASC (campo de consultas de pré-natal na declaração de nascido vivo)
- **Direção**: maior é melhor. Depende diretamente de o município oferecer a consulta.
- **Ressalva**: o dado é declarado no nascimento e há campo ignorado — publicar o percentual
  de "ignorado" junto, ou o número engana.

### IDEB ↑
- **Pergunta**: qual a nota das escolas da rede municipal?
- **Fonte**: INEP, divulgação por município
- **Anos**: só 2023 (ver B2)
- **Ressalva**: a nota reflete contexto socioeconômico; não é ranking de escola nem de
  professor. Régua de comparação é exceção documentada (mediana estadual, PRODUTO §2.3).

### Internações evitáveis (ICSAP) ↓
- **Pergunta**: quantas pessoas foram internadas por problema que o posto de saúde poderia
  ter resolvido?
- **Fonte**: SIH, por município de residência, lista brasileira de ICSAP (Portaria 221/2008)
- **Direção**: menor é melhor — mede se a atenção básica funciona.
- **Ressalva**: **suprimir células < 5** (reidentificação, SEGURANCA §1); não culpar unidade.

### Horas sem energia (DEC) ↓
- **Fonte**: ANEEL
- **Ressalva estrutural**: o grão real é **conjunto elétrico**, não município — dizer "área
  atendida", nunca "sua cidade ficou X horas sem luz" como se fosse medida municipal exata.

### Saldo de empregos formais ↑
- **Fonte**: Novo CAGED
- **Ressalva**: saldo formal ≠ desemprego; não atribuir causa à prefeitura; nunca citar empresa.
