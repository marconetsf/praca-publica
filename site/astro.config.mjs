// @ts-check
import { defineConfig } from "astro/config";

export default defineConfig({
  // SSG puro: o build embute os dados nas páginas, o leitor não roda JS para ler
  output: "static",
  // trailingSlash consistente evita 301 desnecessário quando servido por CDN
  trailingSlash: "ignore",
  server: {
    port: 4321,
    // `astro dev --host` publica na rede local (necessário para acessar via Meshnet)
    host: false,
  },
});
