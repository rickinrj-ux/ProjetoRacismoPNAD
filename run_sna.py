"""
run_sna.py
==========
Social Network Analysis — mobilidade profissional como grafo.
PNAD Contínua 2016-2025.

FRAMEWORK TEÓRICO:
    Granovetter (1973) — "The Strength of Weak Ties":
        Acesso a informações e oportunidades profissionais depende de
        QUEM você conhece (network position), não apenas do que sabe.
        Trabalhadores em posições de baixa centralidade perdem
        oportunidades que não chegam à sua bolha.

    Burt (2004) — "Structural Holes and Good Ideas":
        Constraint_i = Σ_j (p_ij + Σ_q p_iq·p_qj)²
        Baixo constraint → "buraco estrutural" → vantagem de corretagem.
        Quem conecta grupos desconexos obtém rendas relacionais
        (acesso antecipado a vagas, promoções, mentoria).

    Wilson (1987) — "The Truly Disadvantaged":
        Segregação residencial limita não só o acesso a serviços, mas
        também o capital social: negros em bairros segregados não têm
        acesso às redes de indicação dos bairros brancos de maior renda.

CONSTRUÇÃO DA REDE:
    Nós (10): grupos demográficos = raça × educação
        {Branco, Negro} × {Sem_Instr, Fundamental, Médio, Superior, Pós}

    Arestas: dois grupos estão conectados quando coexistem na mesma UPA.
        Peso = N de UPAs compartilhadas (volume de co-residência).
        Jaccard = |UPAs_A ∩ UPAs_B| / |UPAs_A ∪ UPAs_B|  (0-1).

    Lógica: trabalhadores da mesma UPA têm acesso às mesmas redes de
    indicação, frequentam os mesmos espaços de interação social e
    profissional. Co-residência = oportunidade de capital social misto.

    Buracos estruturais: grupos altamente separados residencialmente
    têm alto constraint → baixo acesso à rede oposta → gap salarial.
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
handlers = [
    logging.FileHandler("logs/sna.log", encoding="utf-8"),
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
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

try:
    import community as community_louvain
    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False
    logger.warning("python-louvain nao disponivel — Louvain desabilitado.")

FEATURES_PATH = Path("data/processed/features.parquet")
OUTPUTS_TB    = Path("outputs/tables")
OUTPUTS_FIG   = Path("outputs/figures")
OUTPUTS_TB.mkdir(parents=True, exist_ok=True)
OUTPUTS_FIG.mkdir(parents=True, exist_ok=True)

# ── Categorias de educação ─────────────────────────────────────────────────────
EDUC_LABELS = {0: "Sem_Instr", 1: "Fundamental", 2: "Medio", 3: "Superior", 4: "Pos"}
EDUC_ORDER  = [0, 1, 2, 3, 4]

RACE_COLORS = {"Branco": "#4C72B0", "Negro": "#DD8452"}
EDUC_MARKERS = {0: "o", 1: "s", 2: "^", 3: "D", 4: "P"}


# ── Carregamento ───────────────────────────────────────────────────────────────

def load_data():
    logger.info(f"Carregando {FEATURES_PATH} ...")
    df = pd.read_parquet(FEATURES_PATH)
    logger.info(f"  Total: {len(df):,} obs.")

    # Classifica educação em 5 níveis a partir dos dummies
    df["educ_grp"] = 0  # Sem instrução / incompleto
    df.loc[df["educ_fund_completo"].fillna(0).astype(bool), "educ_grp"]     = 1
    df.loc[df["educ_medio_completo"].fillna(0).astype(bool), "educ_grp"]    = 2
    df.loc[df["educ_superior_completo"].fillna(0).astype(bool), "educ_grp"] = 3
    df.loc[df["educ_pos_graduacao"].fillna(0).astype(bool), "educ_grp"]     = 4

    # Mantém só observações com raça e UPA definidos
    df = df.dropna(subset=["negro", "UPA"]).copy()
    df["negro"]    = df["negro"].astype(float)
    df["race_lbl"] = df["negro"].map({1.0: "Negro", 0.0: "Branco"})
    df["node_id"]  = df["race_lbl"] + "_" + df["educ_grp"].map(EDUC_LABELS)

    logger.info(
        f"  Apos filtros: {len(df):,} obs. | "
        f"Negros: {df['negro'].mean()*100:.1f}% | "
        f"UPAs: {df['UPA'].nunique():,}"
    )
    return df


# ── Construção da rede ────────────────────────────────────────────────────────

def build_network(df):
    logger.info("Construindo rede demográfica (nós=grupos raça×educação) ...")
    t0 = time.time()

    # Atributos de cada nó
    node_attrs = {}
    for node_id, grp in df.groupby("node_id"):
        node_attrs[node_id] = {
            "race":       grp["race_lbl"].iloc[0],
            "educ_grp":   grp["educ_grp"].iloc[0],
            "educ_label": EDUC_LABELS[grp["educ_grp"].iloc[0]],
            "n_workers":  len(grp),
            "mean_renda": float(grp["log_renda"].mean()) if grp["log_renda"].notna().any() else 0.0,
            "mean_educ":  float(grp["educ_grp"].mean()),
            "pct_empregado": float(grp["empregado"].fillna(0).astype(float).mean())
                if "empregado" in grp.columns else 0.0,
        }

    # Para cada UPA, identifica quais grupos estão presentes
    logger.info("  Calculando co-presença por UPA ...")
    upa_groups = df.groupby("UPA")["node_id"].apply(set)

    # Conta UPAs compartilhadas por par de grupos
    edge_counts = {}
    for groups in upa_groups:
        grp_list = sorted(groups)
        for a, b in combinations(grp_list, 2):
            key = (a, b) if a < b else (b, a)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    # Jaccard por par
    upa_per_node = df.groupby("node_id")["UPA"].nunique().to_dict()
    edges_jaccard = {}
    for (a, b), shared in edge_counts.items():
        union = upa_per_node.get(a, 0) + upa_per_node.get(b, 0) - shared
        edges_jaccard[(a, b)] = shared / union if union > 0 else 0.0

    # Monta o grafo
    G = nx.Graph()
    for node_id, attrs in node_attrs.items():
        G.add_node(node_id, **attrs)
    for (a, b), jac in edges_jaccard.items():
        G.add_edge(a, b, weight=jac, shared_upas=edge_counts[(a, b)])

    logger.info(
        f"  Rede: {G.number_of_nodes()} nós | "
        f"{G.number_of_edges()} arestas | {time.time()-t0:.1f}s"
    )
    return G


# ── Métricas de rede ──────────────────────────────────────────────────────────

def compute_metrics(G):
    logger.info("Calculando métricas de rede ...")

    # Centralidades (ponderadas pelo peso Jaccard)
    degree_centrality   = nx.degree_centrality(G)
    betweenness         = nx.betweenness_centrality(G, weight="weight", normalized=True)
    eigenvector         = nx.eigenvector_centrality_numpy(G, weight="weight")
    clustering          = nx.clustering(G, weight="weight")

    # Constraint de Burt (buracos estruturais)
    constraint = _burt_constraint(G)

    metrics_rows = []
    for node in G.nodes():
        attrs = G.nodes[node]
        metrics_rows.append({
            "node":              node,
            "race":              attrs["race"],
            "educ_label":        attrs["educ_label"],
            "educ_grp":          attrs["educ_grp"],
            "n_workers":         attrs["n_workers"],
            "mean_renda":        round(attrs["mean_renda"], 4),
            "degree_centrality": round(degree_centrality[node], 4),
            "betweenness":       round(betweenness[node], 4),
            "eigenvector":       round(eigenvector[node], 4),
            "clustering":        round(clustering[node], 4),
            "constraint":        round(constraint.get(node, np.nan), 4),
        })

    df_metrics = pd.DataFrame(metrics_rows).sort_values(["race", "educ_grp"])

    logger.info("  Métricas por nó:")
    for _, row in df_metrics.iterrows():
        logger.info(
            f"    {row['node']:<25s}  degree={row['degree_centrality']:.3f}  "
            f"between={row['betweenness']:.3f}  constraint={row['constraint']:.3f}  "
            f"renda={row['mean_renda']:.3f}"
        )

    return df_metrics


def _burt_constraint(G):
    """
    Constraint de Burt (2004): mede o quanto os contatos de i estão
    conectados entre si (alta constraint = rede fechada = sem buracos estruturais).

    C_i = Σ_j (p_ij + Σ_q≠i,j p_iq·p_qj)²
    p_ij = w_ij / Σ_k w_ik  (proporção do capital relacional investido em j)
    """
    constraint = {}
    for i in G.nodes():
        neighbors = list(G.neighbors(i))
        if not neighbors:
            constraint[i] = 1.0
            continue
        total_w = sum(G[i][j]["weight"] for j in neighbors)
        if total_w == 0:
            constraint[i] = 1.0
            continue
        p = {j: G[i][j]["weight"] / total_w for j in neighbors}
        c_i = 0.0
        for j in neighbors:
            indirect = sum(
                p.get(q, 0) * G[q][j]["weight"] / max(sum(G[q][r]["weight"] for r in G.neighbors(q)), 1e-9)
                for q in neighbors if q != j and G.has_edge(q, j)
            )
            c_i += (p[j] + indirect) ** 2
        constraint[i] = round(c_i, 6)
    return constraint


# ── Detecção de comunidades (Louvain) ─────────────────────────────────────────

def detect_communities(G):
    if not HAS_LOUVAIN:
        return {n: 0 for n in G.nodes()}
    partition = community_louvain.best_partition(G, weight="weight", random_state=42)
    n_comm = len(set(partition.values()))
    logger.info(f"  Louvain: {n_comm} comunidades detectadas")
    return partition


# ── Homofilia racial ──────────────────────────────────────────────────────────

def compute_homophily(G):
    """
    Índice de homofilia racial: compara peso intra-racial vs inter-racial.
    H > 0.5 → redes racialmente segregadas.
    H = 0.5 → mistura aleatória.
    H < 0.5 → heterofilia (mistura acima do esperado).
    """
    intra = sum(
        d["weight"]
        for u, v, d in G.edges(data=True)
        if G.nodes[u]["race"] == G.nodes[v]["race"]
    )
    inter = sum(
        d["weight"]
        for u, v, d in G.edges(data=True)
        if G.nodes[u]["race"] != G.nodes[v]["race"]
    )
    total = intra + inter
    h = intra / total if total > 0 else 0.5
    logger.info(f"  Homofilia racial: H={h:.4f} (intra={intra:.2f}, inter={inter:.2f})")
    return h, intra, inter


# ── Análise temporal: gap por ano ─────────────────────────────────────────────

def temporal_gap(df):
    """Gap racial na rede por ano: como a homofilia e renda evoluíram."""
    if "Ano" not in df.columns:
        return None
    rows = []
    for ano, grp in df.groupby("Ano"):
        renda_branco = grp.loc[grp["negro"] == 0, "log_renda"].mean()
        renda_negro  = grp.loc[grp["negro"] == 1, "log_renda"].mean()
        pct_negro    = grp["negro"].mean()
        # Homofilia residencial: razão UPAs exclusivamente negras vs mistas
        upa_compo = grp.groupby("UPA")["negro"].mean()
        pct_upa_mista = ((upa_compo > 0.1) & (upa_compo < 0.9)).mean()
        rows.append({
            "Ano":         int(ano),
            "renda_branco": round(float(renda_branco), 4),
            "renda_negro":  round(float(renda_negro), 4),
            "gap_log":      round(float(renda_branco - renda_negro), 4),
            "pct_negro":    round(float(pct_negro), 4),
            "pct_upa_mista":round(float(pct_upa_mista), 4),
        })
    return pd.DataFrame(rows)


# ── Visualizações ─────────────────────────────────────────────────────────────

def plot_network(G, df_metrics, partition, title_suffix=""):
    """
    Layout spring ponderado.
    Tamanho do nó = mean_renda (normalizado).
    Cor = raça (azul=branco, laranja=negro).
    Espessura da aresta = peso Jaccard.
    Símbolo = nível de educação.
    """
    fig, ax = plt.subplots(figsize=(12, 9))

    pos = nx.spring_layout(G, weight="weight", seed=42, k=2.5)

    # Normaliza tamanho dos nós por renda
    rendas = np.array([G.nodes[n]["mean_renda"] for n in G.nodes()])
    rendas_norm = (rendas - rendas.min()) / (rendas.max() - rendas.min() + 1e-9)
    node_sizes = 400 + rendas_norm * 1800

    node_colors = [RACE_COLORS[G.nodes[n]["race"]] for n in G.nodes()]

    # Arestas com espessura proporcional ao peso
    edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
    max_w = max(edge_weights) if edge_weights else 1
    edge_widths = [2 + 8 * (w / max_w) for w in edge_weights]

    # Cor das arestas: intra-racial cinza claro, inter-racial vermelho
    edge_colors = [
        "#cccccc" if G.nodes[u]["race"] == G.nodes[v]["race"] else "#e74c3c"
        for u, v in G.edges()
    ]

    nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths,
                           edge_color=edge_colors, alpha=0.6)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                           node_size=node_sizes, alpha=0.92)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7.5, font_weight="bold")

    # Legenda
    legend_elements = [
        mpatches.Patch(facecolor=RACE_COLORS["Branco"], label="Branco"),
        mpatches.Patch(facecolor=RACE_COLORS["Negro"],  label="Negro"),
        Line2D([0], [0], color="#cccccc", linewidth=2, label="Aresta intra-racial"),
        Line2D([0], [0], color="#e74c3c", linewidth=2, label="Aresta inter-racial"),
        mpatches.Patch(facecolor="white", edgecolor="gray",
                       label="Tamanho nó ∝ renda média"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9, framealpha=0.8)
    ax.set_title(
        f"Rede de Co-residência por Grupo Demográfico{title_suffix}\n"
        "PNAD 2016-2025 | Nós = raça × educação | "
        "Arestas = proporção de UPAs compartilhadas (Jaccard)\n"
        "Vermelho = conexão inter-racial | Cinza = intra-racial | Tamanho ∝ renda média",
        fontsize=10, pad=12,
    )
    ax.axis("off")
    plt.tight_layout()
    path = OUTPUTS_FIG / "sna_rede_demografica.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Rede salva: {path}")


def plot_constraint_vs_renda(df_metrics):
    """Scatter: constraint (Burt) × renda — cores por raça."""
    fig, ax = plt.subplots(figsize=(8, 6))
    for race, sub in df_metrics.groupby("race"):
        color = RACE_COLORS[race]
        ax.scatter(
            sub["constraint"], sub["mean_renda"],
            c=color, s=sub["n_workers"] / sub["n_workers"].max() * 400 + 80,
            label=race, alpha=0.85, edgecolors="white", linewidths=0.8,
        )
        for _, row in sub.iterrows():
            ax.annotate(
                row["educ_label"], (row["constraint"], row["mean_renda"]),
                fontsize=7.5, ha="left", va="bottom",
                xytext=(4, 3), textcoords="offset points",
            )

    ax.set_xlabel("Constraint de Burt (maior = mais isolado / sem buracos estruturais)",
                  fontsize=10)
    ax.set_ylabel("log_Renda médio", fontsize=10)
    ax.set_title(
        "Buracos Estruturais × Renda por Grupo Demográfico\n"
        "PNAD 2016-2025 | Tamanho do ponto ∝ N de trabalhadores\n"
        "Grupos à direita (alto constraint) = posição periférica na rede",
        fontsize=10,
    )
    ax.legend(fontsize=10)
    ax.axvline(df_metrics["constraint"].median(), color="gray",
               linestyle="--", alpha=0.5, label="mediana constraint")

    # Quadrante anotado
    xmax = df_metrics["constraint"].max()
    ymax = df_metrics["mean_renda"].max()
    ax.text(xmax * 0.05, ymax * 0.97, "Alto renda\nBaixo constraint\n(posição de corretagem)",
            fontsize=8, color="gray", va="top")
    ax.text(xmax * 0.75, ymax * 0.55, "Baixo renda\nAlto constraint\n(isolamento estrutural)",
            fontsize=8, color="gray", va="top")

    plt.tight_layout()
    path = OUTPUTS_FIG / "sna_constraint_vs_renda.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Constraint vs renda salvo: {path}")


def plot_homophily_by_educ(G):
    """Peso inter-racial vs intra-racial por nível de educação."""
    educ_levels = sorted(set(G.nodes[n]["educ_grp"] for n in G.nodes()))
    intra_by_educ = []
    inter_by_educ = []

    for educ in educ_levels:
        nodes_educ = [n for n in G.nodes() if G.nodes[n]["educ_grp"] == educ]
        intra = sum(
            d["weight"] for u, v, d in G.edges(data=True)
            if u in nodes_educ and v in nodes_educ
        )
        inter = sum(
            d["weight"] for u, v, d in G.edges(data=True)
            if (u in nodes_educ) != (v in nodes_educ)
        )
        intra_by_educ.append(intra)
        inter_by_educ.append(inter)

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(educ_levels))
    w = 0.35
    bars1 = ax.bar(x - w/2, intra_by_educ, w, label="Intra-racial", color="#95a5a6", alpha=0.85)
    bars2 = ax.bar(x + w/2, inter_by_educ, w, label="Inter-racial", color="#e74c3c", alpha=0.85)

    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([EDUC_LABELS[e] for e in educ_levels], fontsize=10)
    ax.set_ylabel("Peso acumulado Jaccard (co-residência)")
    ax.set_title(
        "Homofilia Racial por Nível de Educação\n"
        "PNAD 2016-2025 | Intra = brancos↔brancos ou negros↔negros | "
        "Inter = brancos↔negros\n"
        "Maior barra inter-racial = mais integração residencial nesse nível",
        fontsize=10,
    )
    ax.legend()
    plt.tight_layout()
    path = OUTPUTS_FIG / "sna_homofilia_por_educ.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Homofilia por educação salvo: {path}")


def plot_temporal_gap(df_temporal):
    if df_temporal is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(df_temporal["Ano"], df_temporal["gap_log"], "o-", color="#e74c3c",
                 linewidth=2, markersize=6)
    axes[0].fill_between(df_temporal["Ano"], df_temporal["gap_log"], alpha=0.15, color="#e74c3c")
    axes[0].set_xlabel("Ano"); axes[0].set_ylabel("Gap racial (log-renda branco − negro)")
    axes[0].set_title("Evolução do Gap Salarial Racial\n2016-2025")
    axes[0].axhline(df_temporal["gap_log"].mean(), color="gray",
                    linestyle="--", alpha=0.6, label=f"Média = {df_temporal['gap_log'].mean():.3f}")
    axes[0].legend()

    axes[1].plot(df_temporal["Ano"], df_temporal["pct_upa_mista"] * 100, "s-",
                 color="#4C72B0", linewidth=2, markersize=6)
    axes[1].set_xlabel("Ano"); axes[1].set_ylabel("% de UPAs racialmente mistas")
    axes[1].set_title("Integração Residencial ao Longo do Tempo\n"
                      "(UPAs com 10%–90% negros)")

    plt.suptitle("Tendências Temporais — Gap Salarial e Segregação Residencial (PNAD 2016-2025)",
                 fontsize=11, y=1.02)
    plt.tight_layout()
    path = OUTPUTS_FIG / "sna_temporal_gap.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"  Gráfico temporal salvo: {path}")


# ── Sumário narrativo ─────────────────────────────────────────────────────────

def print_summary(G, df_metrics, h_index, df_temporal):
    sep = "=" * 78

    # Constraint médio por raça
    c_branco = df_metrics.loc[df_metrics["race"] == "Branco", "constraint"].mean()
    c_negro  = df_metrics.loc[df_metrics["race"] == "Negro",  "constraint"].mean()

    # Nós com mais e menos constraint
    top_constraint    = df_metrics.nlargest(3, "constraint")[["node", "constraint", "mean_renda"]]
    bottom_constraint = df_metrics.nsmallest(3, "constraint")[["node", "constraint", "mean_renda"]]

    # Entre nós negros de alta educação
    neg_sup = df_metrics[
        (df_metrics["race"] == "Negro") & (df_metrics["educ_grp"] >= 3)
    ][["node", "constraint", "betweenness", "mean_renda"]]

    bra_sup = df_metrics[
        (df_metrics["race"] == "Branco") & (df_metrics["educ_grp"] >= 3)
    ][["node", "constraint", "betweenness", "mean_renda"]]

    print(f"""
{sep}
  SUMARIO SNA — REDE DE CO-RESIDENCIA DEMOGRAFICA
  PNAD 2016-2025 | Framework: Granovetter (1973) + Burt (2004)
{sep}

  ESTRUTURA DA REDE:
    Nos:     {G.number_of_nodes()} grupos demograficos (raca x educacao)
    Arestas: {G.number_of_edges()} pares com co-residencia em UPAs compartilhadas
    Densidade: {nx.density(G):.4f}

  HOMOFILIA RACIAL (indice H):
    H = {h_index:.4f}
    {"Alta segregacao residencial — negros e brancos raramente compartilham UPAs" if h_index > 0.6 else
     "Segregacao moderada — alguma mistura residencial" if h_index > 0.45 else
     "Baixa segregacao — grupos raciais bem misturados residencialmente"}

  CONSTRAINT DE BURT (isolamento na rede):
    Brancos: constraint medio = {c_branco:.4f}
    Negros:  constraint medio = {c_negro:.4f}
    Diferenca: {c_negro - c_branco:+.4f}
    {"Negros enfrentam MAIOR constraint -> menos buracos estruturais -> desvantagem de corretagem" if c_negro > c_branco
     else "Negros enfrentam MENOR constraint (resultado inesperado — investigar)"}

  GRUPOS COM MAIS BURACOS ESTRUTURAIS (menor constraint = posicao de corretagem):""")
    for _, row in bottom_constraint.iterrows():
        print(f"    {row['node']:<25s}  constraint={row['constraint']:.4f}  renda={row['mean_renda']:.3f}")

    print(f"""
  GRUPOS MAIS ISOLADOS (maior constraint = sem buracos estruturais):""")
    for _, row in top_constraint.iterrows():
        print(f"    {row['node']:<25s}  constraint={row['constraint']:.4f}  renda={row['mean_renda']:.3f}")

    print(f"""
  NEGROS DE ALTA EDUCACAO vs BRANCOS DE ALTA EDUCACAO:
    {"Node":<25s}  {"Constraint":>12s}  {"Betweenness":>12s}  {"log_Renda":>10s}""")
    for df_sub, label in [(bra_sup, "BRANCO"), (neg_sup, "NEGRO")]:
        for _, row in df_sub.iterrows():
            print(f"    [{label}] {row['node']:<20s}  {row['constraint']:>12.4f}  "
                  f"{row['betweenness']:>12.4f}  {row['mean_renda']:>10.3f}")

    if df_temporal is not None:
        gap_ini = df_temporal.iloc[0]["gap_log"]
        gap_fin = df_temporal.iloc[-1]["gap_log"]
        print(f"""
  TENDENCIA TEMPORAL:
    Gap 2016: {gap_ini:.4f} | Gap 2025: {gap_fin:.4f} | Variacao: {gap_fin-gap_ini:+.4f}
    {"Gap AUMENTOU ao longo da serie" if gap_fin > gap_ini else "Gap DIMINUIU ao longo da serie"}
    UPAs mistas 2016: {df_temporal.iloc[0]['pct_upa_mista']*100:.1f}% | "
    "2025: {df_temporal.iloc[-1]['pct_upa_mista']*100:.1f}%""")

    print(f"\n{sep}\n")


# ── Pipeline principal ─────────────────────────────────────────────────────────

def main():
    t_total = time.time()
    logger.info("=" * 70)
    logger.info("SNA — REDE DEMOGRAFICA PNAD 2016-2025")
    logger.info("=" * 70)

    df = load_data()
    G  = build_network(df)

    df_metrics  = compute_metrics(G)
    partition   = detect_communities(G)
    h_idx, _, _ = compute_homophily(G)
    df_temporal = temporal_gap(df)

    # Adiciona comunidade Louvain às métricas
    df_metrics["community"] = df_metrics["node"].map(partition)

    # Salva tabelas
    df_metrics.to_csv(OUTPUTS_TB / "sna_metricas_nos.csv", index=False)

    # Arestas com atributos
    edges_df = pd.DataFrame([
        {
            "source": u, "target": v,
            "weight_jaccard": round(d["weight"], 5),
            "shared_upas":    d["shared_upas"],
            "inter_racial":   G.nodes[u]["race"] != G.nodes[v]["race"],
        }
        for u, v, d in G.edges(data=True)
    ]).sort_values("weight_jaccard", ascending=False)
    edges_df.to_csv(OUTPUTS_TB / "sna_arestas.csv", index=False)

    if df_temporal is not None:
        df_temporal.to_csv(OUTPUTS_TB / "sna_temporal.csv", index=False)

    try:
        import jinja2  # noqa: F401
        latex = df_metrics[[
            "node", "race", "educ_label", "n_workers", "mean_renda",
            "degree_centrality", "betweenness", "constraint",
        ]].to_latex(
            index=False,
            caption=(
                "Métricas de Rede por Grupo Demográfico (raça × educação). "
                "PNAD Contínua 2016-2025. "
                "Constraint de Burt: maior valor = maior isolamento estrutural."
            ),
            label="tab:sna_metricas",
            escape=False,
        )
        (OUTPUTS_TB / "sna_metricas_nos.tex").write_text(latex, encoding="utf-8")
    except ImportError:
        pass

    # Visualizações
    plot_network(G, df_metrics, partition)
    plot_constraint_vs_renda(df_metrics)
    plot_homophily_by_educ(G)
    plot_temporal_gap(df_temporal)

    # Sumário
    print_summary(G, df_metrics, h_idx, df_temporal)

    # Tabela completa no console
    print("--- Métricas Completas dos Nós ---")
    display = df_metrics.sort_values(["race", "educ_grp"])[[
        "node", "race", "educ_label", "n_workers", "mean_renda",
        "degree_centrality", "betweenness", "constraint", "clustering",
    ]]
    print(display.to_string(index=False))

    print("\n--- Top 10 Arestas Inter-raciais (maior Jaccard) ---")
    top_inter = edges_df[edges_df["inter_racial"]].head(10)
    print(top_inter.to_string(index=False))

    if df_temporal is not None:
        print("\n--- Evolução Temporal ---")
        print(df_temporal.to_string(index=False))

    elapsed = (time.time() - t_total) / 60
    logger.info(f"CONCLUIDO em {elapsed:.1f} min")
    print(f"\n=== CONCLUIDO em {elapsed:.1f} min | Outputs: {OUTPUTS_TB} / {OUTPUTS_FIG} ===")


if __name__ == "__main__":
    main()
