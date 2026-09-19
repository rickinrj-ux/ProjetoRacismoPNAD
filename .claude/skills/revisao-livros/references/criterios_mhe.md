# Critérios destilados — Mostly Harmless Econometrics (Angrist & Pischke, 2009)

Leitura integral (caps. 1–8 + apêndices). Formulação própria; cada item vira um check (ID) na skill.
Marcação [TCC] = ponto onde o projeto PNAD está diretamente exposto.

## Cap. 1 — As 4 perguntas de pesquisa (FAQs)
- MHE-01 A relação causal de interesse está enunciada com precisão (o que é o "tratamento", o que é o desfecho, em que população)? [TCC: "raça" não é manipulável → a pergunta identificável é *discriminação* (tratamento diferente por raça percebida), como em audit studies. O texto deve distinguir "efeito da raça" (FUQ) de "penalidade racial condicional a X" (descritivo/associacional).]
- MHE-02 O experimento ideal foi descrito (mesmo que hipotético)? Se nenhum experimento responderia a pergunta, ela é FUQ (fundamentalmente não identificada) — não vender como causal.
- MHE-03 A estratégia de identificação está explícita (como os dados observacionais aproximam um experimento)? Se é seleção em observáveis, dizer isso com todas as letras.
- MHE-04 O modo de inferência está declarado: população, amostra, desenho amostral, como os erros-padrão foram construídos (cluster? pesos?). Haiku: "T-stat looks too good / try clustered standard errors / significance gone".

## Cap. 2 — Ideal experimental e viés de seleção
- MHE-10 Toda comparação bruta = efeito + viés de seleção. O texto identifica o sinal provável do viés de seleção em cada comparação (ex.: quem entra em ocupação qualificada é positivamente selecionado).
- MHE-11 Balanceamento: tabela de covariáveis por grupo (negros × brancos) com testes, para mostrar onde a comparação é "maçã com laranja" antes de controlar.
- MHE-12 Atrição/seleção amostral: quem sai da amostra (desocupados, sem renda, PNAD com não-resposta) e se isso difere por grupo.
- MHE-13 Controles em experimento só aumentam precisão; em observacional, mudam o estimando. Mostrar a sequência curta→longa (M0…M4) e explicar CADA mudança do coeficiente racial via fórmula de OVB.

## Cap. 3 — Regressão: CEF, causalidade, OVB, bad control, matching, pesos, LDV
- MHE-20 Regressão = melhor aproximação linear da CEF, independentemente de linearidade; o coeficiente é uma média ponderada pela variância condicional do regressor. Interpretar como tal, não como "efeito estrutural".
- MHE-21 Modelos saturados: com regressores discretos, saturar (dummies + interações) ajusta a CEF exatamente. Nunca incluir interação sem os efeitos principais.
- MHE-22 **Erros-padrão robustos (White/HC)** como padrão; se robusto ≠ convencional em mais de ~30% (ou robusto < convencional), suspeitar de bug ou viés finito. Regra: reportar max(convencional, HC2/HC3).
- MHE-23 CIA (seleção em observáveis) como hipótese-chave e explicitada: "condicional a X, raça é como se fosse aleatória" — dizer que isso NÃO vale para raça (X não esgota o processo) e interpretar o resíduo como "não explicado", não "discriminação medida".
- MHE-24 **Fórmula do OVB**: curto = longo + (efeito do omitido)×(regressão do omitido no incluído). Usar para discutir a direção do viés do coeficiente racial ao omitir habilidade/qualidade escolar/redes (viés provável: superestimar a penalidade se omitidos correlacionam negativamente com ser negro e positivamente com renda… ou o contrário se educ de qualidade pior — discutir).
- MHE-25 **Bad control** [TCC — crítico]: controles que são eles próprios desfechos do tratamento (ocupação/CBO, formalidade, setor, horas, escolaridade completada depois da exposição à discriminação) não têm interpretação causal; o coeficiente racial "líquido de ocupação" mistura efeito e viés de seleção (composição do pool muda). O texto deve (a) apresentar versões com e sem bad controls, (b) tratar a versão com ocupação como *limite inferior descritivo* e a sem ocupação como gap total, (c) reconhecer que a parte "explicada" do Oaxaca por ocupação pode ser discriminação canalizada.
- MHE-26 **Proxy control**: controle medido depois do tratamento (ex.: "habilidade tardia") atenua o coeficiente; usar como limite e testar se o proxy responde ao regressor de interesse.
- MHE-27 Timing: bons controles são determinados ANTES do regressor de interesse (idade, sexo, região de nascimento, escolaridade dos pais); classificar cada controle do M4 por timing.
- MHE-28 Regressão ≈ matching com pesos diferentes (variância do tratamento vs. distribuição entre tratados); ambos impõem **suporte comum**. Verificar overlap: há células (UF×educação×ocupação) sem negros ou sem brancos? Reportar ATE vs. TOT quando relevante.
- MHE-29 Propensity score: opcional; regressão flexível costuma bastar. Se usar PSM/IPW, mostrar overlap (0,1<p<0,9) e não vender como mais causal que a regressão.
- MHE-30 **Pesos amostrais** [TCC]: usar peso da PNAD quando o alvo é a regressão populacional (pweights); NÃO ponderar só por heterocedasticidade; dados agrupados → ponderar por tamanho do grupo. Declarar o que foi feito em CADA modelo (HLM ponderado? QR ponderada?).
- MHE-31 **LDV / efeitos marginais** [TCC]: coeficientes probit/logit não são efeitos; reportar efeitos marginais médios (diferença de probabilidade) ao lado dos OR. LPM costuma dar o mesmo resultado que os efeitos marginais — usar como checagem. Tobit raramente justificado (censura real vs. zeros verdadeiros).
- MHE-32 **COP / condicionar em positivo** [TCC]: log-renda só para quem tem renda>0 é condicionar num desfecho — viés tipo bad control se raça afeta participação/emprego. Decompor: efeito na participação × efeito condicional; reportar ambos; Heckman é uma resposta, mas com pressupostos fortes (aqui: exclusão precisa ser crível).
- MHE-33 Efeitos distribucionais: em vez de COP, olhar 1[y>c] para vários c, ou quantis (cap. 7).
- MHE-34 Regressão para a média (Galton) e correlação intergeracional: interpretação cuidadosa em mobilidade.

## Cap. 4 — IV (o TCC não usa IV; critérios de leitura aplicáveis)
- MHE-40 Se algum dia usar IV: primeiro estágio reportado + F>10; forma reduzida visível; exclusão argumentada separadamente de independência; LATE = efeito nos compliers (validade externa discutida); mesmas covariáveis nos dois estágios; nunca "forbidden regression" (plugar fitted de probit); checar sobreidentificação com cautela; LIML em sobreidentificados.
- MHE-41 Checagens de placebo: instrumento/tratamento não deve "afetar" variáveis pré-determinadas nem desfechos anteriores.
- MHE-42 **Peer effects / reflexão** [TCC — crítico]: regredir y_ij em ȳ_j (média do grupo da própria variável) é mecanicamente ≈1 e não informativo; choques comuns ao grupo criam "efeito de pares" espúrio. `media_renda_upa` como preditor da renda individual é exatamente isso. Aceitável apenas: (a) média *excluindo i* (leave-one-out) E reconhecendo choques comuns, ou (b) características ex ante dos pares (predeterminadas). No HLM, a variância entre UPA é legítima como *decomposição*; o que não é legítimo é chamar a média de renda da UPA de "determinante".
- MHE-43 Viés de 2SLS com muitos instrumentos fracos → analogia: muitos regressores/efeitos aleatórios fracos também inflam ajuste; cuidado com overfitting em modelos com centenas de dummies.

## Cap. 5 — Efeitos fixos, DD, painel
- MHE-50 DD exige **tendências paralelas**; mostrar gráfico pré-tratamento com várias observações antes. [TCC Tier 3: event study COVID e teste de Chow — exibir a série 2016–2019 como placebo de tendência.]
- MHE-51 Leads e lags (Granger): efeitos "antecipatórios" devem ser zero; padrão temporal dos lags é informativo.
- MHE-52 Tendências específicas por grupo/UF como robustez; se o efeito some, era tendência.
- MHE-53 Composição do grupo muda com o tratamento (migração/entrada na PEA) → cuidado.
- MHE-54 Efeitos fixos removem viés fixo mas amplificam erro de medida (atenuação); não fazer afirmações fortes.
- MHE-55 Efeitos fixos vs. variável dependente defasada: não aninhados; usar ambos como *bracketing* do efeito.
- MHE-56 Efeitos aleatórios (RE) assumem não-correlação com regressores; preferir "corrigir os EP" a GLS quando a hipótese é duvidosa. [TCC: HLM = RE; o texto deve discutir por que RE de UPA/UF é aceitável (ou testar contra FE — Hausman — como robustez).]

## Cap. 6 — RD (não usado)
- MHE-60 Se houver cortes de regra (ex.: idade, salário mínimo), RD é opção; checar continuidade de covariáveis e densidade (McCrary); polinômio flexível + janela estreita.

## Cap. 7 — Regressão quantílica [TCC núcleo]
- MHE-70 QR aproxima a função quantílica condicional (CQF) como OLS aproxima a CEF; útil mesmo se CQF não é linear.
- MHE-71 Coeficientes constantes entre quantis = *location shift* (homocedasticidade); coeficientes crescentes no topo = dispersão aumenta com o regressor (heterocedasticidade/"fanning out"). Interpretar o teto de vidro nesses termos.
- MHE-72 **Efeitos sobre distribuições, não sobre indivíduos**: "a penalidade no q90 é maior" ≠ "os negros do topo sofrem mais", salvo rank-invariance. O texto deve usar a linguagem correta.
- MHE-73 Quantis condicionais ≠ quantis marginais; ir de um ao outro exige Machado-Mata / RIF (Firpo, Fortin, Lemieux). O RIF-OB do TCC é a ferramenta certa — explicitar que RIF responde sobre o quantil *incondicional*.
- MHE-74 Censura (top-coding) afeta só quantis acima do ponto de censura; verificar se a PNAD tem top-code e em que quantil.
- MHE-75 EP da QR dependem da densidade do resíduo em zero → bootstrap é o padrão prático; com cluster, bootstrap em blocos (UPA).
- MHE-76 QR "controla" via covariáveis do mesmo modo que OLS: mesmo problema de bad control/CIA.

## Cap. 8 — Erros-padrão não padrão [TCC — crítico]
- MHE-80 EP robustos podem ser mais viesados que os convencionais com pouca heterocedasticidade; usar HC2/HC3 e a regra do máximo; robusto < convencional = bandeira vermelha.
- MHE-81 **Cluster/Moulton**: observações na mesma UPA/domicílio/UF são correlacionadas; regressor que varia no nível do grupo (ex.: `media_renda_upa`, dummies de UF) tem EP subestimado por fator √(1+(n−1)ρ). Toda regressão não-multinível (OLS, OB, QR, RIF, logit simples, XGBoost-SHAP não se aplica) deve ter EP clusterizados no nível amostral (UPA) ou bootstrap em blocos. O desenho amostral da PNAD (estratos, UPA, pesos) é exatamente um caso de Moulton/"design effect" (Kish).
- MHE-82 Poucos clusters (<42) → EP clusterizados não confiáveis; usar t com g−k g.l., BRL, ou agregação por grupo. [TCC: 27 UFs < 42 → qualquer inferência clusterizada por UF precisa dessa correção; UPAs são milhares, ok.]
- MHE-83 Correlação serial em painéis/DD: clusterizar um nível acima (UF) e reconhecer o problema de poucos clusters.
- MHE-84 Bootstrap: pares, resíduos, wild, blocos; usar blocos para dados agrupados.
- MHE-85 Efeito de tamanho de amostra: com N na casa dos milhões, tudo é "significativo"; enfatizar magnitude, IC e relevância econômica, não p-valores.

## Últimas palavras
- MHE-90 "Seja seu melhor cético": a seção de limitações deve listar, item a item, as hipóteses (CIA, bad controls, reflexo, RE, pesos, cluster) e o que acontece se falharem. Sem pânico, sem overclaim.
