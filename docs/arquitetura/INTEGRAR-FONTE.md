# Integrar uma base de dados nova — o procedimento

> Estratégia aplicável a **qualquer** fonte, definida em 16/08/2026. Não é conselho: cada etapa
> termina num artefato verificável, e as três primeiras são portões — não se avança sem elas.
>
> A pergunta que este documento responde de uma vez por todas: *"precisamos baixar isso?"*

## A regra que sustenta tudo

**Computar não exige cópia. Publicar exige.**

Medido em 16/08/2026: o DuckDB contou 3 milhões de linhas de um parquet remoto de 50 MB em
**0,4 s sem baixar o arquivo**. Então explorar uma fonte é barato e não precisa de storage nenhum.

Mas todo número publicado tem que ter seu insumo guardado por nós, datado e com hash. O motivo não é
técnico, é editorial: emitir errata (regra 7) é dizer *"no dia X a fonte dizia Y, hoje diz Z"*. Sem o
insumo guardado, isso vira palavra contra palavra — e a página perde a única prova de boa-fé que tem.

O que se guarda é **o insumo do número**, nunca "a fonte inteira". Confundir os dois é o que faz o
storage virar gargalo: guardar o PNCP inteiro custaria 57,7 GB/ano para sustentar zero indicadores.

## Os cinco modos de guarda

| Modo | O que fica conosco | Publica? |
|---|---|:--:|
| `integral` | os bytes originais inteiros | ✅ |
| `recorte` | só a fatia que alimenta um indicador | ✅ |
| `colheita` | as respostas de cada execução, com os parâmetros usados | ✅ |
| `remota` | **nada** — leitura por `httpfs` para dimensionar | ❌ |
| `nenhuma` | nada, e o motivo escrito | ❌ |

A fronteira de `remota` é o que fecha a conta: **como ela nunca publica, não existe número cujo
insumo esteja fora do nosso alcance.** Ler remoto para decidir é grátis e legítimo; ler remoto para
publicar seria trocar auditabilidade por economia de disco.

---

## As sete etapas

### 1. Reconhecer — mede, não baixa

```bash
python -m pipelines.reconhecer --url https://exemplo.gov.br/base.zip \
    --unidades 5570 --requisicoes 5570 --throttle 1 --risco alto --filtro
```

Sai um relatório e o **bloco `guarda:` pronto para colar** no `config/fontes.yaml`, com o motivo já
escrito. Se a fonte publica parquet, dá para ir além sem baixar nada:

```sql
SELECT count(*), min(ano), max(ano) FROM read_parquet('https://.../base.parquet');
```

**Artefato**: o bloco `guarda:` e a resposta a "essa fonte tem o que eu preciso, no grão que eu
preciso?".

### 2. Decidir o modo — três perguntas, nesta ordem

A primeira que responde decide. A ordem importa: risco de sumiço ganha de volume, porque bytes se
compram e série apagada não volta.

| | Pergunta | Se sim |
|---|---|---|
| **Q1** | A fonte **já provou** que some? (não "pode sumir" — já sumiu) | `integral` agora, mesmo sem indicador definido |
| **Q2** | Cobrir o país cabe em **6 h** de runner? | segue para Q3; se não, `recorte` |
| **Q3** | Cabe no orçamento de bytes? | ≤ 2 GB → `integral` · > 20 GB → `recorte` · API com filtro e resposta pequena → `colheita` |

O teto de tempo morde antes do teto de bytes, e ninguém percebe até o job ser cancelado às 6 h com o
manifesto pela metade. `pipelines/reconhecer.py` aplica exatamente estas regras — o documento
descreve o código, não o contrário.

### 3. Declarar no catálogo — portão

O bloco vai para `config/fontes.yaml`, junto de `sonda:` e `ficha:`. **Fonte sem `guarda:` quebra
`tests/test_guarda.py`**, e o motivo é obrigatório em tudo que não é `integral`: recusa sem motivo
escrito volta como proposta nova a cada seis meses.

```yaml
  guarda:
    modo: recorte
    medido_em: 2026-08-16      # medida sem data não é medida
    volume_gb: 57.7
    risco_sumico: baixo        # já sumiu alguma vez? histórico, não previsão
    onde: actions              # actions | brasil | vps | nenhum
    motivo: >-
      Por que não guardamos tudo. Precisa convencer alguém daqui a seis meses.
    recorte:
      pactuado_em: null        # sem indicador pactuado, o pipeline não colhe
```

O portão tem dentes: `alvos_do_catalogo()` filtra por `guarda.pode_colher()`, então **nem `--todas`
espelha o que foi recusado**.

### 4. Pactuar o indicador — portão

`recorte.pactuado_em: null` faz o pipeline se recusar a colher. É a decisão editorial de 16/08/2026
virando condição que o código lê: **não se coleta dado sem saber que número ele vai virar**, e o
número precisa responder "a cidade melhorou?" (ver [INDICADORES.md](../ciencia-politica/INDICADORES.md)).

Bytes sem finalidade são bytes que ninguém vai revisar e que já contam no plano.

### 5. Adquirir — no lugar certo

| Modalidade | Actions | Rede residencial | VPS |
|---|:--:|:--:|:--:|
| `colheita` (API com filtro) | ✅ | — | — |
| `integral` de arquivo ≤ 10 GB | ✅ | — | — |
| `integral` do INEP | ❌ recusa ASN de datacenter | ✅ | ❌ também é datacenter |
| extração > 14 GB de disco | ❌ | — | ✅ Fase 2 |

**Sobre o INEP**: o bloqueio é por **ASN de datacenter, não geográfico** — em 16/08/2026 baixamos
34,5 MB de uma rede residencial na Espanha, enquanto o runner falha 19 vezes seguidas. Logo VPS
brasileiro **não resolve**; só rede residencial, de qualquer país.

Toda aquisição registra no manifesto: `url`, `sha256`, `bytes`, data. Sem os quatro, não há
procedência — e sem procedência não há errata defensável.

### 6. Promover a staging — só o que passa

Contrato de schema, encoding declarado no YAML (nunca auto-detect), `codigo_municipio_ibge`
VARCHAR(7). Dado suspeito **não sobe** (regra 4): falha ruidosa é melhor que número errado no ar.

### 7. Publicar — com o contrato do indicador

`Indicador` com fórmula legível, ressalvas, `ausencia_significa`, contrato de cobertura e link do
dado bruto. O gate de sanidade roda antes de virar página.

---

## Limites que a estratégia respeita

| Limite | Valor | O que acontece ao cruzar |
|---|---|---|
| Job do Actions | 6 h | cancelado no meio, manifesto pela metade |
| Disco do runner | ~14 GB | extração falha; o espelhador usa pasta temporária **por arquivo**, então o pico é o maior arquivo único |
| Plano do R2 | 10 GB (2,1 usados) | **a escrita passa a falhar** se não houver cartão cadastrado |
| Cópia do acervo | **uma só** | enquanto o espelho B2 não existir, cada GB novo é mais um GB que se perde de uma vez |

Custo de storage não é o gargalo: a US$ 0,015/GB-mês, mesmo 300 GB custam ~US$ 4,35/mês com egress
zero. **O gargalo é operacional** — a escrita parando no meio da onda, contra prazo eleitoral.

## O que a estratégia recusa

1. **Varredura nacional do PNCP** — 57,7 GB/ano e até 18,6 h, contra risco de sumiço inexistente:
   publicar no PNCP é condição de validade do contrato (Lei 14.133).
2. **`remota` sustentando número publicado** — não é economia, é vender auditabilidade.
3. **Triplicar o acervo antes do espelho B2** — a RAIS 2024 sozinha leva a perda potencial de 2,1
   para 6,3 GB, com cópia única.
4. **Terceiro como backup** (Base dos Dados, Internet Archive) — são distribuição, não backup:
   não temos controle de retenção nem imutabilidade neles.
5. **Contornar bloqueio** por proxy residencial ou fingerprint — já decidido para o WAF do
   `cidades.gov.br`, vale para todos.
6. **Um objeto por município por dia** — 5.570 × 30 = 167 mil operações/mês por dataset. Agregue
   por execução.
