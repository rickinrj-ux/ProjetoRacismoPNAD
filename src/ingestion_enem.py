"""
ingestion_enem.py
=================
Computa o gap racial de desempenho no ENEM por UF e ano via basedosdados.

O gap é usado como preditor contextual de Nível 3 no HLM estendido —
NÃO como medida direta de discriminação de avaliadores. Representa a
desigualdade educacional racial acumulada ao nível estadual, consistente
com Botelho, Madeira & Rangel (2015) como mecanismo contribuinte, mas
sem inferência causal direta sobre o comportamento dos avaliadores.

Interpretação do gap_enem_uf:
    gap_enem = média_branco − média_negro (escala 0-1000)
    Valores positivos → brancos com desempenho médio superior.
    Variação entre UFs reflete combinação de:
        - Segregação escolar (escolas de menor qualidade nas periferias)
        - Desigualdade socioeconômica estrutural correlacionada com raça
        - Potencialmente: viés de avaliação (Botelho et al., 2015)
    Esses canais NÃO são separáveis com dados agregados por UF —
    a variável é tratada como proxy de desigualdade educacional racial
    contextual, não de discriminação de avaliadores especificamente.

Score composto: média das 4 áreas objetivas + redação (escala 0-1000).
Período: 2016-2023 (sobreposição com PNAD e RAIS disponíveis).

Referência:
    Botelho, F., Madeira, R. A., & Rangel, M. A. (2015). Racial
    discrimination in grading: Evidence from Brazil.
    American Economic Journal: Applied Economics, 7(4), 37-52.
"""

import logging
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

OUT_DIR = Path("data/external")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# cor_raca no basedosdados ENEM: STRING com valores numéricos
ENEM_NEGRO  = ("'2'", "'3'")   # Preta (2) + Parda (3)
ENEM_BRANCO = ("'1'",)         # Branca (1)

# Mapeamento sigla_uf → código numérico IBGE (padrão PNAD/RAIS)
UF_SIGLA_PARA_CODIGO = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35,
    "PR": 41, "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

# Score composto: média das 5 provas (4 objetivas + redação), escala 0-1000
_SCORE_EXPR = """(
    nota_ciencias_natureza +
    nota_ciencias_humanas  +
    nota_linguagens_codigos +
    nota_matematica        +
    nota_redacao
) / 5.0"""

_SQL_GAP = """
SELECT
    ano,
    sigla_uf_prova                  AS sigla_uf,
    CASE
        WHEN cor_raca IN ('2', '3') THEN 'negro'
        WHEN cor_raca = '1'         THEN 'branco'
    END                             AS grupo,
    AVG({score})                    AS nota_media,
    COUNT(*)                        AS n_candidatos
FROM `basedosdados.br_inep_enem.microdados`
WHERE ano BETWEEN {ano_ini} AND {ano_fim}
  AND cor_raca IN ('1', '2', '3')
  AND sigla_uf_prova IS NOT NULL
  AND nota_ciencias_natureza IS NOT NULL
  AND nota_ciencias_humanas  IS NOT NULL
  AND nota_linguagens_codigos IS NOT NULL
  AND nota_matematica         IS NOT NULL
  AND nota_redacao            IS NOT NULL
  AND presenca_ciencias_natureza = '1'
  AND presenca_matematica        = '1'
  AND presenca_redacao           = '1'
GROUP BY 1, 2, 3
""".format(score=_SCORE_EXPR, ano_ini="{ano_ini}", ano_fim="{ano_fim}")


def _query_gap_bruto(project_id: str,
                     ano_ini: int = 2016,
                     ano_fim: int = 2023) -> pd.DataFrame:
    """Consulta BigQuery: nota média por UF × ano × grupo racial."""
    try:
        import basedosdados as bd
    except ImportError:
        raise ImportError("pip install basedosdados")

    sql = _SQL_GAP.format(ano_ini=ano_ini, ano_fim=ano_fim)
    logger.info(f"Consultando ENEM {ano_ini}–{ano_fim} no basedosdados...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = bd.read_sql(sql, billing_project_id=project_id)
    logger.info(f"  Retornado: {len(df):,} linhas (UF × ano × grupo)")
    return df


def _computar_gap(df_bruto: pd.DataFrame) -> pd.DataFrame:
    """
    Pivota branco/negro e computa gap = média_branco − média_negro por UF/ano.

    Também z-escore o gap dentro de cada ano para uso como preditor
    contextual padronizado no HLM (comparável com os demais preditores _z).
    """
    pivot = df_bruto.pivot_table(
        index=["ano", "sigla_uf"],
        columns="grupo",
        values="nota_media",
    ).reset_index()
    pivot.columns.name = None

    if "branco" not in pivot.columns or "negro" not in pivot.columns:
        raise ValueError("Grupos 'branco' ou 'negro' ausentes após pivot.")

    pivot["gap_enem"] = pivot["branco"] - pivot["negro"]

    # Z-score por ano: padroniza variação entre UFs dentro de cada período
    pivot["gap_enem_z"] = (
        pivot.groupby("ano")["gap_enem"]
             .transform(lambda x: (x - x.mean()) / x.std())
    )

    # Código numérico IBGE para merge com features.parquet (UF numérico)
    pivot["UF_cod"] = pivot["sigla_uf"].map(UF_SIGLA_PARA_CODIGO)
    n_missing = pivot["UF_cod"].isna().sum()
    if n_missing:
        logger.warning(f"  {n_missing} UFs sem mapeamento: "
                       f"{pivot.loc[pivot['UF_cod'].isna(), 'sigla_uf'].unique()}")

    pivot = pivot.dropna(subset=["gap_enem", "UF_cod"]).reset_index(drop=True)
    pivot["UF_cod"] = pivot["UF_cod"].astype(int)

    logger.info(
        f"Gap ENEM por UF/ano: {len(pivot)} registros | "
        f"gap médio={pivot['gap_enem'].mean():.1f} pontos | "
        f"range=[{pivot['gap_enem'].min():.1f}, {pivot['gap_enem'].max():.1f}]"
    )
    return pivot[["ano", "sigla_uf", "UF_cod", "branco", "negro",
                  "gap_enem", "gap_enem_z"]]


def run_ingestion_enem(
    project_id: str,
    ano_ini: int = 2016,
    ano_fim: int = 2023,
    output_path: str | Path = "data/external/enem_gap_uf.parquet",
) -> pd.DataFrame:
    """
    Consulta ENEM, computa gap racial por UF/ano e salva parquet.

    Parameters
    ----------
    project_id  : ID do projeto GCP para faturamento BigQuery
    ano_ini     : primeiro ano do período (default 2016)
    ano_fim     : último ano do período (default 2023)
    output_path : destino do parquet

    Returns
    -------
    DataFrame com colunas: ano, sigla_uf, UF_cod, branco, negro,
                           gap_enem, gap_enem_z
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df_bruto = _query_gap_bruto(project_id, ano_ini, ano_fim)
    df_gap   = _computar_gap(df_bruto)

    df_gap.to_parquet(output_path, index=False)
    logger.info(f"Salvo em: {output_path}")

    # Sumário por macrorregião
    regioes = {
        "Norte":        [11,12,13,14,15,16,17],
        "Nordeste":     [21,22,23,24,25,26,27,28,29],
        "Sudeste":      [31,32,33,35],
        "Sul":          [41,42,43],
        "Centro-Oeste": [50,51,52,53],
    }
    df_gap["regiao"] = "Outra"
    for nome, ufs in regioes.items():
        df_gap.loc[df_gap["UF_cod"].isin(ufs), "regiao"] = nome

    resumo = (df_gap.groupby("regiao")["gap_enem"]
              .agg(["mean", "min", "max"])
              .rename(columns={"mean": "gap_médio", "min": "gap_mín", "max": "gap_máx"})
              .round(1))
    logger.info(f"\nGap ENEM por macrorregião:\n{resumo.to_string()}")

    return df_gap
