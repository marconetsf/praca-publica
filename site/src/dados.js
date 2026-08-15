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
 * O rótulo do semáforo. Indicador de composição de gasto não tem valência moral
 * (PRODUTO §2 regra 4): gastar mais não é bom nem ruim, então a cor é neutra e o
 * texto diz apenas a posição relativa.
 */
export function rotuloComparacao(valor, comparacao) {
  if (!comparacao) return null;
  const mediana = comparacao.mediana_parecidos;
  const diferenca = (valor - mediana) / mediana;
  if (Math.abs(diferenca) < 0.1) return "na média dos parecidos";
  return diferenca > 0 ? "acima dos parecidos" : "abaixo dos parecidos";
}

/** "as 7 do Norte com 100 a 500 mil habitantes" */
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
  return `as ${n} cidades ${REGIOES[regiao] ?? ""} com ${FAIXAS[faixa] ?? faixa}`;
}
