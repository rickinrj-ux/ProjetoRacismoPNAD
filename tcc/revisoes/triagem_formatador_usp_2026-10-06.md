# Triagem do Relatório de Formatação (Sistema de Trabalho Final, Pecege) — 06/10/2026

Fonte: `Relatório de Formatação - Ricardo Gomes Calheiros.pdf` (gerado 06/10 12:10) e
`Trabalho Final - Formatado - Ricardo Gomes Calheiros.docx` (103 comentários no arquivo).
Critério de julgamento: Manual de Instruções e Normas para TCC (itens 15 a 19, pp. 32–60).

Resumo: **4 problemas + 128 alertas**. Procedentes: 4 problemas e ~122 alertas. Não procedentes ou
dispensáveis pela própria norma: ~6. A maior parte (≈100) tem **uma causa só**: o projeto gera citações e
referências em ABNT (abnTeX2/pandoc), e o manual tem estilo próprio (itens 17–19).

## A. Problemas (4) — todos procedentes

| # | Onde | Causa | Correção |
|---|---|---|---|
| P1–P2 | Tabela 14 (painel B) | o pandoc gera o painel B como 2.ª tabela, sem título nem Fonte | juntar os painéis numa tabela só (linha "Painel B" no corpo) |
| P3–P4 | Tabela 15 / Figura 10 | a figura 10 vem dentro de tabela de leiaute do pandoc | inserir a figura fora de tabela, com legenda e Fonte próprias |

## B. Alertas por grupo

| Grupo | Qtd | Veredito | Base no manual | Correção |
|---|---|---|---|---|
| Referências fora do formato do manual (autoria em CAIXA ALTA, nome por extenso, ano no fim, "v. n. p.", local antes da editora, "2. ed.", datas por extenso) | 87 | **Procedente** | 18.1, 19.1–19.6 | estilo CSL próprio do manual no pandoc + completar campos no .bib (cidade/UF/país, edição, DOU) |
| Dois autores com ";" em vez de "e" | 15 | **Procedente** | 17.2 | mesmo CSL (citação) |
| Três ou mais autores por extenso em vez de "et al." | 5 | **Procedente** | 17.2 | mesmo CSL |
| Citação no meio da frase com nome entre parênteses ("(Blinder, 1973" → "Blinder (1973)") | 1 | **Procedente** | 17.2 | citação narrativa no texto |
| Konfound citado como "(Konfound, Frank et al. (2013))" | 1 | **Procedente** | 17 | reescrever: "Konfound (Frank et al., 2013)" |
| Brasil 2023b e 2023c sem correspondência | 2 | **Procedente** | 17.2 (mesmo autor e ano: a, b, c também na referência) | CSL com sufixo de ano nas referências |
| Soares (2009) "não encontrado" | 1 | Não procedente (a referência existe) — some com o novo estilo | — | — |
| Tabela/figura não citada ou citada depois da inserção (Tab. 3, 8, 12; Fig. 3, 9) | 5 | **Procedente** | 15.1, 15.2 | chamada no parágrafo anterior |
| Chamada não está no parágrafo imediatamente anterior (Tab. 4, 6, 9, 10; Fig. 6) | 5 | **Procedente** | 15.1, 15.2 | mover a chamada ou o objeto |
| Equações sem número / eq. (2) sem chamada | 2 | **Procedente** | 15.3 | numerar (1), (2) à direita e chamar "eq. (1)" antes |
| Sigla entre parênteses na 1.ª ocorrência ([UPA], [IPS]) | 2 | **Procedente** (vale para todas as siglas, não só essas) | Tab. 6 do manual | colchetes na 1.ª definição de cada sigla |
| Resumo com "Concluiu-se que" | 1 | **Procedente** | regra do formatador (estilo) | reescrever a última frase do Resumo |
| Figuras com painéis rotulados "(a)/(b)", "(A)/(B)", "Estados/Bairros" | 3 | **Procedente** | 15.1 | letra maiúscula sem parênteses no canto superior esquerdo |
| Gráfico inserido como imagem | ~7 | **Não procedente** na inserção (exceção: gerado em Python, não reproduzível no Excel); **procedente** na formatação: título dentro da imagem e linhas de grade são vedados | 15.1, Tab. 8 | manter imagem; retirar título interno e grade das figuras |
| Imagem dentro de célula de tabela | 2 | **Procedente** | 15.1 | = problemas P3–P4 |

## C. Ajustes automáticos do formatador (387) — pontos a conferir

- "Fonte: Resultados originais" → "Dados originais" nas tabelas da seção de Implementação: **correto**
  pelo manual (Tab. 9: "Dados originais" na Metodologia; "Resultados originais" em Resultados e Discussão).
- Tabelas divididas com "(continua)/(conclusão)": aceitável pela norma; no nosso Word elas ficam inteiras.

## D. Dados que faltam para fechar as referências

- Documentos jurídicos: data de publicação no DOU, seção e página (8 normas) — verificar em fonte oficial.
- Frank et al. (2013) e Wilm et al. (2026): o manual exige **todos** os autores na referência.
- Cidade/estado/país das editoras (livros) e do evento (Chen e Guestrin, 2016).

## E. Aplicado em 06/10/2026 (manhã)

| Grupo | Como | Onde |
|---|---|---|
| Citações e referências (≈110) | estilo CSL do manual + .bib próprio do Word (autoria "Sobrenome, I.", ano após autor, sufixo 2026a/b/c, "e"/"et al.", local com UF e país, "2ed.", páginas com hífen, DOU com data, seção e página conferidos na Câmara) | `tcc/scripts/esalq_mba.csl`, `tcc/scripts/bib_manual_esalq.bib`, `gerar_tcc_normas_docx.py` |
| Problemas P1–P4 | Tabela 14 em duas (14 e 15, cada uma com título, Fonte e chamada); Figura dos waterfalls numa imagem só, painéis A e B | `gerar_tabela_cv.py`, `gerar_figura_waterfall_ab.py`, `enxuto_patches.py` |
| Chamada antes da inserção (10) | regra no conversor: cada objeto vai para depois do parágrafo que o cita, na mesma seção; chamadas novas para a Tab. de simetria e a figura SHAP | `chamada_antes()` em `gerar_tcc_normas_docx.py` |
| Equações (2) | número "(1)", "(2)" fora da equação, no fim da linha, parágrafo à direita; "eq. (1) e (2)" no parágrafo anterior | `numerar_equacoes()` em `formatar_docx_normas.py` |
| Siglas (2+) | colchetes na definição quando as iniciais formam a sigla (UPA, IPS, LR, ML) | `siglas_em_colchetes()` |
| Resumo | "Concluiu-se que" → frase direta no pretérito | `tcc_normas_texto.py` |
| Konfound / Blinder / bad controls | citações reescritas | `enxuto_patches.py` |
| Figuras | sem título interno nem grade; painéis A/B; legendas "no painel A/B"; cópia da SHAP sem título | `src/figuras_ptbr.norma_manual`, geradores das figuras |
| Fonte "Dados originais" na Implementação | por seção, no pós-processamento | `formatar_docx_normas.py` |
| E-mail do orientador | linha provisória retirada (envio sem e-mail, decisão do autor) | `tcc_normas_texto.py` |

Portões: norma 31/31 (novos: referências no formato do manual, sem caixa alta), Word 49 pp.,
fósseis 0, números sem fonte 0, validate consistente, verificar_analises 0 ALTO.
Não aplicado: gráfico como objeto do Excel (exceção do manual para software que não reproduz no Excel).

## F. Segundo relatório (06/10 14:06): 0 problemas, 30 alertas

| Alerta | Qtd | Veredito | Ação |
|---|---|---|---|
| E-mail do orientador | 1 | procede | decisão do autor: enviar sem (dado não disponível) |
| Ordem das obras no mesmo parênteses (1 autor → 2 → et al.) | 2 | procede (17.2) | `ordenar_citacoes()` no formatador |
| Equação (1) com número fora do fim da linha | 1 | procede | equação compactada (vetor **E** das dummies de escolaridade): cabe na linha |
| Tabela 3 e Tabela 7: chamada só em nota de rodapé | 2 | procede | `chamada_antes` ignora notas de rodapé; chamada da tabela de ajuste do GLMM no corpo |
| Gráfico como imagem | 1 | não procede (exceção do manual: software que não reproduz no Excel) | — |
| Subtítulos de livros com iniciais maiúsculas | ~12 | procede (nota 1, p. 51: subtítulo só com a 1.ª letra maiúscula) | subtítulos corrigidos no `bib_manual_esalq.bib` |
| Título principal de livro em minúsculas ("Racismo estrutural", "brasil") | ~8 | **não procede**: o manual (18.1) manda iniciais maiúsculas em título de livro, exceto preposições; a ferramenta sugere até "brasil" minúsculo | mantido conforme o manual |
| Data por extenso no nome da lei ("13 de abril de 1995") | 1 | **não procede**: é o nome oficial da norma; o exemplo do próprio manual (19.5) mantém "de 27 de setembro de 2021" e abrevia só a data do DOU | mantido |
| "Alencar 2026c não citada" / "Alencar 2026 sem sufixo" / "Brasil 2023 sem sufixo" | 3 | **não procede**: o manual (17.2) manda "Mariano (2019a, b)" e o mesmo sufixo na referência; a ferramenta não lê "2026a, b, c" | mantido |
| Apostilas como "Trabalhos Acadêmicos"; Henriques como relatório online; "Xgboost" | 3 | divergência de classificação ou de grafia (nome próprio XGBoost) | mantido |

## G. Terceiro relatório (06/10, fim da tarde): 0 problemas, 27 alertas

| Alerta | Veredito | Ação |
|---|---|---|
| Equação sem número (Implementação) | procede: a decomposição de Oaxaca estava no meio do parágrafo, sem número | virou eq. (3), com chamada "eq. (3)" |
| "10" por extenso | procede em "Hosmer–Lemeshow em 10 decis" e "VIF acima de 10" | "dez" (os demais são rótulos de tabela e figura) |
| Citação "(2010)" sem referência | formato "(Brasil, 1995, 2010)" é o do manual, mas a ferramenta lê ", 2010)" sozinho | cada lei citada junto do seu nome |
| Tabela 14 partida entre páginas | procede no arquivo deles (tabela em Arial 11 e largura total cresce) | Nota presa à Fonte e à tabela: o bloco muda de página inteiro |
| E-mail do orientador; gráfico como imagem; títulos de livro; datas no nome das leis; 2026a, b, c | mantidos (ver seção F) | — |
