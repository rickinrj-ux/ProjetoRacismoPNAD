# Tratamento de Dados — Documentação para Validação de Pares

**Projeto:** Desigualdade Salarial Racial no Brasil (PNAD Contínua 2016–2025)  
**Repositório:** https://github.com/rickinrj-ux/ProjetoRacismoPNAD  
**Última atualização:** 2026-05-16  
**Autora principal:** Ricardo Calheiros (MBA USP/ESALQ)

Este documento descreve, passo a passo, como os dados brutos foram obtidos, filtrados e transformados para cada análise. O objetivo é permitir que pesquisadores independentes repliquem ou auditem os resultados sem acesso ao ambiente original.

---

## Índice

1. [Fontes de dados](#1-fontes-de-dados)
2. [Ingestão PNAD Contínua](#2-ingestão-pnad-contínua)
3. [Engenharia de features](#3-engenharia-de-features)
4. [Filtros e exclusões](#4-filtros-e-exclusões)
5. [Modelos HLM — amostra e estimação](#5-modelos-hlm--amostra-e-estimação)
6. [Análise Oaxaca-Blinder e retornos raciais](#6-análise-oaxaca-blinder-e-retornos-raciais)
7. [Análise regional](#7-análise-regional)
8. [Ingestão e análise ENEM contextual](#8-ingestão-e-análise-enem-contextual)
9. [Ingestão RAIS](#9-ingestão-rais)
10. [Decisões metodológicas críticas](#10-decisões-metodológicas-críticas)
11. [Reprodução do ambiente](#11-reprodução-do-ambiente)

---

## 1. Fontes de dados

| Fonte | Período | Acesso | Arquivo de ingestão |
|-------|---------|--------|---------------------|
| PNAD Contínua (IBGE) | 2016–2025 (40 trimestres) | FTP público IBGE | `src/data_ingestion.py` |
| ENEM microdados (INEP) | 2016–2023 | basedosdados/BigQuery | `src/ingestion_enem.py` |
| RAIS (MTE) | 2016–2025 | basedosdados/BigQuery | `src/ingestion_rais.py` |

### PNAD Contínua — URL base
```
https://ftp.ibge.gov.br/Trabalho_e_Rendimento/
  Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/
  Trimestral/Microdados/
```

Dicionários de layout testados em ordem (primeiro disponível é usado):
```
Dicionario_e_input_20221031.zip
Dicionario_e_input_20200220.zip
Dicionario_e_input_20190529.zip
```

---

## 2. Ingestão PNAD Contínua

**Arquivo:** `src/data_ingestion.py`  
**Runner:** `python run_features.py` ou `python run_features_completo.py`

### Variáveis selecionadas (subconjunto dos microdados)

| Código PNAD | Descrição | Uso |
|-------------|-----------|-----|
| `Ano`, `Trimestre` | Período de referência | Painel temporal |
| `UF` | Unidade da Federação (código IBGE) | Nível 3 do HLM |
| `UPA` | Unidade Primária de Amostragem | Nível 2 do HLM (proxy de bairro) |
| `V1022` | Situação do domicílio (1=Urbano, 2=Rural) | Dummy `urbano` |
| `V2007` | Sexo (1=Homem, 2=Mulher) | `sexo_fem` |
| `V2009` | Idade | `idade_c`, `idade_sq` (Mincer) |
| `V2010` | **Cor ou raça** (variável central) | `negro` (Preto+Pardo) |
| `V3009A` | Nível de instrução mais elevado | `educ_*` dummies |
| `VD4002` | Condição de ocupação | `empregado`, `pea` |
| `VD4016` | Rendimento habitual do trabalho principal | Descritiva |
| `VD4020` | **Rendimento efetivo de todos os trabalhos** | `log_renda` (variável dependente) |
| `VD4031` | Horas trabalhadas efetivas | `log_horas` |
| `V4010` | Código CBO (ocupação, 4 dígitos) | `ocp_grupo_cbo` |
| `V4013` | CNAE-Domiciliar (setor econômico) | `setor_cnae` |
| `VD4008` | Tipo de vínculo empregatício | `tipo_vinculo` |
| `VD4009` | Posição na ocupação (10 categorias) | `emprego_formal`, `conta_propria` |

### Formato de saída
- Arquivos Parquet particionados por Ano/Trimestre em `data/raw/pnad/`
- Compressão Snappy (redução ~5–10× vs. TXT original)
- Leitura em chunks de 100.000 linhas para controle de memória

---

## 3. Engenharia de features

**Arquivo:** `src/feature_engineering.py`  
**Runner:** `python run_feature_engineering.py`  
**Output:** `data/processed/features.parquet`

### 3.1 Classificação racial (`negro`)

```python
RACE_NEGRO  = {2, 4}   # V2010: Preto (2) + Pardo (4)
RACE_BRANCO = {1}      # V2010: Branco (1)
# Amarelos (3) e Indígenas (5) excluídos por n insuficiente
# para inferência estatística robusta em subgrupos regionais.
```

Resultado: `negro = 1` (Preto ou Pardo), `negro = 0` (Branco). Observações com `V2010 ∈ {3, 5}` ou `NA` são excluídas da análise principal (158.491 observações removidas no filtro racial, ~1% da amostra total).

**Referência:** Hasenbalg (1979); IBGE (2021) — padrão adotado pela literatura de desigualdade racial no Brasil.

### 3.2 Rendimento (`log_renda`)

```
VD4020 → winsorização a 1% no limite superior
        → exclusão de observações com renda < p1
        → log(1 + renda) = log_renda
```

- **Variável dependente:** `VD4020` (rendimento efetivo de todos os trabalhos, inclui trabalho principal e secundários)
- **Winsorização**: apenas limite superior (outliers ricos), preserva estrutura amostral complexa da PNAD
- **log1p**: evita `-inf` para `renda = 0`; interpretação dos coeficientes como variação percentual (`exp(β) - 1`)

### 3.3 Educação (`educ_*`)

Mapeamento de `V3009A` (8 categorias IBGE) em escala ordinal e 4 dummies de conclusão de ciclo:

| V3009A | Categoria | Dummy criada |
|--------|-----------|--------------|
| 1 | Sem instrução | referência |
| 2 | Fund. incompleto | — |
| 3 | **Fund. completo** | `educ_fund_completo` |
| 4 | Méd. incompleto | — |
| 5 | **Méd. completo** | `educ_medio_completo` |
| 6 | Sup. incompleto | — |
| 7 | **Sup. completo** | `educ_superior_completo` |
| 8 | **Pós-graduação** | `educ_pos_graduacao` |

Apenas níveis de **conclusão de ciclo** geram dummies — categorias incompletas não constituem credenciais no mercado formal (Carneiro, Heckman & Masterov, 2005).

### 3.4 Idade e experiência (`idade_c`, `idade_sq`)

Seguindo a equação de Mincer (1974):

```
idade_c  = V2009 - mean(V2009)   # centralizado na média — reduz multicolinearidade
idade_sq = idade_c²              # captura relação côncava renda × experiência
```

### 3.5 Horas trabalhadas (`log_horas`)

```python
horas = VD4031.clip(lower=1)     # evita log(0)
log_horas = log(horas)
```

**Justificativa de inclusão:** controle predeterminado (horas são parcialmente independentes de discriminação salarial). Sem esse controle, a sobre-representação de negros em trabalhos part-time inflaria o coeficiente racial estimado.

### 3.6 Área urbana (`urbano`)

```python
urbano = int(V1022 == 1)   # 1=Urbano, 0=Rural
```

**Justificativa:** o prêmio salarial urbano (~30%) é geograficamente predeterminado, não mediado por discriminação no mercado de trabalho. Controlar evita confusão com diferenciais regionais de custo de vida.

### 3.7 Variáveis contextuais de Nível 2 (UPA)

Calculadas como médias/proporções dentro de cada UPA sobre **todos os membros da UPA** (não só os com renda positiva):

| Variável | Fórmula | Hipótese testada |
|----------|---------|-----------------|
| `pct_negro_upa` | Proporção negros na UPA | Segregação residencial → duplo disadvantage |
| `tx_desemprego_upa` | 1 − média(empregado) na PEA da UPA | Escassez de oportunidades locais |
| `media_educ_upa` | Média de `educ_ord` na UPA | Spillovers de capital humano |
| `media_renda_upa` | Média de `log_renda` na UPA | Riqueza do networking local |

**Padronização z-score** aplicada no momento do ajuste do HLM para comparabilidade de coeficientes entre preditores de escalas diferentes.

**Exclusão de UPAs pequenas:** UPAs com n < 10 respondentes têm estimativas contextuais marcadas como `NaN` e excluídas dos modelos multinível (56 UPAs afetadas, < 0,1% do total).

### 3.8 Variáveis contextuais de Nível 3 (UF)

Análogas às de Nível 2, calculadas no nível estadual: `pct_negro_uf_z`, `tx_desemprego_uf_z`, `media_educ_uf_z`.

---

## 4. Filtros e exclusões

Aplicados sequencialmente em `src/multilevel_model.py → load_features()`:

| Etapa | Critério | Observações removidas |
|-------|----------|----------------------|
| Filtro racial | V2010 ∈ {Amarelo, Indígena, NA} | 158.491 |
| Renda positiva | log_renda > 0 e não-NA | ~8.224.114 (fora da PEA ou sem rendimento) |
| Dropna | NA em qualquer variável do modelo | 23.363 |
| UPA mínima | UPAs com < 10 respondentes | 4.772 |
| **Dataset analítico** | | **7.689.426 obs.** |

**Total bruto:** 15.941.675 observações (2016–2025, 40 trimestres, 27 UFs, 41.517 UPAs).

> **Nota sobre amostragem nos modelos HLM:** Os modelos HLM da série completa (`run_hlm_serie_completa.py`) foram estimados com 20% do dataset analítico (1.537.885 obs.) por limitação computacional do solver Powell/REML em Python (statsmodels). Os modelos OLS com efeitos fixos de UF foram estimados na amostra completa (7.689.426 obs.) e confirmam os coeficientes HLM dentro de ±0,003 log-pontos — a convergência das duas abordagens valida a robustez dos resultados.

---

## 5. Modelos HLM — amostra e estimação

**Arquivo:** `src/multilevel_model.py`  
**Runner:** `python run_hlm_serie_completa.py`

### Estrutura de 3 níveis

```
Nível 1 — Indivíduo (i):
    log_renda_{ijk} = β_{0jk} + β_{1jk}·negro + controles_individuais + ε_{ijk}

Nível 2 — UPA (j):
    β_{0jk} = γ_{00k} + γ_{01}·PctNegro_j + γ_{02}·TxDesemp_j + γ_{03}·MediaEduc_j + u_{0jk}

Nível 3 — UF (k):
    γ_{00k} = δ_{000} + δ_{001}·PctNegro_k + δ_{002}·TxDesemp_k + δ_{003}·MediaEduc_k + v_{00k}
```

### Equação de Nível 1 (fórmula completa)

```python
_INDIVIDUAL_TERMS = (
    "negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + log_horas + urbano + C(Ano)"   # controles predeterminados adicionados
)
```

Os termos `log_horas`, `urbano` e `C(Ano)` (dummies de ano) são **controles predeterminados** — não são mediadores de discriminação e sua inclusão aumenta a precisão da estimativa de `β_negro` sem introduzir viés de controle ruim (*bad control*).

### Método de estimação

- **HLM:** `statsmodels.MixedLM`, REML=True, método Powell, grupos=UF
- **OLS robustez:** `statsmodels.OLS` com `C(UF)` como efeitos fixos e SE clusterizado por UF
- **Covariância de Nível 2:** `vc_formula={"UPA_str": "0 + C(UPA_str)"}` — UPA como efeito aleatório cruzado

### Sequência de modelos

| Modelo | Preditores adicionados | Propósito |
|--------|----------------------|-----------|
| M0 — Nulo | Intercepto apenas | ICC de referência |
| M1 — Individual | Características individuais + C(Ano) | Gap bruto |
| M2 — Localidade | M1 + contexto UPA (Nível 2) | Mediação por vizinhança |
| M3 — Completo | M2 + contexto UF (Nível 3) | Gap líquido 3 níveis |
| M4 — Ocupação | M3 + ocupação/formalidade | Limite superior (bad control caveat) |

### Controles ruins (*bad controls*) — deliberadamente excluídos de M1–M3

Ocupação (`V4010`/CBO), setor econômico (`V4013`/CNAE), setor público/privado e tamanho de empresa são **mediadores** da discriminação racial — negros são canalizados para ocupações piores pelo próprio mercado discriminatório. Controlá-los em M1–M3 removeria parte do efeito causal que se busca estimar. O M4 os inclui apenas como *upper bound* da discriminação "pós-ocupação".

---

## 6. Análise Oaxaca-Blinder e retornos raciais

**Arquivo:** `src/analise_retornos_raciais.py`  
**Runner:** `python run_analise_retornos_raciais.py`

### Decomposição Oaxaca-Blinder (twofold)

Decompõe o gap salarial bruto (Δȳ = ȳ_branco − ȳ_negro) em dois componentes:

```
Δȳ = (X̄_B − X̄_N)·β_B    +    X̄_N·(β_B − β_N)
      ───────────────────        ──────────────────────
      Efeito dotação              Efeito coeficiente
      (diferenças em             (retornos diferentes
      capital humano)             para mesmas dotações)
```

- **Efeito dotação:** quanto do gap é explicado por negros terem, em média, menos escolaridade, menos experiência, etc.
- **Efeito coeficiente:** quanto persiste quando negros têm as mesmas características que brancos — limite inferior da discriminação direta.

**Implementação:** OLS separado por grupo racial, decomposição manual + bootstrap (n=200 replicações) para erros-padrão.

**Fórmula OLS base:**
```python
FORMULA_OLS = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
    " + log_horas + urbano + C(Ano) + C(UF)"
)
```

### Interação negro × escolaridade (desconto de credencial)

Testa se o retorno à educação é menor para trabalhadores negros:

```python
FORMULA_INTERACAO = (
    "log_renda ~ negro * (educ_fund_completo + educ_medio_completo"
    "             + educ_superior_completo + educ_pos_graduacao)"
    " + sexo_fem + idade_c + idade_sq + log_horas + urbano + C(Ano) + C(UF)"
)
```

Um coeficiente `negro:educ_superior_completo < 0` indica que o ensino superior tem retorno **menor** para negros que para brancos com idêntico grau — evidência de desconto de credencial.

### Regressão quantílica com interação

Estima se o desconto cresce ao longo da distribuição de renda (glass ceiling):

```python
FORMULA_QR = "log_renda ~ negro + ... + log_horas + urbano + C(Ano)"
quantis = [0.10, 0.25, 0.50, 0.75, 0.90]
```

Se `β_negro` cresce em valor absoluto de τ=0.10 para τ=0.90, discriminação é mais intensa no topo — efeito "teto de vidro".

---

## 7. Análise regional

**Arquivo:** `src/analise_regional.py`  
**Runner:** `python run_analise_regional.py`

### Hipóteses testadas

- **H1:** `β_negro` varia significativamente entre macrorregiões (heterogeneidade espacial)
- **H2:** *Glass ceiling* (gap maior no topo) predomina no Sudeste/Sul (mercado mais formal)
- **H3:** *Sticky floor* (gap maior na base) predomina no Nordeste/Norte

### Macrorregiões e UFs

| Região | Códigos IBGE |
|--------|-------------|
| Norte | 11, 12, 13, 14, 15, 16, 17 |
| Nordeste | 21, 22, 23, 24, 25, 26, 27, 28, 29 |
| Sudeste | 31, 32, 33, 35 |
| Sul | 41, 42, 43 |
| Centro-Oeste | 50, 51, 52, 53 |

### HLM por região

Para cada macrorregião: `statsmodels.MixedLM` com grupos=UF (intercepto aleatório), covariáveis de Nível 2 (UPA) como slopes fixos. Extrai `β_negro`, `ICC_UF` e componentes de variância por região.

### Regressão quantílica por região

`statsmodels.QuantReg` para τ ∈ {0.10, 0.25, 0.50, 0.75, 0.90}, fórmula idêntica ao HLM (sem efeito aleatório).

---

## 8. Ingestão e análise ENEM contextual

**Arquivo ingestão:** `src/ingestion_enem.py`  
**Arquivo análise:** `src/analise_enem_contextual.py`  
**Runner ingestão:** `python run_ingestion_enem.py --project tcc-racismo-pnad`  
**Runner análise:** `python run_analise_enem_contextual.py`

### Query BigQuery (corrigida — schema basedosdados 2024+)

```sql
SELECT
    ano,
    sigla_uf_prova AS sigla_uf,
    CASE
        WHEN cor_raca IN ('2', '3') THEN 'negro'
        WHEN cor_raca = '1'         THEN 'branco'
    END AS grupo,
    AVG((nota_ciencias_natureza + nota_ciencias_humanas +
         nota_linguagens_codigos + nota_matematica + nota_redacao) / 5.0) AS nota_media,
    COUNT(*) AS n_candidatos
FROM `basedosdados.br_inep_enem.microdados`
WHERE ano BETWEEN 2016 AND 2023
  AND cor_raca IN ('1', '2', '3')
  AND sigla_uf_prova IS NOT NULL
  AND nota_matematica IS NOT NULL
  AND nota_redacao IS NOT NULL
  AND presenca_ciencias_natureza = '1'   -- STRING '1' = presente (schema v2024)
  AND presenca_matematica        = '1'
  AND presenca_redacao           = '1'
GROUP BY 1, 2, 3
```

**Nota schema:** O campo `presenca_*` no basedosdados usa valores `'0'`/`'1'`/`'2'` como STRING, não `'Presente'`/`'Ausente'`. Esta correção foi necessária após verificação empírica do schema real da tabela.

### Codificação racial ENEM

| Código | Grupo no ENEM | Mapeamento |
|--------|--------------|------------|
| `'1'`  | Branca       | branco |
| `'2'`  | Preta        | negro |
| `'3'`  | Parda        | negro |
| `'4'`  | Amarela      | excluído |
| `'5'`  | Indígena     | excluído |
| `'0'`  | Não declarado| excluído |

### Cálculo do gap ENEM por UF/ano

```
gap_enem = nota_media_branco − nota_media_negro   (escala 0–1000)
gap_enem_z = (gap_enem − média_ano) / dp_ano     (z-score por ano)
```

O z-score normaliza a variação entre UFs dentro de cada ano, tornando o gap comparável como preditor de Nível 3 no HLM.

### Modelo M3_ENEM

Adiciona `gap_enem_uf_z` ao M3 completo como preditor de Nível 3:

```
γ_{00k} = δ_{000} + δ_{001}·PctNegro_k + δ_{002}·TxDesemp_k
                  + δ_{003}·MediaEduc_k + δ_{004}·GapEnem_k + v_{00k}
```

**Interpretação cautelosa:** `δ_{004}` não deve ser interpretado como efeito causal da discriminação de avaliadores (Botelho, Madeira & Rangel, 2015). É uma correlação ecológica (nível UF) entre desigualdade educacional e salarial — canais causais (segregação escolar, SES, potencial viés de avaliação) não são separáveis com dados agregados por UF.

---

## 9. Ingestão RAIS

**Arquivo:** `src/ingestion_rais.py`  
**Runner:** `python run_ingestion_rais.py`  
**Fonte:** `basedosdados.br_me_rais.microdados_vinculos` (BigQuery)

### Variáveis selecionadas

| Variável | Código RAIS | Uso |
|----------|------------|-----|
| Ano | `ano` | Painel temporal |
| UF | `sigla_uf` | Nível 3 |
| Raça/cor | `raca_cor` | `negro` binário |
| Remuneração média | `valor_remuneracao_media` | Validação cruzada com PNAD |
| Horas semanais | `quantidade_horas_contratadas` | `log_horas_rais` |
| Vínculo ativo | `vinculo_ativo_31_12` | Filtro de vínculos ativos |
| CNAE setor | `cnae2_subclasse` | `setor_cnae_rais` |
| Grau instrução | `grau_instrucao_apos_2005` | `educ_rais` |

**Uso no projeto:** validação cruzada dos gaps salariais estimados via PNAD. A RAIS cobre apenas o setor formal, portanto os gaps tendem a ser menores que na PNAD (que inclui informal).

---

## 10. Decisões metodológicas críticas

### 10.1 Por que HLM e não apenas OLS?

O ICC (Intraclass Correlation Coefficient) do modelo nulo (M0) é 9,8% — quase 10% da variância de log-renda é explicada pelo estado de residência, violando a premissa de independência do OLS. O HLM estima corretamente os erros-padrão considerando a estrutura hierárquica, evitando subestimação dos SE e inflação falsa de significância.

O OLS com efeitos fixos de UF é reportado como robustez — seus coeficientes convergem com o HLM dentro de ±0,003 log-pontos, validando os resultados.

### 10.2 Variável dependente: VD4020 vs. VD4016

`VD4020` (rendimento efetivo de todos os trabalhos) foi escolhido sobre `VD4016` (habitual do trabalho principal) porque:
1. Captura múltiplos empregos — mais frequentes entre negros como estratégia de sobrevivência
2. Reflete renda efetiva do mês de referência, mais próxima da realidade material

### 10.3 Agrupamento Preto+Pardo (`negro`)

Seguimos o padrão da literatura sociológica brasileira (Hasenbalg, 1979; IPEA, 2021) e do IBGE para análises de desigualdade racial: a categoria "negro" engloba Pretos (V2010=2) e Pardos (V2010=4). Amarelos e Indígenas são excluídos por tamanho amostral insuficiente para inferência em subgrupos regionais (< 1% da amostra).

### 10.4 Mediação UF = 0%

O achado de que M2 e M3 têm `β_negro` idêntico (-0,1020) — UF não agrega mediação após controle de UPA — é substantivamente relevante: a desigualdade racial opera primariamente na escala do **bairro**, não do estado. A política pública eficaz deve ser dirigida ao nível local (habitação, segregação residencial), não apenas ao nível estadual.

### 10.5 Robustez: ΔR² vs. Δβ_negro

A adição de `log_horas`, `urbano` e `C(Ano)` ao modelo base aumentou o R² em +14,2pp (de ~36% para ~50%). Porém, `β_negro` mudou apenas +0,003 log-pontos — o gap racial **não é um confound** de horas trabalhadas, urbanização ou ciclo econômico. Este é o argumento central de robustez do TCC.

---

## 11. Reprodução do ambiente

### Dependências Python

```bash
pip install pandas numpy scipy statsmodels matplotlib scikit-learn \
            pyarrow basedosdados google-cloud-bigquery mlflow tqdm
```

### Sequência de execução completa

```bash
# 1. Ingestão PNAD (requer acesso FTP IBGE)
python run_features_completo.py

# 2. Feature engineering (reconstrução de features.parquet)
python run_feature_engineering.py

# 3. Ingestão ENEM (requer projeto GCP com billing)
python run_ingestion_enem.py --project SEU_PROJETO_GCP

# 4. Ingestão RAIS (requer projeto GCP com billing)
python run_ingestion_rais.py --project SEU_PROJETO_GCP

# 5. Modelos HLM principais
python run_hlm_serie_completa.py

# 6. Análises complementares
python run_analise_retornos_raciais.py
python run_analise_regional.py
python run_analise_enem_contextual.py
```

### Estrutura de diretórios

```
ProjetoRacismoPNAD/
├── data/
│   ├── raw/pnad/          # Parquets trimestrais originais
│   ├── processed/
│   │   └── features.parquet   # Dataset analítico consolidado
│   └── external/
│       ├── enem_gap_uf.parquet
│       └── rais_processada.parquet
├── src/                   # Módulos Python do projeto
├── outputs/
│   ├── figures/           # Gráficos PNG (150 dpi)
│   └── tables/            # Tabelas CSV + LaTeX
├── logs/                  # Logs de execução por script
└── relatorio_tcc.tex      # Relatório LaTeX principal
```

### Verificação de integridade do dataset analítico

```python
import pandas as pd
df = pd.read_parquet("data/processed/features.parquet",
                     columns=["Ano","negro","log_renda","log_horas","urbano"])
assert df.shape[0] == 15_941_675, "N total incorreto"
assert set(df["Ano"].unique()) == set(range(2016, 2026)), "Anos incompletos"
assert "log_horas" in df.columns and "urbano" in df.columns, "Features ausentes"
print("Integridade OK:", df.shape)
```

---

## Referências metodológicas

- Blinder, A. S. (1973). Wage Discrimination: Reduced Form and Structural Estimates. *Journal of Human Resources*, 8(4), 436-455.
- Botelho, F., Madeira, R. A., & Rangel, M. A. (2015). Racial discrimination in grading: Evidence from Brazil. *American Economic Journal: Applied Economics*, 7(4), 37-52.
- Carneiro, P., Heckman, J. J., & Masterov, D. V. (2005). Labor market discrimination and racial differences in premarket factors. *Journal of Law and Economics*, 48(1), 1-39.
- Darity, W. A., & Mason, P. L. (1998). Evidence on discrimination in employment. *Journal of Economic Perspectives*, 12(2), 63-90.
- Hasenbalg, C. (1979). *Discriminação e Desigualdades Raciais no Brasil*. Graal.
- IBGE. (2023). *PNAD Contínua — Notas Metodológicas*. Rio de Janeiro: IBGE.
- Mincer, J. (1974). *Schooling, Experience, and Earnings*. NBER.
- Oaxaca, R. (1973). Male-Female Wage Differentials in Urban Labor Markets. *International Economic Review*, 14(3), 693-709.
- Raudenbush, S. W., & Bryk, A. S. (2002). *Hierarchical Linear Models* (2nd ed.). Sage.
- Reardon, S. F., & Bischoff, K. (2011). Income Inequality and Income Segregation. *American Journal of Sociology*, 116(4), 1092-1153.
- Sampson, R. J., Raudenbush, S. W., & Earls, F. (1997). Neighborhoods and violent crime. *Science*, 277, 918-924.
- Wilson, W. J. (1987). *The Truly Disadvantaged*. University of Chicago Press.
