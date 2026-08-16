/**
 * O canal por onde o leitor fala com a Praça Pública.
 *
 * Está `null` de propósito: o projeto ainda não tem domínio nem endereço
 * próprio, e publicar um e-mail pessoal do mantenedor num site que quer virar
 * público é decisão de outra ordem. Enquanto for `null`, a página `/feedback`
 * diz isso de frente, e `tests/test_pagina_feedback.py` impede que qualquer
 * e-mail apareça em qualquer página.
 *
 * Quando houver endereço, basta trocar por uma string
 * (ex.: "contato@pracapublica.org.br") — a página passa a mostrar o link e o
 * teste inverte o que cobra.
 */
export const CANAL_DE_CONTATO = null;
