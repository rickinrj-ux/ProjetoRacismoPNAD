"""
ingestion_rais.py
=================
Ingestão e limpeza dos microdados RAIS via basedosdados (BigQuery).

Fonte: basedosdados.br_me_rais.microdados_vinculos
       Dados originais do MTE, harmonizados pela equipe do basedosdados.
       Cota gratuita BigQuery: 1 TB/mês de dados lidos.

Harmoniza as variáveis RAIS com as definições da PNAD Contínua usadas em
feature_engineering.py, gerando parquet pronto para run_validacao.py.

Período coberto: 2016-2024 (espelho da PNAD Contínua).
    RAIS 2025 ainda não divulgada (defasagem ~12 meses).

Pré-requisitos:
    1. Conta Google Cloud com projeto criado (gratuito):
       https://console.cloud.google.com/
    2. BigQuery API habilitada no projeto.
    3. Autenticação local:
       ! gcloud auth application-default login
       (instale gcloud SDK: https://cloud.google.com/sdk/docs/install)

Uso:
    python run_ingestion_rais.py --project seu-projeto-gcp
    python run_ingestion_rais.py --project seu-projeto-gcp --anos 2019 2020 2021 2022
    python run_ingestion_rais.py --project seu-projeto-gcp --ufs SP RJ MG

Referências:
    basedosdados.org/dataset/br-me-rais
    MTE. Dicionário de Variáveis RAIS — Vínculos (2016+). Brasília, 2024.
    Raca/Cor RAIS: 1=Indigena 2=Branca 4=Preta 6=Amarela 8=Parda 9=N.I.
    Grau Instrucao: 1(Analfabeto) ... 11(Doutorado)
    Salario minimo: 2016=R$880 -> 2024=R$1.412
"""

import logging
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

OUT_DIR = Path("data/external")

# ── Constantes de mapeamento ───────────────────────────────────────────────────

# RAIS Raca Cor → negro (espelho PNAD: Preto + Pardo)
RAIS_NEGRO  = {4, 8}   # 4=Preta, 8=Parda
RAIS_BRANCO = {2}      # 2=Branca

# RAIS Grau Instrucao apos 2005 (1-11) → educ_ord (0-7, escala PNAD)
RAIS_EDUC_ORD = {
    1: 0,   # Analfabeto              → sem_instrucao
    2: 1,   # Ate 5a Incompleto       → fund_incompleto
    3: 2,   # 5a Completo Fundamental → fund_completo
    4: 1,   # 6a a 9a Fundamental     → fund_incompleto
    5: 2,   # Fundamental Completo    → fund_completo
    6: 3,   # Medio Incompleto        → medio_incompleto
    7: 4,   # Medio Completo          → medio_completo
    8: 5,   # Superior Incompleto     → superior_incompleto
    9: 6,   # Superior Completo       → superior_completo
    10: 7,  # Mestrado                → pos_graduacao
    11: 7,  # Doutorado               → pos_graduacao
}

# Salario minimo mensal nominal por ano (Decreto presidencial)
SALARIO_MINIMO = {
    2016: 880,  2017: 937,  2018: 954,  2019: 998,
    2020: 1045, 2021: 1100, 2022: 1212, 2023: 1320,
    2024: 1412, 2025: 1518,
}

# Anos disponiveis no basedosdados (RAIS tem defasagem de ~1 ano)
ANOS_DISPONIVEIS = list(range(2016, 2024))  # 2016-2023 confirmados

# SQL base — colunas minimas para harmonizacao com PNAD
_SQL_TEMPLATE = """
SELECT
    ano,
    sigla_uf,
    raca_cor,
    grau_instrucao_apos_2005,
    sexo,
    idade,
    valor_remuneracao_dezembro,
    valor_remuneracao_media,
    valor_remuneracao_dezembro_sm,
    quantidade_horas_contratadas,
    natureza_juridica,
    cbo_2002,
    cnae_2_subclasse,
    tempo_emprego
FROM `basedosdados.br_me_rais.microdados_vinculos`
WHERE ano = {ano}
  AND vinculo_ativo_3112 = '1'
  AND SAFE_CAST(raca_cor AS INT64) IN (2, 4, 8)
  AND valor_remuneracao_dezembro > 0
{filtro_uf}
"""


# ── Consulta BigQuery via basedosdados ────────────────────────────────────────

def _query_ano(ano: int, project_id: str,
               ufs: Optional[list[str]] = None,
               sample_pct: Optional[float] = None) -> pd.DataFrame:
    """
    Consulta um ano da RAIS no basedosdados.

    Parameters
    ----------
    ano        : ano de referência (2016-2023)
    project_id : ID do projeto GCP para faturamento BigQuery
    ufs        : lista de siglas UF para filtrar (None = todas)
    sample_pct : percentual de amostragem 0-100 via TABLESAMPLE (None = tudo)
    """
    try:
        import basedosdados as bd
    except ImportError:
        raise ImportError(
            "Instale o pacote: pip install basedosdados\n"
            "Depois autentique: gcloud auth application-default login"
        )

    filtro_uf = ""
    if ufs:
        siglas = ", ".join(f"'{u.upper()}'" for u in ufs)
        filtro_uf = f"  AND sigla_uf IN ({siglas})"

    sql = _SQL_TEMPLATE.format(ano=ano, filtro_uf=filtro_uf)

    # TABLESAMPLE reduz bytes lidos e custo (disponivel no BigQuery)
    if sample_pct and sample_pct < 100:
        sql = sql.replace(
            "`basedosdados.br_me_rais.microdados_vinculos`",
            f"`basedosdados.br_me_rais.microdados_vinculos` TABLESAMPLE SYSTEM ({sample_pct} PERCENT)"
        )

    logger.info(f"  Consultando BigQuery: ano={ano} | UFs={ufs or 'todas'}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = bd.read_sql(sql, billing_project_id=project_id)

    logger.info(f"  Retornado: {len(df):,} vinculos ativos")
    return df


# ── Harmonizacao com PNAD ─────────────────────────────────────────────────────

def harmonizar_rais(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma variaveis RAIS (basedosdados) para nomenclatura PNAD.

    Variaveis produzidas:
        negro, sexo_fem, idade_c, idade_sq,
        educ_ord, educ_medio_completo, educ_superior_completo, educ_pos_graduacao,
        log_renda, emprego_formal, setor_publico,
        horas_c, UF_str, ocp_grupo_cbo, Ano, fonte
    """
    out = pd.DataFrame()
    out["Ano"]   = df_raw["ano"].astype(int)
    out["fonte"] = "RAIS"

    # ── Raca ─────────────────────────────────────────────────────────────────
    raca = pd.to_numeric(df_raw["raca_cor"], errors="coerce")
    out["negro"] = np.nan
    out.loc[raca.isin(RAIS_NEGRO),  "negro"] = 1.0
    out.loc[raca.isin(RAIS_BRANCO), "negro"] = 0.0

    # ── Sexo ─────────────────────────────────────────────────────────────────
    # RAIS basedosdados: 1=Masculino, 3=Feminino
    out["sexo_fem"] = (
        pd.to_numeric(df_raw["sexo"], errors="coerce") == 3
    ).astype("int8")

    # ── Idade ────────────────────────────────────────────────────────────────
    idade = pd.to_numeric(df_raw["idade"], errors="coerce")
    idade = idade.where(idade.between(14, 80))
    out["idade_c"]  = idade - idade.mean()
    out["idade_sq"] = out["idade_c"] ** 2

    # ── Educacao ─────────────────────────────────────────────────────────────
    grau = pd.to_numeric(df_raw["grau_instrucao_apos_2005"], errors="coerce")
    out["educ_ord"]               = grau.map(RAIS_EDUC_ORD).astype("float32")
    out["educ_medio_completo"]    = (grau >= 7).astype("int8")
    out["educ_superior_completo"] = (grau >= 9).astype("int8")
    out["educ_pos_graduacao"]     = (grau >= 10).astype("int8")

    # ── Salario → log_renda ──────────────────────────────────────────────────
    # Prioridade: dezembro nominal > media nominal > dezembro em SM * SM_ano
    sal = pd.to_numeric(df_raw.get("valor_remuneracao_dezembro"), errors="coerce")
    if sal.isna().mean() > 0.5:
        sal = pd.to_numeric(df_raw.get("valor_remuneracao_media"), errors="coerce")
    if sal.isna().mean() > 0.5 and "valor_remuneracao_dezembro_sm" in df_raw.columns:
        ano_ref = int(out["Ano"].iloc[0])
        sm = SALARIO_MINIMO.get(ano_ref, 1100)
        sal = pd.to_numeric(df_raw["valor_remuneracao_dezembro_sm"], errors="coerce") * sm

    sal = sal.where(sal > 0)
    p01, p99 = sal.quantile(0.01), sal.quantile(0.99)
    sal = sal.clip(p01, p99)
    out["log_renda"] = np.log1p(sal)

    # ── Horas contratadas ────────────────────────────────────────────────────
    horas = pd.to_numeric(df_raw.get("quantidade_horas_contratadas"), errors="coerce")
    horas = horas.where(horas.between(1, 99))
    out["horas_c"] = horas - horas.mean()

    # ── Vinculo / setor publico ──────────────────────────────────────────────
    # Todos os registros RAIS sao empregos formais por definicao
    out["emprego_formal"] = 1
    nat = pd.to_numeric(df_raw.get("natureza_juridica"), errors="coerce")
    out["setor_publico"] = (nat < 2000).astype("int8")

    # ── Tempo de emprego (proxy de duracao para sobrevivencia) ───────────────
    if "tempo_emprego" in df_raw.columns:
        out["tempo_emprego_meses"] = pd.to_numeric(
            df_raw["tempo_emprego"], errors="coerce"
        )

    # ── UF ───────────────────────────────────────────────────────────────────
    out["UF_str"] = df_raw["sigla_uf"].astype("category")

    # ── CBO → grupo ocupacional (primeiro digito) ────────────────────────────
    if "cbo_2002" in df_raw.columns:
        out["ocp_grupo_cbo"] = (
            df_raw["cbo_2002"].astype(str).str.strip().str[:1]
        )

    # ── Limpeza final ────────────────────────────────────────────────────────
    out = out.dropna(subset=["negro", "log_renda"]).reset_index(drop=True)
    out["negro"] = out["negro"].astype("float32")

    return out


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_ingestion_rais(
    project_id: str,
    anos: Optional[list[int]] = None,
    output_path: str | Path = "data/external/rais_processada.parquet",
    ufs: Optional[list[str]] = None,
    sample_pct: Optional[float] = None,
) -> pd.DataFrame:
    """
    Consulta RAIS no basedosdados ano a ano, harmoniza e salva parquet.

    Parameters
    ----------
    project_id  : ID do projeto GCP (ex: "meu-projeto-123")
    anos        : anos a incluir (default: 2016-2023)
    output_path : caminho do parquet de saida
    ufs         : lista de UFs (None = todas)
    sample_pct  : percentual TABLESAMPLE 0-100 para testes (None = tudo)

    Returns
    -------
    DataFrame harmonizado, pronto para run_validacao.py --rais_path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if anos is None:
        anos = ANOS_DISPONIVEIS
    anos_validos = [a for a in anos if a in range(2016, 2026)]
    if not anos_validos:
        raise ValueError(f"Nenhum ano valido. Disponiveis: {ANOS_DISPONIVEIS}")

    logger.info(
        f"Iniciando ingestion RAIS via basedosdados | "
        f"projeto={project_id} | anos={anos_validos} | UFs={ufs or 'todas'}"
    )
    if sample_pct:
        logger.info(f"  Modo amostra: TABLESAMPLE {sample_pct}%")

    frames = []
    for ano in sorted(anos_validos):
        try:
            df_raw  = _query_ano(ano, project_id, ufs=ufs, sample_pct=sample_pct)
            df_harm = harmonizar_rais(df_raw)
            gap = df_harm.groupby("negro")["log_renda"].mean()
            gap_val = gap.get(1.0, np.nan) - gap.get(0.0, np.nan)
            logger.info(
                f"  {ano}: {len(df_harm):,} obs | "
                f"negro={df_harm['negro'].mean():.1%} | "
                f"gap bruto={gap_val:+.4f} ({(np.exp(gap_val)-1)*100:+.1f}%)"
            )
            frames.append(df_harm)
        except Exception as exc:
            logger.error(f"  Erro no ano {ano}: {exc}")
            continue

    if not frames:
        raise RuntimeError(
            "Nenhum dado retornado. Verifique:\n"
            "  1. gcloud auth application-default login\n"
            "  2. BigQuery API habilitada no projeto GCP\n"
            f"  3. project_id correto: '{project_id}'"
        )

    df_final = pd.concat(frames, ignore_index=True)

    # ── Estatisticas finais ───────────────────────────────────────────────────
    gap = df_final.groupby("negro")["log_renda"].mean()
    gap_val = gap.get(1.0, np.nan) - gap.get(0.0, np.nan)
    logger.info(f"RAIS final: {len(df_final):,} obs | anos={sorted(df_final['Ano'].unique().tolist())}")
    logger.info(f"  % negro  : {df_final['negro'].mean():.1%}")
    logger.info(f"  gap bruto: {gap_val:+.4f} ({(np.exp(gap_val)-1)*100:+.1f}%)")

    df_final.to_parquet(output_path, index=False)
    logger.info(f"Salvo em: {output_path}")

    return df_final
