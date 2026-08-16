# Produto: Páginas, Design e Navegabilidade

> Público-alvo: cidadão comum, mobile-first (WhatsApp dominante), baixa familiaridade com dados.
> Secundário: jornalistas e pesquisadores. Especificado em 26/07/2026.

## 1. Arquitetura de informação

### Mapa de páginas

```
/                                    Home = busca (porta de entrada)
/municipio/{uf}/{slug}               Página do município (produto central)
/m/{codigo_ibge}                     Rota curta p/ compartilhamento (301 → canônica, via Pages
                                     Function com tabela código→slug — o _redirects estático do
                                     Pages não comporta 5.570 regras)
/uf/{uf}                             Hub estadual (SEO: profundidade ≤3 até todo município)
/ranking/{indicador}                 Ranking nacional; filtros ?uf=&porte=
/comparar?m={a},{b}                  Comparação como ilha client-side com URL compartilhável —
                                     NÃO pré-renderizada (pares de municípios explodem o limite
                                     de 20k arquivos do Pages); sem promessa de indexação
/metodologia e /metodologia/{indicador}
/fontes                              Ficha por órgão: o que publica, com que atraso, o que já está
                                     no site, o que está guardado e o que está bloqueado. Gerada por
                                     `pipelines/marts/fontes.py` — a situação é DERIVADA dos fatos
                                     (indicador publicado, manifesto, watcher), nunca declarada à mão
/feedback                            Como conferir um número na fonte, por que uma ausência
                                     aparece e o que fazemos quando erramos. O canal de envio
                                     mora em `site/src/contato.js` e hoje é `null` — a página
                                     diz isso de frente em vez de prometer atendimento
/dados                               Bulk download (parquet/CSV), licenças, changelog
/erratas                             Correções públicas, com RSS
/sobre                               Quem faz, financiamento, política editorial
/glossario                           Termos em linguagem simples
```

Decisões:
- **Slug por UF** (`/municipio/pe/petrolina`): nomes são únicos dentro da UF, não no país (4 "Bom Jesus"). Código IBGE é chave interna (rodapé + JSON-LD), nunca na URL principal.
- **Fase 1 = página única por município com âncoras** (`#dinheiro #saude #educacao #energia #trabalho`). Subpáginas temáticas só na v1.1 (evita 33 mil páginas rasas — thin content).
- **Busca é a home**: campo único, autocomplete client-side sobre índice estático (5.570 nomes + apelidos, ~300 KB gzip). Sem CEP (DNE é pago); geolocalização opcional do navegador resolvida por ponto-em-polígono contra centroides.

### SEO programático (5.570 páginas)

| Elemento | Template |
|---|---|
| `<title>` | `{Município} ({UF}): para onde vai o dinheiro, saúde e educação — Praça Pública` |
| description | `Veja em linguagem simples os dados públicos de {Município} ({UF}): orçamento, saúde, educação, energia e empregos. Fonte: {órgãos}, dados de {ano}.` |
| `<h1>` | `{Município} — {UF}` |
| OG image | por município (nome + número-manchete + marca), 1200×630 — ver CRESCIMENTO.md |

JSON-LD: `City` (com código IBGE em `identifier`), `BreadcrumbList`, `Dataset` por bloco temático (`isBasedOn` → SICONFI/DataSUS/INEP, `temporalCoverage`, `license`, `dateModified` = última coleta). Sitemaps particionados por UF; `lastmod` = último rebuild com dado novo daquele município (nunca a data do build geral).

## 2. Página de município (produto central)

### Wireframe (mobile 360 px)

```
┌──────────────────────────────────┐
│ Praça Pública        [buscar 🔍] │
│ Brasil › PE › Petrolina          │
├──────────────────────────────────┤
│ PETROLINA — PE                   │
│ 386 mil habitantes · porte grande│
├──────────────────────────────────┤
│ EM RESUMO                        │  ← "entende em 5 s"
│ • De cada R$ 100 da prefeitura,  │
│   R$ 27 vão para saúde — mais    │
│   que o típico das parecidas.    │
│ • Criou 2.140 empregos com       │
│   carteira em 12 meses.          │
│ • Faltam dados de educação de    │
│   2025 (INEP ainda não publicou).│
│            [ compartilhar 📤 ]   │
├──────────────────────────────────┤
│ [Dinheiro][Saúde][Educação]...   │  ← âncoras sticky
├──────────────────────────────────┤
│ 💰 DINHEIRO DA PREFEITURA        │
│ ┌ Gasto com saúde por morador ┐  │
│ │        R$ 812 /ano           │  │
│ │  ● na média dos parecidos    │  │
│ │  parecidos: R$ 790 (mediana) │  │
│ │  ▁▂▃▅▆█  2019→2024           │  │
│ │  Fonte: Siconfi · ano 2024 · │  │
│ │  coletado 07/2026            │  │
│ │  [o que isso significa? ⓘ]   │  │
│ └──────────────────────────────┘  │
├──────────────────────────────────┤
│ COMPARE  Petrolina × [cidade ▾]  │
│ PARECIDAS · VIZINHAS (12 links)  │
│ Metodologia · IBGE 2611101 · CSV │
└──────────────────────────────────┘
```

### Regras editoriais (invioláveis)

1. **"Em resumo" primeiro**: 3 frases template com comparação embutida — é o que aparece no print de WhatsApp. Uma pode ser lacuna de dado (transparência ativa).
2. **Padrão de frase-número**: `[tradução concreta] + [comparação com parecidos] + [tendência]`. Ex.: "De cada 1.000 bebês nascidos, 12 não completaram 1 ano" (nunca "‰"); "subiu de R$ 10 para R$ 14 por morador" (nunca "%" sem base).
3. **Comparação obrigatória — RÉGUA ÚNICA DO PROJETO** (todos os demais docs referenciam esta regra): nenhum card sem valor de referência. Grupo fixo e nomeado: **mesma faixa de porte na mesma Grande Região, mediana** (robusta a outliers; no texto público, escrever "o típico das parecidas" ou "mediana" — **nunca "média"**). As 7 faixas de porte: até 5 mil; 5–10 mil; 10–20 mil; 20–50 mil; 50–100 mil; 100–500 mil; acima de 500 mil habitantes — fixadas pelo ano de referência da população em `dim_municipio.faixa_porte` (município que muda de faixa entre estimativas mantém a faixa do ano de referência do dado). "Cidades parecidas = as 94 do Nordeste com 100 a 500 mil habitantes". Exceções por indicador (ex.: IDEB vs mediana estadual) existem apenas se documentadas em `/metodologia/{indicador}`.
4. **Semáforo com rótulo textual sempre** (nunca só cor):
   - Cor neutra para indicadores **sem valência moral** (composição de gasto): `● acima / na média / abaixo dos parecidos`. Gasto alto ≠ bom.
   - Verde/âmbar/laranja **só** para resultado com direção pactuada (mortalidade infantil ↓, cobertura vacinal ↑), documentada em `/metodologia/{indicador}`.
5. **Dado ausente ≠ zero — regra de ferro.** Card em estado próprio (hachura + "Sem dados: {município} não enviou a declaração de 2024 ao Tesouro — acontece com ~25% dos municípios"). Ausência nunca entra em ranking, mediana ou sparkline (gap visível, não interpolado).
6. **Ranking ≠ mérito**: posição sempre com denominador e grupo ("34º entre os 94 parecidos"); nunca "melhor/pior cidade".
7. Números arredondados na leitura (R$ 812; "386 mil"); valor exato no detalhe e no CSV.

## 3. Design system enxuto

- **Fonte: Atkinson Hyperlegible Next** (self-hosted woff2; desenhada para baixa visão, distingue 1/l/I e 0/O); `tabular-nums` em números. Base 17 px mobile, escala 1,25; linha 1,5; texto ≤ 34em.
- **Paleta Okabe-Ito** (segura para daltonismo): tinta `#1A1A2E`/branco (15,6:1); primária azul `#0072B2`; neutra `#5B6470`; positivo verde-azulado `#009E73`; atenção laranja `#D55E00` (não vermelho puro); ausência = hachura `#C7CCD1` + ícone. **Cor nunca é o único canal** — todo estado tem ícone + texto. Contraste ≥ 4,5:1 texto, ≥ 3:1 componentes.
- **Tom de voz nível Fundamental II**: frases ≤ 20 palavras, voz ativa. Dicionário obrigatório (`/glossario`): empenho→"compromisso de gasto", per capita→"por morador", exercício→"ano". Proibido: sigla sem expansão, juridiquês, % sem base. Ano eleitoral: descritivo, nunca prescritivo; sem nomes de políticos na Fase 1.
- **6 componentes**: CardIndicador (título em pergunta), GraficoEvolucao (SVG estático do build, zero JS), TabelaRanking, SeletorComparacao, **Proveniencia** (obrigatório em todo número: `Fonte: {órgão} · dados de {ref} · coletado em {data}`), BotaoCompartilhar (Web Share API; fallback copiar `/m/{ibge}`).
- **Performance como design**: página ≤ 60 KB HTML+CSS, **0 JS obrigatório para ler** (ilhas só em busca/comparação), LCP < 2 s em 3G — o público está em Android de entrada.

## 4. Navegabilidade

- **Jornada principal**: link no WhatsApp → OG image já entrega nome + número → "Em resumo" na 1ª dobra (5 s) → âncoras → parecidas/comparar → compartilhar (botão no resumo e no fim de cada seção).
- **Malha de links**: fim de toda página, **6 parecidas + 6 vizinhas** (fronteira via geobr) — é o que faz o Google rastrear as 5.570 páginas e o usuário "andar pelo mapa".
- **Estados vazios**: município quase sem dados **tem página mesmo assim** (identidade IBGE + população sempre existem) com "não enviou dados ao Tesouro nos últimos {n} anos" — a ausência é informação pública. Nunca 404 para município válido. Busca sem resultado sugere por distância de edição.

## 5. Confiança e transparência

- **Proveniência em todo número**: órgão + data de referência + data de coleta (separadas — a diferença é a defasagem que o leitor precisa conhecer). Cumpre atribuição (TSE CC-BY; BCB/ANEEL ODbL) e é a defesa editorial.
- **`/metodologia/{indicador}`**: o que mede (linguagem simples), fórmula exata, fonte, defasagem, **limitações conhecidas** (lacuna SICONFI ~25%, subnotificação SIM/SINASC), faixas do semáforo e direção assumida.
- **`/fontes`**: a contrapartida de cobrar transparência dos entes. Quatro estados, derivados: **no site**, **guardado** (espelhado, ainda sem virar indicador), **ainda não fomos buscar** e **fora do alcance** (com o motivo por extenso). Duas regras editoriais fortes: a página **nunca acusa o órgão** — falha da nossa sonda vira "pode ser bloqueio ao nosso acesso", e falha isolada é distinguida de queda persistente pelo número de checagens seguidas; e **nenhum rastro técnico** (exceção de Python, host, porta) chega ao leitor.
- **`/dados`**: parquet + CSV dos marts, dicionário, manifesto (sha256 por fonte), licenças (CC-BY nossos agregados; ODbL onde herdado), changelog.
- **`/feedback`**: o leitor confere o número na fonte (o link já está em cada card), entende os três motivos de uma ausência e sabe que erro nosso vira errata datada. **Enquanto `CANAL_DE_CONTATO` for `null`, nenhum e-mail pode aparecer em página nenhuma** (cobrado por `tests/test_pagina_feedback.py`) e a página declara a falta do canal: promessa de atendimento que ninguém presta é pior do que não ter a página — mesma regra do dado ausente.
- **Política de erro em `/sobre`** + `/erratas` com RSS (ver SEGURANCA.md §5).
- **Ano eleitoral**: banner permanente "A Praça Pública não apoia candidatos..."; **metodologia congelada de agosto à diplomação**.

## 6. Stack de frontend

**Decisão: Astro (SSG puro) + Cloudflare Pages.**

- Astro entrega HTML com **zero JS por padrão** (Next embarca ~85 KB de runtime React sem necessidade); islands cobrem busca/comparação. Ecossistema de SSG programático mais maduro que SvelteKit.
- Build: 5.570 páginas × ~11 KB de dados = < 5 min; o build lê os JSONs de `serving/` no R2 (token de leitura em variável de ambiente do build — ver ARQUITETURA §3 e OPERACAO §2). Sem API em produção.
- **Cloudflare Pages** via git-integration (preview por PR nativo): banda **ilimitada** no free tier (Netlify: 100 GB/mês — pico viral estoura); 500 builds/mês; 20k arquivos comportam a Fase 1. Dado novo sem mudança de código dispara rebuild por deploy hook chamado pelo `build-marts`.
- Busca: índice estático + minisearch client-side. Fase 2 (consulta dinâmica de CNPJ): Cloudflare Workers sobre a mesma infra — Astro tem adapter híbrido, sem migração.

## 7. Acessibilidade (WCAG 2.1 AA como piso)

1. Contraste verificado com axe-core no CI (amostra de páginas geradas).
2. Sem dependência de cor (ícone + rótulo em todo semáforo; tracejado além de cor em gráficos).
3. Teclado: foco lógico, `:focus-visible`, skip-link, combobox ARIA no autocomplete.
4. Gráficos: `role="img"` + descrição por template + tabela equivalente em `<details>`; sparklines decorativas `aria-hidden` (informação duplicada no texto).
5. Números para leitor de tela: "R$ 1,2 bi" com `aria-label="1,2 bilhão de reais"`; `lang="pt-BR"`.
6. Alvos de toque ≥ 44×44 px; layout íntegro a 200% de zoom e 320 px.
7. Semântica: 1 `<h1>`, headings sem salto, landmarks, `<th scope>` + `<caption>` em tabelas.
8. `prefers-reduced-motion` respeitado.
9. **Linguagem simples é acessibilidade**: Flesch pt-BR ≥ 60 verificado no CI editorial.
