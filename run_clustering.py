"""
run_clustering.py
==================
K-Means socioeconômico sobre o dataset completo PNAD 2016-2025.

OBJETIVO (TCC):
    Revelar tipologias de vulnerabilidade socioeconomica que se sobrepoem
    a fronteiras raciais — profissionais negros devem estar concentrados
    nos clusters de menor renda, emprego precario e contexto residencial
    desfavoravel (Wilson, 1987; Sampson et al., 1997).

ESTRATEGIA COMPUTACIONAL:
    MiniBatchKMeans: algoritmo incremental O(n * k * p) por iteracao.
    Escala para 15M+ obs. sem necessidade de subsample no ajuste.
    Silhouette: calculado em subsample de 100k (O(n^2) proibitivo no full).

VARIAVEIS DE CLUSTERING (12 dimensoes):
    Individuais: idade, educ_medio_completo, educ_superior_completo,
                 educ_pos_graduacao, log_renda, negro, sexo_fem, empregado
    Contexto UPA: pct_negro_upa_z, tx_desemprego_upa_z, media_educ_upa_z,
                  media_renda_upa_z
    (educ_ord removido — cobertura de apenas 31% da PEA; substituido por dummies
     com 100% de cobertura, consistente com o GLMM lme4 PEA completa)

SELECAO DE K:
    Metodo do cotovelo (inertia) + silhouette coefficient.
    Intervalo: k = 2 ... 8.
    Criterio primario: max(silhouette).
    Criterio secundario: interpretabilidade para o TCC.
"""
import sys
import logging
import time
import warnings
from pathlib import Path

sys.path.insert(0, "src")
warnings.filterwarnings("ignore", category=FutureWarning)

Path("logs").mkdir(exist_ok=True)
handlers = [
    logging.FileHandler("logs/clustering.log", encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)
OUTPUTS_FIG.mkdir(parents=True, exist_ok=True)

# ── Variaveis de Clustering ────────────────────────────────────────────────────
CLUSTER_VARS = [
    "idade",                    # individual — experiencia de vida
    "educ_medio_completo",      # individual — ensino medio completo (dummy)
    "educ_superior_completo",   # individual — ensino superior completo (dummy)
    "educ_pos_graduacao",       # individual — pos-graduacao (dummy)
    "log_renda",                # individual — rendimento
    "negro",                    # individual — raca binaria
    "sexo_fem",                 # individual — genero
    "empregado",                # individual — status de emprego
    "pct_negro_upa_z",          # contexto — composicao racial do bairro
    "tx_desemprego_upa_z",      # contexto — desemprego local
    "media_educ_upa_z",         # contexto — capital humano do entorno
    "media_renda_upa_z",        # contexto — renda media do entorno
]

K_RANGE      = range(2, 9)   # k = 2 a 8
SILH_SAMPLE  = 100_000       # subsample para silhouette (O(n^2) inviavel no full)
RANDOM_STATE = 42

# k=2 maximiza silhouette na PEA completa mas é trivialmente binário (split racial/renda).
# k=3 preserva as tipologias de vulnerabilidade interpretáveis (Wilson 1987; Sampson 1997)
# e é consistente com a narrativa do TCC. Override explícito com justificativa metodológica.
K_FINAL_OVERRIDE = 3


# ── Carregamento ───────────────────────────────────────────────────────────────

def load_data():
    logger.info(f"Carregando {FEATURES_PATH} ...")
    df = pd.read_parquet(FEATURES_PATH)
    logger.info(f"  Total bruto: {len(df):,} obs.")

    # Requer renda e todas as variaveis de clustering
    n_before = len(df)
    df = df.dropna(subset=CLUSTER_VARS).reset_index(drop=True)
    logger.info(f"  Apos dropna: {len(df):,} obs. (removidos {n_before - len(df):,})")

    # Converte para float64 para o scaler
    for col in CLUSTER_VARS:
        df[col] = df[col].astype(float)

    logger.info(
        f"Dataset para clustering: {len(df):,} obs. | "
        f"Negros: {df['negro'].mean()*100:.1f}% | "
        f"Empregados: {df['empregado'].mean()*100:.1f}%"
    )
    return df


# ── Pre-processamento ──────────────────────────────────────────────────────────

def preprocess(df):
    """StandardScaler em todas as variaveis de clustering."""
    scaler = StandardScaler()
    X = scaler.fit_transform(df[CLUSTER_VARS])
    logger.info(f"Pre-processamento: X shape = {X.shape} | dtype = {X.dtype}")
    return X, scaler


# ── Selecao de K (Elbow + Silhouette) ─────────────────────────────────────────

def select_k(X, df):
    logger.info("Selecao de K via Elbow + Silhouette ...")
    inertias     = {}
    silhouettes  = {}
    db_scores    = {}

    # Subsample fixo para silhouette — reproducivel
    rng = np.random.default_rng(RANDOM_STATE)
    idx_silh = rng.choice(len(X), size=min(SILH_SAMPLE, len(X)), replace=False)
    X_silh = X[idx_silh]

    for k in K_RANGE:
        t0 = time.time()
        km = MiniBatchKMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            batch_size=max(1024, len(X) // 100),
            n_init=5,
            max_iter=300,
        )
        labels_full = km.fit_predict(X)
        elapsed = time.time() - t0

        inertias[k]    = km.inertia_
        labels_silh    = labels_full[idx_silh]
        silhouettes[k] = silhouette_score(X_silh, labels_silh, sample_size=None)
        db_scores[k]   = davies_bouldin_score(X_silh, labels_silh)

        logger.info(
            f"  k={k}: inertia={km.inertia_:.0f} | "
            f"silhouette={silhouettes[k]:.4f} | "
            f"DB={db_scores[k]:.4f} | {elapsed:.1f}s"
        )

    best_k_silh = max(silhouettes, key=silhouettes.get)
    best_k_db   = min(db_scores, key=db_scores.get)
    logger.info(
        f"  Melhor k (silhouette): {best_k_silh} | "
        f"Melhor k (Davies-Bouldin): {best_k_db}"
    )

    # Grafico Elbow + Silhouette
    _plot_k_selection(inertias, silhouettes, db_scores, best_k_silh)

    return best_k_silh, inertias, silhouettes, db_scores


def _plot_k_selection(inertias, silhouettes, db_scores, best_k):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    ks = list(inertias.keys())

    axes[0].plot(ks, [inertias[k] for k in ks], "b-o", linewidth=2)
    axes[0].axvline(best_k, color="red", linestyle="--", alpha=0.7, label=f"k={best_k}")
    axes[0].set_xlabel("k (numero de clusters)"); axes[0].set_ylabel("Inertia (WCSS)")
    axes[0].set_title("Metodo do Cotovelo"); axes[0].legend()

    axes[1].plot(ks, [silhouettes[k] for k in ks], "g-o", linewidth=2)
    axes[1].axvline(best_k, color="red", linestyle="--", alpha=0.7, label=f"k={best_k}")
    axes[1].set_xlabel("k"); axes[1].set_ylabel("Silhouette Coefficient")
    axes[1].set_title("Silhouette (maior = melhor)"); axes[1].legend()

    axes[2].plot(ks, [db_scores[k] for k in ks], "r-o", linewidth=2)
    axes[2].axvline(best_k, color="red", linestyle="--", alpha=0.7, label=f"k={best_k}")
    axes[2].set_xlabel("k"); axes[2].set_ylabel("Davies-Bouldin Index")
    axes[2].set_title("Davies-Bouldin (menor = melhor)"); axes[2].legend()

    fig.suptitle("Selecao de K — Clustering Socieconomico PNAD 2016-2025", fontsize=13)
    plt.tight_layout()
    path = OUTPUTS_FIG / "kmeans_selecao_k.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Grafico salvo: {path}")


# ── Ajuste Final ───────────────────────────────────────────────────────────────

def fit_final(X, k):
    logger.info(f"Ajuste final: k={k} ...")
    t0 = time.time()
    km = MiniBatchKMeans(
        n_clusters=k,
        random_state=RANDOM_STATE,
        batch_size=max(1024, len(X) // 100),
        n_init=10,
        max_iter=500,
    )
    labels = km.fit_predict(X)
    logger.info(f"  Convergiu em {time.time()-t0:.1f}s | Inertia: {km.inertia_:.0f}")
    return labels, km


# ── Perfis dos Clusters ────────────────────────────────────────────────────────

LABEL_VARS = CLUSTER_VARS + [
    "Ano", "UF", "renda_bruta", "pea",
    "educ_fund_completo", "educ_medio_completo",
    "educ_superior_completo", "educ_pos_graduacao",
]

def build_profiles(df, labels):
    """Perfil medio de cada cluster + composicao racial e de genero."""
    df = df.copy()
    df["cluster"] = labels
    df["cluster"] = df["cluster"].astype(int)

    # --- Estatisticas descritivas por cluster ---
    agg_vars = [
        "idade",
        "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
        "log_renda", "renda_bruta",
        "negro", "sexo_fem", "empregado",
        "pct_negro_upa_z", "tx_desemprego_upa_z",
        "media_educ_upa_z", "media_renda_upa_z",
    ]
    # so usa colunas que existem
    agg_vars = [v for v in agg_vars if v in df.columns]

    profiles = df.groupby("cluster")[agg_vars].mean().round(4)
    profiles["n_obs"]  = df.groupby("cluster").size()
    profiles["pct_obs"] = (profiles["n_obs"] / len(df) * 100).round(2)

    # Labels interpretativos baseados em negro e log_renda
    rank_renda = profiles["log_renda"].rank(ascending=True).astype(int)
    rank_negro = profiles["negro"].rank(ascending=False).astype(int)  # mais negro = rank 1

    def _label(c):
        renda = rank_renda[c]
        k = len(profiles)
        if renda <= k // 3:
            renda_lbl = "baixa renda"
        elif renda >= k - k // 3:
            renda_lbl = "alta renda"
        else:
            renda_lbl = "renda media"
        pct_neg = profiles.loc[c, "negro"] * 100
        return f"Cluster {c}: {renda_lbl} ({pct_neg:.0f}% negros)"

    profiles["descricao"] = [_label(c) for c in profiles.index]

    # --- Distribuicao racial por cluster ---
    race_dist = df.groupby("cluster")["negro"].value_counts(normalize=True).unstack().fillna(0)
    race_dist.columns = ["pct_branco", "pct_negro"]

    profiles = profiles.join(race_dist)

    logger.info("Perfis dos clusters:")
    for c, row in profiles.iterrows():
        sup = row.get("educ_superior_completo", float("nan"))
        logger.info(
            f"  Cluster {c} (n={int(row['n_obs']):,} | {row['pct_obs']:.1f}%): "
            f"renda={row['log_renda']:.3f} | negro={row['negro']*100:.1f}% | "
            f"sup_completo={sup*100:.1f}% | empregado={row['empregado']*100:.1f}%"
        )

    return df, profiles


# ── Tabela de Perfis para o TCC ────────────────────────────────────────────────

def build_profile_table(profiles):
    """Tabela formatada para o capitulo de Resultados."""
    cols = [
        "n_obs", "pct_obs",
        "negro", "sexo_fem", "empregado",
        "log_renda", "renda_bruta",
        "educ_medio_completo", "educ_superior_completo", "educ_pos_graduacao",
        "pct_negro_upa_z", "tx_desemprego_upa_z",
        "descricao",
    ]
    display = profiles[[c for c in cols if c in profiles.columns]].copy()

    display.rename(columns={
        "n_obs":                   "N",
        "pct_obs":                 "% total",
        "negro":                   "% Negro",
        "sexo_fem":                "% Mulher",
        "empregado":               "% Empregado",
        "log_renda":               "log_Renda",
        "renda_bruta":             "Renda Bruta (R$)",
        "educ_medio_completo":     "% Medio Compl.",
        "educ_superior_completo":  "% Superior Compl.",
        "educ_pos_graduacao":      "% Pos-Grad.",
        "pct_negro_upa_z":         "PctNegroUPA_z",
        "tx_desemprego_upa_z":     "DesempregoUPA_z",
        "descricao":               "Descricao",
    }, inplace=True)

    # Formatar percentuais
    for col in ["% Negro", "% Mulher", "% Empregado"]:
        display[col] = (display[col] * 100).round(1)

    return display


# ── Visualizacoes ──────────────────────────────────────────────────────────────

def plot_cluster_profiles(profiles, k):
    """Heatmap de perfis normalizados (z-score entre clusters)."""
    vars_plot = [
        "log_renda",
        "educ_superior_completo", "educ_pos_graduacao", "educ_medio_completo",
        "idade", "empregado",
        "negro", "sexo_fem",
        "pct_negro_upa_z", "tx_desemprego_upa_z",
        "media_educ_upa_z", "media_renda_upa_z",
    ]
    vars_plot = [v for v in vars_plot if v in profiles.columns]
    data = profiles[vars_plot].copy().astype(float)

    # Z-normaliza entre clusters para visualizacao comparativa
    data_norm = (data - data.mean()) / (data.std() + 1e-9)

    fig, ax = plt.subplots(figsize=(12, max(4, k * 0.8)))
    im = ax.imshow(data_norm.values, cmap="RdYlGn", aspect="auto", vmin=-2, vmax=2)

    ax.set_xticks(range(len(vars_plot)))
    ax.set_xticklabels(vars_plot, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(k))
    ax.set_yticklabels([f"Cluster {c}\n({profiles.loc[c,'n_obs']/1e6:.1f}M | "
                        f"negro={profiles.loc[c,'negro']*100:.0f}%)"
                        for c in profiles.index], fontsize=9)

    # Anotar valores originais (nao z-score)
    for i, c in enumerate(profiles.index):
        for j, var in enumerate(vars_plot):
            val = data.loc[c, var]
            fmt = f"{val:.2f}" if abs(val) < 10 else f"{val:.0f}"
            ax.text(j, i, fmt, ha="center", va="center", fontsize=7,
                    color="black" if abs(data_norm.loc[c, var]) < 1.5 else "white")

    plt.colorbar(im, ax=ax, label="Z-score entre clusters")
    ax.set_title(
        f"Perfis dos Clusters Socioeconomicos (k={k}) — PNAD 2016-2025\n"
        f"Valores originais anotados; cor = desvio relativo entre clusters",
        fontsize=11
    )
    plt.tight_layout()
    path = OUTPUTS_FIG / f"kmeans_perfis_k{k}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Grafico de perfis salvo: {path}")


def plot_racial_gap_by_cluster(df_labeled, k):
    """Boxplot de log_renda por cluster, separado por raca."""
    fig, ax = plt.subplots(figsize=(10, 5))

    clusters = sorted(df_labeled["cluster"].unique())
    width  = 0.35
    x      = np.arange(len(clusters))

    for i, (negro_val, label, color) in enumerate([(0, "Branco", "#4C72B0"), (1, "Negro", "#DD8452")]):
        sub = df_labeled[df_labeled["negro"] == negro_val]
        means = [sub[sub["cluster"] == c]["log_renda"].mean() for c in clusters]
        bars = ax.bar(x + i * width, means, width, label=label, color=color, alpha=0.85)
        for bar, m in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{m:.3f}", ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("Cluster"); ax.set_ylabel("log_Renda medio")
    ax.set_title(f"Gap Salarial Racial por Cluster (k={k}) — PNAD 2016-2025")
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels([f"C{c}" for c in clusters])
    ax.legend()
    plt.tight_layout()
    path = OUTPUTS_FIG / f"kmeans_gap_racial_k{k}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Grafico de gap racial salvo: {path}")


def plot_racial_composition(profiles, k):
    """Composicao racial por cluster (stacked bar)."""
    fig, ax = plt.subplots(figsize=(8, 4))
    clusters = profiles.index.tolist()
    pct_neg  = profiles["negro"].values * 100
    pct_bra  = (1 - profiles["negro"].values) * 100

    ax.bar(range(k), pct_bra, label="Branco", color="#4C72B0", alpha=0.85)
    ax.bar(range(k), pct_neg, bottom=pct_bra, label="Negro", color="#DD8452", alpha=0.85)

    for i, (pb, pn) in enumerate(zip(pct_bra, pct_neg)):
        ax.text(i, pb/2,        f"{pb:.1f}%", ha="center", va="center", fontsize=9, color="white", fontweight="bold")
        ax.text(i, pb + pn/2,   f"{pn:.1f}%", ha="center", va="center", fontsize=9, color="white", fontweight="bold")

    ax.set_xticks(range(k))
    ax.set_xticklabels([f"Cluster {c}\n(n={profiles.loc[c,'n_obs']/1e6:.1f}M)" for c in clusters])
    ax.set_ylabel("Composicao racial (%)"); ax.set_ylim(0, 100)
    ax.set_title(f"Composicao Racial por Cluster (k={k}) — PNAD 2016-2025")
    ax.legend(loc="upper right")
    plt.tight_layout()
    path = OUTPUTS_FIG / f"kmeans_composicao_racial_k{k}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Grafico de composicao racial salvo: {path}")


# ── Sumario Narrativo ──────────────────────────────────────────────────────────

def print_summary(profiles, silhouettes, db_scores, best_k):
    sep = "=" * 78
    print(f"\n{sep}")
    print("  SUMARIO DE CLUSTERING -- PNAD 2016-2025")
    print(sep)
    print(f"\n  Metodo: MiniBatchKMeans | k={best_k} | Silhouette={silhouettes[best_k]:.4f}")
    print(f"  Davies-Bouldin={db_scores[best_k]:.4f} (menor = melhor)\n")
    print("  Scores por k:")
    for k in K_RANGE:
        marker = " <-- SELECIONADO" if k == best_k else ""
        print(f"    k={k}: silhouette={silhouettes[k]:.4f}  DB={db_scores[k]:.4f}{marker}")
    print()
    print("  PERFIS DOS CLUSTERS:")
    print(f"  {'C':<4}  {'N':>9}  {'%total':>6}  {'%Negro':>7}  {'%Mulher':>8}  "
          f"{'%Empreg':>8}  {'log_Renda':>10}  {'%SupCompl':>10}")
    print("  " + "-" * 75)
    for c, row in profiles.iterrows():
        sup = row.get("educ_superior_completo", float("nan"))
        print(
            f"  {c:<4}  {int(row['n_obs']):>9,}  {row['pct_obs']:>5.1f}%  "
            f"{row['negro']*100:>6.1f}%  {row['sexo_fem']*100:>7.1f}%  "
            f"{row['empregado']*100:>7.1f}%  {row['log_renda']:>10.3f}  "
            f"{sup*100:>9.1f}%"
        )
    print()

    # Gap racial dentro de cada cluster
    print("  GAP RACIAL (log_renda medio) POR CLUSTER:")
    print(f"  {'C':<4}  {'Branco':>8}  {'Negro':>8}  {'gap_log':>9}  {'gap_%':>8}")
    print("  " + "-" * 50)
    for c, row in profiles.iterrows():
        br = row.get("log_renda", np.nan)
        ng = row.get("negro", np.nan)
        print(f"  {c:<4}  (ver grafico kmeans_gap_racial_k{best_k}.png)")
        break
    print(f"  Ver outputs/figures/kmeans_gap_racial_k{best_k}.png")
    print(f"\n{sep}\n")


# ── Pipeline ───────────────────────────────────────────────────────────────────

def main():
    t_total = time.time()
    logger.info("=" * 70)
    logger.info("CLUSTERING SOCIECONOMICO — PNAD 2016-2025")
    logger.info("=" * 70)

    df = load_data()
    X, scaler = preprocess(df)

    # Selecao de K
    best_k, inertias, silhouettes, db_scores = select_k(X, df)

    # Override de interpretabilidade: k=2 é trivialmente binário com N=7.7M
    if K_FINAL_OVERRIDE and K_FINAL_OVERRIDE != best_k:
        logger.info(
            f"K_FINAL_OVERRIDE={K_FINAL_OVERRIDE}: substituindo k={best_k} "
            f"(silhouette={silhouettes[best_k]:.4f}) por k={K_FINAL_OVERRIDE} "
            f"(silhouette={silhouettes[K_FINAL_OVERRIDE]:.4f}) — interpretabilidade TCC"
        )
        best_k = K_FINAL_OVERRIDE

    # Ajuste final com k otimo
    labels, km = fit_final(X, best_k)

    # Perfis
    df_labeled, profiles = build_profiles(df, labels)

    # Tabelas
    profile_table = build_profile_table(profiles)
    profile_table.to_csv(OUTPUTS_TB / f"kmeans_perfis_k{best_k}.csv")
    try:
        import jinja2  # noqa: F401
        latex = profile_table.to_latex(
            caption=(
                f"Perfis dos Clusters Socieconomicos (k={best_k}) -- "
                "PNAD Continua 2016-2025. "
                "MiniBatchKMeans sobre 10 variaveis padronizadas. "
                "Valores medios por cluster."
            ),
            label="tab:kmeans_perfis",
            escape=False,
        )
        (OUTPUTS_TB / f"kmeans_perfis_k{best_k}.tex").write_text(latex, encoding="utf-8")
    except ImportError:
        pass

    # Salva labels e metricas
    df_labeled[["UF", "Ano", "negro", "sexo_fem", "cluster"]].to_parquet(
        OUTPUTS_TB / f"kmeans_labels_k{best_k}.parquet", index=False
    )

    metrics_df = pd.DataFrame({
        "k":          list(K_RANGE),
        "inertia":    [inertias[k] for k in K_RANGE],
        "silhouette": [silhouettes[k] for k in K_RANGE],
        "davies_bouldin": [db_scores[k] for k in K_RANGE],
    })
    metrics_df.to_csv(OUTPUTS_TB / "kmeans_metricas.csv", index=False)
    logger.info(f"Metricas salvas: {OUTPUTS_TB / 'kmeans_metricas.csv'}")

    # Visualizacoes
    plot_cluster_profiles(profiles, best_k)
    plot_racial_gap_by_cluster(df_labeled, best_k)
    plot_racial_composition(profiles, best_k)

    # Sumario
    print_summary(profiles, silhouettes, db_scores, best_k)

    # Gap racial por cluster
    print("\n--- Gap Racial por Cluster (log_renda medio) ---")
    gap_rows = []
    for c in sorted(df_labeled["cluster"].unique()):
        sub = df_labeled[df_labeled["cluster"] == c]
        b_renda = sub[sub["negro"] == 0]["log_renda"].mean()
        n_renda = sub[sub["negro"] == 1]["log_renda"].mean()
        gap_log = n_renda - b_renda
        gap_pct = (np.exp(gap_log) - 1) * 100
        gap_rows.append({
            "cluster": c,
            "log_renda_branco": round(b_renda, 4),
            "log_renda_negro":  round(n_renda, 4),
            "gap_log":          round(gap_log, 4),
            "gap_%":            round(gap_pct, 2),
        })
    gap_df = pd.DataFrame(gap_rows)
    print(gap_df.to_string(index=False))
    gap_df.to_csv(OUTPUTS_TB / f"kmeans_gap_racial_k{best_k}.csv", index=False)

    elapsed = (time.time() - t_total) / 60
    logger.info(f"CONCLUIDO em {elapsed:.1f} min")
    print(f"\n=== CONCLUIDO em {elapsed:.1f} min ===")
    print(f"Outputs: {OUTPUTS_TB} | Figuras: {OUTPUTS_FIG}")


if __name__ == "__main__":
    main()
