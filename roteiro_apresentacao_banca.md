# Roteiro de Apresentação — Banca de Defesa TCC
## Racismo Estrutural e Mercado de Trabalho no Brasil
**Ricardo Calheiros | MBA Data Science & Analytics | USP/ESALQ | 2026**

---

> **Leia este roteiro em voz alta pelo menos duas vezes antes da defesa.**
> O objetivo não é memorizar palavra por palavra, mas internalizar os números e as conexões lógicas entre os slides.
> Tempo total de apresentação: **20 minutos**. Perguntas: em geral 15–25 min adicionais.

---

## ORIENTAÇÕES GERAIS

- **Tom**: objetivo e técnico. Você está apresentando evidências, não fazendo militância. Deixe os números falarem.
- **Postura**: ao citar um número, olhe para a plateia — não para o slide. Você conhece o dado.
- **Transições**: as frases de transição entre slides estão marcadas com → . Use-as literalmente até se sentir confortável.
- **Se travar**: respire, olhe para o slide e leia o número principal. Isso reorienta qualquer raciocínio.
- **Nunca diga "como eu disse antes"**: a banca não quer saber o que você disse — quer saber o que os dados dizem.

---

## SLIDE 1 — CAPA (1 min)

**Fala de abertura:**

> "Bom dia/boa tarde. Meu trabalho investiga o racismo estrutural no mercado de trabalho brasileiro usando a PNAD Contínua de 2016 a 2025 — dez anos de dados, quase 1,5 milhão de observações por rodada.
>
> A pergunta central é: depois de controlar escolaridade, experiência, horas trabalhadas e localização geográfica, existe ainda uma penalidade salarial associada à raça? E se sim — ela é igual ao longo de toda a distribuição de renda, ou se concentra no topo?
>
> Vou apresentar cinco metodologias que respondem a essa pergunta de ângulos complementares."

→ *Vire para o slide 2*

---

## SLIDE 2 — O PROBLEMA (1,5 min)

**Fala:**

> "O Brasil tem um gap salarial racial de aproximadamente 37% na renda mediana. Parte disso é composição — negros têm, em média, menos escolaridade e ocupações menos qualificadas, reflexo de desigualdades históricas acumuladas. Mas parte é discriminação pura — uma penalidade que persiste mesmo comparando pessoas com o mesmo perfil.
>
> Distinguir as duas fontes é o que este trabalho faz. E para isso uso cinco métodos que se complementam: HLM para decompor o gap em níveis geográficos, ML com SHAP para identificar quais variáveis mais explicam a renda, Oaxaca-Blinder para separar dotações de retornos, logit multinível para analisar o gap de acesso a empregos qualificados, e regressão quantílica para testar se há um teto de vidro no topo da distribuição.
>
> A inovação principal está na triangulação: nenhum método sozinho é suficiente. A convergência entre eles é o que sustenta as conclusões."

→ *Vire para o slide 3*

---

## SLIDE 3 — BASE DE DADOS (1 min)

**Fala:**

> "A fonte é a PNAD Contínua — pesquisa domiciliar do IBGE com cerca de 350 mil domicílios por trimestre. Eu uso 10 anos de dados anuais agregados: 2016 a 2025, totalizando 7,7 milhões de observações com renda positiva.
>
> O dataset tem três camadas hierárquicas naturais: indivíduos aninhados em unidades primárias de amostragem — as UPAs —, que estão dentro de estados. Isso justifica metodologicamente o uso de modelos multinível, porque ignorar essa estrutura inflaria os erros padrão e nos daria intervalos de confiança espúrios."

→ *Vire para o slide 4*

---

## SLIDE 4 — ARQUITETURA METODOLÓGICA (1,5 min)

**Fala:**

> "As metodologias formam uma arquitetura convergente em três camadas. Cada uma responde uma pergunta diferente:
>
> Na camada de *inferência causal*: o HLM pergunta *quanto* do gap é gerado em cada nível geográfico; o GLMM logístico pergunta se negros têm acesso menor a cargos qualificados — e produz um OR de 0,741, que será explicado a seguir.
>
> Na camada de *mecanismos*: o Oaxaca-Blinder separa dotações de retornos; o RIF-OB faz essa separação por quantil — revelando que a discriminação de mercado é maior na base (sticky floor), não no topo; e o OB 4 grupos formaliza a interseccionalidade raça-gênero com uma penalidade extra de 9,5 pontos percentuais para mulheres negras.
>
> Na camada de *robustez*: o ML/SHAP valida sem pressuposto de forma funcional; a SNA mapeia redes; e os testes de sensibilidade — Konfound para HLM, E-values para GLMM — mostram que 96 a 99% do efeito precisaria ser confundido por variáveis não observadas para invalidar a inferência.
>
> A resposta convergente de todos esses métodos é: existe uma penalidade racial sistemática que resiste a qualquer controle razoável."

→ *Vire para o slide 5*

---

## SLIDE 5 — HLM: DECOMPOSIÇÃO DO GAP (2 min)

**Fala:**

> "O modelo HLM tem quatro estágios. M1 é o modelo nulo — apenas a variável raça, sem controle nenhum. Ele mostra um gap de 5,39% na escala log — que equivale a aproximadamente 37% na renda real.
>
> À medida que adicionamos controles de capital humano no M2 — educação, idade, sexo —, o gap cai. No M3, adicionamos contexto geográfico: percentual de negros na UPA, acesso a metrópoles. O gap cai mais.
>
> O M4 é o ponto chave: adicionamos as variáveis ocupacionais — horas trabalhadas, formalidade, setor, grupo CBO. O gap cai para −0,0554 em log — mas ainda é altamente significativo. Isso representa 74,4% de mediação total, mas 25,6% do gap original permanece inexplicado depois de todos os controles.
>
> O componente ocupacional sozinho — a diferença entre M3 e M4 — explica 20,5% do gap. Isso significa que negros estão concentrados em ocupações piores não por acaso, mas por restrição sistemática de acesso. Essa é a face estrutural do racismo: não precisa de intenção discriminatória para produzir resultado discriminatório."

**Número-chave para memorizar:** *Gap M1 = −5,39% | Mediação total = 74,4% | Gap residual M4 = −0,0554 | Mediação ocupacional = 20,5%*

→ *Vire para o slide 6*

---

## SLIDE 6 — COMPOSIÇÃO OCUPACIONAL (1,5 min)

**Fala:**

> "Se olharmos a estrutura ocupacional por raça, o padrão é muito claro. No topo — dirigentes e profissionais —, a razão negro/branco é de 0,42 e 0,45: ou seja, negros têm menos da metade da representação proporcional que teriam se a distribuição fosse equânime.
>
> No fundo — trabalhos elementares —, a razão sobe para 2,1: negros têm o dobro da representação esperada.
>
> E no topo da distribuição de renda, o Índice de Representação é ainda mais extremo. No top 5% das rendas nas capitais, apenas 28,5% dos ocupantes são negros — numa população onde negros são 60% da força de trabalho local. O IR é 0,47 — metade do que seria equânime.
>
> Isso não é mérito diferencial. É exclusão sistemática do topo."

→ *Vire para o slide 7*

---

## SLIDE 7 — OAXACA-BLINDER (1,5 min)

**Fala:**

> "O Oaxaca-Blinder decompõe o gap em duas partes. A pergunta é: se um negro tivesse exatamente as mesmas características observáveis de um branco — mesma educação, mesma experiência, mesmo setor —, quanto do gap fecharia?
>
> A resposta: 84% do gap de 42 pontos percentuais se deve a dotações — os negros têm, em média, menos capital humano e estão em ocupações piores. Os outros 16% se devem a retornos — os brancos são remunerados mais pelos mesmos atributos.
>
> Isso parece dizer que a discriminação é pequena. Mas atenção: o mecanismo principal não é 'pagar menos pelo mesmo trabalho' — é restringir o acesso ao trabalho qualificado. O preconceito age no portão de entrada, não no cheque de pagamento. É por isso que o logit multinível é essencial para completar o diagnóstico."

**Número-chave:** *Gap total = 42,3% | Dotações = 84% | Retornos = 16%*

→ *Vire para o slide 8*

---

## SLIDE 8 — GLMM LOGÍSTICO MULTINÍVEL: TETO DE VIDRO OCUPACIONAL (2 min)

**Fala:**

> "O GLMM logístico de dois níveis — indivíduos aninhados em UPAs — estima a probabilidade de acesso a cargo qualificado, ao top 20% e ao top 10% da renda. Diferente de um logit com efeitos fixos de UF, o GLMM captura explicitamente a variância entre UPAs e produz estimativas de efeito aleatório que validam a estrutura hierárquica dos dados.
>
> Os resultados são consistentes e robustos. Para ocupação qualificada — o desfecho principal — o odds ratio controlado é de 0,741. Isso significa que, depois de igualar escolaridade, sexo, idade e contexto geográfico, um trabalhador negro tem 26% menor chance de ocupar um cargo qualificado em relação a um branco com o mesmo perfil. O efeito médio marginal é de menos 1,12 ponto percentual.
>
> Para top 20% de renda, OR=0,743 — igualmente robusto. Para top 10%, OR=0,698 — o teto se aperta ainda mais no extremo superior.
>
> Para formalidade — surpreendentemente — OR=1,06 depois dos controles. Isso é o Paradoxo de Simpson: no bruto, negros têm menos formalidade por concentração em estratos sem mercado formal. Dentro do mesmo estrato, negros buscam vínculo CLT mais ativamente — estratégia protetiva contra discriminação no mercado informal.
>
> A robustez desse achado é validada pelo E-value: E=2,04 para o desfecho principal. Um confundidor precisaria ter associação de pelo menos 2 vezes com raça E com a probabilidade de acesso a cargo qualificado para eliminar completamente o OR observado. Nenhum confundidor plausível atinge esse limiar."

**Números-chave:** *ocp_qualif M2: OR=0,741 (IC: 0,729–0,752), AME=−1,12 pp, E-value=2,04 | top20: OR=0,743 | top10: OR=0,698 | formalidade: OR=1,06 (paradoxo Simpson)*

→ *Vire para o slide 9*

---

## SLIDE 9 — REGRESSÃO QUANTÍLICA (1,5 min)

**Fala:**

> "A regressão quantílica estima o gap em cada ponto da distribuição de renda — não só na média. Se o gap é maior no topo do que no fundo, confirmamos o teto de vidro.
>
> No modelo M3 — sem variáveis ocupacionais —, o gap vai de −8,2% no percentil 10 até −12,3% no percentil 95. O coeficiente piora monotonicamente ao longo da distribuição. Isso confirma o teto de vidro.
>
> Quando adicionamos as variáveis ocupacionais no M4, o gap cai substancialmente — de −3,2% no q10 a −7,9% no q95 —, mas a trajetória crescente se mantém. O gap residual — o que sobra depois de controlar ocupação — ainda aumenta conforme se sobe na renda.
>
> Isso significa que mesmo negros que conseguem chegar a ocupações equivalentes às dos brancos ainda enfrentam uma penalidade maior nos escalões superiores. O teto de vidro não é só de acesso — é também de remuneração."

**Números-chave:** *M3 q10=−8,2% → q95=−12,3% (Δ=−4,5 p.p.) | M4 q10=−3,2% → q95=−7,9% | Trajetória crescente em ambos os modelos confirmada*

→ *Vire para o slide 10*

---

## SLIDE 10 — ML/SHAP (1,5 min)

**Fala:**

> "O XGBoost atingiu R² de 0,62 — comparado a 0,44 nos modelos anteriores sem variáveis ocupacionais. Isso valida a importância das variáveis de horas trabalhadas, grupo CBO e formalidade.
>
> No ranking SHAP — que mede a contribuição marginal real de cada variável para a previsão individual —, os três principais preditores são: horas trabalhadas com SHAP de 0,166, CBO profissional com 0,119, e emprego formal com 0,109.
>
> A variável 'negro' aparece na posição 11, com SHAP de −0,025 — ou seja, ser negro reduz a renda prevista em 2,5% de forma direta, depois de descontar tudo o que o modelo já controlou. Isso é o resíduo de discriminação pura que o ML detecta sem nenhuma hipótese prévia sobre forma funcional."

**Número-chave:** *R²=0,62 | negro: rank 11, SHAP=−2,5%*

→ *Vire para o slide 11*

---

## SLIDE 11 — ANÁLISE DE REDES (SNA) (1 min)

**Fala:**

> "A análise de redes mapeia a estrutura de conexões ocupacionais e demográficas. O índice de restrição de Burt — que mede o quanto um nó fica preso em um único cluster sem pontes para outros grupos — é significativamente maior para negros de baixa renda nas regiões de interior.
>
> Isso sugere que a segregação ocupacional tem uma dimensão de capital social: negros com menos escolaridade estão em redes mais fechadas, com menor acesso a informação sobre oportunidades em outros estratos. Não é apenas segregação de renda — é segregação de conectividade."

→ *Vire para o slide 12*

---

## SLIDE 12 — SÍNTESE: TRIÂNGULO DO RACISMO ESTRUTURAL (1 min)

**Fala:**

> "A síntese do trabalho pode ser representada em três vértices. No vértice ACESSO, o logit multinível mostra que negros têm probabilidade significativamente menor de alcançar empregos qualificados e o topo da renda. No vértice REMUNERAÇÃO, o HLM e a regressão quantílica mostram que há penalidade salarial residual — que cresce no topo. No vértice REDES, a SNA mostra que a segregação ocupacional se auto-reforça via redes de capital social.
>
> Os três mecanismos operam simultaneamente e se retroalimentam. Isso é o que caracteriza o racismo estrutural: não é um ato individual de discriminação — é um sistema que produz desigualdade de forma autossustentada."

→ *Vire para o slide 13*

---

## SLIDE 13 — IMPLICAÇÕES DE POLÍTICA (1 min)

**Fala:**

> "As implicações de política pública derivam diretamente dos três vértices. Para o gap de acesso, a prioridade são cotas e programas de inclusão nos escalões superiores do setor privado — o setor público já tem mecanismos mais estabelecidos. Para o gap de remuneração, é necessário maior transparência salarial e fiscalização de discriminação em promoções. Para o gap de redes, programas de mentoria e acesso a redes profissionais qualificadas podem romper a segregação de conectividade."

→ *Vire para o slide 14*

---

## SLIDE 14 — LIMITAÇÕES E AGENDA FUTURA (1 min)

**Fala:**

> "Toda análise tem limites que precisam ser reconhecidos explicitamente. Três são centrais aqui. Primeiro, causalidade: os métodos são correlacionais — não há variável instrumental ou experimento natural que identifique causalidade formal. Os resultados são consistentes com discriminação, mas outros mecanismos não podem ser totalmente descartados. Os testes de Konfound e E-values quantificam o limiar de confundimento — pkonfound acima de 96% — mas não substituem identificação causal formal.
>
> Segundo, raça autodeclarada na PNAD tem reclassificação ao longo do tempo: em torno de 6 a 8% dos indivíduos trocam de categoria racial entre rodadas. Isso gera atenuação clássica (attenuation bias) que, por definição, subestima o gap — ou seja, meus resultados são conservadores.
>
> Terceiro, CBO autodeclarado é sujeito a erros de classificação. A agenda futura inclui validação cruzada com a RAIS — dados administrativos sem autorrelato — para verificar se o gap de acesso ao emprego qualificado persiste em dados de registro."

→ *Vire para o slide 15*

---

## SLIDE 15 — CONCLUSÃO (1 min)

**Fala de encerramento:**

> "Em síntese: os dados mostram com clareza que o mercado de trabalho brasileiro produz desigualdades raciais sistemáticas que não se explicam por diferenças de capital humano ou de localização.
>
> Mesmo depois de controlar escolaridade, experiência, horas trabalhadas, setor e grupo ocupacional, um gap residual persiste: 74,4% de mediação, mas 25,6% que resiste a todas as explicações observáveis. E esse gap é pior no topo — 12,3% no percentil 95 contra 8,2% no percentil 10.
>
> O racismo estrutural no mercado de trabalho brasileiro não é uma hipótese — é uma regularidade estatística robusta, confirmada por cinco métodos independentes, 7,7 milhões de observações e dez anos de dados.
>
> Agradeço a atenção e fico à disposição para as perguntas."

---

---

# PERGUNTAS ESPERADAS DA BANCA

## Perguntas Metodológicas

### P1 — "Você implementou um GLMM completo? Quais as diferenças em relação ao logit com efeitos fixos?"
> "Sim — o trabalho implementa um GLMM logístico de dois níveis com efeitos aleatórios de UPA, estimado por máxima verossimilhança restrita. O modelo é substancialmente diferente do logit com dummies de UF: ele captura explicitamente a variância entre UPAs no intercepto aleatório, decompõe a variância total entre nível individual e nível de vizinhança, e produz OR com intervalos de confiança que já incorporam a incerteza hierárquica. O resultado principal é OR=0,741 para acesso a cargo qualificado, com IC 95% de 0,729 a 0,752 — estreito o suficiente para descartar efeito nulo mesmo com N de 2,36 milhões. A validação de robustez é feita com E-value de VanderWeele & Ding (2017): E=2,04, significando que nenhum confundidor razoável elimina esse efeito."

### P2 — "O que garante que o gap residual é discriminação e não uma variável omitida?"
> "Tecnicamente, nada garante isso — é a principal limitação do trabalho, e eu a reconheço explicitamente. O que posso dizer é: vários métodos com arquiteturas distintas convergem para o mesmo resíduo. E esse resíduo é quantitativamente robusto a confundidores. O Konfound para o HLM M4 mostra pkonfound de 96,3%: seria necessário que 96,3% do efeito estimado fosse gerado por variáveis não observadas para invalidar a inferência — e o HLM já captura a estrutura hierárquica geográfica que outros modelos ignoram. Para o GLMM, o E-value de 2,04 significa que um confundidor teria de ter associação pelo menos duas vezes maior com raça E com o desfecho simultaneamente. Se houvesse um único confundidor desse nível de magnitude, ele já seria bem conhecido na literatura. O ML/SHAP, que opera sem pressuposto de forma funcional, detecta SHAP=−2,5% para raça independentemente. A convergência entre todos esses métodos torna a hipótese de confundimento total muito improvável — embora eu reconheça que identificação causal formal, com variável instrumental, seria o passo seguinte."

### P3 — "Como interpretar o Paradoxo de Simpson no logit de formalidade?"
> "O raw gap mostra que negros têm 5,4 pontos percentuais a menos de formalidade que brancos. Mas isso é composição: negros estão concentrados em estratos de baixa escolaridade e em regiões com mercados de trabalho menos formalizados — como o interior —, onde *todo mundo* tem menos acesso ao emprego formal. Quando comparamos negros e brancos dentro do mesmo estrato socioeconômico e da mesma região, a relação se inverte: negros buscam emprego formal *mais* ativamente — OR=1,06. Isso é interpretado como estratégia protetiva: diante da discriminação no mercado informal, o vínculo CLT oferece proteção contratual adicional. Não é um artefato estatístico — é um comportamento adaptativo documentado na literatura de segregação laboral."

### P4 — "Por que usar 20% de amostra e não 100%?"
> "A amostra de 20% tem 1,538 milhão de observações — suficiente para detectar efeitos da ordem de 0,001 em log com intervalos de confiança estreitos. O ganho de usar 100% seria marginal em termos de precisão, mas o custo em tempo de estimação dos modelos quantílicos — que exigem 6 rodadas de otimização — multiplicaria por 5 o tempo de processamento. Em termos de viés de estimação, a amostra aleatória de 20% é não-viesada por construção. O trade-off foi explicitamente avaliado e justificado."

### P5 — "A regressão quantílica pressupõe independência dos erros. Como isso se sustenta com dados clustered?"
> "Boa pergunta. Os erros padrão reportados usam bootstrap por pares, que é consistente na presença de clustering. O pptx implementa `smf.quantreg` do statsmodels com bootstrap por pares de 200 replicações por quantil — isso fornece CI válidos mesmo sem independência estrita dos erros. A consistência da estimativa do coeficiente em si não depende de independência — apenas os erros padrão, e esses são corrigidos via bootstrap."

### P6 — "Qual o tamanho do efeito? É economicamente relevante?"
> "−12,3% no percentil 95 em escala log equivale a uma penalidade de aproximadamente 11,5% na renda real — para trabalhadores que já ganham o equivalente a 8 a 10 salários mínimos. Em valores absolutos, isso representa entre R$ 600 e R$ 1.000 mensais no topo da distribuição. Economicamente relevante? Sim: acumulado ao longo de uma carreira de 30 anos, o diferencial de patrimônio resultante é da ordem de R$ 250 a 400 mil — o que explica muito da diferença de riqueza intergeracional entre famílias negras e brancas."

### P7 — "O índice de representação (IR) pode ser influenciado por diferenças regionais?"
> "Sim, e por isso apresento o IR separado por área: Capital, RM e Interior. O padrão se mantém nas três — IR entre 0,47 e 0,62 no top 5%. A variação regional existe: nas RM exceto capital, o IR é ligeiramente mais alto do que nas capitais. Mas a sub-representação de negros no topo é sistemática em todos os contextos geográficos analisados."

### P8 — "Os resultados são generalizáveis para outros países?"
> "A análise usa dados brasileiros e a interpretação é específica ao Brasil — o racismo à brasileira tem características próprias: ambiguidade racial, mito da democracia racial, ausência de segregação jurídica formal mas presença de segregação socioeconômica intensa. Os métodos são, evidentemente, generalizáveis. Os resultados quantitativos são específicos ao contexto brasileiro. Comparações com EUA — que têm discriminação com maior componente de retornos e menor componente de dotações — seriam metodologicamente ricas, mas demandariam um design comparativo que está além do escopo deste trabalho."

### P8b — "A decomposição RIF-OB mostra sticky floor, não glass ceiling discriminatório. Isso contradiz as hipóteses do trabalho?"
> "Não contradiz — enriquece. O glass ceiling no *gap bruto* é confirmado: o gap total cresce de 0,31 no q25 para 0,48 no q90. O que a RIF-OB adiciona é a *decomposição por mecanismo*: esse gradiente crescente é dominado pelo componente de dotações — diferenças de capital humano acumulado — não pelo componente de retornos. O componente de retornos, que é o que se interpreta como discriminação de mercado, *declina* de 33,1% no q10 para 11,2% no q90. Isso é o sticky floor discriminatório: a penalidade de mercado proporcional é maior na base da distribuição, não no topo. A interpretação econômica é importante: o glass ceiling no gap bruto é resultado de décadas de acumulação desigual de capital humano e redes — desvantagens pré-mercado. Eliminar discriminação de mercado (retornos) fecharia mais o gap na base; políticas de educação e redes são necessárias para o topo. Não é contradição — é especificidade de mecanismo."

### P8c — "O que significa a penalidade interseccional de 9,5 pp? É esperada ou surpreendente?"
> "É o resultado central de Crenshaw (1989) confirmado empiricamente com 2,36 milhões de observações. O gap da Mulher Negra em relação ao Homem Branco é de 96,4%. Se os dois eixos — ser negro e ser mulher — fossem independentes e aditivos, esperaríamos gap(Mulher Negra) = gap(Mulher Branca) + gap(Homem Negro) = 46,6% + 40,3% = 86,9%. A diferença real é 96,4% − 86,9% = 9,5 pp — isso é a penalidade interseccional: um mecanismo discriminatório específico à combinação raça-gênero que não se reduz aos dois eixos somados. O que é surpreendente — e relevante para política — é a decomposição por mecanismo: o gap da Mulher Negra é 70,4% por retornos (discriminação de mercado) versus 29,6% por dotações. Ou seja, a penalidade interseccional extra opera principalmente pelo lado discriminatório, não pelo lado de capital humano. Isso indica que intervenções antidiscriminação que tratam raça e gênero separadamente deixam de capturar esse resíduo específico."

### P8d — "Por que Konfound e E-values, e não Oster bounds, para avaliar sensibilidade do HLM e GLMM?"
> "Porque Oster (2019) foi desenvolvido especificamente para OLS linear e pressupõe: (1) decomposição de variância por R², (2) coeficiente único sem efeitos aleatórios, (3) seleção proporcional à variância explicada. No HLM, a variância é particionada entre níveis — UPA, UF, indivíduo — e o R² marginal e condicional são métricas distintas com interpretações diferentes. Aplicar a fórmula de δ* do Oster a um R² marginal do HLM seria combinar grandezas incompatíveis. Para o GLMM, a função de ligação logística invalida a lógica linear. Por isso usamos: Konfound de Frank et al. (2013), que opera diretamente no t-estatístico do próprio HLM sem exigir R² linear; e E-values de VanderWeele & Ding (2017), que são agnósticos ao link function e operam no OR observado. Mantivemos o Oster apenas para os modelos OLS auxiliares da decomposição OB — onde ele é formalmente válido. A comparação explicita que usar o OLS como proxy para testar a robustez do HLM subestimaria o pkonfound em 5 a 9,5 pontos percentuais."

---

## Perguntas sobre Teoria

### P9 — "Qual é a sua hipótese causal? É Arrow (1973), Becker (1957) ou algo diferente?"
> "As evidências são mais consistentes com a teoria de discriminação estatística de Arrow e com o modelo de segregação ocupacional do que com o modelo de preconceito de Becker. No modelo de Becker, firmas preconceituosas perdem lucro e seriam eliminadas pela competição — mas o gap persiste por 10 anos de dados, o que é inconsistente com essa predição. No modelo de discriminação estatística, o empregador usa raça como proxy de produtividade não observável — o que explica o gap de acesso ao emprego qualificado mesmo entre indivíduos com qualificações observáveis equivalentes. Mas não descarto a coexistência de múltiplos mecanismos — o racismo brasileiro é suficientemente complexo para operar por vários canais simultaneamente."

### P10 — "O conceito de 'racismo estrutural' no título é sociológico ou tem definição operacional no modelo?"
> "O uso do termo no título é deliberado e tem ancoragem dupla. Sociologicamente, sigo Almeida (2019): estrutural porque é produzido e reproduzido pelas estruturas econômicas e institucionais, não por atos individuais. Operacionalmente, defino como: a parcela do gap salarial que persiste depois de controlar todas as características individuais observáveis. Isso é o que o HLM, o Oaxaca e o ML detectam convergentemente. A convergência entre cinco métodos com diferentes premissas torna a conclusão mais robusta do que qualquer resultado isolado."

---

## Perguntas de Defesa (mais difíceis)

### P11 — "O R² de 0,62 do XGBoost é bom para prever renda, mas não garante que o resíduo de raça seja discriminação. Um modelo perfeito poderia zerar o SHAP de raça com variáveis que nós não temos."
> "Correto — e essa é exatamente a limitação que reconheço. O que posso argumentar é: o XGBoost tem capacidade de capturar interações não-lineares que modelos paramétricos perdem. Se existe uma variável latente correlacionada com raça e renda, ela se manifestaria via SHAP como interações com as variáveis existentes. O fato de raça aparecer com SHAP negativo próprio — e não apenas como moderador — sugere que o efeito é direto. Mas a prova definitiva dependeria de dados de experimento controlado ou variável instrumental, que não existem para o mercado de trabalho brasileiro em escala nacional."

### P12 — "Você tem resultados robustos para o período de pandemia (2020-2021)? O gap pode ser estruturalmente diferente nesses anos."
> "Não faço análise separada por período no TCC — uso o período completo 2016–2025 como uma única estrutura de painel anual. A literatura mostra que a pandemia aprofundou desigualdades raciais — negros tiveram maior perda de emprego formal e menor acesso a auxílios. Isso poderia enviesar minha estimativa do gap para cima nos anos de pandemia. Como extensão natural, a análise de quebra estrutural nos coeficientes — um Chow test por ano — seria relevante, mas está além do escopo atual. Posso incorporar como agenda futura se a banca considerar relevante."

---

## PERGUNTAS SOBRE AS HIPÓTESES DO ESTADO (Anexo A)

### P13 — "O Estado é indutor de desigualdade ou de igualdade?"
> "A resposta depende de qual dimensão analisamos. Para a desigualdade geral (H1), o Estado é indutor: o prêmio público bruto é de +99,6% sobre o privado, e a decomposição de Theil mostra que 7,8% da desigualdade total vem da diferença entre setores público e privado. Para a desigualdade racial (H2), o Estado é atenuador: o gap racial controlado é 4 pontos percentuais menor no público (−25,2%) do que no privado (−29,2%). Para gênero (H3), surpreendentemente, o Estado é indutor: o gap de gênero controlado é maior no setor público (−18,8%) que no privado (−16,9%), porque a igualdade do concurso na entrada não se traduz em igualdade na progressão de carreira. Então: o Estado reduz discriminação racial mas amplia desigualdade de renda geral e não garante igualdade de gênero."

### P14 — "O gap de gênero maior no setor público não contraria a expectativa teórica?"
> "Contraria a narrativa ingênua, mas não a teoria. O setor público tem concurso público equânime para entrada — o que de fato reduz discriminação de acesso por gênero. Mas os cargos de maior remuneração — DAS, postos de comando militar, procuradoria, judicatura — têm prevalência masculina e são preenchidos por promoção interna ou indicação política, não por concurso. O resultado é que, dentro do setor público, as mulheres se concentram nos cargos de nível médio-inferior (magistério, enfermagem, assistência) enquanto os homens dominam o topo. Depois de controlar educação e setor, o gap se inverte. Isso é um exemplo de discriminação estrutural que o concurso público não resolve."

### P15 — "A hipótese H4 confirma ou contraria o governo atual?"
> "Minha análise é descritiva e temporal, não normativa. Os dados mostram que: (1) a taxa de emprego atingiu máximo histórico de 94,4% em 2025; (2) a renda real cresceu fortemente de R$1.106 em 2022 para R$1.345 em 2024 — +21,6% real, acima da inflação; (3) em 2025, a renda real recuou para R$1.283 apesar do emprego em alta. A interpretação neutra é: o crescimento do emprego em 2025 foi concentrado em setores de baixa produtividade, o que é consistente com a armadilha da renda média documentada em H5. Não cabe ao TCC fazer julgamentos sobre governos — o que faço é mostrar que emprego e renda real podem divergir quando o crescimento não é acompanhado de upgrade ocupacional."

---

## JUSTIFICAÇÃO DA ESCOLHA DOS MODELOS (Item 8 — ESALQ)

### Por que HLM e não OLS?
> "Três argumentos formais. Primeiro: o ICC_UF=9,83% no modelo nulo supera o limiar de 5% de Raudenbush e Bryk (2002), indicando que 9,8% da variância de rendimentos é atribuível ao estado — o que viola o pressuposto de independência do OLS. Segundo: o LRT entre HLM Nulo e OLS Nulo gera χ²=191.625 com Δk=1, rejeitando o modelo plano com p≈0. Terceiro: o OLS com FE de UF (27 dummies) tem AIC=3.684.832 — pior que o OLS com controles básicos (AIC=3.660.787) — enquanto o HLM Contextual (AIC=3.588.684) obtém desempenho equivalente com metade dos parâmetros e standard errors válidos para inferência hierárquica. O HLM é mais parcimonioso, mais eficiente e produz intervalos de confiança corretos."

### Por que regressão quantílica e não apenas OLS?
> "O OLS estima o efeito médio do gap racial. A hipótese de glass ceiling é sobre heterogeneidade do efeito: o gap deve ser maior no topo da distribuição do que na base. Isso não pode ser testado com OLS sem especificações ad hoc de interações. A regressão quantílica estima β̂_negro(q) para qualquer quantil sem pressuposto paramétrico sobre os erros — e os erros padrão por bootstrap são robustos a heteroscedasticidade. O teste é direto: β̂_negro(q95) < β̂_negro(q10) significa glass ceiling. Confirmado: Δ=−0,0455."

### Por que logit e não LPM (OLS para desfecho binário)?
> "O LPM — OLS para variável binária — produz probabilidades previstas fora de [0,1] para valores extremos das covariáveis, e é heteroscedástico por construção (variância = p(1−p) depende dos preditores). O logit garante probabilidades coerentes e é consistente com a distribuição de Bernoulli do desfecho. A crítica válida ao LPM — de que seus coeficientes são diretamente interpretáveis como probabilidade — não se aplica aqui porque reporto AMEs, que têm interpretação de probabilidade direta mesmo no logit."

### Por que XGBoost e não regressão linear múltipla para o ML?
> "A regressão linear pressupõe forma funcional linear e aditiva. Renda é determinada por interações complexas entre educação, ocupação, localização e raça que um modelo linear não captura. O XGBoost — boosting de árvores — captura interações não-lineares automaticamente, sem especificação manual. O ganho de R² foi de 0,44 (modelo linear com mesmas variáveis) para 0,62 com XGBoost — evidência empírica de que a forma funcional importa. O SHAP permite explicar cada previsão individual, tornando o modelo interpretável apesar da não-linearidade."

### Por que Oaxaca-Blinder two-fold e não three-fold?
> "O estimador three-fold decompõe o gap em dotações, retornos e interação. Em amostras grandes com covariáveis correlacionadas, a parcela de interação pode ser positiva ou negativa dependendo da escolha do grupo de referência — tornando a decomposição sensível a uma escolha arbitrária. O estimador two-fold agrupa retornos e interação em um único componente de 'vantagem diferencial', que é equivariante à escolha do grupo de referência. Para fins deste trabalho — onde o objetivo é separar dotações de discriminação, não decomposição granular —, o two-fold é mais robusto."

---

## Dicas Finais para a Defesa

1. **Antes de responder**: repita a pergunta em voz alta ou parafraseie. Isso te dá 5 segundos para pensar e confirma que você entendeu.
2. **Se não souber**: "Essa é uma dimensão que não explorei neste trabalho, mas é uma extensão natural que eu faria assim..." É melhor admitir do que especular e errar.
3. **Números de cabeça**: memorize doze números essenciais — (a) 7,7 mi observações / 10 anos, (b) gap bruto M1 = 37%, (c) gap residual HLM M4 = −6,35% (mediação ~80%), (d) Oaxaca dotações = 84%, (e) XGBoost R²=0,62, (f) LRT HLM vs OLS χ²=191.625, (g) ICC_UPA=17,8%, (h) glass ceiling Δ crescente (q10→q95), (i) GLMM ocp_qualif OR=0,741 AME=−1,12 pp E-value=2,04, (j) penalidade interseccional Mulher Negra +9,5 pp, (k) RIF-OB sticky floor: retornos q10=33,1% → q90=11,2%, (l) Konfound HLM M4 pkonfound=96,3%. Tudo o mais você pode buscar no slide.
4. **Confiança metodológica**: você fez HLM de 3 níveis, regressão quantílica, logit com clustered SE, SHAP e SNA. Poucos TCCs chegam a essa profundidade. Não minimize isso.
5. **Se a banca discordar de uma escolha metodológica**: "Concordo que há trade-offs nessa escolha. Optei por X porque Y. Uma abordagem alternativa seria Z, e planejo explorá-la em trabalhos futuros." Nunca entre em duelo — recognize, explique, proponha extensão.

---

*Atualizado em 2026-05-08 | Resultados: HLM, ML/SHAP, Oaxaca-Blinder, Logit Multinível, Regressão Quantílica, Hipóteses do Estado (Anexo A), Comparativo de Modelos (Anexo B), Seção 6 (Políticas Públicas) — PNAD Contínua 2016–2025*
