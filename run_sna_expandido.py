"""
run_sna_expandido.py
====================
SNA expandida: raça × educação × gênero = 20 nós (antes: 10).
Adiciona dimensão de gênero para capturar interseccionalidade e
tornar as métricas de centralidade estatisticamente mais robustas.

MUDANÇA vs. run_sna.py:
    Antes: 10 nós = {Branco, Negro} × {Sem_Instr, Fund., Médio, Sup., Pós}
    Agora: 20 nós = raça × educação × gênero
             {Branco, Negro} × 5 níveis × {Masc, Fem}

FUNDAMENTAÇÃO:
    Com 10 nós, betweenness centrality tem alta variância e baixa
    generalização (artefato de granularidade). Com 20 nós e
    conexões definidas pela co-presença em UPAs, as métricas
    tornam-se mais estáveis e capturam interseccionalidade
    raça-gênero — dimensão central da hipótese H5.
"""
import sys
import logging
import time
import warnings
from pathlib import Path
from itertools import combinations

sys.path.insert(0, "src")
warnings.filterwarnings("ignore")

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/sna_expandido.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import community as community_louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)
OUTPUTS_FIG.mkdir(parents=True, exist_ok=True)

EDUC_LABELS = {0: "Sem_Instr", 1: "Fundamental", 2: "Medio", 3: "Superior", 4: "Pos"}
EDUC_ORDER  = [0, 1, 2, 3, 4]

RACE_COLORS  = {"Branco_Masc": "#2166AC", "Branco_Fem": "#74ADD1",
                "Negro_Masc":  "#D73027", "Negro_Fem":  "#F46D43"}
NODE_SHAPES  = {"Masc": "o", "Fem": "s"}


def load_data():
    logger.info(f"Carregando {FEATURES_PATH} ...")
    cols_need = ["negro", "sexo_fem", "log_renda", "UPA",
                 "educ_fund_completo", "educ_medio_completo",
                 "educ_superior_completo", "educ_pos_graduacao",
                 "pea", "renda_bruta"]
    df = pd.read_parquet(FEATURES_PATH, columns=cols_need)

    df = df[(df["pea"] == 1) & (df["renda_bruta"] > 0)].copy()
    df = df.dropna(subset=["negro", "UPA"]).copy()

    # Educação em 5 níveis
    df["educ_grp"] = 0
    df.loc[df["educ_fund_completo"].fillna(0).astype(bool),      "educ_grp"] = 1
    df.loc[df["educ_medio_completo"].fillna(0).astype(bool),     "educ_grp"] = 2
    df.loc[df["educ_superior_completo"].fillna(0).astype(bool),  "educ_grp"] = 3
    df.loc[df["educ_pos_graduacao"].fillna(0).astype(bool),      "educ_grp"] = 4

    df["race_lbl"]   = df["negro"].astype(float).map({1.0: "Negro", 0.0: "Branco"})
    df["gender_lbl"] = df["sexo_fem"].astype(float).map({1.0: "Fem", 0.0: "Masc"})

    # Nó expandido: raça × educação × gênero
    df["node_id"] = (df["race_lbl"] + "_" +
                     df["educ_grp"].map(EDUC_LABELS) + "_" +
                     df["gender_lbl"])
    df["race_gen"]  = df["race_lbl"] + "_" + df["gender_lbl"]

    logger.info(f"  N={len(df):,} | Nós únicos: {df['node_id'].nunique()} | "
                f"UPAs: {df['UPA'].nunique():,}")
    return df


def build_network(df):
    logger.info("Construindo rede expandida (raça × educação × gênero) ...")
    t0 = time.time()

    node_attrs = {}
    for node_id, grp in df.groupby("node_id"):
        node_attrs[node_id] = {
            "race":       grp["race_lbl"].iloc[0],
            "gender":     grp["gender_lbl"].iloc[0],
            "race_gen":   grp["race_gen"].iloc[0],
            "educ_grp":   int(grp["educ_grp"].iloc[0]),
            "educ_label": EDUC_LABELS[int(grp["educ_grp"].iloc[0])],
            "n_workers":  len(grp),
            "mean_renda": float(grp["log_renda"].mean()) if grp["log_renda"].notna().any() else 0.0,
        }

    logger.info("  Calculando co-presença por UPA ...")
    upa_groups = df.groupby("UPA")["node_id"].apply(set)

    edge_counts = {}
    for groups in upa_groups:
        grp_list = sorted(groups)
        for a, b in combinations(grp_list, 2):
            key = (a, b) if a < b else (b, a)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    upa_per_node = df.groupby("node_id")["UPA"].nunique().to_dict()
    edges_jaccard = {}
    for (a, b), shared in edge_counts.items():
        union = upa_per_node.get(a, 0) + upa_per_node.get(b, 0) - shared
        edges_jaccard[(a, b)] = shared / union if union > 0 else 0.0

    G = nx.Graph()
    for node_id, attrs in node_attrs.items():
        G.add_node(node_id, **attrs)
    for (a, b), jac in edges_jaccard.items():
        G.add_edge(a, b, weight=jac, shared_upas=edge_counts[(a, b)])

    logger.info(f"  Rede expandida: {G.number_of_nodes()} nós | "
                f"{G.number_of_edges()} arestas | {time.time()-t0:.1f}s")
    return G


def _burt_constraint(G):
    constraint = {}
    for i in G.nodes():
        neighbors = list(G.neighbors(i))
        if not neighbors:
            constraint[i] = 1.0
            continue
        total_w = sum(G[i][j].get("weight", 1.0) for j in neighbors)
        c_i = 0.0
        for j in neighbors:
            p_ij = G[i][j].get("weight", 1.0) / total_w if total_w > 0 else 0.0
            indirect = sum(
                (G[i][q].get("weight", 1.0) / total_w if total_w > 0 else 0.0) *
                G[q][j].get("weight", 0.0)
                for q in G.neighbors(i) if q != j and G.has_edge(q, j)
            )
            c_i += (p_ij + indirect) ** 2
        constraint[i] = round(c_i, 6)
    return constraint


def compute_metrics(G):
    logger.info("Calculando métricas da rede expandida ...")

    degree_centrality = nx.degree_centrality(G)
    betweenness       = nx.betweenness_centrality(G, weight="weight", normalized=True)
    eigenvector       = nx.eigenvector_centrality_numpy(G, weight="weight")
    clustering        = nx.clustering(G, weight="weight")
    constraint        = _burt_constraint(G)

    if HAS_LOUVAIN:
        partition = community_louvain.best_partition(G, weight="weight")
    else:
        partition = {n: 0 for n in G.nodes()}

    rows = []
    for node in G.nodes():
        a = G.nodes[node]
        rows.append({
            "node":              node,
            "race":              a["race"],
            "gender":            a["gender"],
            "race_gen":          a["race_gen"],
            "educ_label":        a["educ_label"],
            "educ_grp":          a["educ_grp"],
            "n_workers":         a["n_workers"],
            "mean_renda":        round(a["mean_renda"], 4),
            "degree_centrality": round(degree_centrality[node], 4),
            "betweenness":       round(betweenness[node], 4),
            "eigenvector":       round(eigenvector[node], 4),
            "clustering":        round(clustering[node], 4),
            "constraint":        constraint[node],
            "community":         partition.get(node, 0),
        })

    df_metrics = pd.DataFrame(rows).sort_values(
        ["race", "gender", "educ_grp"]).reset_index(drop=True)
    df_metrics.to_csv(OUTPUTS_TB / "sna_metricas_nos_expandida.csv", index=False, encoding="utf-8")
    logger.info("  sna_metricas_nos_expandida.csv salvo.")
    return df_metrics


def compute_summary_by_group(df_metrics):
    """Resumo por race×gender para comparação entre grupos."""
    summary = df_metrics.groupby("race_gen").agg(
        n_workers=("n_workers", "sum"),
        mean_renda=("mean_renda", "mean"),
        betweenness_mean=("betweenness", "mean"),
        betweenness_max=("betweenness", "max"),
        constraint_mean=("constraint", "mean"),
        constraint_min=("constraint", "min"),
    ).reset_index()
    summary.to_csv(OUTPUTS_TB / "sna_resumo_race_gender.csv", index=False, encoding="utf-8")
    logger.info("  sna_resumo_race_gender.csv salvo.")
    return summary


def plot_network(G, df_metrics):
    logger.info("Gerando figura da rede expandida ...")

    fig, axes = plt.subplots(1, 2, figsize=(18, 8))
    fig.suptitle("SNA Expandida — Rede de Co-residência: Raça × Educação × Gênero",
                 fontsize=14, fontweight="bold", y=1.01)

    pos = nx.spring_layout(G, seed=42, k=1.5)

    race_gen_colors = {
        "Branco_Masc": "#2166AC", "Branco_Fem": "#74ADD1",
        "Negro_Masc":  "#D73027", "Negro_Fem":  "#F46D43",
    }

    for ax_idx, (ax, metric, title, cmap_scale) in enumerate(zip(
        axes,
        ["betweenness", "constraint"],
        ["Betweenness Centrality\n(capacidade de intermediação)",
         "Constraint de Burt\n(isolamento estrutural — maior = pior)"],
        [True, True],
    )):
        metric_vals = {row["node"]: row[metric] for _, row in df_metrics.iterrows()}
        node_colors = [race_gen_colors.get(G.nodes[n]["race_gen"], "#888888") for n in G.nodes()]
        node_sizes  = [400 + 800 * metric_vals.get(n, 0) for n in G.nodes()]
        node_marker = ["o" if G.nodes[n]["gender"] == "Masc" else "s" for n in G.nodes()]

        edge_weights = [G[u][v].get("weight", 0.1) for u, v in G.edges()]
        max_w = max(edge_weights) if edge_weights else 1.0
        edge_widths = [0.3 + 2.5 * (w / max_w) for w in edge_weights]
        edge_alphas = [0.15 + 0.5 * (w / max_w) for w in edge_weights]

        # Draw edges
        nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths,
                               alpha=0.3, edge_color="#CCCCCC")

        # Draw nodes by marker shape
        for shape in ["o", "s"]:
            nodes_shape = [n for n in G.nodes() if
                           ("Masc" in n and shape == "o") or
                           ("Fem" in n and shape == "s")]
            nc = [race_gen_colors.get(G.nodes[n]["race_gen"], "#888888") for n in nodes_shape]
            ns = [400 + 800 * metric_vals.get(n, 0) for n in nodes_shape]
            pos_sub = {n: pos[n] for n in nodes_shape}
            nx.draw_networkx_nodes(G, pos_sub, nodelist=nodes_shape,
                                   node_color=nc, node_size=ns,
                                   node_shape=shape, ax=ax, alpha=0.85)

        # Labels
        short_labels = {n: n.replace("Branco_", "B_").replace("Negro_", "N_")
                          .replace("_Sem_Instr", "_SemI").replace("_Fundamental", "_Fund")
                          .replace("_Medio", "_Med").replace("_Superior", "_Sup")
                          .replace("_Pos", "_Pos").replace("_Masc", "♂").replace("_Fem", "♀")
                        for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels=short_labels, ax=ax, font_size=6)

        ax.set_title(title, fontsize=11, pad=12)
        ax.axis("off")

        patches = [plt.Line2D([0], [0], marker="o", color="w",
                               markerfacecolor=c, markersize=10, label=lbl)
                   for lbl, c in race_gen_colors.items()] + [
            plt.Line2D([0], [0], marker="o", color="#888", markersize=8, label="Masculino"),
            plt.Line2D([0], [0], marker="s", color="#888", markersize=8, label="Feminino"),
        ]
        ax.legend(handles=patches, loc="lower left", fontsize=7, framealpha=0.8)

    plt.tight_layout()
    plt.savefig(OUTPUTS_FIG / "sna_expandida_rede.png", dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("  sna_expandida_rede.png salvo.")


def plot_betweenness_heatmap(df_metrics):
    logger.info("Gerando heatmap betweenness expandido ...")
    pivot_b = df_metrics.pivot_table(
        index="race_gen", columns="educ_label", values="betweenness", aggfunc="mean"
    )
    educ_ord = ["Sem_Instr", "Fundamental", "Medio", "Superior", "Pos"]
    pivot_b = pivot_b.reindex(columns=[c for c in educ_ord if c in pivot_b.columns])

    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(pivot_b.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(pivot_b.columns)))
    ax.set_xticklabels(pivot_b.columns, rotation=25, ha="right", fontsize=9)
    ax.set_yticks(range(len(pivot_b.index)))
    ax.set_yticklabels(pivot_b.index, fontsize=9)
    for i in range(len(pivot_b.index)):
        for j in range(len(pivot_b.columns)):
            v = pivot_b.values[i, j]
            ax.text(j, i, f"{v:.4f}", ha="center", va="center", fontsize=8,
                    color="black" if v < pivot_b.values.max() * 0.6 else "white")
    plt.colorbar(im, ax=ax, label="Betweenness Centrality")
    ax.set_title("Betweenness por Grupo (Raça × Gênero × Educação)", fontsize=12, pad=10)
    plt.tight_layout()
    plt.savefig(OUTPUTS_FIG / "sna_expandida_betweenness_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("  sna_expandida_betweenness_heatmap.png salvo.")


def print_summary(df_metrics, summary):
    logger.info("\n=== RESUMO SNA EXPANDIDA ===")
    logger.info(f"Nós: {len(df_metrics)}")
    logger.info("\nBetweenness por grupo raça×gênero:")
    for _, row in summary.iterrows():
        logger.info(f"  {row['race_gen']:15s}: mean={row['betweenness_mean']:.4f}  "
                    f"max={row['betweenness_max']:.4f}  constraint={row['constraint_mean']:.4f}")
    neg_groups = df_metrics[df_metrics["race"] == "Negro"]
    bra_groups = df_metrics[df_metrics["race"] == "Branco"]
    logger.info(f"\nNegros: betweenness médio={neg_groups['betweenness'].mean():.4f}")
    logger.info(f"Brancos: betweenness médio={bra_groups['betweenness'].mean():.4f}")
    zero_b = (df_metrics["betweenness"] == 0).sum()
    logger.info(f"Nós com betweenness=0: {zero_b}/{len(df_metrics)}")


def main():
    logger.info("=" * 60)
    logger.info("  SNA EXPANDIDA — Raça × Educação × Gênero (20 nós)")
    logger.info("=" * 60)

    df = load_data()
    G  = build_network(df)
    df_metrics = compute_metrics(G)
    summary    = compute_summary_by_group(df_metrics)
    print_summary(df_metrics, summary)
    plot_network(G, df_metrics)
    plot_betweenness_heatmap(df_metrics)

    logger.info("SNA expandida concluída.")
    return df_metrics, summary


if __name__ == "__main__":
    main()
