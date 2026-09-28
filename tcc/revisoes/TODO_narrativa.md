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

- [x] **N1.1** Reescrever a subseção do HLM (a mais densa). Três movimentos,
      saídos da sessão de divergência: (a) **classificação ABC** --- o que a
      banca vai citar fica na linha de leitura, o aparato (IC, SE, LR, g.l.,
      componentes de variância) desce para nota de rodapé, a escada de
      variância fica na tabela; (b) **régua repetida** --- em três pontos (M1,
      M3, M4) a prosa diz que fração *do gap agregado* já foi percorrida, que é
      a coluna "Mediação acum." da Tabela~tab:mediacao lida em voz alta; (c)
      **rótulo-asserção** --- cada `\paragraph` afirma algo em vez de nomear um
      tópico, e três deles fecham com uma frase de síntese
- [x] **N1.2** Medido. Antes: 849 palavras, 53 números, **6,2%**; pior
      parágrafo 11,1%. Depois: 1.247 palavras, 36 números, **2,9%**; pior
      parágrafo 4,6%. **O PDF continua com 32 páginas** --- a prosa nova foi
      paga cortando o "Como ler" da tabela e a epígrafe em itálico. Invariância
      conferida: entraram 49,3% e 65,9% (já existentes na Tabela~tab:mediacao),
      saiu 16,6% (a mediação *incremental* da ocupação, que a régua acumulada
      torna redundante). Verificador 0 ALTO; anexos 26/26.
- [ ] **N1.3** Só prosseguir com aprovação

### Decisões que ficam para o autor

1. **Orçamento de frases-síntese.** Foram três nesta subseção ("Vale guardar a
   frase: …"). Se todas as dez subseções de resultado receberem o mesmo
   tratamento, são ~25 no trabalho, e a fórmula cansa. Proposta: no máximo uma
   por subseção fora do HLM, reservada aos achados que a banca vai perguntar.
2. **O 16,6% voltar ou não.** Hoje só a fração acumulada (65,9%) aparece. Se
   for para a defesa que o incremento importa, ele volta em nota.
3. **A ressalva viaja junto.** A régua do M1 diz "percorrida no sentido de
   atribuída a um fator observável, e não no sentido de explicada sem
   discriminação" na mesma frase do número. Isso foi deliberado: mandar o freio
   para o rodapé deixaria a afirmação mais forte do que o desenho autoriza.

## N2 — Explicações de método que faltam (vão para a Implementação)

O que expliquei ao autor no chat e não está no documento:

- [x] **N2.1** Por que o logaritmo do rendimento (interpretação multiplicativa,
      assimetria da renda, equação de Mincer) — e a contrapartida da leitura
      percentual, que já tem nota de rodapé
- [x] **N2.2** Por que idade ao quadrado (rendimentos crescem e declinam; o
      efeito marginal depende da idade; onde fica o pico)
- [x] **N2.3** Por que escolaridade em degraus e não em anos (efeito diploma) —
      e por que `educ_missing` existe, que hoje só aparece nas limitações
- [x] **N2.4** O que o intercepto aleatório faz (β₀ⱼ com índice j), em uma
      frase: é o que muda a comparação de "entre bairros" para "dentro do
      bairro"
- [x] **N2.5** O que o ICC significa em linguagem de leitor, não de fórmula

## N3 — Parágrafo de pergunta antes de cada bloco (SWD-71)

Uma ou duas frases que digam o que está prestes a ser descoberto e por que
importa. Hoje as subseções abrem direto no resultado.

- [x] **N3.1** HLM — "quanto do gap sobrevive à comparação entre vizinhos?"
- [x] **N3.2** Machine learning — "e se a forma funcional estiver errada?"
- [x] **N3.3** Oaxaca-Blinder — "é composição ou é preço?"
- [x] **N3.4** Quantílica e RIF — "a penalidade é a mesma em toda a
      distribuição?"
- [x] **N3.5** GLMM — "a barreira está no salário ou antes dele?"
- [x] **N3.6** Interseccionalidade — "raça e gênero se somam?"
- [x] **N3.7** VIF — "os controles estão brigando entre si?"

## N4 — Frase de tradução depois dos números de manchete (SWD-37)

Cada número que a banca vai citar ganha uma frase em linguagem comum.

- [x] **N4.1** ICC = 0,369 → "mais de um terço da diferença de renda entre duas
      pessoas quaisquer vem de morarem em bairros diferentes"
- [x] **N4.2** OR = 0,699 → já tem tradução em pontos percentuais; conferir se
      está na primeira ocorrência
- [x] **N4.3** τ² e σ² → o que cada um mede, sem fórmula
- [x] **N4.4** R² = 0,628 e o erro de R$ 538 → o que significa prever renda
- [x] **N4.5** E-value = 2,2 → o que teria de existir para derrubar o achado
- [x] **N4.6** Revisar os oito parágrafos mais densos da medição

## N5 — Aliviar os parágrafos mais carregados (SWD-30, SWD-40)

- [x] **N5.1** Parágrafo da regressão quantílica (12 números / 97 palavras):
      mover os quantis intermediários para a tabela, manter q10 e q90 no texto
- [x] **N5.2** "O acesso também é bairro" (11/92): manter o ICC, mover o resto
- [x] **N5.3** "A penalidade varia entre bairros" (10/85): manter o LR e o
      desvio-padrão, mover covariância e graus de liberdade
- [x] **N5.4** "A porta é mais estreita" (13/112): manter o gradiente de OR,
      mover AME e IC para a tabela
- [x] **N5.5** "O que faz de um bairro um bairro" (14/136)
- [x] **N5.6** "Ausência de sobreajuste" (11/114)
- [x] **N5.7** Regra geral a aplicar: **no máximo três números por parágrafo de
      prosa**; o resto vive na tabela, que existe para isso

## N6 — Regra no verificador (para não regredir)

- [x] **N6.1** `check_carga_cognitiva`: acusar parágrafo de prosa com mais de
      seis números ou densidade acima de 8%
- [x] **N6.2** Acusar subseção de resultados que abre com número nas primeiras
      15 palavras (falta o parágrafo de pergunta)
- [x] **N6.3** Testar nos dois sentidos, como nas regras anteriores: reprovar o
      texto atual, aprovar o reescrito

## N7 — Fechamento

- [x] **N7.1** Medir a densidade final (alvo: Resultados abaixo de 3%)
- [x] **N7.2** Conferir o limite de páginas (estimativa: 32 → ~36, limite 50)
- [x] **N7.3** Regerar PDF e Word, rodar `conferir_anexos_normas.py`
- [x] **N7.4** Revisão qualitativa pela skill `revisao-livros`

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

---

## Resultado do bloco N1--N7 (28/09/2026)

| | antes | depois |
|---|---|---|
| Resultados e Discussão | **4,2%** | **2,4%** |
| pior subseção | GLMM 6,8% | GLMM 3,1% |
| pior parágrafo | 12,2% (12 números / 98 palavras) | 4,1% |
| páginas do PDF | 32 | **34** (limite 50) |
| anexos do manual | 26/26 | **26/26** |
| verificador | 0 ALTO | **0 ALTO, 0 MÉDIO** |

**Invariância no documento inteiro**: 667 valores distintos antes, 665 depois;
**nenhum número inventado**. Saíram dois: `16,6%` (mediação incremental da
ocupação, que a régua acumulada de 65,9% torna redundante) e `0,62` (o $R^2$
aproximado repetido na prosa, que continua exato na tabela).

### O que foi feito, por subseção

| Subseção | antes | depois | movimento |
|---|---|---|---|
| HLM | 6,2% | 2,4% | ABC + régua do gap agregado + rótulo-asserção |
| GLMM | 6,8% | 3,1% | pergunta de abertura, aparato em nota, gradiente traduzido |
| ML/SHAP | 5,1% | 2,3% | pergunta ("e se a forma estiver errada?"), CV em nota |
| VIF | 9,5% (abertura) | 3,0% | a objeção antes do inventário |
| Interseccionalidade | 4,3% | 2,1% | a inversão em dois tempos, com rótulo |
| Oaxaca--Blinder | 3,9% | 3,1% | pergunta "composição ou preço?" |
| Quantílica/RIF | 2,1% | 1,6% | pergunta "teto de vidro ou piso pegajoso?" |
| Discussão (IBGE, tendência) | 9,6% e 5,8% | abaixo do limite | ressalvas na linha, índices em nota |

### N6 --- a regra que impede a regressão

`check_carga_cognitiva` em `verificar_analises.py`. Acusa parágrafo de prosa
acima de 6% de densidade (ou mais de 6 números acima de 4,5%) e subseção de
resultado que abre com número nas primeiras 15 palavras. Não conta nota de
rodapé, tabela, figura, graus de liberdade, p-valor, número de lei nem rótulo
de modelo (`M4`, `H2`) --- rótulo não é medida. **Testada nos dois sentidos**:
12 achados no texto anterior, 0 no reescrito.

### Uma correção de conteúdo, não só de forma

O parágrafo "Lenta convergência racial" afirmava no corpo que a convergência
levaria mais de um século e guardava `p = 0,077` dentro de um parêntese. O
próprio csv (`tendencia_temporal_testes.csv`) conclui "Gap estável (p>0.05)".
A redação nova mantém o valor pontual e diz, na mesma frase, que a inclinação
não se distingue de zero pelos critérios convencionais --- os dados não
autorizam afirmar que exista convergência.

### Aberto: um número sem fonte em csv

`SHAP médio de −0,0469 para trabalhadores negros --- equivalente a uma
penalidade de 4,6%` está fixado em `scripts/geradores/gerar_relatorio_tcc.py`
(linhas ~1305) e **não sai de nenhum csv de `outputs/tables/`**: os arquivos de
SHAP guardam apenas a média em valor absoluto (`SHAP_mean_abs_XGB` = 0,031),
que é outra grandeza. Não toquei no trecho. Decisão do autor: reexecutar
`run_ml_shap.py` emitindo a média com sinal por grupo, ou retirar a frase e
ficar com o \emph{ranking} e a média absoluta, que têm fonte.
