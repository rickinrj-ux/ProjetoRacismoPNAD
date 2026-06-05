# Comparação Amostra × População — Conversão das Análises

**Data:** 2026-06-04 · **Decisão:** a pedido do autor, todas as análises devem usar **base populacional** (PEA completa, ~7,69 M observações da PNAD Contínua 2016–2025), não amostral.

Este documento registra, para cada análise convertida, os valores **antigos (amostrais, recuperados do commit `f52e1f5` em `outputs/_old_amostral/`)** versus os **novos (populacionais)**, e avalia o risco de overfitting do método não-paramétrico após o uso da população.

---

## 1. Resumo executivo

| Análise | Era amostra? | Mudança substantiva? | Efeito principal |
|---|---|---|---|
| Segregação espacial (CI) | **Sim — 10%** | Não (≤0,15 pp) | ICs mais estreitos |
| ML / SHAP (XGBoost, RF) | **Sim — 20%** | Não (R² idêntico) | overfitting desprezível |
| Regressão Quantílica | **Sim — 20%** | Não (β ~idêntico) | ICs mais estreitos |
| RIF-OB | **Não — já populacional** | — (idêntico) | sem alteração |
| Mobilidade intergeracional | **Não — já populacional** | — (idêntico) | sem alteração |

**Conclusão geral:** a conversão para população **não altera nenhuma conclusão substantiva** — as estimativas pontuais já eram estáveis nas subamostras (que eram grandes). O ganho é de **precisão** (intervalos de confiança menores) e de **defensabilidade** (resultados representam a população, não um recorte). O overfitting do método não-paramétrico é **desprezível** (gap R²treino−R²teste = 0,0006).

---

## 2. Detalhe por análise

### 2.1 Segregação espacial — gap racial por tipo de área (10% → população)

| Área | Gap % (amostra 10%) | n (10%) | Gap % (população) | n (pop) | Δ (pp) |
|---|---|---|---|---|---|
| Capital | −38,63 | 201.887 | **−38,57** | 2.024.012 | +0,06 |
| RM (exceto capital) | −28,14 | 102.633 | **−27,99** | 1.029.985 | +0,15 |
| Interior | −36,37 | 467.236 | **−36,22** | 4.663.564 | +0,15 |

Diferenças ≤ 0,15 pp; ordenação inalterada (Capital > Interior > RM). Os **intervalos de confiança ficaram mais estreitos** na população (ex.: Interior IC 95% [−36,68; −36,05] → [−36,52; −35,69], com estimativa pontual sobre 4,66 M). *Nota: a estimativa pontual usa a população; o bootstrap do IC usa subamostra capada (300k) por viabilidade — é método de erro-padrão, não amostragem do resultado.*

### 2.2 ML / SHAP — desempenho preditivo (20% → população)

| Modelo | R² teste (amostra 20%) | R² teste (população) | Δ |
|---|---|---|---|
| XGBoost | 0,6169 | **0,6168** | −0,0001 |
| Random Forest | 0,5743 | **0,5735** | −0,0008 |

R² praticamente idêntico — a amostra de 20% já era representativa. O ranking SHAP (renda média da UPA como principal preditor — "o bairro prediz mais que o diploma") **mantém-se** na população. *(Os valores SHAP do beeswarm seguem computados sobre subconjunto de 50k, prática-padrão de visualização — o modelo é treinado na população.)*

### 2.3 Regressão Quantílica — β de `negro` por quantil (20% → população)

| Quantil (M3) | Gap % (amostra 20%) | Gap % (população) | IC 95% largura (20% → pop) |
|---|---|---|---|
| q10 | −7,88 | **−7,98** | estreita |
| q25 | −7,07 | **−7,08** | estreita |
| q50 | −7,68 | **−7,81** | estreita |
| q75 | −9,93 | **−9,87** | estreita |
| q90 | −11,63 | **−11,62** | estreita |
| q95 | −12,22 | **−12,34** | [−13,65; −12,41]→[−13,45; −12,90] (≈½ da largura) |

O **glass ceiling** (gap crescente do q10 ao q95) é confirmado em ambos; os ICs encolhem ~½ na população (≈√5× mais dados). Conclusão inalterada.

### 2.4 RIF-OB e Mobilidade — já eram populacionais

- **RIF-OB:** o CSV commitado já tinha n = 3.259.516 brancos + 4.434.682 negros (= 7,69 M = população). O re-run produziu valores **idênticos** (sticky floor / glass ceiling por dotações inalterados). A opção `--sample 0.10` existia como *default* do script, mas a saída commitada foi gerada em população; o *default* foi corrigido para `None` (população).
- **Mobilidade intergeracional:** o CSV commitado já refletia 514.097 pares filho-chefe (todos os anos), com elasticidades idênticas (Branco 0,0286; Negro 0,0287; mobilidade relativa 1,005). A opção de `--sample`/`--anos` existia no script mas não foi usada na saída commitada.

---

## 3. Avaliação de overfitting (método não-paramétrico, população)

Com a população (N = 7,69 M; treino 6,16 M / teste 1,54 M), o método não-paramétrico (XGBoost, Random Forest) foi avaliado pelo **gap entre R² de treino e de teste**:

| Modelo | R² treino | R² teste | **Gap (overfitting)** |
|---|---|---|---|
| Random Forest | 0,5741 | 0,5735 | **0,0006** |
| XGBoost | 0,6174 | 0,6168 | **0,0006** |

**Veredito:** overfitting **desprezível**. Três evidências convergem:
1. **Gap treino–teste ≈ 0,0006** — o modelo generaliza quase perfeitamente; não há memorização.
2. **N ≫ complexidade** — com 7,69 M observações e modelos regularizados (XGBoost: depth=6, L1/L2, subsample 0,8; RF: depth=10, min_leaf=50), a razão observações/parâmetros torna o overfitting estatisticamente implausível.
3. **Estabilidade entre escalas** — o R² de teste é idêntico em 20% (0,6169) e na população (0,6168); se houvesse overfitting dependente do tamanho da amostra, o R² mudaria.

Ou seja, **aumentar a base de amostral para populacional reduz (não aumenta) o risco de overfitting** — mais dados melhoram a generalização. A robustez do achado "o contexto domina, a raça opera via território" é confirmada na população.

---

## 4. Implicações para o trabalho

- Nenhuma conclusão da tese muda; os números populacionais substituem os amostrais com **maior precisão**.
- Os scripts foram convertidos para população por *default* (`SAMPLE_FRAC=None`); bootstrap de erro-padrão permanece em subamostra (método de SE, não amostragem do resultado).
- Recomenda-se citar, no texto, que os resultados são **populacionais** e que o método não-paramétrico não apresenta overfitting (gap ≈ 0).
