"""
validacao_rais.py
=================
Validação cruzada do gap salarial racial entre PNAD Contínua e RAIS.

Estratégia de comparação:
    1. Modelo reduzido (sem variáveis de UPA) ajustado em PNAD e RAIS com
       a mesma especificação — compara β_negro entre as duas bases.
    2. Comparação temporal ano a ano (2016-2023, período de sobreposição).
    3. Heterogeneidade por UF: β_negro por estado em cada base.
    4. Efeito de setor (público vs. privado) dentro da RAIS.

Lógica interpretativa:
    - PNAD cobre formais + informais; RAIS cobre apenas formais com carteira.
    - β_negro consistente entre bases → discriminação presente no setor formal.
    - β_negro_RAIS < β_negro_PNAD → parte do gap ocorre via composição informal.
    - β_negro_RAIS > β_negro_PNAD → discriminação mais intensa no setor formal.

Fórmula base (sem UPA — RAIS não tem esse identificador):
    log_renda ~ negro + sexo_fem + idade_c + idade_sq
              + educ_fund_completo + educ_medio_completo
              + educ_superior_completo + educ_pos_graduacao
    groups = UF_str  (random intercept por estado)

Referências:
    Blinder, A. S. (1973). Wage Discrimination: Reduced Form and Structural
        Estimates. Journal of Human Resources, 8(4), 436-455.
    Oaxaca, R. (1973). Male-Female Wage Differentials in Urban Labor Markets.
        International Economic Review, 14(3), 693-709.
    Card, D. (1999). The Causal Effect of Education on Earnings. In O.
        Ashenfelter & D. Card (Eds.), Handbook of Labor Economics, Vol. 3A.
"""

import logging
import warnings
from pathlib import Path
from typing import Dict, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

logger = logging.getLogger(__name__)

ROOT          = Path(__file__).parent.parent
FEATURES_PATH = ROOT / "data" / "processed" / "features.parquet"
RAIS_DEFAULT  = ROOT / "data" / "external" / "rais_processada.parquet"
OUT_FIG       = ROOT / "outputs" / "figures"
OUT_TAB       = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

# Fórmula comparable entre PNAD e RAIS (sem variáveis UPA)
FORMULA_BASE = (
    "log_renda ~ negro + sexo_fem + idade_c + idade_sq"
    " + educ_fund_completo + educ_medio_completo"
    " + educ_superior_completo + educ_pos_graduacao"
)

VARS_MODELO = [
    "log_renda", "negro", "sexo_fem", "idade_c", "idade_sq",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
    "UF_str",
]

ANOS_OVERLAP = list(range(2016, 2026))  # 2016-2025 (espelho PNAD; anos RAIS ausentes são ignorados automaticamente)


# ── Carregamento ───────────────────────────────────────────────────────────────

def _prep_comum(df: pd.DataFrame, fonte: str) -> pd.DataFrame:
    """Aplica filtros e tipagens comuns às duas bases."""
    df = df[df["log_renda"].notna() & (df["log_renda"] > 0)].copy()
    df = df.dropna(subset=[c for c in VARS_MODELO if c != "UF_str"]).reset_index(drop=True)
    df["fonte"]   = fonte
    df["log_renda"] = df["log_renda"].astype(float)
    if "UF_str" not in df.columns and "UF" in df.columns:
        df["UF_str"] = df["UF"].astype(str)
    return df


def _educ_fund_de_ord(df: pd.DataFrame) -> pd.DataFrame:
    """Deriva educ_fund_completo a partir de educ_ord (escala RAIS→PNAD)."""
    if "educ_fund_completo" not in df.columns:
        if "educ_ord" in df.columns:
            df["educ_fund_completo"] = (df["educ_ord"] >= 2).astype("int8")
        else:
            df["educ_fund_completo"] = 0
    return df


def carregar_pnad(sample_frac: Optional[float] = None,
                  anos: Optional[list] = None) -> pd.DataFrame:
    """
    Carrega features PNAD e reduz ao período de sobreposição com a RAIS.

    Mantém formais e informais (universo completo da PNAD) para comparação.
    """
    df = pd.read_parquet(FEATURES_PATH)

    if anos is not None:
        df = df[df["Ano"].isin(anos)].copy()
    elif "Ano" in df.columns:
        df = df[df["Ano"].isin(ANOS_OVERLAP)].copy()

    df = _prep_comum(df, "PNAD")

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    logger.info(
        f"PNAD carregada: {len(df):,} obs | "
        f"anos={sorted(df['Ano'].unique().tolist()) if 'Ano' in df.columns else 'N/A'}"
    )
    return df


def carregar_rais(rais_path: Optional[str | Path] = None,
                  sample_frac: Optional[float] = None,
                  anos: Optional[list] = None) -> pd.DataFrame:
    """
    Carrega RAIS harmonizada (parquet gerado por ingestion_rais.py).

    Parameters
    ----------
    rais_path   : path do parquet (default: data/external/rais_processada.parquet)
    sample_frac : fração de amostragem para testes
    anos        : lista de anos a filtrar (None = todos disponíveis)
    """
    path = Path(rais_path) if rais_path else RAIS_DEFAULT
    if not path.exists():
        raise FileNotFoundError(
            f"RAIS não encontrada em: {path}\n"
            "Execute primeiro: python run_ingestion_rais.py --project <seu-projeto-gcp>"
        )

    df = pd.read_parquet(path)
    df = _educ_fund_de_ord(df)

    if anos is not None:
        df = df[df["Ano"].isin(anos)].copy()
    elif "Ano" in df.columns:
        df = df[df["Ano"].isin(ANOS_OVERLAP)].copy()

    df = _prep_comum(df, "RAIS")

    if sample_frac:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)

    logger.info(
        f"RAIS carregada: {len(df):,} obs | "
        f"anos={sorted(df['Ano'].unique().tolist()) if 'Ano' in df.columns else 'N/A'}"
    )
    return df


# ── Modelagem ─────────────────────────────────────────────────────────────────

def _ajustar_hlm_uf(df: pd.DataFrame, label: str,
                    formula: str = FORMULA_BASE) -> Optional[Dict]:
    """HLM com random intercept por UF (sem nível UPA — comparável entre bases)."""
    n_ufs = df["UF_str"].nunique() if "UF_str" in df.columns else 0
    if len(df) < 300 or n_ufs < 2:
        logger.warning(f"{label}: amostra insuficiente (n={len(df)}, UFs={n_ufs})")
        return None

    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("ignore")
            model  = smf.mixedlm(formula, data=df, groups=df["UF_str"])
            result = model.fit(method="powell", maxiter=400, reml=True)

        b  = result.params.get("negro", np.nan)
        se = result.bse.get("negro", np.nan)
        pv = result.pvalues.get("negro", np.nan)

        try:
            var_uf = float(result.cov_re.iloc[0, 0]) if result.cov_re.shape[0] > 0 else 0.0
        except Exception:
            var_uf = 0.0
        var_res = float(result.scale)
        icc_uf  = var_uf / (var_uf + var_res) if (var_uf + var_res) > 0 else 0.0

        sig = "***" if pv < 0.001 else ("**" if pv < 0.01 else ("*" if pv < 0.05 else ""))
        logger.info(
            f"  {label}: β_negro={b:.4f}{sig}  gap={((np.exp(b)-1)*100):.1f}%"
            f"  ICC_UF={icc_uf:.3f}  n={len(df):,}"
        )
        return {
            "label":      label,
            "n_obs":      len(df),
            "n_ufs":      n_ufs,
            "beta_negro": b,
            "se_negro":   se,
            "pval":       pv,
            "gap_pct":    (np.exp(b) - 1) * 100,
            "icc_uf":     icc_uf,
        }
    except Exception as exc:
        logger.warning(f"{label}: falha HLM — {exc}")
        return None


# ── Comparação principal PNAD × RAIS ─────────────────────────────────────────

def comparar_pnad_rais(df_pnad: pd.DataFrame,
                       df_rais: pd.DataFrame) -> pd.DataFrame:
    """
    Estima β_negro na mesma especificação para PNAD (all) e RAIS (formal).

    Também estima:
        - PNAD restrito a formais (emprego_formal == 1) se coluna disponível
        - RAIS setor privado (setor_publico == 0)
        - RAIS setor público (setor_publico == 1)
    """
    logger.info("── Comparação PNAD × RAIS ─────────────────────────────────")
    rows = []

    res = _ajustar_hlm_uf(df_pnad, "PNAD — todos")
    if res:
        res["base"] = "PNAD"
        res["subgrupo"] = "todos"
        rows.append(res)

    if "emprego_formal" in df_pnad.columns:
        sub = df_pnad[df_pnad["emprego_formal"] == 1]
        res = _ajustar_hlm_uf(sub, "PNAD — formais")
        if res:
            res["base"] = "PNAD"
            res["subgrupo"] = "formais"
            rows.append(res)

    res = _ajustar_hlm_uf(df_rais, "RAIS — todos")
    if res:
        res["base"] = "RAIS"
        res["subgrupo"] = "todos"
        rows.append(res)

    if "setor_publico" in df_rais.columns:
        for setor, nome in [(0, "privado"), (1, "publico")]:
            sub = df_rais[df_rais["setor_publico"] == setor]
            res = _ajustar_hlm_uf(sub, f"RAIS — {nome}")
            if res:
                res["base"] = "RAIS"
                res["subgrupo"] = nome
                rows.append(res)

    return pd.DataFrame(rows)


# ── Comparação temporal ───────────────────────────────────────────────────────

def comparar_temporal(df_pnad: pd.DataFrame,
                      df_rais: pd.DataFrame) -> pd.DataFrame:
    """
    Estima β_negro por ano em cada base — verifica se as trajetórias são paralelas.

    Trajetórias paralelas (correlação alta) validam consistência metodológica.
    Divergência em anos específicos pode indicar mudança na composição formal/informal.
    """
    if "Ano" not in df_pnad.columns or "Ano" not in df_rais.columns:
        logger.warning("Coluna 'Ano' ausente — comparação temporal impossível.")
        return pd.DataFrame()

    anos_comuns = sorted(
        set(df_pnad["Ano"].unique()) & set(df_rais["Ano"].unique())
    )
    logger.info(f"── Comparação temporal: {len(anos_comuns)} anos ──────────────────")
    rows = []

    for ano in anos_comuns:
        for df, base in [(df_pnad, "PNAD"), (df_rais, "RAIS")]:
            sub = df[df["Ano"] == ano].copy()
            res = _ajustar_hlm_uf(sub, f"{base} {ano}")
            if res:
                res["base"] = base
                res["ano"]  = ano
                rows.append(res)

    df_temp = pd.DataFrame(rows)
    if not df_temp.empty and len(df_temp["base"].unique()) == 2:
        pnad_b = df_temp[df_temp["base"] == "PNAD"]["beta_negro"].values
        rais_b = df_temp[df_temp["base"] == "RAIS"]["beta_negro"].values
        n = min(len(pnad_b), len(rais_b))
        if n >= 3:
            corr = np.corrcoef(pnad_b[:n], rais_b[:n])[0, 1]
            logger.info(f"Correlação temporal PNAD×RAIS (β_negro): r={corr:.3f}")

    return df_temp


# ── Heterogeneidade por UF ────────────────────────────────────────────────────

def comparar_por_uf(df_pnad: pd.DataFrame,
                    df_rais: pd.DataFrame) -> pd.DataFrame:
    """
    OLS com β_negro por UF em cada base — identifica estados onde as bases divergem.

    Usa OLS simples (não HLM) pois cada subgrupo tem apenas uma UF — não há
    variância entre grupos para o modelo misto estimar.
    """
    logger.info("── Comparação por UF ───────────────────────────────────────")
    rows = []
    ufs_comuns = sorted(
        set(df_pnad["UF_str"].unique()) & set(df_rais["UF_str"].unique())
    )
    logger.info(f"  UFs comuns: {len(ufs_comuns)}")

    for uf in ufs_comuns:
        for df, base in [(df_pnad, "PNAD"), (df_rais, "RAIS")]:
            sub = df[df["UF_str"] == uf].copy()
            if len(sub) < 100 or sub["negro"].nunique() < 2:
                continue
            try:
                with warnings.catch_warnings(record=True):
                    warnings.simplefilter("ignore")
                    res = smf.ols(FORMULA_BASE, data=sub).fit()
                b  = res.params.get("negro", np.nan)
                se = res.bse.get("negro", np.nan)
                pv = res.pvalues.get("negro", np.nan)
                rows.append({
                    "uf":         uf,
                    "base":       base,
                    "beta_negro": b,
                    "se_negro":   se,
                    "pval":       pv,
                    "gap_pct":    (np.exp(b) - 1) * 100,
                    "n_obs":      len(sub),
                })
            except Exception as exc:
                logger.debug(f"  UF {uf} {base}: {exc}")

    df_uf = pd.DataFrame(rows)
    if not df_uf.empty and len(df_uf["base"].unique()) == 2:
        pivot = df_uf.pivot(index="uf", columns="base", values="beta_negro").dropna()
        if len(pivot) >= 5:
            corr = pivot.corr().iloc[0, 1]
            logger.info(f"  Correlação β_negro por UF (PNAD×RAIS): r={corr:.3f}")
    return df_uf


# ── Visualizações ─────────────────────────────────────────────────────────────

def plotar_comparacao_geral(df_comp: pd.DataFrame) -> None:
    """Dot-plot com IC95% de β_negro por base/subgrupo."""
    if df_comp.empty:
        return

    fig, ax = plt.subplots(figsize=(8, max(4, len(df_comp) * 0.7)))
    cores = {"PNAD": "#2980b9", "RAIS": "#c0392b"}

    for i, row in df_comp.reset_index(drop=True).iterrows():
        ci = 1.96 * row["se_negro"]
        cor = cores.get(row["base"], "#555555")
        ax.errorbar(
            row["beta_negro"], i,
            xerr=ci, fmt="o", color=cor,
            markersize=8, linewidth=1.5, capsize=4,
        )
        ax.text(
            row["beta_negro"] + ci + 0.002, i,
            f"{(np.exp(row['beta_negro'])-1)*100:.1f}%",
            va="center", fontsize=8, color=cor,
        )

    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_yticks(range(len(df_comp)))
    ax.set_yticklabels(df_comp["label"].tolist(), fontsize=9)
    ax.set_xlabel("β_negro (log-renda) · IC 95%", fontsize=10)
    ax.set_title(
        "Comparação do Gap Salarial Racial\nPNAD Contínua × RAIS",
        fontsize=11,
    )
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=c, marker="o", linestyle="", label=b)
               for b, c in cores.items()]
    ax.legend(handles=handles, fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "rais_comparacao_geral.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: rais_comparacao_geral.png")


def plotar_comparacao_temporal(df_temp: pd.DataFrame) -> None:
    """Série temporal de β_negro PNAD vs. RAIS com IC95%."""
    if df_temp.empty or "ano" not in df_temp.columns:
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    cores   = {"PNAD": "#2980b9", "RAIS": "#c0392b"}
    estilos = {"PNAD": "o-", "RAIS": "s--"}

    for base, grp in df_temp.groupby("base"):
        grp = grp.sort_values("ano")
        cor = cores.get(base, "#555555")
        ax.plot(grp["ano"], grp["beta_negro"],
                estilos.get(base, "o-"), color=cor,
                linewidth=2, markersize=7, label=base)
        ax.fill_between(
            grp["ano"],
            grp["beta_negro"] - 1.96 * grp["se_negro"],
            grp["beta_negro"] + 1.96 * grp["se_negro"],
            color=cor, alpha=0.12,
        )

    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xlabel("Ano", fontsize=11)
    ax.set_ylabel("β_negro (log-renda)", fontsize=11)
    ax.set_title(
        "Trajetória Temporal do Gap Racial\nPNAD Contínua vs. RAIS · IC 95%",
        fontsize=11,
    )
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "rais_comparacao_temporal.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: rais_comparacao_temporal.png")


def plotar_comparacao_uf(df_uf: pd.DataFrame) -> None:
    """Scatter PNAD × RAIS de β_negro por UF com linha de 45°."""
    if df_uf.empty or "base" not in df_uf.columns:
        return

    pivot = df_uf.pivot_table(
        index="uf", columns="base", values="beta_negro"
    ).dropna()
    if pivot.shape[1] < 2 or len(pivot) < 5:
        return

    pnad_col = "PNAD" if "PNAD" in pivot.columns else pivot.columns[0]
    rais_col = "RAIS" if "RAIS" in pivot.columns else pivot.columns[1]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(pivot[pnad_col], pivot[rais_col],
               color="#555555", s=60, zorder=3)
    for uf, row in pivot.iterrows():
        ax.annotate(str(uf), (row[pnad_col], row[rais_col]),
                    fontsize=7, ha="left", va="bottom",
                    xytext=(3, 3), textcoords="offset points")

    lim = [
        min(pivot[pnad_col].min(), pivot[rais_col].min()) - 0.01,
        max(pivot[pnad_col].max(), pivot[rais_col].max()) + 0.01,
    ]
    ax.plot(lim, lim, "k--", linewidth=1, label="Linha 45°")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("β_negro PNAD", fontsize=11)
    ax.set_ylabel("β_negro RAIS", fontsize=11)
    ax.set_title(
        "Gap Racial por UF: PNAD × RAIS\n"
        "(pontos abaixo da 45° = gap menor no setor formal)",
        fontsize=10,
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(OUT_FIG / "rais_scatter_uf.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: rais_scatter_uf.png")


# ── LaTeX ──────────────────────────────────────────────────────────────────────

def _gerar_latex_comparacao(df_comp: pd.DataFrame) -> None:
    """Tabela LaTeX de β_negro por base/subgrupo com estrelas de significância."""
    if df_comp.empty:
        return

    def fmt_coef(b, se, pv):
        sig = "^{***}" if pv < 0.001 else ("^{**}" if pv < 0.01 else ("^{*}" if pv < 0.05 else ""))
        return f"${b:.4f}{sig}$ \\\\ \\small{{({se:.4f})}}"

    rows = []
    for _, r in df_comp.iterrows():
        rows.append({
            "Base/Subgrupo": r["label"],
            "$\\beta_{negro}$": f"{r['beta_negro']:.4f}",
            "SE": f"({r['se_negro']:.4f})",
            "Gap (\\%)": f"{r['gap_pct']:.1f}",
            "p-valor": f"{r['pval']:.3f}",
            "N": f"{int(r['n_obs']):,}",
        })

    df_tex = pd.DataFrame(rows)
    tex = df_tex.to_latex(
        index=False, escape=False,
        caption="Comparação do gap salarial racial entre PNAD Contínua e RAIS",
        label="tab:validacao_rais",
    )
    path = OUT_TAB / "rais_comparacao.tex"
    path.write_text(tex, encoding="utf-8")
    logger.info("LaTeX: rais_comparacao.tex")


# ── LaTeX: limitação metodológica ────────────────────────────────────────────

def _gerar_latex_limitacao(anos_rais: list, anos_pnad: list) -> None:
    """
    Escreve bloco LaTeX com a limitação da RAIS para inclusão no TCC.

    Cobre três aspectos: defasagem de divulgação, cobertura restrita ao
    setor formal e diferença conceitual entre dado administrativo e survey.
    """
    anos_rais_str  = f"{min(anos_rais)}--{max(anos_rais)}" if anos_rais else "N/D"
    anos_pnad_str  = f"{min(anos_pnad)}--{max(anos_pnad)}" if anos_pnad else "N/D"
    n_rais = len(anos_rais)
    n_pnad = len(anos_pnad)
    faltantes = sorted(set(range(2016, 2026)) - set(anos_rais))
    faltantes_str = ", ".join(str(a) for a in faltantes) if faltantes else "nenhum"

    tex = r"""\subsection*{Limitações da Validação Cruzada com a RAIS}
\label{sec:limitacoes_rais}

A validação cruzada entre a PNAD Contínua e a Relação Anual de Informações
Sociais (RAIS) está sujeita a três limitações metodológicas que devem ser
consideradas na interpretação dos resultados.

\textbf{Defasagem de divulgação.}
A RAIS é divulgada pelo Ministério do Trabalho e Emprego (MTE) com defasagem
aproximada de 12 meses em relação ao ano de referência.
""" + f"Em razão disso, os anos {faltantes_str} não estavam disponíveis no repositório " + r"""
\textit{basedosdados} na data de execução desta análise (maio de 2026).
""" + f"A comparação cobre, portanto, {n_rais} anos ({anos_rais_str}), enquanto a PNAD abrange " + f"{n_pnad} anos ({anos_pnad_str})." + r"""
Os achados referentes aos anos mais recentes da PNAD não puderam ser
confrontados com a RAIS e devem ser interpretados sem esse contraponto.

\textbf{Cobertura restrita ao setor formal.}
A RAIS registra exclusivamente vínculos empregatícios com Carteira de Trabalho
assinada (CLT) e estatutários, excluindo trabalhadores informais, autônomos e
domésticos sem registro. No período analisado, o emprego informal correspondia
a aproximadamente 40\% da força de trabalho brasileira
\citep[IBGE, PNADC]{ibge2024pnadc}.
Consistência entre os coeficientes das duas bases indica que a discriminação
salarial racial ocorre também no setor formal regulamentado; divergências
podem refletir diferenças na composição da força de trabalho formal e informal
por raça.

\textbf{Diferença conceitual entre dado administrativo e \textit{survey}.}
A PNAD Contínua é uma pesquisa amostral com expansão por pesos de calibração,
enquanto a RAIS é um censo administrativo do setor formal.
A variável de rendimento da RAIS (\textit{vl\_remun\_dezembro\_nom}) corresponde
à remuneração de competência de dezembro, ao passo que a PNAD capta o
rendimento habitualmente recebido no trabalho principal.
Diferenças de magnitude nos coeficientes entre as bases podem, portanto,
refletir parcialmente essa distinção conceitual, e não apenas heterogeneidade
entre os mercados formal e informal.
"""

    path = OUT_TAB / "rais_limitacao_tcc.tex"
    path.write_text(tex, encoding="utf-8")
    logger.info("LaTeX: rais_limitacao_tcc.tex")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def run_validacao_rais(
    rais_path: Optional[str | Path] = None,
    sample_frac: Optional[float] = None,
    anos: Optional[list] = None,
) -> Dict:
    """
    Pipeline de validação cruzada PNAD × RAIS.

    Parameters
    ----------
    rais_path   : path do parquet RAIS harmonizado (ingestion_rais.py)
    sample_frac : fração de amostragem para testes (None = dados completos)
    anos        : lista de anos a usar (None = todos disponíveis em comum)

    Returns
    -------
    dict com chaves: 'comparacao', 'temporal', 'por_uf'
    """
    # ── Carregamento ──────────────────────────────────────────────────────────
    df_pnad = carregar_pnad(sample_frac=sample_frac, anos=anos)
    df_rais = carregar_rais(rais_path=rais_path, sample_frac=sample_frac, anos=anos)

    # ── Limitação metodológica (LaTeX para TCC) ───────────────────────────────
    anos_rais_disp = sorted(df_rais["Ano"].unique().tolist()) if "Ano" in df_rais.columns else []
    anos_pnad_disp = sorted(df_pnad["Ano"].unique().tolist()) if "Ano" in df_pnad.columns else []
    _gerar_latex_limitacao(anos_rais_disp, anos_pnad_disp)

    # ── Análises ──────────────────────────────────────────────────────────────
    logger.info("Iniciando comparação geral PNAD × RAIS...")
    df_comp = comparar_pnad_rais(df_pnad, df_rais)
    if not df_comp.empty:
        df_comp.to_csv(OUT_TAB / "rais_comparacao.csv", index=False)
        _gerar_latex_comparacao(df_comp)
        plotar_comparacao_geral(df_comp)

    logger.info("Iniciando comparação temporal...")
    df_temp = comparar_temporal(df_pnad, df_rais)
    if not df_temp.empty:
        df_temp.to_csv(OUT_TAB / "rais_comparacao_temporal.csv", index=False)
        plotar_comparacao_temporal(df_temp)

    logger.info("Iniciando comparação por UF...")
    df_uf = comparar_por_uf(df_pnad, df_rais)
    if not df_uf.empty:
        df_uf.to_csv(OUT_TAB / "rais_comparacao_uf.csv", index=False)
        plotar_comparacao_uf(df_uf)

    # ── Sumário ───────────────────────────────────────────────────────────────
    print("\n── SUMÁRIO: Validação Cruzada PNAD × RAIS ──")
    if not df_comp.empty:
        for _, r in df_comp.iterrows():
            sig = "***" if r["pval"] < 0.001 else ("**" if r["pval"] < 0.01 else "*")
            print(
                f"  {r['label']:<28} β={r['beta_negro']:+.4f}{sig}"
                f"  gap={r['gap_pct']:+.1f}%  n={int(r['n_obs']):,}"
            )

    if not df_temp.empty and "ano" in df_temp.columns:
        pnad_t = df_temp[df_temp["base"] == "PNAD"]
        rais_t = df_temp[df_temp["base"] == "RAIS"]
        print(f"\n  Temporal PNAD: β médio={pnad_t['beta_negro'].mean():.4f}"
              f"  range=[{pnad_t['beta_negro'].min():.4f}, {pnad_t['beta_negro'].max():.4f}]")
        print(f"  Temporal RAIS: β médio={rais_t['beta_negro'].mean():.4f}"
              f"  range=[{rais_t['beta_negro'].min():.4f}, {rais_t['beta_negro'].max():.4f}]")

    if not df_uf.empty:
        pivot = df_uf.pivot_table(index="uf", columns="base", values="beta_negro").dropna()
        if "PNAD" in pivot.columns and "RAIS" in pivot.columns and len(pivot) >= 5:
            corr = pivot[["PNAD", "RAIS"]].corr().iloc[0, 1]
            print(f"\n  Correlação β_negro por UF (PNAD×RAIS): r={corr:.3f}")

    print(f"\n  Outputs: outputs/tables/rais_*.csv|.tex")
    print(f"           outputs/figures/rais_*.png")

    return {
        "comparacao": df_comp,
        "temporal":   df_temp,
        "por_uf":     df_uf,
    }
