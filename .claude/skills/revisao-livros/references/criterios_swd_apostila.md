# Critérios destilados — Storytelling com Dados (Knaflic) + Apostila Árvores/Ensembles (Alencar, USP/ESALQ)

Formulação própria a partir da leitura integral. Cada item vira um check (ID) na skill.

## A. Knaflic — Storytelling com Dados (leitura integral, caps. 1–10)

### A1. Contexto (cap. 1)
- SWD-01 Público único e explícito (a banca / o orientador), não "interessados em geral".
- SWD-02 Explanatório, não exploratório: mostrar as "pérolas", não as 100 ostras. Sinal de violação: coleção de métodos/gráficos sem seleção.
- SWD-03 Grande Ideia em UMA frase completa (ponto de vista + o que está em jogo). Deve existir literalmente no resumo/introdução/conclusão.
- SWD-04 História de 3 minutos existe (resumo executivo / roteiro de defesa).
- SWD-05 Storyboard: títulos primeiro; estrutura decidida antes do software.
- SWD-06 Não esconder dados que contradizem — mostrar contra e a favor (credibilidade).
- SWD-07 Mecanismo: apresentação ao vivo = poucos slides, pouco texto; documento = mais denso e autossuficiente. Não produzir "slidemento" (híbrido que não serve a nenhum).
- SWD-08 Tom coerente com o assunto (análise estatística → clínico/sóbrio; paleta discreta).

### A2. Escolha do visual (cap. 2)
- SWD-10 Um ou dois números → texto simples, não gráfico.
- SWD-11 Tabelas: para leitura linha a linha, público misto, múltiplas unidades. Bordas leves/cinza; dados em primeiro plano. Raramente em apresentação ao vivo (jogar para apêndice).
- SWD-12 Mapa de calor: saturação de uma única cor + legenda.
- SWD-13 Linhas para dados contínuos/tempo; intervalos de tempo consistentes no eixo x; pode mostrar média + faixa (IC) no próprio gráfico.
- SWD-14 Gráfico de inclinação (slopegraph) para dois períodos/pontos de comparação.
- SWD-15 Barras para categóricos; **linha de base ZERO obrigatória** em barras (não em linhas, mas avisar se base ≠ 0). Largura da barra > espaço entre barras.
- SWD-16 Barras horizontais preferidas para categorias com nomes longos; ordenação lógica (natural se ordinal; senão decrescente/crescente pelo valor).
- SWD-17 Barras empilhadas só para totais + partes; empilhadas 100% para Likert/partes do todo com linha de base nos dois lados.
- SWD-18 Cascata para decomposições (ex.: Oaxaca-Blinder: gap bruto → explicado → não explicado).
- SWD-19 Evitar: pizza, rosca, 3D (nunca), eixo y secundário (separar gráficos ou legendar direto), gráficos de área (exceto magnitudes muito díspares).
- SWD-20 Ética: sem escala truncada, sem manipulação que exagere diferenças.

### A3. Eliminar saturação (cap. 3)
- SWD-30 Cada elemento custa carga cognitiva; maximizar data-ink (Tufte)/sinal-ruído.
- SWD-31 Gestalt: proximidade, similaridade, acercamento, fechamento, continuidade, conexão — usar para tirar bordas, fundos, gridlines.
- SWD-32 Remover: borda do gráfico, gridlines (ou cinza fino), marcadores de dados por padrão, zeros à direita nos rótulos, texto diagonal.
- SWD-33 Legendar séries diretamente ao lado dos dados (proximidade) e na mesma cor (similaridade); evitar legenda separada.
- SWD-34 Alinhamento: texto alinhado à esquerda (não centralizado); títulos no topo-esquerda; linhas limpas.
- SWD-35 Espaço em branco: margens livres; não esticar gráficos para preencher; não "adicionar dados só porque há espaço".
- SWD-36 Contraste estratégico: "o falcão entre pombos" — se tudo é diferente, nada se destaca.
- SWD-37 Manter unidades junto aos números (R$, %, separador de milhar).

### A4. Focalizar atenção (cap. 4)
- SWD-40 Memória de curto prazo ≈ 4 blocos: nunca 10 séries com 10 cores + legenda.
- SWD-41 Atributos pré-atentivos (cor, tamanho, posição, espessura, intensidade): usar para (a) dizer onde olhar e (b) criar hierarquia visual.
- SWD-42 Tudo em cinza, UMA cor de destaque (azul recomendado: daltonismo, imprime em P&B).
- SWD-43 Cor: com moderação; uniforme em todo o trabalho (mesmo grupo = mesma cor em todas as figuras); nunca vermelho×verde como única distinção; pensar no tom.
- SWD-44 Comprimento/posição codificam quantidade; cor categórica não. Escala sequencial = saturação de uma cor.
- SWD-45 Posição na página: zigue-zague em Z; o mais importante no topo-esquerda; escalas negativo→positivo da esquerda para a direita.
- SWD-46 Teste "para onde meus olhos vão primeiro?" em cada figura/slide.
- SWD-47 Tamanho relativo = importância relativa (não deixar o dado mais fácil de obter ocupar 60% do painel).

### A5. Pensar como designer (cap. 5)
- SWD-50 Affordances: realçar no máx. ~10% do visual (Lidwell); negrito > itálico/sublinhado; maiúsculas em rótulos curtos; sobrepor atributos no ponto crucial.
- SWD-51 Eliminar distrações: "eliminar isso mudaria algo? Não? Elimine"; contexto na dose certa; apêndice para o que é necessário mas não central.
- SWD-52 Hierarquia visual clara; supercategorias para organizar muitas categorias (ex.: agrupar 20 controles em capital humano / ocupação / geografia).
- SWD-53 Acessibilidade: "se é difícil de ler, é difícil de fazer"; fonte legível; linguagem simples; siglas definidas na 1ª vez; complexidade só a necessária (o PhD de palavras de cinco sílabas).
- SWD-54 Texto é amigo: todo gráfico com título; todo eixo com título (exceção raríssima e deliberada); fonte dos dados em nota de rodapé; conclusão escrita com palavras (não presumir que dois leitores tirem a mesma conclusão).
- SWD-55 **Títulos de ação** em slides e figuras (afirmam o achado), não títulos descritivos ("Resultados do HLM").
- SWD-56 Anotações no gráfico para explicar nuances/pontos de interesse.
- SWD-57 Estética: cor inteligente + alinhamento + espaço em branco → tolerância do público.
- SWD-58 Aceitação: mostrar antes/depois; opinião de terceiro sem contexto.

### A6. Modelos visuais (cap. 6)
- SWD-60 Previsão/contrafactual distinguível do real (linha pontilhada, sombreado).
- SWD-61 Título de gráfico em cinza escuro, não preto puro; nota de rodapé menor e cinza.
- SWD-62 Ordem das séries empilhadas deliberada (a mais importante junto à linha de base).
- SWD-63 Rótulos numéricos apenas nos pontos que importam; eixo preservado para magnitude geral OU rótulos diretos, não os dois redundantes.

### A7. Storytelling (cap. 7)
- SWD-70 Estrutura em 3 atos: início (contexto, desequilíbrio), meio (o que poderia ser, evidência), fim (chamada para ação / o que a banca deve concluir).
- SWD-71 Conflito/tensão explícita: "o que é vs. o que poderia ser" (ex.: gap persiste apesar de controles).
- SWD-72 Perguntas de Atkinson/McKee: ambiente, protagonista, desequilíbrio, equilíbrio, solução.
- SWD-73 Fluxo: cronológico (credibilidade/processo) ou começar pelo fim (público sabe o "e daí"). Anunciar a estrutura escolhida.
- SWD-74 Bing-Bang-Bongo: sumário executivo → conteúdo → recapitulação (repetição).
- SWD-75 **Lógica horizontal**: ler só os títulos dos slides conta a história inteira.
- SWD-76 **Lógica vertical**: tudo em um slide se reforça; nada extrínseco.
- SWD-77 Storyboard inverso: anotar o ponto principal de cada página e comparar com o esboço.
- SWD-78 Nova perspectiva: alguém sem contexto lê e diz o que entendeu.
- SWD-79 Declarações curtas repetíveis (frase-síntese memorável).
- SWD-80 Protagonista = público; Vonnegut: simplificar, cortar com coragem, ter dó do leitor.

### A8. Processo (caps. 8–10)
- SWD-90 Iterar: "estratégia do optometrista" (A vs. B com uma mudança).
- SWD-91 Mesmo visual, ênfases sucessivas para apresentação ao vivo; versão anotada única para o documento distribuído.
- SWD-92 Ordem lógica em barras; manter a mesma ordem ao contar várias histórias com o mesmo gráfico.
- SWD-93 Gráfico espaguete → destacar uma linha por vez, ou pequenos múltiplos (mesmos eixos min/max).
- SWD-94 Alternativas à pizza: número direto, barras simples, empilhadas 100%, slopegraph.
- SWD-95 Fundo branco por padrão.
- SWD-96 Reservar tempo para a etapa de comunicação (é a única que o público vê).

## B. Alencar — Árvores, Redes e Ensembles I (apostila USP/ESALQ)

- ML-01 Separação treino/teste (ex.: 80/20) obrigatória; métricas reportadas em dados nunca vistos.
- ML-02 Validação cruzada k-fold para robustez e para escolher hiperparâmetros.
- ML-03 Classificação: matriz de confusão + acurácia, precisão, recall, F1, curva ROC/AUC; escolher a métrica pelo custo do erro (FP vs FN) e pelo desbalanceamento.
- ML-04 Regressão: MSE, RMSE, MAE, R²; reportar RMSE/MAE na unidade original (ex.: "erra R$ X mil em média").
- ML-05 Overfitting: comparar desempenho treino vs. teste; queda grande = decorou. Causas: profundidade, variáveis irrelevantes, poucos dados.
- ML-06 Hiperparâmetros (max_depth, min_samples_split, min_samples_leaf, criterion; em XGBoost: learning_rate, n_estimators, subsample) escolhidos por CV, não ad hoc; documentar a grade.
- ML-07 Sensibilidade a pequenas mudanças e a classes majoritárias; dificuldade de extrapolação fora da faixa de treino.
- ML-08 Modelo "white box": cada previsão explicável por regras → no TCC, SHAP cumpre esse papel e deve ser apresentado como explicação, não como causalidade.
- ML-09 Viés-variância como conceito central para justificar ensembles.
- ML-10 Referência-base: Géron (2021), documentação scikit-learn.
