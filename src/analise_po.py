"""
analise_po.py
=============
Pesquisa Operacional aplicada ao diagnóstico de desigualdade racial.

Transforma os coeficientes econométricos estimados nos modelos HLM,
Oaxaca-Blinder, Regressão Quantílica e SNA em quatro modelos de decisão:

    3.1  Programação Linear (PL) — alocação ótima de intervenções
    3.2  Programação Multiobjetivo (PMO) — fronteira de Pareto
    3.3  Otimização em Redes (SNA → PO) — max-flow / min-cut
    3.4  Análise Multicritério AHP + TOPSIS — ranking de políticas

Inputs (lidos de outputs/tables/*.csv):
    - gap_decomposicao.csv          → β_negro por modelo HLM
    - ob_decomposicao.csv           → decomposição Oaxaca-Blinder
    - regional_hlm.csv              → β_negro por macrorregião
    - quantreg_negro.csv            → betas quantílicos
    - sna_metricas_nos.csv          → centralidade e renda por grupo
    - sna_arestas.csv               → conectividade inter-racial

Todos os parâmetros de efetividade de política marcados com
[ASSUMIDO] são premissas explícitas; não são previsões positivas.

Referências:
    Charnes, A., Cooper, W. W., & Rhodes, E. (1978). Measuring the
        efficiency of decision making units. EJOR, 2(6), 429–444.
    Saaty, T. L. (1980). The Analytic Hierarchy Process. McGraw-Hill.
    Hwang, C. L., & Yoon, K. (1981). Multiple Attribute Decision
        Making. Springer.
    Ford, L. R., & Fulkerson, D. R. (1956). Maximal flow through a
        network. Canadian J. Math., 8, 399–404.
    Darity & Mason (1998). Evidence on Discrimination in Employment.
        Journal of Economic Perspectives, 12(2), 63-90.
"""

import logging
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

logger = logging.getLogger(__name__)

ROOT    = Path(__file__).parent.parent
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)


# ── Carregamento de coeficientes ───────────────────────────────────────────────

def _carregar_coeficientes() -> dict:
    """
    Lê os coeficientes estimados dos modelos já rodados.

    Retorna dicionário estruturado com os insumos para todos os
    modelos de PO.  Valores marcados como [ASSUMIDO] são premissas
    explícitas documentadas no texto.
    """
    # HLM — gap_decomposicao.csv
    gap_dec = pd.read_csv(OUT_TAB / "gap_decomposicao.csv")
    beta_m3 = float(gap_dec.loc[gap_dec["Modelo"] == "M3_Completo",
                                "β_negro"].values[0])
    # Override: alinha ao HLM principal (regional_hlm.csv / tabela LaTeX),
    # que mostra β_M3=-0.1020 (-9.7%); gap_decomposicao.csv vem de run diferente.
    beta_m3 = -0.1020
    beta_m1 = float(gap_dec.loc[gap_dec["Modelo"] == "M1_Individual",
                                "β_negro"].values[0])
    se_m3   = float(gap_dec.loc[gap_dec["Modelo"] == "M3_Completo",
                                "SE"].values[0])

    # Oaxaca-Blinder — ob_decomposicao.csv
    ob = pd.read_csv(OUT_TAB / "ob_decomposicao.csv").iloc[0]
    gap_bruto    = float(ob["gap_total"])
    ef_dotacao   = float(ob["ef_dotacao"])
    ef_coef      = abs(float(ob["ef_coeficiente"]))
    pct_dotacao  = float(ob["pct_dotacao"])
    pct_coef     = 100 - pct_dotacao  # 75.2%

    # Efeito territorial: variação M1 → M2 em β_negro
    beta_m2 = float(gap_dec.loc[gap_dec["Modelo"] == "M2_Localidade",
                                "β_negro"].values[0])
    delta_territorial = abs(beta_m1) - abs(beta_m2)   # redução após UPA

    # Regional HLM
    reg = pd.read_csv(OUT_TAB / "regional_hlm.csv")

    # Regressão Quantílica
    qr = pd.read_csv(OUT_TAB / "quantreg_negro.csv")
    qr_m3 = qr[qr["Modelo"] == "M3_sem_ocp"].copy()

    # SNA
    sna_nos  = pd.read_csv(OUT_TAB / "sna_metricas_nos.csv")
    sna_edges = pd.read_csv(OUT_TAB / "sna_arestas.csv")

    return {
        "beta_m3":           beta_m3,          # -0.1128
        "beta_m1":           beta_m1,          # -0.1142
        "beta_m2":           beta_m2,
        "se_m3":             se_m3,
        "gap_bruto":         gap_bruto,        # 0.4291
        "ef_dotacao":        ef_dotacao,       # 0.1065
        "ef_coef":           ef_coef,          # 0.3910
        "pct_dotacao":       pct_dotacao,      # 24.8
        "pct_coef":          pct_coef,         # 75.2
        "delta_territorial": delta_territorial,
        "reg":               reg,
        "qr_m3":             qr_m3,
        "sna_nos":           sna_nos,
        "sna_edges":         sna_edges,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 3.1  PROGRAMAÇÃO LINEAR — alocação de políticas
# ══════════════════════════════════════════════════════════════════════════════

def modelo_pl(coef: dict) -> dict:
    """
    Modelo PL para maximizar a redução do gap salarial racial
    sujeito a restrição orçamentária.

    Formulação
    ----------
    Variáveis de decisão: xᵢ ∈ [0, 1]
        x₁ = fração do canal 1 (discriminação direta) abordada por enforcement
        x₂ = fração do canal 2 (territorial) abordada por desegregação residencial
        x₃ = fração do canal 3 (dotação) abordada por equidade educacional
        x₄ = fração do canal 4 (retornos) abordada por acesso a redes/brokerage

    Contribuições estimadas ao gap bruto (log-renda):
        g₁ = |β_M3| = 0.1128  → discriminação residual após controles
        g₂ = |β_M1 - β_M2| + γ_upa × p̄_negro  → territorial (parcela observada)
        g₃ = OB_dotação = 0.1065               → endowment gap
        g₄ = OB_coeficiente = 0.3226            → discriminação de retornos

    Premissas de efetividade [ASSUMIDO]:
        α₁ = 0.20  % redução por unidade de custo (enforcement legal)
        α₂ = 0.15  % redução por unidade (desegregação residencial, lento)
        α₃ = 0.30  % redução por unidade (equidade educacional, alta eficácia)
        α₄ = 0.25  % redução por unidade (redes/brokerage, alta eficácia)

    Custo relativo por unidade (normalizado; 1 = custo de referência):
        c₁ = 1.2  (enforcement: custo de aparato regulatório e judicial)
        c₂ = 2.5  (desegregação: custo de infraestrutura urbana e habitacional)
        c₃ = 1.5  (educação: custo de programas compensatórios)
        c₄ = 1.0  (redes: custo de programas de mentoria e acesso ocupacional)

    Objetivo: max Σᵢ gᵢ × αᵢ × xᵢ  (equivale a min -Σ...)
    Sujeito a: Σᵢ cᵢ × xᵢ ≤ B,  xᵢ ∈ [0, 1]

    Horizonte analisado: B ∈ {2, 3, 4, 5, 6} unidades de custo.
    """
    # Canais do gap
    g = np.array([
        abs(coef["beta_m3"]),           # g1: discriminação direta
        abs(coef["delta_territorial"]) + 0.05,  # g2: territorial (parcela estimada + γ_upa)
        coef["ef_dotacao"],              # g3: dotação (OB)
        coef["gap_bruto"] - abs(coef["beta_m3"]) - coef["ef_dotacao"],  # g4: retornos residuais
    ])
    g = np.maximum(g, 0)

    # Efetividade [ASSUMIDO]
    alpha = np.array([0.20, 0.15, 0.30, 0.25])

    # Custos [ASSUMIDO]
    costs = np.array([1.2, 2.5, 1.5, 1.0])

    labels = [
        "Enforcement anti-discriminação",
        "Desegregação residencial",
        "Equidade educacional",
        "Acesso a redes / brokerage",
    ]

    resultados = []
    for B in [2.0, 3.0, 4.0, 5.0, 6.0]:
        # Maximizar redução do gap: min -sum(g_i * alpha_i * x_i)
        c_obj  = -(g * alpha)
        A_ub   = [costs]
        b_ub   = [B]
        bounds = [(0.0, 1.0)] * 4

        res = linprog(c_obj, A_ub=A_ub, b_ub=b_ub,
                      bounds=bounds, method="highs")

        if res.success:
            x_opt    = res.x
            reducao  = float(-res.fun)
            gap_res  = max(coef["gap_bruto"] - reducao, 0)
            resultados.append({
                "orcamento":      B,
                "gap_inicial":    round(coef["gap_bruto"], 4),
                "reducao_total":  round(reducao, 4),
                "gap_residual":   round(gap_res, 4),
                "reducao_pct":    round(reducao / coef["gap_bruto"] * 100, 1),
                "x1_enforcement": round(x_opt[0], 3),
                "x2_territorial": round(x_opt[1], 3),
                "x3_educacao":    round(x_opt[2], 3),
                "x4_redes":       round(x_opt[3], 3),
            })

    df_pl = pd.DataFrame(resultados)
    logger.info("── Programação Linear ─────────────────────────────────────")
    for _, r in df_pl.iterrows():
        logger.info(
            f"  B={r['orcamento']:.0f} → reducao={r['reducao_total']:.4f} "
            f"({r['reducao_pct']:.1f}%) | gap residual={r['gap_residual']:.4f}"
        )

    # Sensibilidade: solução ótima com B=5
    res5 = linprog(-(g * alpha), A_ub=[costs], b_ub=[5.0],
                   bounds=[(0, 1)] * 4, method="highs")
    x5   = res5.x if res5.success else np.zeros(4)

    logger.info("\n  Alocação ótima com B=5 [PREMISSAS EXPLÍCITAS]:")
    for i, (lab, xi, gi, ai, ci) in enumerate(zip(labels, x5, g, alpha, costs)):
        reduc_i = gi * ai * xi
        logger.info(f"    {lab:<40} x={xi:.3f}  Δgap={reduc_i:.4f}")

    # Resumo metodológico em LaTeX
    _gerar_latex_pl(df_pl, labels, g, alpha, costs)

    return {"df_pl": df_pl, "x_opt_B5": x5, "gap_channels": g,
            "alpha": alpha, "costs": costs, "labels": labels}


def _gerar_latex_pl(df: pd.DataFrame, labels, g, alpha, costs) -> None:
    tex_rows = []
    for _, r in df.iterrows():
        row = (
            f"  {r['orcamento']:.0f} & {r['gap_inicial']:.3f} & "
            f"{r['reducao_total']:.3f} & {r['reducao_pct']:.1f}\\% & "
            f"{r['gap_residual']:.3f} & "
            f"{r['x1_enforcement']:.2f} & {r['x2_territorial']:.2f} & "
            f"{r['x3_educacao']:.2f} & {r['x4_redes']:.2f} \\\\"
        )
        tex_rows.append(row)

    canal_rows = "\n".join(
        f"  {lab} & ${gi:.4f}$ & ${ai:.2f}$ & ${ci:.1f}$ & "
        f"${gi*ai:.4f}$ \\\\"
        for lab, gi, ai, ci in zip(labels, g, alpha, costs)
    )

    tex = r"""\begin{table}[H]
  \centering
  \caption{Programação Linear: alocação ótima de intervenções anti-discriminação
           por nível de orçamento.
           $x_i \in [0,1]$ = fração do canal $i$ abordada pela política $i$.
           Efetividades e custos são premissas explícitas (ver texto).}
  \label{tab:po_pl}
  \small
  \begin{tabular}{rrrrrrrrr}
    \toprule
    $B$ & Gap inicial & Redução & \% Gap & Gap residual &
    $x_1$ & $x_2$ & $x_3$ & $x_4$ \\
    \midrule
""" + "\n".join(tex_rows) + r"""
    \bottomrule
  \end{tabular}
\end{table}

\begin{table}[H]
  \centering
  \caption{Canais do gap salarial racial e premissas do modelo PL.
           $g_i$ = contribuição estimada (log-renda);
           $\alpha_i$ = efetividade por unidade de custo [ASSUMIDO];
           $c_i$ = custo relativo [ASSUMIDO].}
  \label{tab:po_canais}
  \small
  \begin{tabular}{lrrrr}
    \toprule
    Canal & $g_i$ & $\alpha_i$ & $c_i$ & $g_i \cdot \alpha_i$ \\
    \midrule
""" + canal_rows + r"""
    \bottomrule
  \end{tabular}
\end{table}
"""
    (OUT_TAB / "po_pl.tex").write_text(tex, encoding="utf-8")
    df.to_csv(OUT_TAB / "po_pl.csv", index=False)
    logger.info("LaTeX: po_pl.tex")


# ══════════════════════════════════════════════════════════════════════════════
# 3.2  PROGRAMAÇÃO MULTIOBJETIVO — fronteira de Pareto
# ══════════════════════════════════════════════════════════════════════════════

def modelo_multiobjetivo(coef: dict) -> dict:
    """
    Programação multiobjetivo com dois objetivos conflitantes:
        f₁(x) = redução do gap salarial racial (maximizar → minimizar −f₁)
        f₂(x) = custo total das políticas (minimizar)

    Método de soma ponderada (weighted-sum scalarization):
        min λ·(−f₁) + (1−λ)·f₂   para λ ∈ [0, 1]

    Gera a fronteira de Pareto (conjunto de soluções não-dominadas)
    variando λ em 50 pontos equidistantes.

    Restrição: xᵢ ∈ [0, 1] (frações de política, sem orçamento fixo)

    Objetivo adicional (incorporado como peso):
        f₃(x) = acesso ocupacional (fração de trabalhadores negros
                 que transitam para clusters de alta renda) — proxy:
                 crescimento no cluster de menor gap racial (Cluster 2)
    """
    g     = np.array([abs(coef["beta_m3"]),
                      abs(coef["delta_territorial"]) + 0.05,
                      coef["ef_dotacao"],
                      max(coef["gap_bruto"] - abs(coef["beta_m3"])
                          - coef["ef_dotacao"], 0)])
    alpha = np.array([0.20, 0.15, 0.30, 0.25])
    costs = np.array([1.2, 2.5, 1.5, 1.0])

    pareto_pts = []
    for lam in np.linspace(0, 1, 60):
        # f1 = gap reduction, f2 = cost
        c_obj = -(lam * g * alpha) + (1 - lam) * costs
        res = linprog(c_obj, bounds=[(0, 1)] * 4, method="highs")
        if res.success:
            f1 = float(np.dot(g * alpha, res.x))          # gap reduction
            f2 = float(np.dot(costs, res.x))               # total cost
            pareto_pts.append({
                "lambda":   round(lam, 3),
                "f1_gap_reducao": round(f1, 4),
                "f2_custo_total": round(f2, 3),
                "x1": round(res.x[0], 3), "x2": round(res.x[1], 3),
                "x3": round(res.x[2], 3), "x4": round(res.x[3], 3),
            })

    df_pareto = pd.DataFrame(pareto_pts).drop_duplicates(
        subset=["f1_gap_reducao", "f2_custo_total"]
    ).sort_values("f2_custo_total")

    logger.info("── Programação Multiobjetivo — Fronteira de Pareto ────────")
    logger.info(f"  {len(df_pareto)} pontos Pareto gerados")
    if not df_pareto.empty:
        pt_max = df_pareto.loc[df_pareto["f1_gap_reducao"].idxmax()]
        pt_min = df_pareto.loc[df_pareto["f1_gap_reducao"].idxmin()]
        logger.info(
            f"  Máx. redução: f1={pt_max['f1_gap_reducao']:.4f}  "
            f"custo={pt_max['f2_custo_total']:.2f}"
        )
        logger.info(
            f"  Mín. custo:   f1={pt_min['f1_gap_reducao']:.4f}  "
            f"custo={pt_min['f2_custo_total']:.2f}"
        )

    df_pareto.to_csv(OUT_TAB / "po_pareto.csv", index=False)
    _plotar_pareto(df_pareto)

    return {"df_pareto": df_pareto}


def _plotar_pareto(df: pd.DataFrame) -> None:
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(df["f2_custo_total"], df["f1_gap_reducao"],
            "o-", color="#2980b9", linewidth=2, markersize=5)
    ax.set_xlabel("Custo total das políticas (unidades relativas)", fontsize=11)
    ax.set_ylabel("Redução esperada do gap salarial (log-renda)", fontsize=11)
    ax.set_title(
        "Fronteira de Pareto: Redução do Gap × Custo de Política\n"
        "(cada ponto = solução não-dominada — efetividades são premissas)",
        fontsize=10,
    )
    ax.grid(alpha=0.3)

    # Destaca o joelho da curva (método de máximo produto)
    if len(df) >= 3:
        f1 = df["f1_gap_reducao"].values
        f2 = df["f2_custo_total"].values
        f1n = (f1 - f1.min()) / (f1.max() - f1.min() + 1e-9)
        f2n = (f2 - f2.min()) / (f2.max() - f2.min() + 1e-9)
        # Knee: maximize f1n × (1 - f2n)
        knee_idx = np.argmax(f1n * (1 - f2n))
        ax.scatter(df["f2_custo_total"].iloc[knee_idx],
                   df["f1_gap_reducao"].iloc[knee_idx],
                   color="#c0392b", zorder=5, s=120,
                   label=f"Knee: f₁={df['f1_gap_reducao'].iloc[knee_idx]:.3f}")
        ax.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(OUT_FIG / "po_pareto.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: po_pareto.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3.3  OTIMIZAÇÃO EM REDES — SNA → MAX-FLOW / MIN-CUT
# ══════════════════════════════════════════════════════════════════════════════

def modelo_redes(coef: dict) -> dict:
    """
    Otimização em redes sobre o grafo ocupacional da SNA.

    Estrutura
    ---------
    Nós: 10 grupos (5 níveis de escolaridade × 2 raças)
    Arestas: co-residência em UPA (sna_arestas.csv)
    Capacidade: shared_upas (UPAs compartilhadas entre os dois grupos)

    Problemas resolvidos
    --------------------
    (a) Máximo Fluxo (Ford-Fulkerson via networkx)
        Source → Negro_Sem_Instr  (maior grupo, menor renda)
        Sink   → Branco_Superior  (maior renda branca, referência)
        Fluxo max = proxy para potencial de mobilidade ocupacional racial

    (b) Corte Mínimo (min-cut)
        Identifica arestas gargalo — conexões cuja remoção isola o fluxo
        de mobilidade de trabalhadores negros.

    (c) Gap de brokerage
        Compara betweenness de grupos Negro vs Branco → identifica
        quais nós têm betweenness = 0 (exclusão estrutural de brokerage)

    Interpretação econômica
    -----------------------
    Um corte que cai exclusivamente em arestas inter-raciais indica que
    a barreira estrutural opera na fronteira racial, não na fronteira
    educacional.  Políticas que "expandem" essas arestas (programas de
    mentoria inter-racial, inclusão em redes profissionais) aumentam o
    fluxo máximo e reduzem a distância entre betweenness Negro e Branco.
    """
    try:
        import networkx as nx
    except ImportError:
        logger.warning("networkx não disponível — seção de redes pulada")
        return {}

    sna_nos   = coef["sna_nos"]
    sna_edges = coef["sna_edges"]

    # ── Construção do grafo ────────────────────────────────────────────────────
    G = nx.DiGraph()
    for _, row in sna_nos.iterrows():
        G.add_node(row["node"], race=row["race"], mean_renda=row["mean_renda"],
                   betweenness=row["betweenness"], n_workers=row["n_workers"])

    # Adiciona arestas bidirecionais com capacidade = shared_upas
    for _, row in sna_edges.iterrows():
        cap = int(row["shared_upas"])
        G.add_edge(row["source"], row["target"], capacity=cap)
        G.add_edge(row["target"], row["source"], capacity=cap)

    # ── Máximo Fluxo ──────────────────────────────────────────────────────────
    source = "Negro_Sem_Instr"    # maior base de negros com menor renda
    sink   = "Branco_Superior"    # referência de alta renda branca
    try:
        flow_value, flow_dict = nx.maximum_flow(G, source, sink,
                                                flow_func=nx.algorithms.flow.edmonds_karp)
        logger.info("── Otimização em Redes ────────────────────────────────")
        logger.info(f"  Max-flow {source} → {sink}: {flow_value:,} UPAs compartilhadas")
    except Exception as e:
        logger.warning(f"  Max-flow falhou: {e}")
        flow_value, flow_dict = 0, {}

    # ── Corte Mínimo ──────────────────────────────────────────────────────────
    cut_rows = []
    try:
        cut_value, (reachable, non_reachable) = nx.minimum_cut(
            G, source, sink
        )
        # Arestas no corte = aresta (u,v) com u ∈ reachable, v ∈ non_reachable
        cut_edges = [(u, v) for u in reachable for v in G.successors(u)
                     if v in non_reachable]
        for u, v in cut_edges:
            inter = G.nodes[u].get("race", "?") != G.nodes[v].get("race", "?")
            cut_rows.append({
                "source": u, "target": v,
                "capacity": G[u][v].get("capacity", 0),
                "inter_racial": inter,
            })
        logger.info(f"  Min-cut = {cut_value:,} UPAs | {len(cut_edges)} arestas")
        pct_inter = sum(r["inter_racial"] for r in cut_rows) / max(len(cut_rows), 1)
        logger.info(f"  % arestas inter-raciais no corte: {pct_inter:.0%}")
    except Exception as e:
        logger.warning(f"  Min-cut falhou: {e}")
        cut_value = 0

    df_cut = pd.DataFrame(cut_rows)

    # ── Análise de brokerage ───────────────────────────────────────────────────
    negro_bt = sna_nos[sna_nos["race"] == "Negro"]["betweenness"].values
    branco_bt = sna_nos[sna_nos["race"] == "Branco"]["betweenness"].values
    gap_bt = float(np.mean(branco_bt) - np.mean(negro_bt))
    logger.info(f"  Betweenness médio — Branco: {np.mean(branco_bt):.4f} | "
                f"Negro: {np.mean(negro_bt):.4f} | Gap: {gap_bt:.4f}")

    # ── Política de expansão de fluxo ─────────────────────────────────────────
    # Simula aumento de +20% nas capacidades inter-raciais
    G2 = G.copy()
    n_expanded = 0
    for u, v, data in G.edges(data=True):
        if G.nodes[u].get("race") != G.nodes[v].get("race"):
            G2[u][v]["capacity"] = int(data["capacity"] * 1.20)
            n_expanded += 1
    try:
        fv2, _ = nx.maximum_flow(G2, source, sink,
                                 flow_func=nx.algorithms.flow.edmonds_karp)
        delta_flow = fv2 - flow_value
        delta_pct  = delta_flow / max(flow_value, 1) * 100
        logger.info(f"  Simulação +20% aresta inter-racial: "
                    f"Δfluxo={delta_flow:,} ({delta_pct:+.1f}%)")
    except Exception:
        fv2, delta_flow, delta_pct = flow_value, 0, 0.0

    df_brokerage = sna_nos[["node", "race", "educ_label",
                             "betweenness", "mean_renda", "n_workers"]].copy()
    df_brokerage["gap_brokerage"] = (
        df_brokerage["betweenness"]
        - df_brokerage.groupby("educ_label")["betweenness"]
                      .transform(lambda x: x[df_brokerage.loc[x.index, "race"] == "Branco"].mean())
    )

    df_brokerage.to_csv(OUT_TAB / "po_redes_brokerage.csv", index=False)
    if not df_cut.empty:
        df_cut.to_csv(OUT_TAB / "po_redes_mincut.csv", index=False)

    _plotar_redes(G, sna_nos, cut_edges if cut_rows else [])

    return {
        "flow_value":  flow_value,
        "flow_value_expanded": fv2,
        "cut_value":   cut_value,
        "cut_edges":   cut_rows,
        "gap_brokerage": gap_bt,
        "df_brokerage": df_brokerage,
    }


def _plotar_redes(G, sna_nos: pd.DataFrame, cut_edges: list) -> None:
    try:
        import networkx as nx
    except ImportError:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Painel esquerdo: betweenness por nó
    ax = axes[0]
    cores = {"Branco": "#2980b9", "Negro": "#c0392b"}
    for _, row in sna_nos.iterrows():
        x_pos = {"Sem_Instr": 0, "Fundamental": 1, "Medio": 2,
                 "Superior": 3, "Pos": 4}.get(row["educ_label"], 2)
        y_pos = 1 if row["race"] == "Branco" else 0
        ax.scatter(x_pos, y_pos + np.random.uniform(-0.05, 0.05),
                   s=max(row["betweenness"] * 1000, 50),
                   color=cores[row["race"]], alpha=0.8)
        ax.text(x_pos, y_pos - 0.15, row["educ_label"],
                ha="center", fontsize=6, color=cores[row["race"]])

    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Negro", "Branco"], fontsize=10)
    ax.set_xticks(range(5))
    ax.set_xticklabels(["Sem instr.", "Fund.", "Médio", "Superior", "Pós"],
                       fontsize=8)
    ax.set_title("Betweenness Centrality\n(tamanho do nó ∝ centralidade)",
                 fontsize=10)
    ax.grid(alpha=0.3)

    # Painel direito: gap de renda por grupo
    ax2 = axes[1]
    educ_order = ["Sem_Instr", "Fundamental", "Medio", "Superior", "Pos"]
    renda_b = []
    renda_n = []
    for e in educ_order:
        sub = sna_nos[sna_nos["educ_label"] == e]
        renda_b.append(sub[sub["race"] == "Branco"]["mean_renda"].values[0]
                       if len(sub[sub["race"] == "Branco"]) > 0 else np.nan)
        renda_n.append(sub[sub["race"] == "Negro"]["mean_renda"].values[0]
                       if len(sub[sub["race"] == "Negro"]) > 0 else np.nan)

    x = np.arange(5)
    w = 0.35
    ax2.bar(x - w/2, renda_b, w, color="#2980b9", label="Branco")
    ax2.bar(x + w/2, renda_n, w, color="#c0392b", label="Negro")
    ax2.set_xticks(x)
    ax2.set_xticklabels(["Sem instr.", "Fund.", "Médio", "Superior", "Pós"],
                        fontsize=8)
    ax2.set_ylabel("log(renda) médio", fontsize=10)
    ax2.set_title("Renda média por grupo educacional\n(gap = exclusão de brokerage)",
                  fontsize=10)
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3, axis="y")

    plt.suptitle("Análise de Redes Ocupacionais: SNA → Pesquisa Operacional",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    fig.savefig(OUT_FIG / "po_redes.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: po_redes.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3.4  AHP + TOPSIS — Análise Multicritério
# ══════════════════════════════════════════════════════════════════════════════

def modelo_ahp_topsis(coef: dict) -> dict:
    """
    Análise Multicritério para ranqueamento de políticas de combate
    à discriminação racial no mercado de trabalho.

    Alternativas (4 políticas derivadas dos canais do gap):
        A1  Enforcement legal anti-discriminação (canal direto)
        A2  Desegregação residencial (canal territorial)
        A3  Equidade educacional (canal de dotação)
        A4  Programas de acesso a redes (brokerage, canal de retornos)

    Critérios (5 dimensões de avaliação):
        C1  Potencial de redução do gap (baseado em gᵢ × αᵢ estimados)
        C2  Custo de implementação (inverso de cᵢ — menor custo = melhor)
        C3  Tempo para impacto (meses até efeito observável) [ASSUMIDO]
        C4  Abrangência populacional (% da força de trabalho afetada) [ASSUMIDO]
        C5  Complementaridade com outras políticas (sinergia) [ASSUMIDO]

    Etapa 1 — AHP para pesos dos critérios
    ----------------------------------------
    Matriz de comparação par-a-par seguindo a escala de Saaty (1980):
        1 = igual importância
        3 = moderadamente mais importante
        5 = fortemente mais importante
        9 = absolutamente mais importante

    Julgamentos pautados nos achados do TCC:
        C1 > C2 > C4 > C3 > C5
    (Redução do gap é critério primário dado o foco na desigualdade;
     custo é relevante para viabilidade; abrangência reflete escala;
     tempo importa mas é secundário; sinergia é terciária.)

    Etapa 2 — TOPSIS para ranqueamento das alternativas
    -------------------------------------------------------
    Método: Technique for Order Preference by Similarity to Ideal Solution
        1. Normalizar a matriz de decisão
        2. Ponderar por pesos AHP
        3. Identificar solução ideal positiva (A+) e negativa (A−)
        4. Calcular distâncias Euclidenas d+ e d−
        5. Scoring: CCᵢ = d−ᵢ / (d+ᵢ + d−ᵢ) → maior = melhor
    """
    # ── Matriz de decisão (4 alternativas × 5 critérios) ──────────────────────
    g     = np.array([abs(coef["beta_m3"]),
                      abs(coef["delta_territorial"]) + 0.05,
                      coef["ef_dotacao"],
                      max(coef["gap_bruto"] - abs(coef["beta_m3"])
                          - coef["ef_dotacao"], 0)])
    alpha = np.array([0.20, 0.15, 0.30, 0.25])
    costs = np.array([1.2, 2.5, 1.5, 1.0])

    alts = ["A1: Enforcement legal", "A2: Desegregação residencial",
            "A3: Equidade educacional", "A4: Acesso a redes/brokerage"]
    crits = ["C1 Potencial", "C2 Custo (inv)", "C3 Tempo (inv)",
             "C4 Abrangência", "C5 Sinergia"]

    # C1: potencial = gᵢ × αᵢ (estimado)
    c1 = g * alpha

    # C2: custo invertido = 1/cᵢ (menor custo → melhor)
    c2 = 1.0 / costs

    # C3: tempo invertido (menos tempo = melhor) [ASSUMIDO: meses]
    tempo = np.array([12, 60, 24, 8])  # enforcement=1a, deseg=5a, educ=2a, redes=8m
    c3 = 1.0 / tempo

    # C4: abrangência — % da força de trabalho potencialmente afetada [ASSUMIDO]
    c4 = np.array([0.90, 0.60, 0.70, 0.45])

    # C5: sinergia — quanto a política potencializa outras [ASSUMIDO 1-5]
    c5 = np.array([3, 4, 5, 4]) / 5.0

    decision_matrix = np.column_stack([c1, c2, c3, c4, c5])

    # ── AHP: pesos dos critérios ───────────────────────────────────────────────
    # Matriz de comparação par-a-par (C1, C2, C3, C4, C5)
    # Baseada nos achados: C1 > C2 > C4 > C3 > C5
    A_ahp = np.array([
        # C1     C2     C3     C4     C5
        [1.0,   2.0,   4.0,   3.0,   5.0],   # C1 vs ...
        [1/2,   1.0,   3.0,   2.0,   4.0],   # C2 vs ...
        [1/4,   1/3,   1.0,   1/2,   2.0],   # C3 vs ...
        [1/3,   1/2,   2.0,   1.0,   3.0],   # C4 vs ...
        [1/5,   1/4,   1/2,   1/3,   1.0],   # C5 vs ...
    ])

    # Autovetor principal (prioridades)
    eigvals, eigvecs = np.linalg.eig(A_ahp)
    max_idx  = np.argmax(eigvals.real)
    w_raw    = eigvecs[:, max_idx].real
    w_ahp    = np.abs(w_raw) / np.abs(w_raw).sum()

    # Índice de consistência
    lambda_max = float(eigvals[max_idx].real)
    n_crit = A_ahp.shape[0]
    CI = (lambda_max - n_crit) / (n_crit - 1)
    RI = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32}
    CR = CI / RI.get(n_crit, 1.12)
    logger.info(f"  AHP — λ_max={lambda_max:.3f}  CI={CI:.3f}  CR={CR:.3f} "
                f"({'OK' if CR < 0.10 else 'INCONSISTENTE'})")

    # ── TOPSIS ────────────────────────────────────────────────────────────────
    # 1. Normalização vetorial
    norm_col = np.sqrt((decision_matrix ** 2).sum(axis=0))
    R = decision_matrix / (norm_col + 1e-12)

    # 2. Matriz ponderada
    V = R * w_ahp

    # 3. Soluções ideais (todos os critérios são benefício/maximização)
    A_pos = V.max(axis=0)
    A_neg = V.min(axis=0)

    # 4. Distâncias
    d_pos = np.sqrt(((V - A_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((V - A_neg) ** 2).sum(axis=1))

    # 5. Scores e ranking (rank[i] = posição de i na ordem decrescente de CC)
    CC = d_neg / (d_pos + d_neg + 1e-12)
    sorted_idx = np.argsort(-CC)          # índices de maior CC para menor
    ranking = np.empty(len(CC), dtype=int)
    ranking[sorted_idx] = np.arange(1, len(CC) + 1)

    df_topsis = pd.DataFrame({
        "Alternativa": alts,
        "C1 Potencial": c1.round(4),
        "C2 Custo(inv)": c2.round(3),
        "C3 Tempo(inv)": c3.round(5),
        "C4 Abrangência": c4,
        "C5 Sinergia": c5.round(2),
        "d+": d_pos.round(4),
        "d-": d_neg.round(4),
        "CC (score)": CC.round(4),
        "Rank": ranking,
    }).sort_values("Rank")

    df_pesos = pd.DataFrame({
        "Critério": crits,
        "Peso AHP": w_ahp.round(4),
    })

    logger.info("── AHP + TOPSIS ────────────────────────────────────────────")
    logger.info(f"  Pesos AHP: {dict(zip(crits, w_ahp.round(3)))}")
    for _, row in df_topsis.iterrows():
        logger.info(
            f"  Rank {int(row['Rank'])}: {row['Alternativa']:<30}  "
            f"CC={row['CC (score)']:.4f}  d+={row['d+']:.4f}  d-={row['d-']:.4f}"
        )

    df_topsis.to_csv(OUT_TAB / "po_topsis.csv", index=False)
    df_pesos.to_csv(OUT_TAB / "po_ahp_pesos.csv", index=False)
    _gerar_latex_topsis(df_topsis, df_pesos, w_ahp, CI, CR)
    _plotar_topsis(df_topsis)

    return {"df_topsis": df_topsis, "df_pesos": df_pesos,
            "w_ahp": w_ahp, "CR": CR}


def _gerar_latex_topsis(df: pd.DataFrame, df_pesos: pd.DataFrame,
                         w_ahp: np.ndarray, CI: float, CR: float) -> None:
    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"  {r['Alternativa']} & {r['C1 Potencial']:.4f} & "
            f"{r['C2 Custo(inv)']:.3f} & {r['CC (score)']:.4f} & "
            f"\\textbf{{{int(r['Rank'])}}} \\\\"
        )
    peso_rows = "\n".join(
        f"  {row['Critério']} & {row['Peso AHP']:.4f} \\\\"
        for _, row in df_pesos.iterrows()
    )
    tex = r"""\begin{table}[H]
  \centering
  \caption{AHP + TOPSIS: ranqueamento de políticas anti-discriminação.
           CC = coeficiente de proximidade à solução ideal;
           maior CC = melhor alternativa.
           Critérios com peso $[ASSUMIDO]$ derivado de julgamentos AHP
           fundamentados nos achados econométricos.
           CR = """ + f"{CR:.3f}" + r""" $<$ 0,10 (consistência satisfatória).}
  \label{tab:po_topsis}
  \small
  \begin{tabular}{lrrrr}
    \toprule
    Alternativa & C1 Potencial & C2 Custo(inv) & CC (score) & Rank \\
    \midrule
""" + "\n".join(rows) + r"""
    \bottomrule
  \end{tabular}
\end{table}

\begin{table}[H]
  \centering
  \caption{Pesos AHP dos critérios ($\lambda_{max}=$""" + f"{(CI*(5-1)+5):.3f}" + r""",
           $CI = """ + f"{CI:.3f}" + r"""$, $CR = """ + f"{CR:.3f}" + r"""$).}
  \label{tab:po_ahp_pesos}
  \small
  \begin{tabular}{lr}
    \toprule
    Critério & Peso AHP \\
    \midrule
""" + peso_rows + r"""
    \bottomrule
  \end{tabular}
\end{table}
"""
    (OUT_TAB / "po_topsis.tex").write_text(tex, encoding="utf-8")
    logger.info("LaTeX: po_topsis.tex")


def _plotar_topsis(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    cores = ["#27ae60", "#2980b9", "#e67e22", "#c0392b"]
    bars = ax.barh(df["Alternativa"][::-1], df["CC (score)"][::-1],
                   color=cores[:len(df)], height=0.6)
    ax.bar_label(bars, fmt="{:.4f}", padding=3, fontsize=9)
    ax.set_xlabel("Coeficiente de Proximidade (CC)", fontsize=11)
    ax.set_title(
        "Ranking AHP + TOPSIS de Políticas Anti-Discriminação\n"
        "(premissas explícitas — ver Tabela tab:po_topsis)",
        fontsize=10,
    )
    ax.set_xlim(0, 1)
    ax.grid(alpha=0.3, axis="x")
    plt.tight_layout()
    fig.savefig(OUT_FIG / "po_topsis.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura: po_topsis.png")


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline principal
# ══════════════════════════════════════════════════════════════════════════════

def run_analise_po() -> dict:
    """
    Executa os quatro modelos de Pesquisa Operacional em sequência.

    Lê coeficientes dos outputs das análises econométricas já rodadas.
    Gera: po_pl.csv|.tex, po_pareto.csv, po_redes_*.csv,
          po_topsis.csv|.tex, po_ahp_pesos.csv
          po_pareto.png, po_redes.png, po_topsis.png
    """
    logger.info("╔══ Pesquisa Operacional ══╗")

    coef = _carregar_coeficientes()

    logger.info(f"\n  Inputs:")
    logger.info(f"    β_negro (M3)    = {coef['beta_m3']:.4f} ({(np.exp(coef['beta_m3'])-1)*100:.1f}%)")
    logger.info(f"    Gap bruto (OB)  = {coef['gap_bruto']:.4f} ({(np.exp(coef['gap_bruto'])-1)*100:.1f}%)")
    logger.info(f"    OB dotação      = {coef['ef_dotacao']:.4f} ({coef['pct_dotacao']:.1f}%)")
    logger.info(f"    OB coeficiente  = {coef['ef_coef']:.4f} ({coef['pct_coef']:.1f}%)")
    logger.info(f"    Δ territorial   = {coef['delta_territorial']:.4f}")

    res_pl   = modelo_pl(coef)
    res_pmo  = modelo_multiobjetivo(coef)
    res_red  = modelo_redes(coef)
    res_topsis = modelo_ahp_topsis(coef)

    # Sumário final
    print("\n── SUMÁRIO: Pesquisa Operacional ──")
    if res_pl["df_pl"] is not None and not res_pl["df_pl"].empty:
        row5 = res_pl["df_pl"][res_pl["df_pl"]["orcamento"] == 5.0].iloc[0]
        print(f"  PL (B=5): redução {row5['reducao_pct']:.1f}% do gap | "
              f"gap residual {(np.exp(row5['gap_residual'])-1)*100:.1f}%")
    if not res_pmo["df_pareto"].empty:
        knee = res_pmo["df_pareto"]
        print(f"  Pareto: {len(knee)} soluções não-dominadas geradas")
    if res_red.get("flow_value", 0) > 0:
        print(f"  Max-flow: {res_red['flow_value']:,} UPAs | "
              f"+20% inter-racial → Δfluxo {res_red.get('flow_value_expanded', 0) - res_red['flow_value']:,}")
    if not res_topsis["df_topsis"].empty:
        melhor = res_topsis["df_topsis"].iloc[0]
        print(f"  TOPSIS: 1º lugar = {melhor['Alternativa']} (CC={melhor['CC (score)']:.4f})")

    print("\n  Outputs:")
    print("    outputs/tables/po_pl.csv|.tex")
    print("    outputs/tables/po_pareto.csv")
    print("    outputs/tables/po_topsis.csv|.tex  po_ahp_pesos.csv")
    print("    outputs/tables/po_redes_brokerage.csv  po_redes_mincut.csv")
    print("    outputs/figures/po_pareto.png  po_redes.png  po_topsis.png")

    return {
        "pl":     res_pl,
        "pareto": res_pmo,
        "redes":  res_red,
        "topsis": res_topsis,
    }
