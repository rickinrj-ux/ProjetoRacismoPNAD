# Lições aprendidas — TCC PNAD

3/10/2026 · Ricardo Calheiros
Versão viva (para editar e comentar): https://claude.ai/code/artifact/63d05268-8ab4-4927-b6a1-70d3df9c545d

Em cinco meses, a penalidade racial condicional passou de 9,7% a 10,4% e caiu para 6,1%; a razão de chances de acesso a cargo qualificado foi de 0,704 a 0,814. Quase toda essa mudança veio de erros de dados e de especificação, não de escolha de método. Este documento registra 23 episódios, como cada um foi descoberto, o que custou em números e a prática que fica.

## Linha do tempo dos números-manchete

A maior mudança (10,4% → 6,1%) não veio de um método novo: veio de uma variável lida errado durante quatro meses.

| Data | Penalidade condicional (M3) | OR de acesso a cargo qualificado | O que mudou |
| --- | --- | --- | --- |
| 03/10/2026 | 6,1% | 0,814 | Escolaridade pela VD3004 (a V3009A era lida como nível), renda deflacionada com efeito de ano, fundamental completo em todos os modelos |
| 01/10/2026 | 10,4% | 0,697 | Médias de contexto do bairro sem a própria pessoa (leave-one-out) |
| 20/09/2026 | 10,2% | 0,699 | HLM refeito em dois níveis com intercepto aleatório de UPA; GLMM de verdade (glmer) no lugar do logit rotulado como GLMM |
| 15/06/2026 | 9,6% | 0,705 (logit com efeito fixo) | Escopo reduzido ao núcleo de 4 métodos; indicador `educ_missing` desde 03/06 |
| 26/05/2026 | — | 0,691 | GLMM passa a usar a população ocupada inteira (N de 2,4 milhões para 7,7 milhões) |
| 25/05/2026 | 9,7% | — | HLM na população completa, não mais em amostra de 20% |
| 18/05/2026 | — | 0,704 | Primeiro GLMM (N = 2.395.285; o desfecho real era `ocp_qualif`, não `emprego_formal`) |
| 16/05/2026 | 9,7% | — | Primeira escada do HLM, em amostra de 20% (N = 1.537.885) |

Repare na assimetria: as correções de método (dois níveis, glmer, leave-one-out) mexeram na casa decimal; a correção de dado mexeu em quatro pontos percentuais.

## Dados: as seis lições que mais mudaram os números

### 1. Leia o dicionário antes de mapear uma variável

- **O que aconteceu:** a escolaridade vinha da V3009A, que é o *curso mais elevado que a pessoa frequentou* (15 códigos), mapeada com um dicionário de 8 níveis feito para outra variável. O código 7 (fundamental regular) virava "superior completo"; os códigos 9 a 15 (médio, superior, pós; 5,2 milhões de pessoas) viravam ausentes.
- **Como apareceu:** na releitura de 02/10, como "escolaridade implausível": negros com mais superior completo que brancos (27,8% × 19,8%) e retorno negativo do ensino médio. Tabular a renda média por código revelou o erro em segundos.
- **Custo:** a penalidade condicional caiu de 10,4% para 6,1%; o OR de acesso subiu de 0,697 para 0,814; o ICC do M3 caiu de 0,144 para 0,076.
- **Prática:** para cada variável recodificada, abrir o dicionário da pesquisa e fazer uma tabela de sanidade (média do desfecho por código, proporções esperadas). Ficou como `checar_escolaridade.py` e `auditar_wrangling.py`.

### 2. Trate a causa, não o sintoma

- **O que aconteceu:** em maio, a escolaridade cobria só 31% da população. Preencher os ausentes com zero invertia os sinais da educação; em 03/06 criou-se um indicador `educ_missing` e os sinais voltaram.
- **Por que era só sintoma:** o "grupo faltante de alta renda" era simplesmente quem tinha médio ou mais — o efeito da lição 1. O remendo durou quatro meses e gerou efeitos colaterais: VIF de 22, uma decomposição interseccional que rodava em 31% da base dizendo "população completa".
- **Prática:** quando um dado faltante tem padrão (aqui, os mais escolarizados), perguntar *por que* ele falta antes de modelar a falta. Cobertura de 31% numa variável básica de uma pesquisa oficial é um alarme, não uma característica dos dados.

### 3. Deflacione séries monetárias

- **O que aconteceu:** a renda era nominal de 2016 a 2025 — subiu 0,57 log-ponto no período, cerca de cinco vezes a penalidade racial. A winsorização de 1% cortava mais o topo dos anos recentes e mais a base dos antigos.
- **Correção:** deflator oficial da PNAD Contínua (UF × trimestre), reais do 2º trimestre de 2026, e efeito de ano em todos os modelos.
- **Prática:** dinheiro em série temporal vai para reais constantes antes de qualquer outra coisa.

### 4. A própria pessoa não pode entrar na média que a descreve

- **O que aconteceu:** as médias do bairro (% de negros, escolaridade, renda, desemprego) incluíam a própria pessoa. É o problema do reflexo (Manski, 1993): a raça de quem se estuda entra no regressor que descreve o seu bairro.
- **Custo:** corrigido em 30/09 com médias *leave-one-out*. A penalidade subiu de 10,2% para 10,4%: o vazamento a subestimava.
- **Recidiva:** a reconstrução da base em 02/10 perdeu o leave-one-out do desemprego, porque ele vivia num script de remendo e não no código que gera a base. O impacto medido foi nulo (β da raça idêntico até a quinta casa), mas ninguém percebeu por um dia.
- **Prática:** correção mora na origem, nunca em remendo; e toda correção ganha um teste que acusa a volta do erro (hoje, média de contexto constante dentro do bairro reprova a base).

### 5. Confira o desfecho e o N que o modelo realmente usa

- **O que aconteceu:** em 18/05 o texto dizia que o GLMM modelava emprego formal com 7,7 milhões de pessoas; o código modelava cargo qualificado com 2,4 milhões. O N encolhido foi atribuído a "empregados com renda", depois à escolaridade faltante; a causa real só apareceu em 02/10 (lição 1). Três diagnósticos até a raiz.
- **Prática:** imprimir, para cada modelo, o desfecho, o N e a taxa do desfecho, e comparar com a população. A amostra do GLMM tinha 3,9% de cargos qualificados; a população, 29,8%.

### 6. Resultado que só existe na amostra não é resultado

- **O que aconteceu:** os primeiros modelos rodavam em 20% da base. Numa amostra, o ICC do bairro deu 14,6% para negros e 11,2% para brancos, e isso virou narrativa ("duplo disadvantage contextual"). Na população completa, a diferença era zero.
- **Prática:** população completa sempre que o computador aguentar; amostra só declarada e aprovada (ficou como regra do projeto). Diferenças pequenas entre subgrupos são as primeiras a sumir.

## Especificação e inferência

### 7. O modelo descrito tem de ser o modelo estimado

- **O que aconteceu:** por meses, o texto descreveu um HLM de três níveis que o código não estimava (o bairro tinha virado efeito fixo para caber na memória). E a tabela "GLMM com efeito aleatório de bairro" vinha de um logit com efeito fixo de estado; o glmer de verdade existia, mas não alimentava a tabela.
- **Correção (20/09):** HLM de dois níveis com escada M0 → M4 e testes de razão de verossimilhança; GLMM em R (lme4), um modelo por processo; o logit com efeito fixo ficou como robustez.
- **Prática:** a legenda de cada tabela deve sair do mesmo código que estimou o modelo, não ser escrita à parte.

### 8. Agrupe os erros-padrão no nível em que os dados são agrupados

- **O que aconteceu:** o erro-padrão publicado ignorava que pessoas do mesmo bairro e estado compartilham choques. Agrupado por estado, era 15 vezes maior para a raça e 55 vezes maior para o % de negros no bairro (fator de Moulton).
- **Correção:** agrupamento por UPA e por UF, bootstrap em blocos de UPA na Oaxaca e na regressão quantílica.
- **Prática:** com 7,7 milhões de observações tudo é "significativo"; o erro-padrão certo é o que separa um resultado de um artefato.

### 9. Uma variável que é resultado do processo não é controle neutro

- **O que aconteceu:** a Oaxaca tratava a ocupação como "característica" do trabalhador. Mas o acesso à ocupação é parte da discriminação estudada (*bad control*, Angrist e Pischke). Com ela, o não explicado era 16%; sem ela, 29%.
- **Prática:** apresentar as duas especificações e chamar a com ocupação de limite inferior. Comparar com a literatura só na mesma especificação.

### 10. Os modelos precisam controlar as mesmas coisas

- **O que aconteceu:** HLM e GLMM tinham a dummy de fundamental completo; Oaxaca, quantílica e RIF não. Com dummies cumulativas, a categoria de referência desses três misturava quem não tem instrução com quem completou o fundamental. O mesmo tipo de assimetria apareceu com a jornada de trabalho e com o efeito de ano.
- **Prática:** uma tabela de "simetria de controles" (bloco × modelo) conferida a cada mudança de especificação.

### 11. Decomposições têm contas que precisam fechar

- **O que aconteceu:** a primeira Oaxaca omitia a diferença dos interceptos e dava "discriminação" de −91%. A primeira RIF somava uma coluna de interação que já estava dentro das dotações (dupla contagem) e misturava o gap observado com percentuais do gap decomposto.
- **Prática:** conferir que as partes somam o todo e que o todo bate com o gap observado; quando não bate, mostrar os dois.

### 12. "Convergiu" é uma informação, não um detalhe

- **O que aconteceu:** o otimizador padrão parava com variância do bairro igual a zero e verossimilhança infinita; outro devolvia `converged=False` com a variância 12% acima do ótimo. O efeito da raça mudava pouco, mas o ICC mudava (0,161 → 0,144).
- **Prática:** registrar a convergência de todo modelo e testar um segundo otimizador quando ela falha; ficar com o de maior verossimilhança.

## Redação estatística

O número certo com a frase errada é um erro: a banca lê a frase.

### 13. Razão de chances não é probabilidade

"OR = 0,70" não quer dizer "30% menos probabilidade"; quer dizer chances (*odds*) 30% menores. Em probabilidade, o efeito era de 5,6 pontos percentuais (hoje, 2,6). **Prática:** dizer "chances X% menores" e mostrar o efeito marginal em pontos percentuais ao lado.

### 14. "Metade" só quando é metade

O título "metade do gap desaparece no mesmo bairro" nasceu de uma mediação de 47%; com os números corrigidos, ela é 39%. **Prática:** palavras quantitativas ("metade", "um em cada dez", "a maior parte") são geradas a partir do número, com uma regra ("metade" só entre 45% e 55%), nunca escritas à mão.

### 15. Não ranqueie grandezas de unidades diferentes

"A barreira mais dura não é o salário, é a porta" comparava pontos percentuais de probabilidade com % de salário — e as magnitudes, nas mesmas unidades, diziam o contrário. **Prática:** duas barreiras em unidades diferentes ficam lado a lado, sem "maior" nem "supera". A frase que ficou: "o diploma quase iguala o salário, mas não abre a porta".

### 16. Condicional e incondicional respondem a perguntas diferentes

A regressão quantílica (penalidade crescente no topo, entre pessoas de mesmo perfil) e a RIF (parcela não explicada maior na base da renda do país) pareciam se contradizer. Não se contradizem: uma compara pares, a outra decompõe a distribuição. E "os negros do topo sofrem mais" é frase sobre indivíduos que quantis não sustentam.

### 17. Média de quem? Estados ou pessoas

No mapa da penalidade por estado, a "média nacional" era a média *entre estados*, em que Roraima pesa quase o mesmo que São Paulo. Na pós-graduação, ela dava 6,7%; a média do país, em que cada pessoa pesa igual, dá 1,1%. Cheguei a levantar uma hipótese errada (efeitos fixos × aleatórios) antes de ver que era só o peso. **Prática:** toda média diz quem tem peso nela.

### 18. Conclusão escrita antes do número envelhece

"A década não produziu convergência mensurável" valia com p = 0,169; com a base corrigida, p = 0,027 e a convergência é significativa (e lenta). A frase-manchete, o título do bairro e o contraste diploma × porta passaram a ser escolhidos pelo código conforme os números. **Prática:** frases que dependem do resultado são condicionais ao parâmetro.

### 19. Leitura log-linear e linguagem causal

Um coeficiente de −0,2123 em log-renda não é "21,2% a menos": é 1 − e^−0,2123 = 19,1%. E "comprova", "determina", "principal determinante" não cabem em dados observacionais transversais. **Prática:** converter sempre (exp(β) − 1) e usar "associa-se", "é consistente com", "penalidade condicional".

## Engenharia e reprodutibilidade

### 20. Números digitados viram fósseis

- **O que aconteceu:** cada reestimação deixava números velhos espalhados: OR 0,741 num lugar e 0,704 noutro na mesma semana; um "R$ 73 bilhões" sem nenhum cálculo de origem; 45 números digitados no deck da Defesa; um "41.517 clusters" que eram 40.968.
- **Correção em três gerações:** um arquivo de parâmetros (maio), uma fonte única que lê os csv, `params_nucleo.py`, com 249 parâmetros (setembro), e por fim marcadores no texto e dois portões automáticos — um que caça números digitados no código e outro que confere cada número dos entregáveis contra os csv (outubro).
- **Prática:** nenhum número de resultado é digitado. O texto pede o parâmetro; o parâmetro vem do csv; o csv vem do modelo.

### 21. Cache é um resultado antigo esperando para ser publicado

- **O que aconteceu:** depois da correção de 30/09, o HLM devolveu silenciosamente os modelos de 23/09 guardados em cache, e a RIF devolveu as estimativas pontuais de junho guardadas em checkpoint — uma tabela saiu com erros-padrão novos e estimativas velhas.
- **Prática:** toda mudança na base invalida explicitamente caches e checkpoints (mover para backup antes de reestimar), e o cache deve guardar a identidade dos dados que o geraram.

### 22. Regressões silenciosas precisam de alarme

A perda do leave-one-out do desemprego (lição 4), os geradores antigos que sobrescreviam entregáveis bons, um verificador que "sempre falhava" e por isso deixou de ser lido, um teste visual que dava 21 de 21 com falso positivo. **Prática:** um portão que falha sempre é tão inútil quanto nenhum; geradores superados ficam travados; cada correção ganha seu teste.

### 23. Computação grande pede um modelo por processo e mudanças pequenas e salvas

- **O que aconteceu:** 7,7 milhões de linhas estouraram a memória várias vezes (seis HLMs juntos, um `glm()` acima de 20 GB, processos encerrados por falta de memória). A saída foi uma fila de passos, um modelo por processo, retomando do que já estava gravado.
- **E o que ainda está em risco:** nada do que aconteceu de 29/09 a 03/10 foi para o git — 233 arquivos modificados, incluindo a correção da escolaridade. É a lição mais barata de aplicar: **commitar a cada correção que muda números, com o porquê na mensagem.** Foram as mensagens de commit que permitiram reconstruir este documento.

### 24. "Os mesmos controles" precisa ser verificado, não declarado

- **O que aconteceu:** o texto dizia que a Oaxaca, a RIF e a regressão quantílica usavam os controles do HLM M3, mas jornada, área urbana e UF faltavam nas três. Com eles, a parcela "preço" da Oaxaca caiu de 23,4% para 17,9% e a penalidade da QR na base, de 5,7% para 4,3%.
- **Prática:** comparar as fórmulas lado a lado por código (conjuntos de variáveis), e não pela legenda.

### 25. O agregado esconde a composição

- **O que aconteceu:** a mulher negra parecia "alçada" no acesso a cargos CBO 1–4 (OR 1,31). Separado por grande grupo, era o apoio administrativo e as profissões feminizadas; entre dirigentes, ela tinha a menor chance de todos (OR 0,63). Foi a desconfiança do autor, apoiada no que se noticia, que puxou a desagregação.
- **Prática:** antes de narrar um resultado surpreendente, desagregar a categoria.

### 26. Escala e fórmula mudam a conclusão

- **O que aconteceu:** a "penalidade extra de +4,4 pp" da mulher negra somava percentuais (escala convexa); em log-pontos o efeito era sub-aditivo. E o E-value aplicado direto à razão de chances de um desfecho com 30% de prevalência saía 1,76 em vez de 1,46.
- **Prática:** somar efeitos só na escala aditiva (log); conferir a hipótese de cada fórmula (desfecho raro) antes de aplicá-la.

### 27. Arquivo gerado não se edita

- **O que aconteceu:** referências acrescentadas direto no `.bib` sumiram na regeneração seguinte, porque o arquivo é escrito por um gerador.
- **Prática:** antes de editar um arquivo, saber quem o escreve; editar a fonte.

## Checklist para o próximo projeto

Os 23 episódios cabem em quinze perguntas. Antes de confiar num número:

**Dados**

- [ ] Cada variável recodificada foi conferida no dicionário, com uma tabela do desfecho por código?
- [ ] A cobertura de cada variável é plausível para a fonte? (31% é alarme.)
- [ ] Valores monetários estão em reais constantes, com efeito de período?
- [ ] Nenhuma média de grupo inclui a própria observação que ela descreve?
- [ ] Desfecho, N e taxa do desfecho de cada modelo batem com a população?
- [ ] Rodou na população completa, ou a amostra está declarada e aprovada?

**Modelos**

- [ ] A legenda descreve o modelo que o código estimou?
- [ ] Os erros-padrão estão agrupados no nível em que os dados são agrupados?
- [ ] Algum controle é ele próprio resultado do processo estudado (*bad control*)?
- [ ] Todos os modelos controlam o mesmo conjunto de variáveis?
- [ ] Todos convergiram, e as decomposições somam o todo?

**Texto e entrega**

- [ ] Algum número, "metade" ou "maior" foi escrito à mão em vez de vir do resultado?
- [ ] Odds, probabilidade, % e log-pontos estão nas unidades certas, sem comparações entre unidades diferentes?
- [ ] Caches e checkpoints foram invalidados depois da última mudança na base?
- [ ] A correção está no código de origem, com um teste e um commit que explica o porquê?

## Fontes

Tudo vem do próprio repositório do projeto (`ProjetoRacismoPNAD`); nenhum número foi recalculado para este documento.

- **Histórico do git:** 151 commits de 15/05 a 28/09/2026 — as mensagens trazem o porquê de cada correção. Os episódios de 29/09 a 03/10 ainda não estão commitados.
- **Revisões em `tcc/revisoes/`:** `revisao_2026-09-18.md`, `auditoria_pre_entrega_2026-09-29.md`, `releitura_2026-10-02.md`, `RETOMADA_reestimacao_loo.md`, `antes_depois_2026-10-03.md`, `TODO_revisao.md`.
- **Perícia de 15/06:** `tcc/PERICIA.md`.
- **Comparação amostra × população:** `docs/COMPARACAO_AMOSTRA_POPULACAO.md`.
- **Código com o registro das correções:** `src/feature_engineering.py` (escolaridade, deflação, leave-one-out), `tcc/scripts/params_nucleo.py` (fonte única), `tcc/scripts/checar_escolaridade.py` e `tcc/scripts/auditar_wrangling.py` (sanidade da base).
- **Backups dos resultados anteriores:** `outputs/_backup_pre_loo/` e `outputs/_backup_pre_educ/`.
- **Memória do projeto:** notas por episódio mantidas ao longo do trabalho (escolaridade, GLMM, amostragem, números fósseis, leave-one-out).
