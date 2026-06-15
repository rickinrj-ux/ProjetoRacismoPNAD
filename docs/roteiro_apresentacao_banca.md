# Roteiro de Apresentação — Banca de Defesa TCC
## Racismo Estrutural e Mercado de Trabalho no Brasil
**Ricardo Calheiros | MBA Data Science & Analytics | USP/ESALQ | 2026**

---

> **Leia este roteiro em voz alta pelo menos duas vezes antes da defesa.**
> Internalize os números e a lógica de convergência entre os quatro métodos do núcleo.
> Tempo total: **20 minutos**. Perguntas: 15–25 min adicionais.

> **Escopo (núcleo de 4 métodos).** Após o feedback do orientador, o trabalho foi
> priorizado em **quatro métodos complementares** — HLM, Oaxaca-Blinder, Regressão
> Quantílica/RIF e GLMM logístico — validados por **robustez** (ML/SHAP, E-values,
> interseccionalidade). Análises adicionais (redes sociais, agrupamento, setor público,
> pesquisa operacional) existem no repositório como **agenda futura/versão estendida** e
> não fazem parte do corpo defendido.

---

## ORIENTAÇÕES GERAIS

- **Tom**: objetivo e técnico. Você apresenta evidências, não militância. Deixe os números falarem.
- **Postura**: ao citar um número, olhe para a plateia — você conhece o dado.
- **Transições**: as frases marcadas com → conectam os slides.
- **Se travar**: respire e leia o número principal do slide.

---

## SLIDE 1 — CAPA (1 min)

> "Bom dia/boa tarde. Meu trabalho investiga o racismo estrutural no mercado de trabalho
> brasileiro usando a PNAD Contínua de 2016 a 2025 — dez anos de dados, com até 7,7 milhões
> de observações com renda positiva por análise.
>
> A pergunta central é: depois de controlar escolaridade, experiência, horas, localização e
> ocupação, ainda existe uma penalidade associada à raça? E se sim, ela está no salário, no
> acesso às melhores ocupações, ou em ambos?
>
> Respondo com quatro métodos complementares que se triangulam."

→ *Slide 2*

---

## SLIDE 2 — O PROBLEMA (1,5 min)

> "O rendimento médio do trabalho de brancos supera o de negros em cerca de **53%** (gap
> bruto). Parte disso é **composição** — negros têm, em média, menos escolaridade e ocupações
> menos qualificadas, reflexo de desigualdades históricas. Parte é **discriminação** — uma
> penalidade que persiste comparando pessoas de mesmo perfil.
>
> Distinguir as duas fontes é o que este trabalho faz. E, crucialmente, mostro que mesmo a
> parte de 'composição' não é neutra: o acesso às boas ocupações é, ele próprio, restringido
> por raça.
>
> Uso quatro métodos: **HLM** para decompor o gap em níveis geográficos; **Oaxaca-Blinder**
> para separar composição de discriminação; **regressão quantílica com RIF** para ver como o
> gap muda ao longo da renda; e **GLMM logístico** para medir o gap de *acesso* a ocupações
> qualificadas. A convergência entre eles sustenta a conclusão."

→ *Slide 3*

---

## SLIDE 3 — BASE DE DADOS (1 min)

> "A fonte é a PNAD Contínua do IBGE — cerca de 350 mil domicílios por trimestre. Uso dez
> anos (2016–2025), com a população econômica completa nas análises populacionais.
>
> O dado tem três camadas hierárquicas naturais: indivíduos dentro de unidades primárias de
> amostragem — as UPAs, proxy de bairro — dentro de estados. Isso justifica o uso de modelos
> multinível: ignorar essa estrutura inflaria os erros-padrão."

→ *Slide 4*

---

## SLIDE 4 — ARQUITETURA METODOLÓGICA (1,5 min)

> "Os quatro métodos respondem perguntas distintas e não-redundantes:
>
> **HLM** pergunta *quanto* do gap sobrevive aos controles e em que nível geográfico nasce.
> **Oaxaca-Blinder** separa *composição* de *discriminação*. **Regressão quantílica/RIF**
> pergunta se a penalidade muda ao longo da distribuição de renda. **GLMM logístico** mede o
> gap de *acesso* a cargos qualificados e ao topo.
>
> Como camada de **robustez**: o ML com SHAP valida o resíduo racial sem pressuposto de forma
> funcional; os **E-values** quantificam quanto um confundidor precisaria pesar para invalidar
> o achado; e a decomposição **interseccional** formaliza a penalidade raça × gênero.
>
> A resposta convergente: existe uma penalidade racial sistemática, concentrada no acesso, que
> resiste a qualquer controle razoável."

→ *Slide 5*

---

## SLIDE 5 — HLM: DECOMPOSIÇÃO E MEDIAÇÃO DO GAP (2 min)

> "O HLM tem quatro estágios. Partindo do gap bruto de ~53%:
>
> **M1** adiciona capital humano — escolaridade, idade, sexo: o gap cai para **−19,1%**.
> **M2** adiciona contexto de moradia (UPA): cai para **−9,6%** — ou seja, **52,5%** do gap do
> M1 é mediado por *onde a pessoa mora*. **M3** adiciona o estado: praticamente sem efeito
> adicional. **M4** adiciona **ocupação e formalidade**: o gap cai para **−6,2%**.
>
> No total, **69,8%** do gap é mediado por contexto e ocupação — mas um resíduo de **−6,2%**
> persiste após *todos* os controles observáveis. Essa é a face estrutural: negros estão
> concentrados em piores ocupações e bairros não por acaso, mas por restrição sistemática de
> acesso."

**Números-chave:** *bruto ~53% | M1 −19,1% | M2 −9,6% (mediação contextual 52,5%) | M4 −6,2% (mediação total 69,8%)*

→ *Slide 6*

---

## SLIDE 6 — COMPOSIÇÃO OCUPACIONAL (1,5 min)

> "A estrutura ocupacional por raça é clara. No topo — dirigentes e profissionais — negros têm
> menos da metade da representação proporcional. No fundo — trabalhos elementares — têm o
> dobro. No top 5% das rendas nas capitais, negros são minoria mesmo onde são maioria da força
> de trabalho local.
>
> Isso não é mérito diferencial. É exclusão sistemática do topo — que o GLMM vai quantificar."

→ *Slide 7*

---

## SLIDE 7 — OAXACA-BLINDER: COMPOSIÇÃO vs. DISCRIMINAÇÃO (2 min)

> "O Oaxaca-Blinder decompõe o gap em duas partes: quanto se deve a *diferenças de
> características* (dotações) e quanto a *retornos diferenciais* às mesmas características
> (discriminação).
>
> Na especificação de **acesso** — tratando ocupação e contexto como dotações — **83,8%** do
> gap é composição e **16,2%** é não-explicado. À primeira vista, a discriminação salarial
> direta parece pequena.
>
> Mas atenção à ressalva metodológica, que é o coração do argumento: incluir a ocupação como
> 'dotação' **subestima** a discriminação, porque o acesso à ocupação é ele próprio
> discriminatório. O preconceito age principalmente no **portão de entrada**, não no cheque de
> pagamento. Por isso o Oaxaca precisa ser lido junto com o GLMM."

**Números-chave:** *Dotações 83,8% | Discriminação (não-explicado) 16,2% | ressalva Oaxaca & Ransom (1999): ocupação como dotação subestima a discriminação*

→ *Slide 8*

---

## SLIDE 8 — REGRESSÃO QUANTÍLICA E RIF: TETO DE VIDRO E STICKY FLOOR (2 min)

> "A regressão quantílica estima o gap em cada ponto da distribuição de renda. Sem controlar
> ocupação (M3), o gap vai de **−8,0%** no percentil 10 a **−12,3%** no percentil 95: o gap
> **cresce** monotonicamente rumo ao topo. Isso é o **teto de vidro** no gap bruto.
>
> A decomposição **RIF-OB** acrescenta a nuance. Ela separa, por quantil, dotação e retorno.
> O componente de **retorno** — a discriminação de preço — é **maior na base** (35,1% no q10)
> e **decresce** rumo ao topo (12,9% no q90). Isso é o **sticky floor**: a discriminação
> salarial proporcional pesa mais embaixo.
>
> Conciliando: o gap *total* cresce no topo (porque lá faltam dotações — negros são excluídos
> das posições rentáveis), enquanto a discriminação *de preço* pesa mais na base. Dois
> mecanismos distintos, capturados pela mesma decomposição."

**Números-chave:** *QR M3: q10 −8,0% → q95 −12,3% (teto de vidro) | RIF retornos: q10 35,1% → q90 12,9% (sticky floor)*

→ *Slide 9*

---

## SLIDE 9 — GLMM LOGÍSTICO: O TETO DE VIDRO NO ACESSO (2 min)

> "O GLMM logístico de dois níveis — indivíduos em UPAs — estima a probabilidade de **acesso**
> a cargo qualificado e ao topo da renda, com efeito aleatório de UPA.
>
> Para cargo qualificado, o odds ratio controlado é **0,705**: depois de igualar escolaridade,
> sexo, idade e contexto, um trabalhador negro tem cerca de **30% menos chance** de ocupar um
> cargo qualificado que um branco de mesmo perfil. O efeito marginal médio é de **−4,7 pontos
> percentuais**.
>
> O teto aperta no extremo: para o top 20% de renda, OR=**0,691**; para o top 10%, OR=**0,656**.
>
> A robustez vem do **E-value de 2,2**: um confundidor não-observado precisaria ter associação
> de pelo menos 2,2 vezes com raça *e* com o desfecho, simultaneamente, para anular o efeito.
> Nenhum confundidor plausível atinge esse limiar."

**Números-chave:** *ocp_qualif OR=0,705 (AME −4,7 p.p., E-value 2,2) | top20 OR=0,691 | top10 OR=0,656*

→ *Slide 10*

---

## SLIDE 10 — ROBUSTEZ: ML/SHAP (1,5 min)

> "Como validação livre de forma funcional, o XGBoost atingiu R²=**0,62**, contra 0,44 dos
> modelos lineares sem ocupação.
>
> No ranking SHAP, a variável **raça aparece na posição 11**, com contribuição direta de
> cerca de −3% na renda prevista, mesmo após o modelo já ter usado todas as demais variáveis.
> Esse é o resíduo de discriminação que o ML detecta sem nenhuma hipótese prévia.
>
> Uma ressalva metodológica importante: o contexto territorial (renda média da UPA) figura
> entre os preditores de maior peso, mas é um preditor **parcialmente endógeno** — agrega o
> próprio indivíduo (problema do reflexo, Manski 1993). Por isso o interpreto como evidência
> de **mediação territorial**, não como 'determinante causal' isolado."

**Número-chave:** *R²=0,62 | raça: rank 11, SHAP ≈ −3%*

→ *Slide 11*

---

## SLIDE 11 — INTERSECCIONALIDADE: RAÇA × GÊNERO (1,5 min)

> "A decomposição interseccional compara quatro grupos com o Homem Branco. A **Mulher Negra**
> tem o maior gap — **96,4%** — e, mais importante, uma **penalidade extra de 9,5 pontos
> percentuais** que *não* se reduz à soma de 'ser negro' e 'ser mulher' isoladamente.
>
> É a confirmação empírica de Crenshaw (1989): a discriminação interseccional é um mecanismo
> próprio da combinação raça-gênero, não a soma de dois eixos. Política que trata raça e gênero
> separadamente deixa esse resíduo intacto."

**Número-chave:** *Mulher Negra: gap 96,4% | penalidade interseccional extra +9,5 p.p.*

→ *Slide 12*

---

## SLIDE 12 — SÍNTESE (1 min)

> "A convergência dos quatro métodos conta uma história coerente:
>
> O gap salarial é **majoritariamente composição** (Oaxaca: 83,8%). Mas a composição **não é
> neutra**: o GLMM mostra que o acesso às boas ocupações é restringido por raça (OR 0,705), e a
> RIF mostra que, dentro das ocupações, ainda há discriminação de preço — maior na base.
>
> Em uma frase: o racismo no mercado de trabalho brasileiro opera sobretudo no **acesso**, e o
> resíduo salarial persiste mesmo após todos os controles. Não é um ato individual — é um
> sistema que produz desigualdade de forma autossustentada."

→ *Slide 13*

---

## SLIDE 13 — IMPLICAÇÕES DE POLÍTICA (1 min)

> "As implicações seguem do diagnóstico. Como o mecanismo dominante é o **acesso**, a prioridade
> são instrumentos que ampliem o ingresso de negros em ocupações qualificadas — cotas e
> programas de inclusão nos escalões superiores do setor privado, onde os mecanismos são menos
> estabelecidos que no setor público. Para o resíduo salarial e o sticky floor, transparência
> salarial e fiscalização de discriminação. Educação isolada é necessária mas insuficiente: o
> gargalo está no portão, não só no diploma."

→ *Slide 14*

---

## SLIDE 14 — LIMITAÇÕES E AGENDA FUTURA (1 min)

> "Três limites centrais. **Primeiro, causalidade**: os métodos são correlacionais — não há
> instrumento ou experimento natural. Os resultados são consistentes com discriminação, e os
> E-values mostram que seria preciso um confundidor implausível para invalidá-los, mas isso não
> substitui identificação causal formal. **Segundo, raça autodeclarada** tem reclassificação ao
> longo do tempo, o que atenua e portanto *subestima* o gap — meus resultados são conservadores.
> **Terceiro, CBO autodeclarada** está sujeita a erro de classificação.
>
> A agenda futura — já iniciada na versão estendida do trabalho — inclui análise de redes
> sociais do acesso, validação com a RAIS (dados administrativos), e o recorte do setor
> público."

→ *Slide 15*

---

## SLIDE 15 — CONCLUSÃO (1 min)

> "Em síntese: o mercado de trabalho brasileiro produz desigualdades raciais sistemáticas que
> não se explicam por capital humano ou localização.
>
> O gap é majoritariamente composição — mas a composição é produto de discriminação no acesso:
> negros têm 30% menos chance de chegar a cargos qualificados, com mesmo perfil. E um resíduo
> salarial de −6,2% persiste após todos os controles, pior na base da distribuição.
>
> Não é hipótese — é regularidade estatística robusta, confirmada por quatro métodos
> independentes, até 7,7 milhões de observações e dez anos de dados.
>
> Agradeço a atenção e fico à disposição."

---
---

# PERGUNTAS ESPERADAS DA BANCA

## Perguntas Metodológicas

### P1 — "Por que HLM e não OLS?"
> "Três argumentos. Primeiro: o ICC indica que parcela relevante da variância de rendimentos é
> atribuível ao nível geográfico, violando a independência do OLS. Segundo: o teste de razão de
> verossimilhança rejeita o modelo plano. Terceiro: o HLM produz erros-padrão válidos para a
> estrutura hierárquica e é mais parcimonioso que OLS com dezenas de dummies de UF. Referência:
> Raudenbush & Bryk (2002)."

### P2 — "O Oaxaca dá 83,8% de dotações. Então a discriminação é pequena (16%)?"
> "Não — e essa é a leitura mais importante do trabalho. Os 83,8% de dotações incluem a
> **ocupação**. Mas o acesso à ocupação é ele próprio discriminatório, como o GLMM mostra
> (OR 0,705 para cargo qualificado). Tratar a ocupação como dotação, pela ressalva de Oaxaca &
> Ransom (1999), **subestima** a discriminação total. O número de 16% é a discriminação salarial
> *dentro* da ocupação — o limite inferior. A discriminação maior opera no portão de entrada,
> que o Oaxaca não captura mas o GLMM sim. Os dois métodos são complementares por construção."

### P3 — "Por que tratar ocupação como dotação? Não há especificação alternativa?"
> "Há, e eu a reconheço. Se eu *excluir* a ocupação do Oaxaca — tratando a segregação
> ocupacional como parte da discriminação — a parcela não-explicada sobe muito. Optei pela
> especificação de acesso (ocupação como dotação) porque ela é coerente com a arquitetura do
> trabalho: o Oaxaca mede a discriminação salarial *condicional à ocupação*, e o GLMM mede
> separadamente a discriminação *de acesso* à ocupação. Separar os dois canais é mais informativo
> que somá-los numa única cifra. A versão estendida reporta também a especificação sem ocupação."

### P4 — "O Oaxaca é two-fold ou three-fold? E a identidade fecha?"
> "Two-fold, com referência nos coeficientes do grupo branco. A identidade fecha exatamente:
> dotação mais coeficiente igual ao gap total — inclusive o termo de intercepto está no
> componente não-explicado, como manda a decomposição. Os erros-padrão vêm de bootstrap
> agrupado por UF (200 replicações). Optei pelo two-fold porque o termo de interação do
> three-fold é sensível à escolha do grupo de referência."

### P5 — "Como interpretar teto de vidro e sticky floor juntos? Não se contradizem?"
> "Não — são mecanismos distintos. O gap *total* cresce no topo (teto de vidro): de −8% no q10
> a −12,3% no q95. Mas a decomposição RIF mostra que esse crescimento no topo é dominado por
> **dotações** — negros são excluídos das posições rentáveis. Já o componente de **retorno** (a
> discriminação de preço) é maior na base (35,1% no q10) e cai para 12,9% no q90: isso é sticky
> floor. Em política: o teto de vidro pede reforma de acesso e redes; o sticky floor pede
> enforcement antidiscriminação na base."

### P6 — "O GLMM é completo ou um logit com dummies?"
> "É um GLMM com efeito aleatório de UPA, que captura explicitamente a variância de vizinhança e
> produz OR com intervalos que incorporam a incerteza hierárquica. O resultado principal é
> OR=0,705 para acesso a cargo qualificado (IC estreito dado o N), com efeito marginal de −4,7
> pontos percentuais. A robustez é o E-value de 2,2 (VanderWeele & Ding, 2017)."

### P7 — "O R²=0,62 do XGBoost não garante que o resíduo de raça seja discriminação."
> "Correto, e reconheço. O que argumento: o XGBoost captura interações não-lineares que modelos
> paramétricos perdem; se houvesse variável latente correlacionada com raça e renda, ela se
> manifestaria via SHAP. O fato de a raça ter SHAP negativo *próprio* (rank 11, ~−3%), e não só
> como moderador, sugere efeito direto. Mas a prova definitiva exigiria experimento ou
> instrumento, que não existem em escala nacional para o Brasil."

### P8 — "Por que amostra/população? E sobreajuste no ML?"
> "As análises populacionais usam a PEA completa (até 7,7 milhões). Onde uso amostra (alguns
> modelos quantílicos), o ganho de precisão de usar 100% seria marginal. No ML, o gap entre R²
> de treino e teste é de 0,0006 — não há sobreajuste."

### P9 — "A penalidade interseccional de 9,5 p.p. é esperada ou surpreendente?"
> "É Crenshaw (1989) confirmado empiricamente. O gap da Mulher Negra vs. Homem Branco é 96,4%.
> Se raça e gênero fossem aditivos, esperaríamos a soma das penalidades isoladas; a diferença
> real — 9,5 pontos — é a penalidade interseccional pura, um mecanismo específico da combinação
> que intervenções de eixo único não capturam."

---

## Perguntas sobre Teoria

### P10 — "Qual a hipótese causal? Becker (1957) ou Arrow (1973)?"
> "As evidências são mais consistentes com **discriminação estatística** (Arrow) e com
> segregação ocupacional do que com o preconceito de gosto de Becker. No modelo de Becker,
> firmas preconceituosas perderiam lucro e seriam eliminadas pela competição — mas o gap
> persiste por dez anos. Na discriminação estatística, o empregador usa raça como proxy de
> produtividade não observável — o que explica o gap de *acesso* mesmo entre pessoas de
> qualificação observável equivalente. Não descarto a coexistência de mecanismos."

### P11 — "'Racismo estrutural' no título é sociológico ou operacional?"
> "Tem ancoragem dupla. Sociologicamente, sigo Almeida (2019): estrutural porque é reproduzido
> pelas estruturas econômicas e institucionais, não por atos individuais. Operacionalmente, é a
> parcela do gap — de acesso e de remuneração — que persiste após controlar todas as
> características observáveis. A convergência entre os quatro métodos torna a conclusão robusta."

---

## Perguntas de Defesa (mais difíceis)

### P12 — "Você reduziu o escopo. Não enfraqueceu o trabalho?"
> "Pelo contrário. Concentrar em quatro métodos que respondem perguntas distintas e
> não-redundantes deixa a inferência mais defensável e a narrativa mais clara. Cada método extra
> abriria um flanco metodológico sem agregar uma pergunta nova. As análises adicionais —
> redes, agrupamento, setor público, pesquisa operacional — permanecem como agenda futura
> documentada, mas não pertencem ao argumento central."

### P13 — "Os resultados valem para o período de pandemia?"
> "Uso o período completo 2016–2025 como painel anual, sem recorte de pandemia no corpo do TCC.
> A literatura indica que a pandemia aprofundou desigualdades raciais, o que tenderia a tornar
> minhas estimativas conservadoras. Uma análise de quebra estrutural é extensão natural, já
> esboçada na versão estendida."

---

## Dicas Finais

1. **Antes de responder**: parafraseie a pergunta — ganha 5 segundos e confirma o entendimento.
2. **Se não souber**: "Não explorei essa dimensão neste trabalho, mas é uma extensão natural que
   eu faria assim..." É melhor que especular.
3. **Números de cabeça** (dez essenciais): (a) 7,7 mi obs / 10 anos; (b) gap bruto ~53%;
   (c) HLM M1 −19,1% → M4 −6,2% (mediação total 69,8%); (d) Oaxaca dotações 83,8% / discrim. 16,2%;
   (e) ressalva Oaxaca & Ransom: ocupação como dotação subestima discriminação;
   (f) QR teto de vidro q10 −8,0% → q95 −12,3%; (g) RIF sticky floor retornos 35,1% → 12,9%;
   (h) GLMM ocp_qualif OR=0,705, AME −4,7 p.p., E-value 2,2; top10 OR=0,656;
   (i) XGBoost R²=0,62, raça rank 11; (j) penalidade interseccional Mulher Negra +9,5 p.p.
4. **Confiança**: HLM de 3 níveis, Oaxaca-Blinder com bootstrap, quantílica/RIF e GLMM com efeito
   aleatório são um conjunto sólido. Não minimize.
5. **Se discordarem de uma escolha**: "Concordo que há trade-offs. Optei por X porque Y. Uma
   alternativa seria Z, que exploro na versão estendida." Reconheça, explique, proponha extensão.

---

*Atualizado em 2026-06-15 | Núcleo de 4: HLM, Oaxaca-Blinder, Regressão Quantílica/RIF, GLMM
logístico | Robustez: ML/SHAP, E-values, Interseccionalidade | PNAD Contínua 2016–2025.
Análises estendidas (SNA, agrupamento, setor público, pesquisa operacional) = agenda futura.*
