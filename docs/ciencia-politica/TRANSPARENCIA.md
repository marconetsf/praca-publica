# O que a sua cidade ainda não publica

> Desenho de 16/08/2026. Responde a uma pergunta que o produto ainda não responde: hoje, quando
> um município não publica um dado, o leitor vê um card vazio e a informação morre ali. A
> ausência é fato público, e fato público a gente conta.
>
> **Enquadramento (decisão do mantenedor, e é ela que organiza o documento inteiro):
> isto é diagnóstico, não punição.** Um exame não acusa o paciente — nomeia o que está
> faltando para que dê para tratar. Ter esta medida é bom **para o próprio município**: ela
> mostra onde a informação da cidade não está chegando ao cidadão. Se em algum ponto o texto
> soar como nota da gestão, o texto está errado, não o leitor.
>
> **Este documento é desenho, não implementação.** Nada aqui vira página antes das pendências
> do §8 e da decisão do §9. Estamos dentro do congelamento eleitoral (SEGURANCA §6.3) — ver §5.4.

---

## 0. Recomendação, antes do desenho

Sim, a medida deve existir. **Não** na forma de um score de transparência.

Três peças separadas, com riscos muito diferentes:

| Peça | O que é | Risco | Quando |
|---|---|---|---|
| **A. Estado das fontes** | Ficha por órgão federal: o que ele publicava, o que parou de publicar, o que apagou — com nossa cópia datada ao lado | Baixo. Fala de órgão, não de gestão; a prova é nosso próprio espelho | Pode ser feita agora |
| **B. Inventário municipal** | Na página do município: o que consta, o que ainda não consta, **o motivo de cada falta**, e quantas pessoas ficam sem aquela informação. Sem taxa, sem nota | Médio. É uma afirmação *sobre* o ente | Depois da diplomação |
| **C. Retrato agregado** | Por UF, faixa de porte e nacional — **sempre dois números lado a lado**: quantas prefeituras e quantas pessoas (§4.4) | Baixo-médio. Não singulariza ninguém | Depois da diplomação |

O que recomendo **não** publicar: taxa de entrega por município como número-manchete, nota
0–100, ranking de transparência, selo, medalha, semáforo colorido. Cada um converte um
inventário verificável em juízo de valor sobre uma prefeitura.

**Sobre a ponderação por população** (§4): ela está incorporada e é a decisão certa — mas o
resultado da análise é que ela **não substitui** a contagem de municípios, e sim **exige** que
as duas apareçam juntas. Com os dados reais do Norte, as duas apontam para lados opostos, e
publicar só uma esconderia metade do fato. O §4.5 mostra o cálculo.

---

## 1. Definição

> **A medida diz, para um ente e um ano, quais das informações que a Praça Pública acompanha
> chegaram até nós em condição de publicação, quais ainda não chegaram, por quê — e quantas
> pessoas ficam sem cada uma delas.**

É um **inventário com motivo e alcance**. Não é uma nota, e a diferença entre as duas coisas é
o assunto de metade deste documento.

### 1.1 O que ela mede

- **Entrega, não qualidade.** O município mandou a DCA de 2024? Chegou? Passou no gate de
  sanidade? Três perguntas de sim ou não sobre um conjunto declarado de itens.
- **Um evento homogêneo, repetido.** Todo item conta 1 — ver §3.1.
- **Com denominador enumerado.** O leitor vê a lista inteira do que era esperado, não só o
  total. A conta é conferível no olho.
- **Com alcance humano.** Uma informação que falta em Vigia (PA) deixa 54.062 pessoas sem ela;
  em Muricilândia (TO), 3.501. É o mesmo item faltando e não é o mesmo tamanho de problema.

### 1.2 O que ela explicitamente **não** mede

| Não mede | Por quê |
|---|---|
| **Transparência no sentido da LAI** | Portal da prefeitura, prazo de resposta a pedido de informação, diário oficial acessível — nada disso está no nosso catálogo. Uma cidade com portal exemplar e DCA atrasada aparece pior aqui que uma cidade sem portal nenhum que só manda a DCA |
| **Qualidade da gestão** | Entregar formulário no prazo é capacidade administrativa, não resultado de política pública |
| **Honestidade** | Declaração que chega, bate na aritmética e é falsa passa em todos os nossos testes. Nós conferimos o possível, não o verdadeiro |
| **Intenção de ocultar** | Não temos nenhum dado que distinga "escondeu" de "não conseguiu". O verbo público é sempre **"ainda não consta"** |
| **O que o município publicou** | Medimos **o que a Praça Pública obteve**. São coisas diferentes, e a diferença cabe inteira em nós — §7.1 |

### 1.3 O enquadramento de diagnóstico, e onde a analogia quebra

O que o enquadramento **decide de fato**, e não é só tom:

1. **O verbo é "ainda não".** "Ainda não consta", "ainda não chegou". O advérbio não é enfeite:
   ele diz que o estado é reversível e que a página vai registrar quando mudar.
2. **A peça termina com o caminho, não com o veredito.** Ao lado de cada falta, o link para a
   declaração daquele município na API do Tesouro — que serve ao cidadão para conferir e à
   prefeitura para ver o que consta. Um exame útil aponta o que examinar em seguida.
3. **Não existe estado "reprovado".** Não há corte, não há faixa, não há vermelho. Há uma lista.
4. **Nome público**: *"O que a sua cidade ainda não publica"*. Não "nota de transparência", não
   "índice", não "ranking".
5. **Isto é o que alivia a tensão com o princípio 4** (descritivo, nunca prescritivo): um
   diagnóstico enumera achados; uma nota emite juízo. Enquanto a peça for lista de achados com
   motivo e fonte, ela é descritiva no sentido forte — não há adjetivo a remover porque não há
   adjetivo.

**Onde a analogia quebra, e precisa ficar escrito:**

- Um exame é pedido pelo paciente e o resultado é dele. Este é público e ninguém pediu.
- Um exame é lido por quem sabe ler. Este vai para o WhatsApp e pode ser recortado sem o motivo
  ao lado.

Ou seja: **o enquadramento governa a nossa voz e o nosso desenho; ele não é um controle.** O
que impede a peça de virar arma é estrutural — sem ranking, sem nota, comparação só dentro do
grupo, lançamento fora do ciclo eleitoral. Tratar o enquadramento como se fosse proteção
suficiente seria o erro clássico de achar que boa intenção documentada substitui salvaguarda.

---

## 2. Taxonomia da ausência

A regra que separa tudo:

> **Uma falta só é atribuída a um ente se (a) ele era o obrigado a declarar, (b) o prazo já
> venceu, e (c) nós conseguimos perguntar.** Falhando qualquer uma das três, a falta é
> registrada — mas em outra ficha, ou em nenhuma.

| Classe | O que é | Caso real | De quem é | Entra em `E`? | Atribuída ao ente? |
|---|---|---|---|:--:|:--:|
| **A — Fora do universo** | O item não se aplica a este ente | DEC tem grão de conjunto elétrico, não de município; ensino médio não é rede municipal | ninguém | ❌ | ❌ |
| **B — Prazo aberto** | O item existe, mas ainda não venceu | DCA 2025 em agosto de 2026 | ninguém | ❌ | ❌ |
| **C — Ainda não declarou** | Prazo vencido, nada chegou | **7 municípios do Norte sem DCA 2024**: 4 no PA (Vigia, Santa Maria do Pará, Quatipuru, São João da Ponta), 2 no TO (Araguanã, Muricilândia), 1 no AP (Amapá) | o ente | ✅ | ✅ |
| **D — Declarou inválido** | Chegou e é impossível | **31 municípios do TO** com receita de impostos negativa em 2024 | o ente | ✅ | ✅ (rótulo próprio) |
| **E — Suprimido por nós** | Chegou e é válido, mas instável demais para publicar | `n < 5`; grupo de comparação com menos de 5 municípios; denominador abaixo do mínimo do contrato | o projeto | ❌ | ❌ |
| **F — A fonte parou** | O órgão federal deixou de publicar, ou apagou | **IDEB 2019 e 2021 respondem 404** no INEP; **SINASC nacional só existe de 2014 a 2017**; SNIS com host morto | o órgão federal | ❌ | ❌ |
| **G — Falha nossa** | Não coletamos, e o dado estava lá | `download.inep.gov.br` recusa conexão de datacenter — 19 execuções seguidas do Actions | o projeto | ❌ | ❌ |

### 2.1 Por que C e D são classes separadas

Parece detalhe e não é. **C é silêncio; D é ruído que se parece com informação.** Quem ainda
não declarou deixa um buraco que qualquer auditoria enxerga. Quem declara arrecadação negativa
entrega um número que atravessa qualquer painel sem gate de sanidade — e vira "-R$ 3.827 por
morador" em algum lugar. O texto público precisa dizer qual dos dois aconteceu, porque são
situações diferentes e a segunda é, para o próprio município, um problema de sistema que ele
provavelmente não sabe que tem.

Hoje o site não faz essa distinção: `site/src/dados.js → motivoSemDado()` diz honestamente
*"ou a prefeitura não declarou, ou o valor declarado era impossível"*, porque o serving não
carrega o motivo. Trocar essa frase pela frase certa é o primeiro benefício concreto deste
desenho, e vale mesmo que nada mais aqui seja implementado.

### 2.2 As classes F e G são a parte mais valiosa

A classe F não é atribuída a município nenhum — e rende a peça de maior interesse público do
projeto. "O INEP apagou o IDEB de 2019 e 2021" é uma afirmação que:

1. nós podemos provar (o `catalog/watcher_state.json` registra 404 em série; o
   `espelho-defensivo` guardou a cópia de 2023 com sha256);
2. não toca em nenhuma gestão municipal;
3. é exatamente o que ninguém mais está medindo.

A classe G é a que exige mais honestidade nossa. **Enquanto o pipeline do INEP não roda no
Actions, nenhuma falta de dado do INEP pode ser atribuída a um município.** Se algum dia for
mais barato calar sobre a classe G do que declará-la, a medida inteira perdeu a razão de ser.

### 2.3 A taxonomia precisa ser derivada, não editorial

Classificar caso a caso reintroduz o julgamento que a medida existe para evitar. Cada classe
sai de um campo declarado:

| Classe | Origem mecânica |
|---|---|
| A | `Cobertura.alcanca(codigo)` — já existe em `contrato.py` |
| B | `Cobertura.anos` + prazo do item (campo a criar, §8.1) |
| C | ausência de linha no staging **com o manifesto provando que perguntamos** |
| D | achado `CRITICO` de `sanidade.py` com `indicador_afetado` preenchido |
| E | `Confiabilidade.avaliar()` / `MINIMO_GRUPO` — já existem |
| F | `Cobertura.lacunas(inicio, fim)` — já existe |
| G | `manifest.registrar(..., completo=False)` fora da janela, ou ausência de registro |

Seis dos sete já têm o mecanismo em `pipelines/marts/contrato.py` e
`pipelines/common/manifest.py`. Falta o prazo (B) e falta persistir o resultado (§8.2).

---

## 3. Fórmula — parte 1: o inventário

### 3.1 O cálculo por ente

Para um ente `e`, um ano `t` e o catálogo `K` de itens que a Praça Pública publica:

```
E(e,t)  = { k ∈ K : k se aplica a e  ∧  o prazo de k para t já venceu
                     ∧  a fonte de k publicou t  ∧  nós conseguimos coletar }
                                                        ← classes A, B, F e G saem aqui

P(e,t)  = | { k ∈ E : chegou, é válido e foi publicado } |     (publicadas)
I(e,t)  = | { k ∈ E : chegou e foi barrado pelo gate  } |     (inválidas, classe D)
N(e,t)  = | { k ∈ E : ainda não chegou                } |     (não entregues, classe C)

                    P + I + N = |E|      por construção

cobertura(e,t) = P / |E|
```

Três propriedades, e são elas que respondem ao §5.1:

1. **Sem pesos entre itens.** Todo item vale 1. Não há parâmetro de valor a defender. (A
   ponderação por população do §4 é outra coisa e opera em outro nível — §4.2.)
2. **Fecha por construção.** `P + I + N = |E|` é identidade, não escolha. Se não fechar, é bug
   — e vira asserção de teste.
3. **A supressão nossa (classe E) sai do numerador e do denominador.** Descontar do município
   porque nós decidimos não publicar seria inverter a responsabilidade.

### 3.2 A comparação

A régua única do projeto (PRODUTO §2 regra 3) vale sem exceção: **mesma faixa de porte, mesma
Grande Região, mediana**. Sobre `P`, não sobre a fração — contagem se compara com contagem.

**Uma ressalva de método que não pode ficar implícita.** PRODUTO §2.5 diz que ausência nunca
entra em mediana. Aqui ela entra — porque aqui a ausência *é* a medida. A regra existe para
impedir que um município sem DCA vire "R$ 0 de gasto com saúde" e puxe a mediana de reais para
baixo. Nesta medida não se somam reais: contam-se declarações, e uma declaração que não veio
conta como zero declarações porque isso é literalmente verdade. O denominador é o universo
inteiro do grupo, inclusive quem não entregou nada. Precisa estar escrito em
`/metodologia/o-que-ainda-nao-consta`, senão parece violação da regra de ferro.

### 3.3 Exemplo — Aguiarnópolis (TO)

Dado real de `site/public/dados/municipio/1700301.json`, release de 16/08/2026, exercício 2024.

**Aguiarnópolis — TO · 4.502 habitantes · faixa até 5 mil · Norte**

| Item do catálogo | Estado | Classe |
|---|---|---|
| Gasto com educação por morador | R$ 2.112,41 — publicado | — |
| Gasto com saúde por morador | R$ 1.639,93 — publicado | — |
| Impostos arrecadados por morador | **ainda não publicado**: o valor declarado ao Tesouro era negativo | **D** |

```
E = 3     P = 2     I = 1     N = 0        2 + 1 + 0 = 3 ✓
cobertura = 2/3
```

**Grupo de comparação** — as 88 cidades do Norte com até 5 mil habitantes:

| P | municípios | leitura |
|:--:|--:|---|
| 3 de 3 | 70 | consta tudo |
| 2 de 3 | 15 | falta uma — todas por declaração inválida (classe D) |
| 0 de 3 | 3 | a DCA de 2024 ainda não chegou (classe C) |

```
mediana_grupo = 3        (mediana de 88 valores, dos quais 70 são 3)
Aguiarnópolis = 2
```

---

## 4. Fórmula — parte 2: a ponderação por população

### 4.1 A ideia

A falta de uma informação custa em proporção a quanta gente fica sem ela. Um item ausente em
Vigia (PA) deixa 54.062 pessoas sem aquele dado sobre a própria prefeitura; o mesmo item
ausente em Muricilândia (TO) deixa 3.501. O peso segue **as pessoas prejudicadas**, não a
capacidade administrativa do ente — e isso é coerente com o enquadramento de diagnóstico: o
que se mede é o tamanho do vazio de informação na vida das pessoas, não o desempenho de quem
preenche formulário.

A unidade é a **pessoa-informação**: um par (morador, item do catálogo).

```
faltantes(e,t)      = I(e,t) + N(e,t)                       itens ausentes
pessoas_sem(e,t)    = pop(e,t) × faltantes(e,t)             pessoa-informação ausentes
esperado(e,t)       = pop(e,t) × |E(e,t)|                   pessoa-informação esperadas

Para um conjunto S de entes (UF, faixa, região, país):

                         Σ_{e∈S} pop(e)·P(e)
cobertura_pessoas(S) = ───────────────────────
                         Σ_{e∈S} pop(e)·|E(e)|

                         Σ_{e∈S} P(e)
cobertura_entes(S)   = ─────────────────
                         Σ_{e∈S} |E(e)|
```

### 4.2 A propriedade que decide onde o peso pode ser usado

Para **um único município**, o peso se cancela:

```
cobertura_pessoas({e}) = pop(e)·P(e) / (pop(e)·|E(e)|) = P(e)/|E(e)| = cobertura(e)
```

Isso é importante e é uma boa notícia:

- **A ponderação não muda nada na página do município.** Não existe versão ponderada da nota de
  ninguém, porque a nota de ninguém existe.
- **A ponderação é uma propriedade do agregado**, não do ente. Ela nunca aparece onde há nome
  de prefeito — só onde há "o Pará", "a faixa até 5 mil", "o Brasil".
- Portanto **ela não pode ser lida como grade de gestão**: no nível em que ela opera, não há
  gestão individual sendo avaliada.

O que **sobra** para o nível municipal é a forma absoluta, que é puramente descritiva e não é
taxa: *"em Vigia, 54.062 moradores ainda não têm nenhum dado de finanças da sua prefeitura
para 2024"*. Uma contagem de pessoas, com fonte e data. É a forma mais diagnóstica de todas —
e a que menos se parece com nota.

### 4.3 Dois exemplos reais e contrastantes

**(a) Mesma falta, custo humano 15 vezes maior.** Dois municípios do Norte sem nenhuma
declaração de 2024 — ambos com `P = 0 de 3`, indistinguíveis pelo inventário do §3:

| | Vigia (PA) | Muricilândia (TO) |
|---|--:|--:|
| População | 54.062 | 3.501 |
| Itens esperados (`\|E\|`) | 3 | 3 |
| Itens publicados (`P`) | 0 | 0 |
| `cobertura` (§3) | **0 de 3** | **0 de 3** |
| **Pessoa-informação ausentes** | **162.186** | **10.503** |
| Razão | **15,4×** | 1× |

Pelo inventário são o mesmo caso. Pela ponderação, o vazio de Vigia é 15,4 vezes maior. As duas
leituras são verdadeiras e respondem a perguntas diferentes: *"quantas prefeituras estão sem
informar?"* e *"quantas pessoas estão sem informação?"*.

**(b) Capital × município de até 5 mil.** Aqui vale registrar um achado antes: **as 7 capitais
do Norte entregaram os 3 itens** — Manaus (2.303.732), Belém (1.397.315), Porto Velho (517.709),
Macapá (489.676), Boa Vista (485.477), Rio Branco (389.001) e Palmas (328.499), todas 3 de 3.
Não existe capital com lacuna no dado real, então o contraste com capital só pode ser
**contrafactual — e vai marcado como tal, porque não aconteceu**:

| Cenário (Norte, exercício 2024) | `cobertura_entes` | `cobertura_pessoas` |
|---|--:|--:|
| **Real** — 7 municípios sem nada + 31 com item inválido | **96,15%** | **99,02%** |
| Perfeito (hipotético) | 100,00% | 100,00% |
| *Contrafactual: só Manaus falhando em tudo* | 95,93% | 86,77% |

Lendo as quedas em pontos percentuais:

| Evento | Custa em `cobertura_entes` | Custa em `cobertura_pessoas` |
|---|--:|--:|
| As **38 faltas reais** (7 municípios sem nada + 31 itens inválidos) | **−3,85 pp** | **−0,98 pp** |
| **Manaus sozinha**, se falhasse em tudo (não falhou) | −0,22 pp | **−12,25 pp** |

**As duas medidas apontam para lados opostos, e a diferença é de mais de uma ordem de
grandeza.** Uma falha em Manaus custaria 12,5 vezes mais que todas as 38 faltas reais da região
somadas na medida ponderada — e 17 vezes *menos* que elas na medida por ente. Nenhuma das duas
está errada. Publicar só uma é que estaria.

### 4.4 A regra que decorre: dois números, sempre juntos

> **`cobertura_pessoas` nunca aparece sem `cobertura_entes`, e vice-versa.** Nem no texto, nem
> no gráfico, nem no share card.

Porque cada uma sozinha esconde a outra metade:

- **Só por ente** → sobrepesa os pequenos. No Norte, os 88 municípios de até 5 mil habitantes
  são 19,6% dos municípios e 1,6% da população. Uma medida que os conta igual a Manaus diz
  pouco sobre quantos brasileiros estão sem informação.
- **Só por pessoa** → é dominada por meia dúzia de cidades. Os 4 municípios acima de 500 mil
  são 0,9% dos municípios do Norte e **25,1% da população**. E, no caso real, a ponderação
  **melhora** o número (99,02% contra 96,15%) justamente porque as faltas estão concentradas
  onde mora pouca gente — publicar só ela apagaria o fato de que 7 prefeituras não mandaram
  nada.

Redação-padrão do agregado, com os números reais:

> No Norte, **443 das 450 prefeituras** informaram pelo menos um dado de 2024 — 7 não
> informaram nenhum. Em pessoas: **99,0% dos moradores da região** têm ao menos parte dos dados
> da sua cidade publicados aqui, e **112.426 não têm nenhum**.

Duas frases, quatro números, nenhum adjetivo. E o número absoluto de pessoas (112.426) é o que
comunica melhor — é concreto, não é taxa e não é comparável a nada que pareça nota.

### 4.5 Avaliação: a ponderação resolve ou introduz problema?

**Resolve, com escopo definido — e introduz um problema novo que exige a regra do §4.4.**

**O que resolve bem:**

1. **Dá ao agregado o denominador certo.** "96,15% das declarações chegaram" é uma frase sobre
   formulários; "99,0% das pessoas têm o dado da sua cidade" é uma frase sobre cidadãos, que é
   o público do projeto. A segunda é a pergunta que importa quando se fala do país.
2. **Tira o viés de porte do agregado sem corrigir nada.** Uma média simples entre municípios
   dá a 1.284 municípios de até 5 mil habitantes o mesmo peso que às capitais, o que distorce
   qualquer leitura nacional. A ponderação não "compensa" o pequeno: ela mede outra coisa,
   corretamente.
3. **Não toca no nível de risco.** Como cancela no município (§4.2), ela adiciona zero risco na
   única página que nomeia um ente.
4. **Cabe no enquadramento de diagnóstico.** "Quantas pessoas estão sem esta informação" é
   epidemiologia — prevalência, não culpa.

**O que introduz:**

| Problema | Evidência real | Tratamento |
|---|---|---|
| **Dominação pelas capitais** | 4 municípios = 0,9% dos entes e 25,1% da população do Norte; Manaus sozinha moveria o número 12,5× mais que todas as faltas reais | Regra do §4.4: os dois números sempre juntos. E nunca usar o ponderado como número único de um recorte |
| **Volatilidade** | O agregado ponderado passa a depender de meia dúzia de declarações. Um atraso pontual de uma capital derruba o número da região inteira e vira manchete falsa sobre "piora da transparência" | Publicar sempre a decomposição ("a variação vem de N municípios; o maior é X"), e tratar variação acima de um limiar como o PRODUTO já trata: trava para revisão humana |
| **Inverte a prioridade do nosso trabalho** | Se a métrica guiar em que pipeline investir, o peso diz "só cidade grande importa" — o oposto da tese do projeto, que existe porque ninguém cobre o município pequeno | **A ponderação é medida de comunicação, nunca de priorização interna.** Fila de trabalho usa contagem de entes |
| **É um peso** | O §5.1 argumenta que a medida não é índice composto por não ter ponderação. A população é a única, e precisa ser defendida (§5.1) | Peso de *alcance*, não de *valor*: mesma operação do "por morador" que o site já faz em todos os cards |
| **A população é estimada** | `fonte_populacao = 'siconfi/entes'`; entre censos é projeção (`Natureza.ESTIMADO`). O erro do denominador entra na medida | Declarar fonte e ano da população junto do número, como já se faz nos indicadores per capita |
| **Ranking por pessoas é ranking por população** | "Cidades com mais gente sem informação" seria, na prática, a lista das maiores cidades com qualquer lacuna | Não publicar esse ranking. O número absoluto aparece **na página daquele município**, não em lista ordenada |

**Conclusão da avaliação.** A ponderação entra, no nível agregado, em par obrigatório com a
contagem de entes, e no nível municipal apenas na forma absoluta ("X moradores ainda não têm").
Ela não substitui a defesa do §5.2 contra o viés de porte — porque no município ela cancela, e
é justamente lá que o viés morde. As duas defesas são complementares e nenhuma das duas é
dispensável.

---

## 5. As quatro tensões

### 5.1 "O projeto decidiu não fazer índice composto"

A decisão de INDICADORES.md §1 está certa e continua valendo. A questão é se esta medida é um
índice composto. **Não é — e a diferença é estrutural, não retórica.**

Um índice composto **comensura grandezas heterogêneas**: pega mortalidade infantil (óbitos por
mil), IDEB (nota de 0 a 10) e renda (reais), normaliza cada uma para uma escala arbitrária e
soma com pesos. As três objeções do §1 caem sobre essa operação.

Esta medida **conta ocorrências de um único evento homogêneo**: "a declaração chegou?". É da
mesma família de "12 das 15 câmaras responderam ao pedido de informação" — proporção de um
conjunto contável, não média ponderada de coisas diferentes.

| Objeção do §1 | Por que não se aplica |
|---|---|
| **"Esconde o que mudou"** | Aqui o detalhamento **é** a apresentação. A peça publicada é a lista item a item; a fração é subproduto. Não dá para o número cair sem que a linha que caiu esteja escrita ao lado |
| **"Exige confiar na ponderação"** | Não há ponderação **de valor**. Todo item pesa 1. A única ponderação é por população (§4), que é peso de alcance e é auditável com um número que o leitor já tem na primeira linha da página: a população da cidade |
| **"Vira ranking de prefeito"** | Esta **procede em parte** — e é tratada com decisão de produto, não com argumento: sem ranking, sem nota, sem selo, sem OG card, sem cor, e lançamento fora do ciclo eleitoral (§5.4) |

**A ponderação por população é um índice composto disfarçado?** Não, e o teste é simples: um
índice composto usa peso para *tornar comparáveis coisas incomparáveis*. Aqui os itens já são
comparáveis (todos valem 1) e o peso não incide sobre eles — incide sobre a **agregação entre
entes**, que é exatamente onde "por morador" já opera em todo o site. Ninguém chama "gasto com
saúde por morador" de índice composto.

**Onde eu concedo.** Há uma escolha discricionária escondida: **quais itens entram em `K`.** Um
catálogo com 5 itens de saúde e 1 de finanças mediria outra coisa. Três defesas:

1. **`K` não é escolhido para esta medida.** É o catálogo que o site já publica, decidido em
   INDICADORES.md por critérios que nada têm a ver com transparência. Manipular a medida exige
   manipular o produto inteiro.
2. **`K` é enumerado na página.** O leitor vê os itens, não só o total.
3. **Mudança em `K` é evento datado** e entra em `/erratas` com o efeito sobre a série — porque
   acrescentar um item muda a medida de todos os 5.570 municípios retroativamente.

**Proibições que decorrem, e que devem virar teste:** nada de nota 0–100, letra, estrela, selo,
ou "índice de transparência" na copy. A fração `P/|E|` existe no parquet de `/dados`; o que a
página anuncia é "2 de 3".

### 5.2 "Município pequeno tem menos capacidade administrativa"

**A objeção não é hipotética — está nos dados de hoje.** Exercício 2024, os 450 municípios do
Norte, por faixa de porte:

| Faixa | municípios | % dos entes | % da população | itens publicados | sem nenhuma declaração |
|---|--:|--:|--:|--:|--:|
| até 5 mil | 88 | 19,6% | 1,6% | **90,9%** | 3 |
| 5 a 10 mil | 69 | 15,3% | 2,7% | 94,2% | 1 |
| 10 a 20 mil | 101 | 22,4% | 8,0% | 97,0% | 1 |
| 20 a 50 mil | 120 | 26,7% | 19,8% | 98,9% | 1 |
| 50 a 100 mil | 43 | 9,6% | 15,9% | 97,7% | 1 |
| 100 a 500 mil | 25 | 5,6% | 26,9% | **100,0%** | 0 |
| acima de 500 mil | 4 | 0,9% | 25,1% | **100,0%** | 0 |

O gradiente é monotônico onde há massa. Um score ingênuo publicaria isso como mérito e
penalizaria a faixa que reúne **1.284 municípios no país** — 23% do total — por ter menos gente
no setor de contabilidade.

**Importante: a ponderação por população não resolve isso.** Ela cancela no município (§4.2),
e é no município que o viés morde. O que resolve é a régua, em cinco camadas:

1. **A comparação só existe dentro da faixa e da região.** Aguiarnópolis nunca aparece ao lado
   de Belém: aparece ao lado das outras 87 do Norte com até 5 mil habitantes, que enfrentam a
   mesma estrutura. **É a defesa principal, e a única mecânica** — sai da
   `dim_municipio.grupo_comparacao`, que já existe.
2. **Nenhum ranking nacional nem estadual de cobertura.** Um ranking nacional seria, com boa
   aproximação, um ranking de população invertido. Posição só com denominador e grupo, como
   manda PRODUTO §2 regra 6.
3. **A tabela acima é publicada como contexto.** Em `/metodologia/o-que-ainda-nao-consta`, com
   a frase: *"cidades menores publicam menos, e o motivo mais provável é ter menos gente para
   preencher formulário — não menos vontade de informar."* Publicar o viés desarma o uso
   indevido melhor do que escondê-lo.
4. **Verbo neutro e reversível.** "Ainda não consta", "ainda não chegou". Nunca "omitiu",
   "escondeu", "deixou de prestar contas", "descumpriu".
5. **Denominador honesto por porte.** Item que só se aplica a município com determinada
   estrutura sai de `E` pela classe A, em vez de virar falta.

**O que essas defesas não resolvem.** Dentro da faixa "até 5 mil" ainda há variação enorme de
capacidade, e a medida não a enxerga. Ela **reduz** o viés de sete faixas para uma; não o
elimina. §7 registra isso como limitação, não como detalhe.

### 5.3 "Nem toda ausência é culpa do ente avaliado"

Resolvida pela taxonomia do §2, mecanicamente: as classes A, B, F e G **não entram no
denominador**.

| Caso real | Classe | Efeito na medida municipal |
|---|:--:|---|
| IDEB 2019 e 2021 (404 no INEP) | F | Não entram em `E` de município nenhum. `Cobertura.anos` do IDEB não inclui 2019 nem 2021, e `lacunas()` já devolve o buraco para o gráfico. **O 404 entra na ficha do INEP** |
| SINASC nacional 2018–2024 inexistente | F | Idem. Mortalidade infantil e pré-natal só entram em `E` nos anos em que a fonte existe |
| SNIS com host morto | F | Idem, com um agravante que nos favorece: a série sumiu enquanto tentávamos espelhar, e temos o registro |
| INEP recusa conexão de datacenter | G | **Nunca entra em `E`.** Falha nossa, declarada como nossa em `/metodologia` |
| DCA 2024 ausente (7 municípios do Norte) | C | Entra, e é o coração da medida |
| Impostos negativos (31 do TO) | D | Entra, com rótulo próprio |

`contrato.motivo_ausencia()` já separa `fora_do_universo` de `nao_declarou` — é a semente certa.
Faltam `declarou_invalido`, `fonte_nao_publicou`, `prazo_aberto` e `nao_coletado` (§8.3).

**Teste de aceitação da regra**, que deve virar `test_transparencia.py`: um município sem
nenhuma falta própria sai com `P = |E|` mesmo em um ano em que três fontes federais sumiram. Se
sair diferente, a implementação confundiu falha da fonte com falha do ente.

### 5.4 "Estamos em período eleitoral"

SEGURANCA §6.3 é literal: *"de agosto à diplomação, nenhuma feature nova de destaque/ranking —
só atualização de dados e correções"*. E §6.2: *"metodologia pública; mudanças só entre
releases, datadas; nunca no ciclo eleitoral"*.

O enquadramento de diagnóstico **reduz** o risco — mas não o elimina, e não altera a
recomendação. Há um argumento tentador para abrir exceção: **2026 é eleição estadual e federal;
prefeito não está na urna**. Recomendo recusá-lo:

1. Prefeito não é candidato, mas é ativo de campanha estadual. "A cidade do candidato X esconde
   dados" é um post pronto, e não precisa que a nossa página diga "esconde" — basta que ela
   seja recortável. O enquadramento vive no nosso texto; o print não leva o enquadramento junto.
2. **Inventar exceção no meio do período é exatamente o que a regra existe para impedir.** O
   valor da regra vem de ela ser cega.

| Fase | Janela | O que |
|---|---|---|
| Agora → diplomação | ago–dez/2026 | **Peça A** (estado das fontes), o modelo de dados (§8.1–8.3), e a medida como **gate interno** de qualidade — cobertura por UF vira alerta de operação, não página. Nada disso é destaque nem ranking, e nada fala de município nominalmente |
| Diplomação → release | dez/2026 → jan/2027 | Publicar `/metodologia/o-que-ainda-nao-consta` **antes** de qualquer número. Metodologia primeiro é o que separa diagnóstico de acusação |
| Depois | a partir de 2027 | **Peças B e C**, no primeiro release após a metodologia estar no ar por pelo menos um ciclo |

Isso conversa com a fila real: a medida precisa de catálogo maior que 3 itens (§7.2), o que a
coloca depois do M1 de qualquer jeito. **O congelamento não está custando nada** — a regra
editorial e a dependência técnica apontam para a mesma data.

---

## 6. Como aparece na interface

### 6.1 Onde não aparece

- **Não é card de topo.** Não disputa a primeira dobra com o dado que o leitor veio buscar.
- **Não entra na OG image.** O share card viraliza sem contexto; é o pior lugar possível para
  um número sobre um ente.
- **Não tem verde/âmbar/laranja.** PRODUTO §2.4 reserva cor com valência para *resultado* com
  direção pactuada. Publicar declaração não é resultado para o cidadão. Cor neutra e rótulo
  textual, como nos indicadores de composição de gasto.
- **Não tem selo, medalha, estrela nem "nível".**
- **Não tem taxa ponderada por município** — no município a ponderação cancela (§4.2), e o que
  aparece é a contagem absoluta de pessoas.

### 6.2 Onde aparece

**(a) No card que faltou** — `SemDado.astro` já existe e já reserva o espaço com hachura, selo
e motivo. Muda só o conteúdo: o motivo passa a ser específico em vez de disjuntivo.

| Classe | Texto de hoje | Texto proposto |
|---|---|---|
| C | "Ou a prefeitura não declarou o dado ao Tesouro, ou o valor declarado era impossível…" | "A prefeitura de {município} ainda não enviou a declaração de 2024 ao Tesouro Nacional. Com isso, {população} moradores não têm este dado. Aconteceu com 7 das 450 cidades do Norte." |
| D | (mesmo texto) | "A prefeitura declarou este valor ao Tesouro como negativo, o que não pode acontecer — então não publicamos. Aconteceu com 31 cidades do Tocantins em 2024. → ver a declaração no Tesouro" |
| F | (mesmo texto) | "O INEP não publica mais os dados de 2019 e 2021 — a página do órgão responde 'não encontrado'. Isso não depende da prefeitura. Nós guardamos uma cópia da edição de 2023: {link}." |
| G | (mesmo texto) | "Não conseguimos coletar este dado. O problema é nosso, não da prefeitura: {motivo}." |

Isso sozinho já é uma melhoria grande, e é a única parte que eu implementaria independentemente
do resto.

**(b) Um bloco de fechamento**, depois dos indicadores e antes da malha de links — não um card,
um parágrafo com lista:

```
┌──────────────────────────────────────────┐
│ ▨  O QUE ESTA PÁGINA AINDA NÃO TEM       │
│                                          │
│ Das 3 informações que acompanhamos para  │
│ 2024, Aguiarnópolis tem 2.               │
│                                          │
│ ✓ Gasto com educação por morador         │
│ ✓ Gasto com saúde por morador            │
│ ▨ Impostos arrecadados por morador       │
│   O valor declarado ao Tesouro era       │
│   negativo, o que não pode acontecer.    │
│   4.502 moradores ficam sem este dado.   │
│   → ver a declaração no Tesouro          │
│                                          │
│ O típico das 88 cidades parecidas — as   │
│ do Norte com até 5 mil habitantes — é    │
│ 3 de 3.                                  │
│                                          │
│ Fonte: Tesouro Nacional/SICONFI ·        │
│ dados de 2024 · coletado em 16/08/2026   │
└──────────────────────────────────────────┘
```

Descritivo linha a linha: cada item é fato com link para a origem. A única frase avaliativa
possível — "está abaixo das parecidas" — não é escrita; o leitor compara 2 com 3 sozinho.

Para os 7 municípios da classe C, o bloco é a página quase inteira, e é assim que deve ser:

> Nenhum dado de finanças de Vigia para 2024 está publicado aqui. A prefeitura ainda não enviou
> a declaração ao Tesouro Nacional. **54.062 moradores** ficam sem esta informação. Das 450
> cidades do Norte, 7 estão nesta situação.

**(c) `/fontes` — o estado das fontes** (peça A, a que pode sair primeiro). Uma linha por órgão
e série:

| Fonte | Série esperada | Estado | Nossa cópia |
|---|---|---|---|
| INEP — IDEB anos iniciais | bienal | 2019 e 2021 respondem 404 | 2023, sha256 no manifesto |
| DataSUS — SINASC nacional | anual | só 2014–2017 em arquivo nacional | espelhada |
| SNIS — série histórica | anual | host fora do ar; catálogo federal aponta para servidor morto | não obtida |

Sem adjetivo, sem "descaso", sem "apagão". Data, endereço, resposta HTTP, hash.

**(d) `/uf/{uf}` e nacional — o retrato agregado** (peça C), sempre com os dois números do §4.4
na mesma frase, e sempre com o número absoluto de pessoas ao lado da taxa.

**(e) No "Em resumo"** — nada novo a construir. PRODUTO §2.1 já permite que uma das três frases
seja lacuna de dado. Muda só a frase ficar específica.

### 6.3 Acessibilidade e tom

Vale tudo do PRODUTO §3 e §7: hachura + ícone + texto (cor nunca é canal único), Flesch pt-BR
≥ 60 no CI editorial, frases de até 20 palavras, `role="img"` e tabela equivalente onde houver
gráfico. O bloco do §6.2(b) é HTML semântico — lista, não imagem. E "4.502 moradores" leva
`aria-label` por extenso, como todo número do site.

---

## 7. Limitações honestas

### 7.1 Mede o nosso catálogo, não a transparência do município

Uma prefeitura com portal exemplar, diário oficial em HTML e resposta a LAI em 3 dias aparece
igual a uma que não tem nada disso, se as duas mandaram a mesma DCA. E aparece **pior** que uma
prefeitura opaca em tudo o mais que mandou a DCA no prazo. É a limitação de fundo, e não tem
conserto dentro do escopo atual — tem só declaração.

### 7.2 Com 3 itens, a medida salta em terços

O catálogo de hoje tem três indicadores, e **os três vêm da mesma declaração**:

- Um formulário faltando derruba a cobertura de 100% para 0%. Não há gradação.
- As faltas são perfeitamente correlacionadas: hoje a medida diz "mandou a DCA?", e nada mais.

**Precondição dura: `K` com pelo menos 5 itens de pelo menos 3 fontes distintas antes de
publicar qualquer taxa.** Isso põe a peça B depois de M1.3 (IBGE) e M1.4 (INEP) — o que coincide
com o §5.4. A peça A não depende disso.

### 7.3 Limitações específicas da ponderação por população

Além do §4.5: a ponderação assume que **toda pessoa é afetada igualmente por toda ausência**, o
que é falso em graus que não medimos — o dado de creche interessa mais a quem tem filho pequeno,
o de IPTU a quem tem imóvel. É a simplificação que torna a conta possível, e ela precisa estar
escrita como simplificação, não como fato.

### 7.4 Onde a medida seria injusta

| Situação | Por que erra | Mitigação |
|---|---|---|
| **Coletamos mal e não percebemos** | Vira classe C (do ente) o que é classe G (nossa). É o pior modo de falha, porque transfere culpa | `E` só admite item cujo manifesto prove tentativa bem-sucedida de consulta. Sem prova de que perguntamos, o item sai do denominador |
| **Retificação posterior** | A DCA é `revisavel=True`. Um retrato de agosto aponta uma falta que já não existe em outubro | Data de coleta visível (já é regra); recoleta antes de cada release; **melhora reflete no release seguinte, e piora vira errata** |
| **Falso positivo do gate de sanidade** | Classe D depende de `sanidade.py` estar certo. Check ruim transforma dado válido em "declarou impossível" | Todo achado D exibido com o valor bruto e link para a declaração na API do Tesouro. O leitor confere; não pedimos fé |
| **Município novo ou mudança territorial** | Denominador errado — o ente não existia, ou mudou de código. Afeta também o peso populacional | `Cobertura.alcanca()` por ano; instalação de município é classe A |
| **Calamidade, intervenção, prefeitura sem prefeito** | A falta é real e a atribuição é injusta | Não temos esse dado e não vamos ter. **Fica declarado como não coberto** |
| **População desatualizada** | O peso usa estimativa (`siconfi/entes`), não contagem. Cidade que cresceu muito desde a referência tem seu vazio subestimado | Fonte e ano da população impressos junto do número |
| **Faixa "até 5 mil" internamente heterogênea** | §5.2 — o viés de porte é reduzido, não eliminado | Declarar |

### 7.5 O erro que custa mais caro

Todos os números do site hoje são **transcrições**: valor errado é erro do Tesouro ou do nosso
pipeline. Este é o primeiro número que é **uma afirmação nossa sobre a conduta de um ente**.
Dizer "ainda não declarou" sobre quem declarou é o pior erro que a Praça Pública pode publicar —
pior que um valor trocado, porque não se corrige com um número novo.

Isso traz uma consequência que o enquadramento de diagnóstico não anula: **a Fase 1 passa a
precisar da postura jurídica que SEGURANCA §2 reservou para a Fase 2** — direito de resposta,
texto padrão de resposta a notificação extrajudicial, errata com destaque. Ou se aceita esse
pacote junto com a medida, ou não se publica a medida.

---

## 8. O que precisa existir antes

### 8.1 Contrato: prazo, não só defasagem

`Cobertura` tem `defasagem_meses` (quando o dado *costuma* sair). A medida precisa de quando o
dado *deveria* ter saído — a fronteira entre classe B (prazo aberto) e classe C (não chegou).
Campo novo em `Cobertura`, com o prazo legal quando existir (a DCA tem prazo na LRF) e o prazo
observado quando não existir, **sempre documentado na origem**.

### 8.2 Um fato de cobertura, porque hoje a ausência não tem linha

`fato_indicador.py` usa `INNER JOIN` de propósito: quem não declarou não vira linha com zero.
Está certo para o indicador e **inviabiliza a medida** — o que não existe não se conta.

Precisa de `fato_cobertura_municipio` (município × ano × item × estado), montado por `LEFT JOIN`
contra `dim_municipio`, com `estado ∈ {publicado, nao_declarou, invalido, fora_universo,
prazo_aberto, fonte_nao_publicou, nao_coletado}`, `motivo` legível, `evidencia` (chave do
manifesto ou achado de sanidade) e `populacao_referencia` + `fonte_populacao` (para o peso do
§4 ser reproduzível sem novo join). Tabela nova; nenhuma alteração no fato atual.

### 8.3 `motivo_ausencia()` com os estados que faltam

Hoje devolve `fora_do_universo`, `nao_declarou` ou `None`. Faltam `declarou_invalido` (de
`sanidade.py` via `indicador_afetado`), `fonte_nao_publicou` (de `Cobertura.lacunas`),
`prazo_aberto` (§8.1) e `nao_coletado` (do manifesto). Extensão da função existente, com o
teste que hoje cobre C/A estendido às outras.

### 8.4 Corrigir uma regressão que a medida torna visível

**Os 7 municípios do Norte sem DCA 2024 não têm página nenhuma.** `serving.py` itera sobre o
fato, e quem não tem linha no fato não recebe JSON — então Vigia (PA), Araguanã (TO) e os
outros cinco simplesmente não existem no site. Contraria PRODUTO §4: *"município quase sem dados
tem página mesmo assim… nunca 404 para município válido"*.

**São exatamente os municípios sobre os quais a medida falaria** — e somam **112.426 pessoas**
sem nenhum dado e sem nem sequer uma página. Hoje são invisíveis; a medida os tornaria os mais
visíveis do site. `serving.py` precisa iterar sobre `dim_municipio`, não sobre o fato.

*(Correção de bug, não feature nova — cabe dentro do congelamento eleitoral.)*

### 8.5 Catálogo mínimo

`K` com ≥ 5 itens de ≥ 3 fontes (§7.2). Depende de M1.3 e M1.4.

### 8.6 População com proveniência

O peso do §4 precisa de população com fonte e ano declarados. Hoje vem de `siconfi/entes`
(`dim_municipio.fonte_populacao` já registra isso); no M1.3 passa a ser estimativa oficial do
IBGE, e **a troca muda todos os números ponderados retroativamente** — evento de errata, como
qualquer mudança em `K`.

### 8.7 Página de metodologia, publicada antes

`/metodologia/o-que-ainda-nao-consta`, com: o que a medida não mede (§1.2), o enquadramento e
onde ele quebra (§1.3), a taxonomia (§2), as duas fórmulas (§3 e §4), a regra dos dois números
(§4.4), a tabela de viés de porte (§5.2) e as limitações (§7). No ar **antes** do primeiro
número.

### 8.8 Direito de resposta estendido à Fase 1

§7.5. Canal, prazo e texto padrão, valendo para esta medida.

### 8.9 Testes que precisam existir junto

1. `P + I + N = |E|` para todo ente e ano (identidade, §3.1).
2. Ente sem falta própria sai com `P = |E|` mesmo com fonte federal caída (§5.3).
3. `cobertura_pessoas({e}) == cobertura(e)` para município isolado — a propriedade do §4.2 é o
   que garante que a ponderação não vaza para a página individual.
4. Nenhum texto publica `cobertura_pessoas` sem `cobertura_entes` no mesmo bloco (§4.4).
5. Nenhuma string de nota, letra, selo ou "índice de transparência" no serving nem no site.
6. `serving.py` emite um JSON para cada município de `dim_municipio` (§8.4).

---

## 9. Decisões que dependem do mantenedor

| # | Decisão | Por que não é minha |
|---|---|---|
| 1 | **Publicar a peça A (`/fontes`) agora?** É a de maior valor e menor risco, e o material já existe no watcher e no espelho. Mas é rota nova durante o congelamento — e "rota nova" pode ser lida como destaque, ainda que fale de órgão federal | Interpretação da própria regra editorial do projeto |
| 2 | **Aceitar o pacote jurídico da Fase 2 na Fase 1** (direito de resposta, texto de notificação). Sem ele a peça B não sai — §7.5 | Exposição pessoal do mantenedor |
| 3 | **Cinco itens é o piso certo para `K`?** Escolhi 5 por simetria com a regra de `n ≥ 5` do projeto, não por evidência | Julgamento editorial |
| 4 | **A regra dos dois números (§4.4) é dura ou preferencial?** Recomendo dura, com teste no CI. Ela custa espaço em toda peça agregada | Peso entre rigor e concisão |
| 5 | **Publicar `cobertura_pessoas` por município em `/dados`**, mesmo cancelando na página? Argumento a favor: dado aberto. Contra: convida terceiro a montar o ranking que decidimos não fazer, com a nossa marca na fonte | Postura do projeto sobre reúso |
| 6 | **Nome público.** Proponho "O que a sua cidade ainda não publica". Alternativas: "O que ainda não consta", "O que falta chegar" | Voz do produto |
| 7 | **Retrato agregado na página do estado (§3 do briefing original)**: publicar a taxa dos municípios de uma UF na página do governo estadual? O estado não responde por ela, e o leitor vai atribuir | Risco de atribuição indevida |

---

## 10. Resumo em dez linhas

1. É diagnóstico, não nota: inventário do que ainda não consta, com motivo, fonte e alcance.
2. Mede entregas ao nosso catálogo — não transparência LAI, não qualidade de gestão, e conta
   **o que nós obtivemos**, não o que o município publicou.
3. Sete classes de ausência; só duas (ainda não declarou, declarou inválido) são atribuídas ao
   ente.
4. `P + I + N = |E|`, sem peso entre itens — por isso não é índice composto; a lista item a item
   é a apresentação, não um detalhamento opcional.
5. A ponderação por população **cancela no município** e só opera no agregado: ela nunca aparece
   onde há nome de prefeito.
6. No município ela vira contagem absoluta — "54.062 moradores de Vigia ainda não têm nenhum
   dado de finanças de 2024" — que é a forma mais diagnóstica e a que menos parece nota.
7. **As duas medidas divergem por ordem de grandeza**: as 38 faltas reais do Norte custam
   −3,85 pp por ente e só −0,98 pp por pessoa; uma falha de Manaus custaria −0,22 pp por ente e
   −12,25 pp por pessoa. Daí a regra dura: **os dois números sempre juntos**.
8. O viés de porte é real e está medido (90,9% na faixa até 5 mil × 100% acima de 100 mil no
   Norte); a ponderação **não** o corrige — quem corrige é comparar só dentro da faixa, e
   publicar o viés.
9. Falha da fonte federal e falha nossa nunca entram no denominador do município.
10. Nada municipal no ar antes da diplomação; a dependência técnica aponta para a mesma data.
    Se só uma coisa daqui for feita: **trocar o texto disjuntivo de `motivoSemDado()` pelo
    motivo específico**, e dar página aos 7 municípios que hoje não têm nenhuma.

---

**Fontes dos números deste documento** — `site/public/dados/municipio/*.json` (443 arquivos,
release de 16/08/2026, exercício 2024) e `data/staging/siconfi/entes.parquet` (5.570
municípios, 26 estados, DF e União; população de referência do SICONFI). Os casos qualitativos
vêm de `docs/ciencia-politica/CHECKLIST-INDICADORES.md` (B1, B2), `docs/ESTADO.md` §4–5 e dos comentários de
`pipelines/marts/sanidade.py` e `pipelines/marts/fato_indicador.py`. O cenário de Manaus em
§4.3(b) é **contrafactual explícito**: as 7 capitais do Norte entregaram os 3 itens.
