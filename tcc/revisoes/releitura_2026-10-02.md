# Releitura completa antes da entrega — 02/10/2026

Duas revisões independentes, só de leitura: (1) leitura corrida das 1.806 linhas de
`tcc_normas.tex`; (2) conferência visual de todos os slides e páginas dos decks e Word
(Defesa 22/22, Executiva 10/10, Guia 15/15, Narrativa 7/7, Word de entrega 45/45).
**Números**: corretos em todos os arquivos; nenhum resíduo dos fósseis antigos.

## Já corrigido na fonte (entra na próxima regeneração)

| # | Problema | Correção |
|---|---|---|
| T3 / W5 | "15.941.675.0 observações" (regressão minha: contagem virou float) | contagens `N_*` voltam a int em `params_nucleo` |
| T2 / W4 | frase termina em "…quarta casa). A" | "A" solto removido; "7,7 milhões" desse trecho virou parâmetro |
| T1 / W27 | Declaração de IA duplicada | bloco das Limitações cortado antes da declaração (`gerar_tcc_normas.py`) |
| T7 | Discussão sem cabeçalho, pendurada na subseção do VIF | `\subsection*{Discussão}` em vez de apagar o título |
| T5 | "(Seção )" — `\ref` para seção não numerada | `remissoes_textuais()`: vira subseção "Título" |
| — | frase de chamada de figura duplicada | regex `\r` → `\\ref` em `chamar_antes` |
| T8 | nota troca o β da UF fixa pelo do M2 (sem UF) | compara M3 (UF fixa) com M2 de três níveis (UF aleatória) |
| T16 / W22 | γ01 "praticamente a mesma magnitude" (é ~2×) | "cerca de 2,0 vezes" via `G01_RAZAO` |
| T17 / W21 | título/fecho "o bairro não desconta o salário…" contradizem γ01 | parágrafo reescrito ("o bairro cobra duas vezes") |
| T18 | "Todos os coeficientes com \|t\| > 10" (falso) | frase trocada; "MHE" vira `\cite[cap.~8]{angrist2009}` |
| T19 / W7 | "maior diferença padronizada 1,47" (é a bruta) | `gerar_tabela_robustez` usa `d_cohen` (1,16) |
| T20 / W9 / T41 | "sem aumentar o sobreajuste"; "(atual)"; "versão anterior" | texto e rótulos da tabela de CV corrigidos |
| T21 | N do ML = N do HLM | `ML_N` = treino + teste |
| T22 / W8 | "a menos de 1 pp do M4, com os mesmos controles" | distância calculada (`ML_VS_M4_PP` = 1,1); "controles semelhantes" |
| T55 | "hiperparâmetros escolhidos por CV" | "em partição de validação e confirmados por CV" |
| T61 | "2 variável crítica" + valores de reserva fósseis no VIF | concordância + lê `params_nucleo` sem reserva |
| — | Gini "em torno de 0,48" digitado | `GINI_TOTAL` |
| — | caçador de fósseis classificava texto LaTeX como regex | regra estrutural (AST) |

## Pendente — decisão do autor (mexe no argumento ou no método)

1. **Escada do HLM não aninhada (T14)**: o "agregado" (19,1%) tem efeito fixo de UF; o M1
   não tem; o M3 recoloca a UF. A "mediação pelo bairro" de 47% mistura tirar a UF e pôr
   a UPA. Afeta o número-manchete. Opções: reestimar o agregado sem UF (ou o M1 com UF).
2. **"Discriminação opera sobretudo no acesso" (T10, T11, W33)**: os números dão o
   contrário em magnitude (Oaxaca: 12,4 pp pela porta vs 16,5 pp dentro; HLM: ⅓ vs ⅔).
   "Supera" compara pp de probabilidade com % de salário. Reformular a tese central.
3. **Interseccionalidade (T13, W12)**: "+4,6 pp acima da soma" é artefato de somar
   percentuais exponenciados; em log-pontos é sub-aditivo, como a interação do GLMM.
   Resumo, Abstract, Conclusão, tabela e decks precisam de uma leitura única.
4. **Limite superior × inferior (T9)**: o M3 é chamado de limite inferior, piso e limite
   superior em lugares diferentes. Fixar um enquadramento (OVB → M3 superior; bad
   control → M4 inferior) e aplicar em todo o texto.
5. **Jornada/horas (T23, T24)**: o M3 controla horas, a Oaxaca (A) diz ter "os controles
   do M3" sem horas, e as Limitações chamam horas de bad control.
6. **Resultados regionais sem tabela (T25)**: capitais vs interior, DF, Norte/Nordeste
   aparecem só na Discussão/Conclusão. Incluir resultado ou retirar.
7. **Escolaridade implausível (T26, W40)**: negros com mais superior completo que brancos
   (0,278 × 0,198) e retorno negativo do ensino médio. Auditar `educ_cat` ou discutir a
   seleção de quem tem escolaridade registrada.
8. **E-value (T33)**: calculado tratando OR como RR; para desfecho comum, √OR (≈1,69).
9. **"Na base, a maior parte do gap é preço" (T12, W10)**: 35,5% não é maioria — em 4
   entregáveis (Defesa s14, Executiva s7, Conclusão, Narrativa).
10. **E-mail do orientador**: placeholder "orientador@usp.br" na folha de rosto.
11. **Lei 12.990/2014**: verificar se foi substituída (Lei 15.142/2025?).

## Pendente — forma (sem decisão de mérito; trabalho de engenharia)

- **Word de entrega**: tabelas ilegíveis (larguras de coluna), `\cmidrule` cru,
  chamadas de nota coladas ao texto ("0,69714"), "Referências" sem título, notas que
  começam com ":", legenda duplicada, figura partida em duas páginas.
- **Defesa**: s9 anotação cortada; s17 cartões quebram números; s5/s12/s15/s19 callouts
  transbordam; s10 figuras ilegíveis; s3 "mestrado" e cabeçalho cortado; s22 sem número.
- **Executiva**: s6 título cobre subtítulo e "(slide anterior)" aponta errado; s7 texto
  sobre os eixos; s3 "sem amostragem".
- **Guia**: tabela do GLMM mistura A2 (OR/AME) com A1 (ICC/AUC).
- **Figuras**: SHAP com inglês e ponto decimal; waterfalls com nomes crus.
- **Rótulos M × A no GLMM**: o texto define A1–A4, figura/tabelas/decks usam M1–M4.
- **QR no topo**: 12,7% (q95) em uns lugares, 12,0% (q90) em outros; método declara 5
  quantis, tabela tem 6.
- MÉDIO/BAIXO restantes da leitura corrida: itens 27–80 do relatório.
