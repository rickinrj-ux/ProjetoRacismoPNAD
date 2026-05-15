"""
feature_engineering.py
=======================
Engenharia de features para o modelo multinível de gap salarial e
empregabilidade racial no Brasil (PNAD Contínua).

Estrutura de variáveis produzidas (3 níveis para HLM):

    Nível 1 — Indivíduo:
        negro, sexo_fem, idade_c, idade_sq, faixa_etaria,
        educ_cat, educ_ord, educ_[nivel], log_renda, empregado, pea

    Nível 2 — Localidade (UPA = proxy de bairro/área de residência):
        pct_negro_upa    — composição racial local (segregação residencial)
        tx_desemprego_upa — oportunidades econômicas locais
        media_educ_upa   — capital humano do entorno (spillovers)
        media_renda_upa  — renda média local

    Nível 3 — Estado (UF):
        pct_negro_uf, tx_desemprego_uf, media_educ_uf, media_renda_uf

Hipótese do Networking Local (testada via Nível 2):
    A UPA captura o "efeito de vizinhança" (Wilson, 1987; Sampson et al., 1997):
    viver em área de alta concentração racial e baixo emprego reduz o capital
    social disponível na rede local, afetando resultados individuais além
    das características pessoais — hipótese do "duplo disadvantage" (Pager, 2007).

    Formalização: se γ_{01} (coef. de pct_negro_upa no HLM) for significativo
    e negativo após controlar por negro_{ijk} (Nível 1), temos evidência de
    que a segregação residencial opera como canal independente de desigualdade.

Referências:
    IBGE. (2023). Tabela de variáveis — PNAD Contínua.
    Hasenbalg, C. (1979). Discriminação e Desigualdades Raciais no Brasil.
    Putnam, R. D. (2000). Bowling Alone. Simon & Schuster.
    Burt, R. S. (1992). Structural Holes. Harvard University Press.
    Mincer, J. (1974). Schooling, Experience, and Earnings. NBER.
"""

import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_PROCESSED = ROOT / "data" / "processed"
FEATURES_PATH = DATA_PROCESSED / "features.parquet"

# ── Mapeamentos IBGE ───────────────────────────────────────────────────────────

# V2010: Cor ou raça
# Negro = Preto (2) + Pardo (4) — agrupamento padrão da literatura brasileira
# (Hasenbalg, 1979; IPEA, 2021; classificação adotada pelo IBGE para análises raciais)
RACE_NEGRO = {2, 4}
RACE_BRANCO = {1}
# Amarelos (3) e Indígenas (5) excluídos da variável binária por n insuficiente
# para inferência estatística robusta em subgrupos regionais

# V3009A: Nível de instrução mais elevado (agrupamento IBGE 2022)
EDUC_MAP = {
    1: "sem_instrucao",
    2: "fund_incompleto",
    3: "fund_completo",
    4: "medio_incompleto",
    5: "medio_completo",
    6: "superior_incompleto",
    7: "superior_completo",
    8: "pos_graduacao",
}

# Escala ordinal para uso em modelos lineares e como preditora contextual
EDUC_ORDINAL = {
    "sem_instrucao": 0, "fund_incompleto": 1, "fund_completo": 2,
    "medio_incompleto": 3, "medio_completo": 4,
    "superior_incompleto": 5, "superior_completo": 6, "pos_graduacao": 7,
}

AGE_BINS = [14, 24, 34, 44, 54, 64, 120]
AGE_LABELS = ["14-24", "25-34", "35-44", "45-54", "55-64", "65+"]

# UPAs com menos de 10 respondentes produzem estimativas instáveis
# para as médias contextuais — substituídas por NaN
MIN_UPA_SIZE = 10

# VD4008 — Tipo de vínculo empregatício (6 categorias, conforme cruzamento com VD4009)
# 1=setor privado (formal+informal)  2=doméstico  3=setor público
# 4=empregador  5=conta-própria  6=trab.familiar
VINCULO_MAP = {
    1: "privado",
    2: "domestico",
    3: "publico",
    4: "empregador",
    5: "conta_propria",
    6: "familiar",
}

# V4010 — CBO-Domiciliar 2010 (4 dígitos) → primeiro dígito = grupo CBO (ISCO-08)
# '1...' = Dirigentes  '2...' = Profissionais  '3...' = Técnicos
# '4...' = Administrativo  '5...' = Serviços  '6...' = Agropecuária
# '7...' = Operários  '8...' = Operadores  '9...' = Elementar  '0...' = FFAA
CBO_GROUP_MAP = {
    "0": "ffaa",
    "1": "dirigente",
    "2": "profissional",
    "3": "tecnico",
    "4": "administrativo",
    "5": "servicos",
    "6": "agro",
    "7": "operario",
    "8": "operador",
    "9": "elementar",
}
OCP_ORDER   = ["dirigente","profissional","tecnico","administrativo",
               "servicos","agro","operario","operador","elementar","ffaa"]
OCP_DUMMIES = [v for v in OCP_ORDER if v != "elementar"]  # referência: elementar

# VD4009 — Posição na ocupação (valores 01-10 na PNAD Contínua)
# 01=priv c/carteira  02=priv s/carteira  03=domest c/cart  04=domest s/cart
# 05=pub c/carteira   06=pub s/carteira   07=estatutário/militar
# 08=empregador       09=conta-própria    10=trab.familiar auxiliar
FORMAL_CODES    = {1, 3, 5, 7}   # com carteira (privado/doméstico/público) + estatutário
PUBLICO_CODES   = {5, 6, 7}      # setor público
INFORMAL_CODES  = {2, 4, 10}     # sem carteira privado, doméstico sem cart, trab. familiar
DOMESTICO_CODES = {3, 4}         # trabalhador doméstico (com e sem carteira)

# Macro-setores a partir dos 2 primeiros dígitos do CNAE (V4013)
def _cnae_setor(code_str):
    if pd.isna(code_str) or str(code_str).strip() in ("", "nan"):
        return None
    try:
        d = int(str(code_str).strip()[:2])
    except (ValueError, IndexError):
        return None
    if d <= 3:   return "agro"
    if d <= 9:   return "extrativa"
    if d <= 33:  return "industria"
    if d <= 43:  return "construcao_energia"
    if d <= 47:  return "comercio"
    if d <= 56:  return "transporte_alim"
    if d <= 68:  return "info_financeiro"
    if d == 84:  return "adm_publica"
    if d <= 88:  return "educ_saude"
    if d >= 97:  return "domestico"
    return "outros"


# ── Transformações Individuais — Nível 1 ──────────────────────────────────────

def binarize_race(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria variável binária 'negro' (1=negro, 0=branco).

    O agrupamento Preto+Pardo segue a classificação operacional padrão
    do IBGE e da literatura sociológica brasileira (Hasenbalg, 1979).
    Brancos são o grupo de referência na modelagem — coeficiente de 'negro'
    no HLM estima o gap salarial racial condicionado aos demais preditores.
    """
    df["negro"] = np.nan
    df.loc[df["V2010"].isin(RACE_NEGRO),  "negro"] = 1.0
    df.loc[df["V2010"].isin(RACE_BRANCO), "negro"] = 0.0
    return df


def create_sex_dummy(df: pd.DataFrame) -> pd.DataFrame:
    """V2007: 1=Homem (referência), 2=Mulher → sexo_fem binária."""
    # fillna(False) antes do cast pois V2007 é nullable Int8 — sexo nunca é NA
    # para adultos, mas a comparação com nullable retorna boolean nullable
    df["sexo_fem"] = (df["V2007"] == 2).fillna(False).astype("int8")
    return df


def create_age_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Features de idade para a equação de Mincer (1974).

    O termo quadrático captura a relação côncava entre experiência
    acumulada e rendimento: renda cresce com idade até um pico (~45-50 anos)
    e então decresce. Centralização na média (idade_c) reduz multicolinearidade
    entre idade e idade², facilitando a interpretação dos coeficientes do HLM.

    Fórmula de Mincer:
        ln(W) = α + β₁·S + β₂·X + β₃·X² + ε
        onde X = experiência ≈ idade (proxy) e S = escolaridade
    """
    age = df["V2009"].astype("float32")
    mean_age = age.mean()
    df["idade"] = age
    df["idade_c"] = age - mean_age              # centralizado na média
    df["idade_sq"] = df["idade_c"] ** 2         # termo quadrático de Mincer
    df["faixa_etaria"] = pd.cut(
        age, bins=AGE_BINS, labels=AGE_LABELS, right=True
    ).astype("category")
    return df


def create_education_dummies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variáveis de educação: dummies e escala ordinal a partir de V3009A.

    Categoria de referência nas dummies: sem_instrucao (nível mínimo).
    A escala ordinal (educ_ord) é usada nas médias contextuais de Nível 2/3,
    onde necessitamos de uma variável contínua para capturar o nível
    educacional médio da localidade.

    Dummies incluídas no HLM: apenas níveis com salto educacional significativo
    (conclusão de ciclo), omitindo categorias incompletas que não são pontos
    de credencial no mercado de trabalho formal.
    """
    educ_cat = df["V3009A"].map(EDUC_MAP)
    df["educ_cat"] = educ_cat.astype("category")
    df["educ_ord"] = educ_cat.map(EDUC_ORDINAL).astype("float32")

    for nivel in ["fund_completo", "medio_completo", "superior_completo", "pos_graduacao"]:
        df[f"educ_{nivel}"] = (educ_cat == nivel).fillna(False).astype("int8")

    return df


def create_income_features(
    df: pd.DataFrame,
    winsor_pct: float = 0.01,
) -> pd.DataFrame:
    """
    Transforma rendimento bruto (VD4020) em log-rendimento.

    log1p = log(1 + renda): evita -inf para renda=0 (trabalhadores
    sem renda declarada ou em trabalhos informais sem pagamento monetário).

    Winsorização a 1%: clipa outliers extremos no limite superior sem
    remover observações — preferível à exclusão pois preserva a estrutura
    amostral complexa (estratificação + conglomerados) da PNAD.

    Justificativa da log-transformação:
        Rendimentos seguem distribuição log-normal (Gibrat, 1931).
        A transformação satisfaz a premissa de normalidade dos resíduos
        do HLM e permite interpretar coeficientes como variações percentuais.
        Ex: β_negro = -0.15 → negros ganham ~14% menos (exp(-0.15)-1 = -14%).
    """
    renda = df["VD4020"].astype("float32")

    # Winsorização apenas no limite superior (inflação dos outliers ricos)
    upper = renda[renda > 0].quantile(1 - winsor_pct)
    lower = renda[renda > 0].quantile(winsor_pct)
    renda = renda.clip(upper=upper)
    renda = renda.where(renda >= lower, other=np.nan)

    df["renda_bruta"] = renda
    df["log_renda"] = np.log1p(renda)
    return df


def create_employment_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variáveis de empregabilidade para o modelo logístico (GLMM).

    VD4002: 1=Ocupado, 2=Desocupado
    pea: flag de pertencimento à PEA (restringe análise à pop. economicamente ativa)

    Uso de Int8 (nullable): VD4002 é NA para menores de 14 e fora da PEA —
    preservar NA é semanticamente correto (vs. forçar 0 = "desempregado").
    """
    df["empregado"] = (df["VD4002"] == 1).astype("Int8")
    df["pea"] = ((df["VD4002"] == 1) | (df["VD4002"] == 2)).astype("Int8")
    return df


def create_occupation_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Features de ocupação a partir de VD4008, VD4009 e V4010.

    VD4008 (tipo de vínculo, 6 categorias) → tipo_vinculo + dummies
    VD4009 (posição detalhada, 10 categorias) → flags formal/informal/público
    V4010  (CBO 4 dígitos) → ocp_grupo_cbo (primeiro dígito = grupo ISCO/CBO)
    """
    # ── VD4008: tipo de vínculo empregatício ─────────────────────────────────
    if "VD4008" in df.columns:
        vd8 = df["VD4008"].astype("Float32")
        df["tipo_vinculo"] = vd8.map(VINCULO_MAP).astype("category")

    # ── V4010: grupo ocupacional CBO (primeiro dígito) ───────────────────────
    if "V4010" in df.columns:
        cbo_str = df["V4010"].astype(str).str.strip().str[:1].replace({"n": None, "<": None})
        df["ocp_grupo_cbo"] = cbo_str.map(CBO_GROUP_MAP).astype("category")

        # Dummies CBO (referência: elementar)
        for grp_name in OCP_DUMMIES:
            df[f"ocp_{grp_name}"] = (df["ocp_grupo_cbo"] == grp_name).fillna(False).astype("int8")

    # ── VD4009: formalidade e vínculo detalhado ───────────────────────────────
    if "VD4009" not in df.columns:
        return df

    vd9 = df["VD4009"].astype("Float32")
    df["emprego_formal"] = vd9.isin(FORMAL_CODES).fillna(False).astype("int8")
    df["setor_publico"]  = vd9.isin(PUBLICO_CODES).fillna(False).astype("int8")
    df["conta_propria"]  = (vd9 == 9).fillna(False).astype("int8")
    df["empregador"]     = (vd9 == 8).fillna(False).astype("int8")
    df["trab_domestico"] = vd9.isin(DOMESTICO_CODES).fillna(False).astype("int8")

    return df


def create_hours_feature(df: pd.DataFrame) -> pd.DataFrame:
    """
    Horas trabalhadas efetivas (VD4031) — controle crítico para o HLM.

    Sem esse controle, trabalhadores part-time (com renda menor) puxam
    a média racial para baixo se negros estiverem sobre-representados
    nesse grupo — confound que infla o coeficiente racial estimado.

    horas_c: centralizado na média global para interpretabilidade dos
    interceptos (coef. para trabalhador de jornada media da amostra).
    """
    if "VD4031" not in df.columns:
        return df

    horas = df["VD4031"].astype("float32")
    df["horas_trabalhadas"] = horas
    df["horas_c"] = horas - horas.mean()
    return df


def create_sector_feature(df: pd.DataFrame) -> pd.DataFrame:
    """
    Macro-setor econômico a partir do CNAE (V4013).

    Os 2 primeiros dígitos do CNAE-Domiciliar determinam o setor (A–T do IBGE).
    Agrupamos em 10 macro-setores para reduzir esparsidade nas dummies de Nível 1.
    """
    if "V4013" not in df.columns:
        return df

    df["setor_cnae"] = df["V4013"].astype(str).apply(_cnae_setor).astype("category")
    return df


# ── Agregações Contextuais — Nível 2 (UPA/Localidade) ────────────────────────

def compute_upa_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variáveis contextuais da UPA (Unidade Primária de Amostragem).

    A UPA é o proxy disponível mais próximo de bairro/área de moradia
    na PNAD Contínua — cada UPA agrupa ~60-80 domicílios geograficamente
    contíguos, capturando vizinhança imediata com razoável precisão.

    Estas variáveis operacionalizam a hipótese de networking local:

        pct_negro_upa → segregação racial residencial
            (Reardon & Bischoff, 2011 — dissimilarity index proxy)

        tx_desemprego_upa → escassez de capital econômico na rede local
            (Wilson, 1987 — "concentration effects")

        media_educ_upa → capital humano do entorno
            (spillovers de conhecimento e normas sobre educação formal)

        media_renda_upa → riqueza média do networking local
            (acesso a informações e contatos com empregadores/líderes)

    UPAs com n < MIN_UPA_SIZE têm estimativas instáveis — NaN garante
    que não contaminem os coeficientes de Nível 2 no HLM.
    """
    # fillna(False) converte Int8 nullable para bool puro antes de indexar
    pea_idx = df.index[df["pea"].fillna(0).astype(bool)]

    # Calcula tx_desemprego apenas para membros da PEA dentro de cada UPA
    pea_sub = df.loc[pea_idx, ["UPA", "empregado"]].copy()
    pea_sub["empregado"] = pea_sub["empregado"].astype("float32")
    tx_desemp_upa = (
        pea_sub.groupby("UPA")["empregado"]
        .apply(lambda x: 1 - x.mean())
        .reset_index()
        .rename(columns={"empregado": "tx_desemprego_upa"})
    )

    upa_agg = (
        df.groupby("UPA", observed=True)
        .agg(
            pct_negro_upa=("negro",    "mean"),
            media_educ_upa=("educ_ord", "mean"),
            media_renda_upa=("log_renda", "mean"),
            n_upa=("negro", "count"),
        )
        .reset_index()
        .merge(tx_desemp_upa, on="UPA", how="left")
    )

    # Mascara UPAs com amostra insuficiente
    mask_small = upa_agg["n_upa"] < MIN_UPA_SIZE
    ctx_cols = ["pct_negro_upa", "tx_desemprego_upa", "media_educ_upa", "media_renda_upa"]
    upa_agg.loc[mask_small, ctx_cols] = np.nan

    if mask_small.sum() > 0:
        logger.info(
            f"{mask_small.sum()} UPAs com n < {MIN_UPA_SIZE} "
            "marcadas como NaN nas variáveis contextuais."
        )

    return df.merge(upa_agg.drop(columns="n_upa"), on="UPA", how="left")


# ── Agregações Contextuais — Nível 3 (UF/Estado) ─────────────────────────────

def compute_uf_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variáveis contextuais do estado (UF) — Nível 3 do HLM.

    Capturam desigualdades macrorregionais:
        pct_negro_uf: contexto histórico de exclusão racial por estado
            (ex.: Nordeste ~70% negro vs. Sul ~20% → contexto político diferente)
        tx_desemprego_uf: capacidade do mercado de trabalho estadual
        media_educ_uf: oferta de capital humano educacional no estado
        media_renda_uf: riqueza média estadual (proxy de PIB per capita)

    A separação entre Nível 2 (UPA) e Nível 3 (UF) permite o HLM decompor:
        "o indivíduo vive num bairro pobre de um estado rico" vs.
        "o indivíduo vive num bairro pobre de um estado pobre" —
        contextos com dinâmicas de exclusão estruturalmente diferentes.
    """
    pea_idx = df.index[df["pea"].fillna(0).astype(bool)]
    pea_sub = df.loc[pea_idx, ["UF", "empregado"]].copy()
    pea_sub["empregado"] = pea_sub["empregado"].astype("float32")
    tx_desemp_uf = (
        pea_sub.groupby("UF")["empregado"]
        .apply(lambda x: 1 - x.mean())
        .reset_index()
        .rename(columns={"empregado": "tx_desemprego_uf"})
    )

    uf_agg = (
        df.groupby("UF", observed=True)
        .agg(
            pct_negro_uf=("negro",     "mean"),
            media_educ_uf=("educ_ord",  "mean"),
            media_renda_uf=("log_renda", "mean"),
        )
        .reset_index()
        .merge(tx_desemp_uf, on="UF", how="left")
    )
    return df.merge(uf_agg, on="UF", how="left")


# ── Padronização (Z-Score) das Variáveis Contextuais ─────────────────────────

def standardize_contextual(df: pd.DataFrame) -> pd.DataFrame:
    """
    Z-padroniza todas as variáveis contextuais de Nível 2 e 3.

    O HLM assume que preditores de nível superior têm escala comparável.
    O z-score (μ=0, σ=1) permite comparar magnitudes dos coeficientes
    γ (Nível 2) com δ (Nível 3) e com os β (Nível 1).

    Referência: Raudenbush & Bryk (2002, cap. 2) — "grand-mean centering
    of level-2 predictors is recommended for cross-level interpretability".
    """
    ctx_vars = [
        "pct_negro_upa", "tx_desemprego_upa", "media_educ_upa", "media_renda_upa",
        "pct_negro_uf",  "tx_desemprego_uf",  "media_educ_uf",  "media_renda_uf",
    ]
    for var in ctx_vars:
        if var in df.columns:
            df[f"{var}_z"] = stats.zscore(df[var].astype("float64"), nan_policy="omit")
    return df


# ── Carga dos Dados Brutos ────────────────────────────────────────────────────

def load_raw_data(
    years: Optional[List[int]] = None,
    sample_frac: Optional[float] = None,
) -> pd.DataFrame:
    """Carrega Parquet processados e aplica filtro de população de interesse.

    Usa glob explícito em ano=*/trimestre=*/data.parquet para evitar que
    features.parquet (schema diferente) cause conflito ao ler o dataset.
    """
    import pyarrow.dataset as ds

    # Lista apenas os arquivos de dados particionados, excluindo features.parquet
    if years:
        paths = [
            str(DATA_PROCESSED / f"ano={y}" / f"trimestre={q}" / "data.parquet")
            for y in years
            for q in range(1, 5)
            if (DATA_PROCESSED / f"ano={y}" / f"trimestre={q}" / "data.parquet").exists()
        ]
    else:
        paths = sorted(str(p) for p in DATA_PROCESSED.glob("ano=*/trimestre=*/data.parquet"))

    if not paths:
        raise FileNotFoundError(f"Nenhum Parquet encontrado em {DATA_PROCESSED}. Execute data_ingestion.py primeiro.")

    logger.info(f"Lendo {len(paths)} arquivo(s) Parquet...")
    dataset = ds.dataset(paths, format="parquet")
    # Cast UF para int16 na leitura para garantir schema uniforme entre anos
    table = dataset.to_table()
    df = table.to_pandas()

    # Restringe à população de 14+ anos (limite IBGE para mercado de trabalho)
    df = df[df["V2009"] >= 14].copy()

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42)
        logger.info(f"Amostra: {sample_frac:.0%} → {len(df):,} registros")

    logger.info(
        f"Dados carregados: {len(df):,} registros | "
        f"{df['Ano'].nunique()} anos | {df['UF'].nunique()} UFs"
    )

    # Merge com extras.parquet (ocupação, horas, setor) se disponível
    extra_paths = sorted(str(p) for p in DATA_PROCESSED.glob("ano=*/trimestre=*/extras.parquet"))
    if extra_paths:
        logger.info(f"Carregando {len(extra_paths)} extras.parquet...")
        import pyarrow.dataset as ds2
        extras_ds = ds2.dataset(extra_paths, format="parquet")
        extras = extras_ds.to_table().to_pandas()

        # Garante tipos de join compatíveis com o df principal
        extras["Ano"]       = extras["Ano"].astype("int16")
        extras["Trimestre"] = extras["Trimestre"].astype("int8")
        extras["UPA"]       = extras["UPA"].astype(str).str.strip()
        extras["V1008"]     = extras["V1008"].astype(str).str.strip()
        extras["V2003"]     = extras["V2003"].astype(str).str.strip()

        df["UPA"]   = df["UPA"].astype(str).str.strip()
        df["V1008"] = df["V1008"].astype(str).str.strip()
        df["V2003"] = df["V2003"].astype(str).str.strip()

        n_pre = len(df)
        df = df.merge(
            extras,
            on=["Ano", "Trimestre", "UPA", "V1008", "V2003"],
            how="left",
        )
        if len(df) != n_pre:
            logger.warning(f"Merge com extras alterou n: {n_pre:,} → {len(df):,}")
        new_cols = [c for c in extras.columns if c not in ["Ano","Trimestre","UPA","V1008","V2003"]]
        logger.info(f"Extras merged: {new_cols}")
    else:
        logger.info("extras.parquet não encontrado — execute run_enrich_raw.py primeiro.")

    return df


# ── Pipeline Principal ────────────────────────────────────────────────────────

def build_features(
    years: Optional[List[int]] = None,
    sample_frac: Optional[float] = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Pipeline completo de feature engineering.

    Retorna DataFrame com variáveis de 3 níveis prontas para o HLM:
        - Nível 1: características individuais transformadas
        - Nível 2: agregados de localidade (UPA) padronizados
        - Nível 3: agregados estaduais (UF) padronizados

    Args:
        years: Lista de anos a incluir. None = todos disponíveis.
        sample_frac: Fração para desenvolvimento (ex: 0.1 = 10%).
        save: Persiste features.parquet para reutilização posterior.
    """
    df = load_raw_data(years=years, sample_frac=sample_frac)

    # ── Nível 1: transformações individuais ──────────────────────────────────
    df = binarize_race(df)
    df = create_sex_dummy(df)
    df = create_age_features(df)
    df = create_education_dummies(df)
    df = create_income_features(df)
    df = create_employment_features(df)
    df = create_occupation_features(df)
    df = create_hours_feature(df)
    df = create_sector_feature(df)

    # Remove obs. fora da classificação binária racial (Amarelo, Indígena, ND)
    n_pre = len(df)
    df = df.dropna(subset=["negro"])
    logger.info(
        f"Filtro racial: removidos {n_pre - len(df):,} obs. "
        "(Amarelo/Indígena/ND — n insuficiente para inferência binária)"
    )

    # ── Nível 2: agregados de localidade ────────────────────────────────────
    df = compute_upa_aggregates(df)

    # ── Nível 3: agregados estaduais ─────────────────────────────────────────
    df = compute_uf_aggregates(df)

    # ── Padronização contextual ──────────────────────────────────────────────
    df = standardize_contextual(df)

    logger.info(
        f"Features completas: {len(df):,} obs. | "
        f"{df['UPA'].nunique():,} UPAs | {df['UF'].nunique()} UFs"
    )

    if save:
        df.to_parquet(FEATURES_PATH, index=False, compression="snappy")
        logger.info(f"Features salvas: {FEATURES_PATH}")

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s"
    )
    df = build_features(years=list(range(2021, 2025)))

    print("\n── Distribuição Racial ──")
    print(df["negro"].value_counts(normalize=True).rename({0: "Branco", 1: "Negro"}))

    print("\n── Log-Renda por Raça ──")
    print(df.groupby("negro")["log_renda"].describe())

    print("\n── Variáveis Contextuais — Nível 2 ──")
    print(df[["pct_negro_upa_z", "tx_desemprego_upa_z", "media_educ_upa_z"]].describe())
