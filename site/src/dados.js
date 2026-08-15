/**
 * Leitura dos JSONs de serving no momento do build.
 *
 * Os arquivos vivem em `public/dados/` porque cumprem dois papéis: alimentam o
 * build (aqui) e ficam servidos como download bruto, que é a promessa de
 * `/dados` no PRODUTO.md. Nenhuma dessas leituras chega ao navegador — o build
 * embute o resultado no HTML.
 */
import fs from "node:fs";
import path from "node:path";

// Ancorado no cwd (a pasta `site/`), não em import.meta.url: no build o módulo é
// empacotado para dist/chunks/ e qualquer caminho relativo ao arquivo aponta errado.
const RAIZ_DADOS = path.join(process.cwd(), "public", "dados");

export function lerIndice() {
  const arquivo = path.join(RAIZ_DADOS, "busca.json");
  if (!fs.existsSync(arquivo)) {
    throw new Error(
      `busca.json não encontrado em ${RAIZ_DADOS}. ` +
        "Rode antes: python -m pipelines.marts.serving --ano 2024"
    );
  }
  return JSON.parse(fs.readFileSync(arquivo, "utf-8"));
}

export function lerMunicipio(codigoIbge) {
  const arquivo = path.join(RAIZ_DADOS, "municipio", `${codigoIbge}.json`);
  return JSON.parse(fs.readFileSync(arquivo, "utf-8"));
}

/**
 * Todos os indicadores que o projeto publica, na ordem em que aparecem na
 * página. Existe por causa da regra de ferro do PRODUTO §2.5: dado ausente não
 * é zero **nem linha sumida**. O JSON de um município traz só os indicadores
 * que ele tem; sem esta lista, o card que falta desapareceria em silêncio e o
 * leitor acharia que o assunto não existe.
 *
 * Montada a partir dos próprios JSONs (nada é inventado aqui) e memoizada: são
 * 443 arquivos pequenos lidos uma vez por build, não uma vez por página.
 */
let _catalogo = null;
export function catalogoIndicadores() {
  if (_catalogo) return _catalogo;
  const mapa = new Map();
  for (const item of lerIndice()) {
    for (const indicador of lerMunicipio(item.codigo_ibge).indicadores) {
      if (mapa.has(indicador.id)) continue;
      mapa.set(indicador.id, {
        id: indicador.id,
        nome: indicador.nome,
        descricao: indicador.descricao,
        unidade: indicador.unidade,
        fonte: indicador.fonte,
        orgao: indicador.procedencia?.orgao ?? null,
      });
    }
  }
  _catalogo = [...mapa.values()].sort((a, b) => a.id.localeCompare(b.id));
  return _catalogo;
}

/** R$ 1.030 — arredondado na leitura; o valor exato fica no JSON e no CSV. */
export function formatarReais(valor) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(valor);
}

export function formatarNumero(valor) {
  return new Intl.NumberFormat("pt-BR").format(valor);
}

export function formatarData(iso) {
  const [ano, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}

/**
 * "R$/morador/ano" é notação de planilha. O leitor precisa da frase.
 * A unidade fica logo abaixo do número, porque valor sem unidade não é dado —
 * e "R$ 1.030" sozinho já foi lido como "o orçamento inteiro da cidade".
 */
export function descreverUnidade(unidade, ano) {
  const MAPA = {
    "R$/morador/ano": ano ? `por morador, em ${ano}` : "por morador, no ano",
    "R$/morador": "por morador",
  };
  return MAPA[unidade] ?? unidade;
}

/**
 * Onde o município está em relação ao típico das cidades parecidas.
 * Devolve só a classe ("acima" | "perto" | "abaixo"); o texto público sai dos
 * mapas abaixo, para que card e resumo nunca digam coisas diferentes do mesmo
 * número. A faixa de 10% em volta da mediana existe porque diferença menor que
 * isso não é diferença: é ruído de declaração.
 */
export function classificarComparacao(valor, comparacao) {
  if (!comparacao || comparacao.mediana_parecidos == null) return null;
  const mediana = comparacao.mediana_parecidos;
  if (!mediana) return null;
  const diferenca = (valor - mediana) / mediana;
  if (Math.abs(diferenca) < 0.1) return "perto";
  return diferenca > 0 ? "acima" : "abaixo";
}

/**
 * Rótulo do card. Composição de gasto não tem valência moral (PRODUTO §2.4):
 * gastar mais não é bom nem ruim, então o texto diz posição, nunca julgamento.
 * E nunca "média": a régua do projeto é a MEDIANA, e chamar mediana de média
 * ensina o leitor a conta errada (CLAUDE.md, regra 5).
 */
export const ROTULO_COMPARACAO = {
  acima: "acima do típico das cidades parecidas",
  perto: "perto do típico das cidades parecidas",
  abaixo: "abaixo do típico das cidades parecidas",
};

/** A mesma classificação, na forma que cabe numa frase do "Em resumo". */
export const FRASE_RESUMO = {
  acima: "mais que o típico das cidades parecidas",
  perto: "perto do típico das cidades parecidas",
  abaixo: "menos que o típico das cidades parecidas",
};

/**
 * "as 25 cidades do Norte com 100 a 500 mil habitantes".
 * Sem `n`, sai a versão curta — "as do Norte com 100 a 500 mil habitantes" —
 * para o card, onde o total já aparece na frase da posição ao lado.
 */
export function descreverGrupo(grupo, n) {
  if (!grupo) return null;
  const [regiao, faixa] = grupo.split("|");
  const REGIOES = {
    N: "do Norte",
    NO: "do Norte",
    NE: "do Nordeste",
    CO: "do Centro-Oeste",
    SE: "do Sudeste",
    S: "do Sul",
  };
  const FAIXAS = {
    ate_5k: "até 5 mil habitantes",
    "5k_10k": "5 a 10 mil habitantes",
    "10k_20k": "10 a 20 mil habitantes",
    "20k_50k": "20 a 50 mil habitantes",
    "50k_100k": "50 a 100 mil habitantes",
    "100k_500k": "100 a 500 mil habitantes",
    acima_500k: "mais de 500 mil habitantes",
  };
  const lugar = `${REGIOES[regiao] ?? ""} com ${FAIXAS[faixa] ?? faixa}`;
  return n ? `as ${n} cidades ${lugar}` : `as ${lugar}`;
}

/**
 * "RR" não diz nada para quem chegou pelo WhatsApp. O nome do estado, sim.
 */
const NOMES_UF = {
  AC: "Acre",
  AL: "Alagoas",
  AP: "Amapá",
  AM: "Amazonas",
  BA: "Bahia",
  CE: "Ceará",
  DF: "Distrito Federal",
  ES: "Espírito Santo",
  GO: "Goiás",
  MA: "Maranhão",
  MT: "Mato Grosso",
  MS: "Mato Grosso do Sul",
  MG: "Minas Gerais",
  PA: "Pará",
  PB: "Paraíba",
  PR: "Paraná",
  PE: "Pernambuco",
  PI: "Piauí",
  RJ: "Rio de Janeiro",
  RN: "Rio Grande do Norte",
  RS: "Rio Grande do Sul",
  RO: "Rondônia",
  RR: "Roraima",
  SC: "Santa Catarina",
  SP: "São Paulo",
  SE: "Sergipe",
  TO: "Tocantins",
};

export function nomeUf(uf) {
  return NOMES_UF[uf?.toUpperCase()] ?? uf;
}

/**
 * O texto da ausência. Duas causas reais produzem a mesma falta no JSON — a
 * prefeitura não declarou ao Tesouro, ou declarou valor impossível (31
 * municípios do TO declararam arrecadação negativa em 2024, e `fato_indicador`
 * recusa promovê-los). Como o serving não distingue as duas, o texto diz as
 * duas: melhor uma explicação honestamente ampla do que uma precisa e falsa.
 */
export function motivoSemDado(nomeMunicipio, ano, orgao = "Tesouro Nacional") {
  return (
    `${nomeMunicipio} não tem este número publicado para ${ano}. ` +
    `Ou a prefeitura não declarou o dado ao ${orgao}, ou o valor declarado era ` +
    "impossível — como uma arrecadação negativa — e nós não publicamos. " +
    "Falta de dado nunca vira zero aqui, e esta cidade não entra na conta das parecidas."
  );
}
