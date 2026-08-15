// @ts-check
import { defineConfig } from "astro/config";

export default defineConfig({
  // SSG puro: o build embute os dados nas páginas, o leitor não roda JS para ler
  output: "static",
  // trailingSlash consistente evita 301 desnecessário quando servido por CDN
  trailingSlash: "ignore",
  build: {
    // O CSS inteiro do site cabe em ~10 KB (≈3 KB comprimido). Inline, ele chega
    // junto com o HTML; em arquivo separado, custa duas idas e voltas bloqueantes
    // antes da primeira pintura. O leitor típico chega de link no WhatsApp, abre
    // UMA página e está em 3G: cache entre páginas vale menos que a primeira
    // pintura. O padrão do Astro ("auto") só embute abaixo de 4 KB, e os nossos
    // dois pacotes passam disso por pouco.
    inlineStylesheets: "always",
  },
  server: {
    port: 4321,
    // `astro dev --host` publica na rede local (necessário para acessar via Meshnet)
    host: false,
  },
});
