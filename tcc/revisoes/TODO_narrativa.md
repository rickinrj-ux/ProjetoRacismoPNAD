# TODO — reduzir a carga cognitiva do TCC

Origem: diagnóstico pedido pelo autor em 23/09/2026 ("dump de resultados com
sobrecarga cognitiva"). Medição em `scratchpad/carga_cognitiva.py`.

## O diagnóstico, em números

| Seção | Densidade | Palavras |
|---|---|---|
| Introdução | 1,2% | 495 |
| Implementação | 4,9% | 1.554 |
| **Resultados e Discussão** | **4,4%** | **6.218** |
| Conclusão | 2,0% | 294 |

- **271 números** em 6.218 palavras de prosa numa seção só
- pior parágrafo: **12 números em 97 palavras** (um a cada oito palavras)
- **47%** dos parágrafos sem nenhum conectivo de explicação
- **31%** abrem com número nas primeiras 14 palavras

**Causa**: o documento foi construído método a método, cada bloco otimizado
para estar correto e completo. A explicação de *por que* cada número importa
existe, mas nunca foi escrita — ficou implícita.

## Knaflic se aplica? Sim, na camada de narrativa

A norma regula **forma** (margens, fonte, nomes de seção, cor em tabela).
Knaflic trata de **sequência e seleção**. Atuam em camadas diferentes.

| Aplicável | Bloqueado pela norma |
|---|---|
| SWD-02 explanatório, não exploratório | títulos de ação nas seções (nomes fixos) |
| SWD-30 carga cognitiva por elemento | título de ação em legenda de tabela |
| SWD-40 memória ≈ 4 blocos | cor como destaque em tabelas (item 15.2) |
| SWD-71 tensão antes da resolução | |
| SWD-79 frase-síntese repetível | |
| SWD-36 contraste estratégico ("falcão entre pombos") | |

---

## N1 — Piloto: uma subseção só, para validar a abordagem

- [ ] **N1.1** Reescrever a subseção do HLM (a mais densa) com os três
      movimentos: parágrafo de pergunta antes, tradução depois de cada número
      de manchete, e o método explicado onde ele aparece
- [ ] **N1.2** Medir a densidade antes/depois e submeter ao autor
- [ ] **N1.3** Só prosseguir com aprovação

## N2 — Explicações de método que faltam (vão para a Implementação)

O que expliquei ao autor no chat e não está no documento:

- [ ] **N2.1** Por que o logaritmo do rendimento (interpretação multiplicativa,
      assimetria da renda, equação de Mincer) — e a contrapartida da leitura
      percentual, que já tem nota de rodapé
- [ ] **N2.2** Por que idade ao quadrado (rendimentos crescem e declinam; o
      efeito marginal depende da idade; onde fica o pico)
- [ ] **N2.3** Por que escolaridade em degraus e não em anos (efeito diploma) —
      e por que `educ_missing` existe, que hoje só aparece nas limitações
- [ ] **N2.4** O que o intercepto aleatório faz (β₀ⱼ com índice j), em uma
      frase: é o que muda a comparação de "entre bairros" para "dentro do
      bairro"
- [ ] **N2.5** O que o ICC significa em linguagem de leitor, não de fórmula

## N3 — Parágrafo de pergunta antes de cada bloco (SWD-71)

Uma ou duas frases que digam o que está prestes a ser descoberto e por que
importa. Hoje as subseções abrem direto no resultado.

- [ ] **N3.1** HLM — "quanto do gap sobrevive à comparação entre vizinhos?"
- [ ] **N3.2** Machine learning — "e se a forma funcional estiver errada?"
- [ ] **N3.3** Oaxaca-Blinder — "é composição ou é preço?"
- [ ] **N3.4** Quantílica e RIF — "a penalidade é a mesma em toda a
      distribuição?"
- [ ] **N3.5** GLMM — "a barreira está no salário ou antes dele?"
- [ ] **N3.6** Interseccionalidade — "raça e gênero se somam?"
- [ ] **N3.7** VIF — "os controles estão brigando entre si?"

## N4 — Frase de tradução depois dos números de manchete (SWD-37)

Cada número que a banca vai citar ganha uma frase em linguagem comum.

- [ ] **N4.1** ICC = 0,369 → "mais de um terço da diferença de renda entre duas
      pessoas quaisquer vem de morarem em bairros diferentes"
- [ ] **N4.2** OR = 0,699 → já tem tradução em pontos percentuais; conferir se
      está na primeira ocorrência
- [ ] **N4.3** τ² e σ² → o que cada um mede, sem fórmula
- [ ] **N4.4** R² = 0,628 e o erro de R$ 538 → o que significa prever renda
- [ ] **N4.5** E-value = 2,2 → o que teria de existir para derrubar o achado
- [ ] **N4.6** Revisar os oito parágrafos mais densos da medição

## N5 — Aliviar os parágrafos mais carregados (SWD-30, SWD-40)

- [ ] **N5.1** Parágrafo da regressão quantílica (12 números / 97 palavras):
      mover os quantis intermediários para a tabela, manter q10 e q90 no texto
- [ ] **N5.2** "O acesso também é bairro" (11/92): manter o ICC, mover o resto
- [ ] **N5.3** "A penalidade varia entre bairros" (10/85): manter o LR e o
      desvio-padrão, mover covariância e graus de liberdade
- [ ] **N5.4** "A porta é mais estreita" (13/112): manter o gradiente de OR,
      mover AME e IC para a tabela
- [ ] **N5.5** "O que faz de um bairro um bairro" (14/136)
- [ ] **N5.6** "Ausência de sobreajuste" (11/114)
- [ ] **N5.7** Regra geral a aplicar: **no máximo três números por parágrafo de
      prosa**; o resto vive na tabela, que existe para isso

## N6 — Regra no verificador (para não regredir)

- [ ] **N6.1** `check_carga_cognitiva`: acusar parágrafo de prosa com mais de
      seis números ou densidade acima de 8%
- [ ] **N6.2** Acusar subseção de resultados que abre com número nas primeiras
      15 palavras (falta o parágrafo de pergunta)
- [ ] **N6.3** Testar nos dois sentidos, como nas regras anteriores: reprovar o
      texto atual, aprovar o reescrito

## N7 — Fechamento

- [ ] **N7.1** Medir a densidade final (alvo: Resultados abaixo de 3%)
- [ ] **N7.2** Conferir o limite de páginas (estimativa: 32 → ~36, limite 50)
- [ ] **N7.3** Regerar PDF e Word, rodar `conferir_anexos_normas.py`
- [ ] **N7.4** Revisão qualitativa pela skill `revisao-livros`

---

## Custo e risco

**Ganho**: densidade dos Resultados de 4,4% para ~3%, e a explicação deixa de
depender de o leitor já saber econometria.

**Custo**: 3 a 4 páginas a mais (32 → ~36, dentro do limite de 50) e trabalho
de redação — rascunho meu, revisão do autor, como na revisão de literatura.

**A Discussão não é tocada.** Medição por bloco (23/09) desfez uma suposição
minha: o acúmulo está só nas subseções de resultado — GLMM 7,2%, HLM 6,3%, ML
5,0% —, enquanto a discussão já respira (Limitações 0,9%; parágrafos de
hipótese, 0,0%). Tradução e discussão são coisas diferentes e não competem:
"ICC = 0,369 significa que um terço da variação está entre bairros" é leitura
do resultado; "isso converge com Wilson (1987)" é discussão. A primeira falta,
a segunda existe.

**O que NÃO muda**: nenhum número, nenhuma tabela, nenhuma figura sai. A
conformidade com a norma (26/26) tem de continuar.
