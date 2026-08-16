# Quais indicadores publicar — e por quê

> Levantamento de 15/08/2026, feito para responder a uma lacuna real: os indicadores do MVP são
> todos de **composição de gasto**, e composição de gasto não tem direção. O leitor pergunta
> "minha cidade está melhorando?" e a página responde "gastou R$ 1.030 por morador", que não é
> resposta.
>
> **Atualização de 16/08/2026**: o orçamento passou de 3 para 15 indicadores. Isso melhora o
> retrato (agora a página diz de onde vem o dinheiro, para onde vai e quanto foi para cada
> área) e dá base à medida de transparência, mas **não resolve a lacuna deste documento** —
> 15 números sem direção continuam sem responder à pergunta. A fila abaixo é o que resolve.
>
> Este documento não é um mecanismo — é o critério de admissão e a fila. A relevância é a
> única das três exigências do projeto (relevante, verdadeiro, simples) que não dá para
> automatizar.

## 1. O que já existe no Brasil, e o que aprendemos com isso

| Iniciativa | O que faz | O que aproveitamos |
|---|---|---|
| **IFDM** (Firjan) | Índice 0–1 em 3 dimensões — emprego & renda, educação, saúde — só com estatística pública oficial, série desde 2005 | A escolha das 3 dimensões, validada por 20 anos de uso |
| **IDSC-BR** (Instituto Cidades Sustentáveis) | 100 indicadores ODS para os 5.570 municípios | O repertório de indicadores com meta declarada |
| **Meu Município** | Receitas e despesas do STN + IBGE, com comparação entre municípios | O mais próximo do que fazemos hoje — e mostra o teto de "só finanças" |
| **IEGM** (TCEs) | Efetividade da gestão, por auditoria | Fora de alcance: depende de dado que o TCE coleta, não publicado de forma uniforme |

**A convergência importa**: IFDM e IDSC-BR chegam, por caminhos diferentes, ao mesmo tripé —
**saúde, educação, trabalho/renda**. Nosso MVP hoje cobre nenhum dos três: cobre orçamento.

### A decisão de não fazer índice composto

IFDM e IDSC-BR entregam nota única (0 a 1). É tentador e está errado para o nosso leitor:

1. **Esconde o que mudou.** "A nota caiu de 0,72 para 0,68" não diz o que piorou.
2. **Exige confiar na ponderação.** Quem decidiu que saúde vale 1/3? O leitor não tem como
   auditar, e o projeto promete auditabilidade.
3. **Vira ranking de prefeito.** Nota única em ano eleitoral é exatamente o que o princípio 4
   proíbe.

Nossa vantagem competitiva é o oposto: **indicador cru, com direção declarada e fonte
clicável**. Quem quiser índice composto já tem IFDM.

## 2. Critérios de admissão

Um indicador entra se cumprir **todos**:

1. **Direção pactuada** — existe consenso técnico de que subir (ou cair) é melhor, e dá para
   documentar isso em `/metodologia`. Se a direção é discutível, o indicador é neutro e não
   serve para responder "está melhorando?".
2. **Série anual ou mais frequente** — sem série não há evolução, e evolução é o que o leitor
   pediu.
3. **O município é a unidade real** — não rateio de dado estadual, não proxy.
4. **Leigo entende sem glossário** — "quantas horas sua cidade ficou sem luz" passa;
   "razão de mortalidade materna padronizada" não.
5. **Fonte que temos ou teremos até o M1.**

E um critério de exclusão que vale mais que os cinco: **se o número puder ser lido como
acusação a uma gestão sem que o dado sustente isso, não entra** — ou entra com a ressalva
escrita antes do lançamento, não depois.

## 3. A fila, por prioridade

Prioridade = (o leitor entende sozinho) × (direção inequívoca) × (dado já espelhado).

### Primeira leva — os que respondem "melhorou ou piorou"

| Indicador | Direção | Fonte | Estado | Por que este |
|---|---|---|---|---|
| **Mortalidade infantil** (óbitos < 1 ano por mil nascidos) | ↓ melhor | SIM + SINASC | **espelhado** | O indicador social mais consagrado do mundo. Todo mundo entende. Série desde 1996 no nosso espelho |
| **Internações evitáveis (ICSAP)** | ↓ melhor | SIH | a coletar | Mede se o posto de saúde funciona: internação por diabetes ou hipertensão significa que a atenção básica falhou. **Gestão municipal direta** |
| **Pré-natal adequado** (7+ consultas) | ↑ melhor | SINASC | **espelhado** | Depende só de o município oferecer consulta. Simples de explicar, difícil de contestar |
| **IDEB anos iniciais** | ↑ melhor | INEP | **espelhado** | A "nota da escola" que as pessoas já conhecem. Rede municipal = responsabilidade do prefeito |
| **Abandono escolar** (ensino fundamental) | ↓ melhor | INEP Censo | **espelhado** | Criança que parou de estudar é fato concreto, não índice |

### Segunda leva — bons, com ressalva que precisa estar escrita

| Indicador | Direção | Ressalva obrigatória |
|---|---|---|
| **Horas sem energia** (DEC) | ↓ melhor | O grão real é conjunto elétrico, não município — dizer "área atendida" |
| **Saldo de empregos formais** | ↑ melhor | Saldo formal ≠ desemprego; não atribuir causa à prefeitura |
| **Cobertura vacinal infantil** | ↑ melhor | Denominador é estimativa populacional; queda pode ser erro de registro |
| **Crianças fora da creche** | ↓ melhor | Denominador é fotografia do Censo 2022 |
| **Gasto com pessoal / RCL** | limite legal 54% | Usar o % já apurado no RGF; "acima do limite da LRF", nunca "ilegal" |

### Terceira leva — neutros, ficam como contexto

Os três atuais (saúde, educação, impostos por morador) **não saem** — mudam de papel. Deixam de
ser a resposta e viram o "quanto se gasta" ao lado do "o que se conseguiu". Gasto alto com
resultado ruim é a pergunta interessante; nenhum dos dois números sozinho é.

## 4. O que isso muda no produto

Hoje a página responde **"quanto sua cidade gasta"**. Com a primeira leva, passa a responder
**"como sua cidade está indo"** — e o gasto vira contexto.

Isso exige três coisas que ainda não existem:

1. **Série histórica no card** (o sparkline previsto no PRODUTO §2) — sem série, "evolução" é
   promessa vazia. O fato já tem a coluna `ano`; falta o serving emitir mais de um ano.
2. **Semáforo com direção**, hoje sempre neutro. Verde/laranja só para estes indicadores, com
   a direção documentada em `/metodologia/{indicador}` — regra 4 do PRODUTO §2.
3. **Processar SIM e SINASC**, que estão espelhados em `.dbc` e ainda não viraram staging
   (M1.5). É o maior trabalho da lista, e destrava três dos cinco indicadores da primeira leva.

## 5. O que eu faria primeiro

**Mortalidade infantil.** Dado já espelhado, direção inequívoca, série longa, e é o indicador
que qualquer pessoa entende sem explicação. Se o projeto só pudesse publicar um número além
das finanças, seria esse.

Depois, **IDEB** — porque o dado está espelhado, a série é bienal e o público já conhece o
nome, o que reduz o custo de explicação a quase zero.
