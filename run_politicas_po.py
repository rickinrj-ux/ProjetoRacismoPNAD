"""
run_politicas_po.py
===================
Pesquisa Operacional aplicada à proposta de políticas públicas anti-discriminação.

Traduz os coeficientes econométricos confirmados (HLM, OB, GLMM, QR) em quatro
modelos de decisão para priorização e alocação ótima de intervenções:

    PL-1  Programação Linear com 6 canais de gap — alocação por orçamento
    PL-2  PL biobjetivo: minimizar gap salarial (QR) + gap de acesso (GLMM)
    PMO   Fronteira de Pareto (impacto vs custo)
    AHP+TOPSIS  Ranking multicritério de 6 políticas

Parâmetros confirmados pelos modelos (não assumidos):
    gap_bruto         = 0.4229   (OB global, 52.6%)
    dotacoes_pct      = 84.0%    (OB: segregação ocupacional/educacional)
    retornos_pct      = 16.0%    (OB: discriminação de remuneração)
    or_cbo14_m1       = 0.708    (GLMM Python logit, ocp_qualif, N=2.395.285)
    ame_cbo14_m1      = -1.30pp  (GLMM M1)
    or_top20_m1       = 0.726    (GLMM)
    or_top10_m1       = 0.671    (GLMM — gradiente glass ceiling)
    qr_q10            = -8.21%   (QR M3)
    qr_q90            = -11.80%  (QR M3)
    delta_kb          = -3.59pp  (KB test: β_q90 - β_q10)
    icc_upa_acesso    = 26.2%    (GLMM lme4 R, random intercept UPA)
    icc_uf_salario    = 9.83%    (HLM)
    eb_temporal_ini   = 17.8%    (OB Retornos 2016-2018)
    eb_temporal_rec   = 15.7%    (OB Retornos 2022-2025)

Premissas de efetividade [ASSUMIDO — premissas normativas explícitas]:
    Baseadas em literatura de avaliação de políticas afirmativas
    (Bertrand & Duflo, 2017; Holzer & Neumark, 2000; Kijima, 2006).
    Não são previsões causais positivas — são cenários de planejamento.

Referências:
    Saaty (1980) AHP; Hwang & Yoon (1981) TOPSIS; Koenker (2005) QR;
    Charnes, Cooper & Rhodes (1978) DEA; Darity & Mason (1998) gap racial.
"""

import sys
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

sys.stdout.reconfigure(encoding="utf-8")

ROOT    = Path(__file__).parent
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_FIG.mkdir(parents=True, exist_ok=True)
OUT_TAB.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/politicas_po.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

Path("logs").mkdir(exist_ok=True)

# ── Parâmetros confirmados pelos modelos ──────────────────────────────────────

# Gap salarial (log-rendimento, OB)
GAP_BRUTO   = 0.4229   # gap total bruto
DOTACOES    = 0.3550   # efeito dotações (84.0%)
RETORNOS    = 0.0679   # efeito retornos (16.0%)

# GLMM logístico (log-odds gap = -ln(OR))
LOG_ODDS_CBO14 = -np.log(0.708)   # = 0.3455  barreira de acesso CBO 1-4
LOG_ODDS_TOP20 = -np.log(0.726)   # = 0.3199  barreira top 20%
LOG_ODDS_TOP10 = -np.log(0.671)   # = 0.3991  barreira top 10%

# QR: gap q10 e q90 em log-renda (M3)
QR_Q10 = 0.0857   # |β_q10|
QR_Q90 = 0.1256   # |β_q90|
DELTA_KB = QR_Q90 - QR_Q10  # 0.0399 = glass ceiling de progressão

# ICC mediation
ICC_UPA = 0.262   # acesso ocupacional
ICC_UF  = 0.098   # salários

# ── Definição das 6 políticas ─────────────────────────────────────────────────
#
#  Canal  | Nome curto         | Ataca                       | Mecanismo
#  -------|--------------------|-----------------------------|-------------------
#  P1     | Cotas CBO 1-4      | OR=0.708 (GLMM)            | Acesso qualificado
#  P2     | Enforcement        | Retornos=16% (OB)          | Discriminação direta
#  P3     | Equidade Educac.   | Dotações=84% (OB)          | Capital humano
#  P4     | Desegregação Resid | ICC_UPA=26.2% (GLMM)       | Territorial
#  P5     | Mentoria/Redes     | SNA brokerage              | Redes profissionais
#  P6     | Transparência Sal. | Remuneração intra-ocupação | Glass ceiling QR
#
POLITICAS = [
    "Cotas ocupacionais CBO 1–4",
    "Enforcement anti-discriminação",
    "Equidade educacional (cotas/bolsas)",
    "Desegregação residencial",
    "Mentoria e redes profissionais",
    "Transparência salarial obrigatória",
]

# Contribuição de cada canal ao gap salarial bruto (log-renda) [CALCULADO + ASSUMIDO]
# P1 ataca LOG_ODDS_CBO14 convertido para log-renda via mediação OB (dotações)
# P3 ataca DOTACOES diretamente
# P2 ataca RETORNOS diretamente
# P4 ataca ICC_UPA × gap bruto (parcela contextual)
# P5 ataca SNA gap (heurística ~15% do gap bruto)
# P6 ataca QR glass ceiling (DELTA_KB convertido para redução de gap médio)
G = np.array([
    LOG_ODDS_CBO14 * 0.30,   # P1: 30% do log-odds de acesso se reflete no salário via OB
    RETORNOS,                 # P2: retornos diferenciais integrais
    DOTACOES * 0.50,          # P3: equidade educ. reduz 50% da gap de dotações (parcial, longo prazo)
    ICC_UPA * GAP_BRUTO,      # P4: parcela territorial (contextual)
    GAP_BRUTO * 0.12,         # P5: redes/brokerage — ~12% do gap bruto [ASSUMIDO]
    DELTA_KB * 0.50,          # P6: transparência reduz metade do glass ceiling progression
])
G = np.maximum(G, 0.01)

# Efetividade α_i: redução no canal i por unidade de custo [ASSUMIDO]
# Baseada em Holzer & Neumark (2000) e Bertrand & Duflo (2017)
ALPHA = np.array([
    0.35,  # P1: cotas CBO — alta efetividade no acesso (evidência Índia/Brasil cotas)
    0.20,  # P2: enforcement — moderado (burocracia judicial lenta)
    0.25,  # P3: equidade educacional — alto (retorno 10+ anos)
    0.10,  # P4: desegregação — baixo por unidade (infra cara, efeito lento)
    0.30,  # P5: mentoria — alto (baixo custo unitário, efeito redes documentado)
    0.25,  # P6: transparência salarial — alto (enforcement corporativo direto)
])

# Custo relativo c_i (normalizado; 1.0 = custo de referência = programa de mentoria)
CUSTOS = np.array([
    1.5,   # P1: cotas CBO — custo regulatório + resistência
    1.2,   # P2: enforcement — aparato fiscal/judicial
    2.0,   # P3: equidade educacional — subsídios e infraestrutura
    4.0,   # P4: desegregação — habitação/infraestrutura urbana
    1.0,   # P5: mentoria — custo de referência
    0.8,   # P6: transparência — baixo custo (regulação, auditoria)
])

# Tempo de efeito em anos (para análise de impacto temporal)
TEMPO_EFEITO = np.array([2, 3, 8, 15, 2, 1])  # P4 e P3 são estruturais/lentos


# ══════════════════════════════════════════════════════════════════════════════
# PL-1: Alocação ótima por orçamento — minimizar gap salarial
# ══════════════════════════════════════════════════════════════════════════════

def pl1_alocacao_orcamento():
    log.info("══ PL-1: Alocação ótima por orçamento ══")
    resultados = []
    for B in [2.0, 3.0, 4.0, 5.0, 6.0, 8.0]:
        res = linprog(
            -(G * ALPHA),
            A_ub=[CUSTOS], b_ub=[B],
            bounds=[(0.0, 1.0)] * 6,
            method="highs"
        )
        if res.success:
            x = res.x
            reducao = float(-res.fun)
            gap_res = max(GAP_BRUTO - reducao, 0)
            row = {"orcamento": B, "gap_inicial": round(GAP_BRUTO, 4),
                   "reducao": round(reducao, 4),
                   "reducao_pct": round(reducao / GAP_BRUTO * 100, 1),
                   "gap_residual": round(gap_res, 4)}
            for i, p in enumerate(POLITICAS):
                row[f"x{i+1}"] = round(x[i], 3)
            resultados.append(row)
            log.info(f"  B={B:.0f} → Δgap={reducao:.4f} ({row['reducao_pct']:.1f}%) "
                     f"| gap_res={gap_res:.4f}")

    df = pd.DataFrame(resultados)
    df.to_csv(OUT_TAB / "po_politicas_pl1.csv", index=False)

    # Figura: gap residual vs orçamento + composição ótima
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    cores = ["#2166AC", "#4DAC26", "#D01C8B", "#FDB863", "#E66101", "#7FBC41"]

    ax = axes[0]
    ax.plot(df["orcamento"], df["gap_residual"], "o-", color="#D01C8B", lw=2, ms=7)
    ax.axhline(y=GAP_BRUTO, color="gray", ls="--", lw=1, label="Gap sem intervenção")
    ax.set_xlabel("Orçamento (unidades de custo)", fontsize=11)
    ax.set_ylabel("Gap salarial residual (log-renda)", fontsize=11)
    ax.set_title("PL-1: Redução do Gap por Nível de Orçamento", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=0.3)

    ax2 = axes[1]
    B5_row = df[df["orcamento"] == 5.0]
    if len(B5_row):
        vals = [float(B5_row[f"x{i+1}"]) for i in range(6)]
        ax2.barh(POLITICAS, vals, color=cores)
        ax2.set_xlabel("Fração do canal alocada (x_i)", fontsize=11)
        ax2.set_title("Alocação Ótima com B=5 (GLMM + OB integrados)", fontsize=12, fontweight="bold")
        ax2.set_xlim(0, 1.05); ax2.grid(alpha=0.3, axis="x")
        for i, v in enumerate(vals):
            ax2.text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUT_FIG / "po_politicas_pl1.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  po_politicas_pl1.csv + po_politicas_pl1.png salvos.")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# PL-2: Biobjetivo — minimizar gap salarial QR-q90 E gap de acesso GLMM
# ══════════════════════════════════════════════════════════════════════════════

def pl2_biobjetivo():
    """
    Teto de vidro duplo exige dois objetivos simultâneos:
        f1 = redução do gap salarial (HLM/QR)
        f2 = redução do gap de acesso (GLMM: log-odds CBO 1-4)

    Política P1 (cotas CBO) tem maior peso em f2.
    Política P6 (transparência salarial) tem maior peso em f1.
    Scalarização convexa: min λ×(-f1) + (1-λ)×(-f2) para λ ∈ [0.1, 0.9]
    """
    log.info("══ PL-2: Biobjetivo salarial × acesso (teto de vidro duplo) ══")

    # Contribuição de cada política ao gap de acesso (log-odds)
    G_ACESSO = np.array([
        LOG_ODDS_CBO14 * 0.70,  # P1: ataca diretamente o acesso CBO 1-4
        LOG_ODDS_TOP20 * 0.20,  # P2: enforcement abre acesso via discriminação legal
        LOG_ODDS_TOP10 * 0.15,  # P3: educação tem efeito lento no acesso ao topo
        ICC_UPA * LOG_ODDS_CBO14 * 0.50,  # P4: desegregação reduz barreira territorial de acesso
        LOG_ODDS_CBO14 * 0.25,  # P5: redes melhoram acesso via brokerage (SNA)
        LOG_ODDS_TOP20 * 0.10,  # P6: transparência melhora acesso por reduzir discriminação oculta
    ])
    G_ACESSO = np.maximum(G_ACESSO, 0.01)

    pareto_points = []
    B = 5.0
    lambdas = np.linspace(0.05, 0.95, 19)
    for lam in lambdas:
        c_obj = -(lam * G * ALPHA + (1 - lam) * G_ACESSO * ALPHA)
        res = linprog(c_obj, A_ub=[CUSTOS], b_ub=[B],
                      bounds=[(0.0, 1.0)] * 6, method="highs")
        if res.success:
            x = res.x
            f1 = float(np.dot(G * ALPHA, x))
            f2 = float(np.dot(G_ACESSO * ALPHA, x))
            pareto_points.append({"lambda": round(lam, 2), "f1_gap_sal": round(f1, 4),
                                   "f2_gap_acesso": round(f2, 4),
                                   **{f"x{i+1}": round(x[i], 3) for i in range(6)}})

    df_par = pd.DataFrame(pareto_points)
    df_par.to_csv(OUT_TAB / "po_politicas_pl2_pareto.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    ax = axes[0]
    sc = ax.scatter(df_par["f2_gap_acesso"], df_par["f1_gap_sal"],
                    c=df_par["lambda"], cmap="coolwarm", s=80, zorder=3)
    ax.plot(df_par["f2_gap_acesso"], df_par["f1_gap_sal"], "k-", alpha=0.3, lw=1)
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("λ (peso gap salarial)", fontsize=9)
    ax.set_xlabel("Redução gap de acesso (log-odds GLMM)", fontsize=10)
    ax.set_ylabel("Redução gap salarial (log-renda OB/QR)", fontsize=10)
    ax.set_title("Fronteira de Pareto — Teto de Vidro Duplo\n(B=5 unidades de custo)", fontsize=11, fontweight="bold")
    ax.grid(alpha=0.3)
    # Destaque no ponto de equilíbrio λ=0.5
    eq = df_par[df_par["lambda"] == 0.50]
    if len(eq):
        ax.scatter(eq["f2_gap_acesso"], eq["f1_gap_sal"], s=200, color="gold",
                   edgecolors="black", zorder=5, label="λ=0.5 (equilíbrio)")
        ax.legend(fontsize=9)

    ax2 = axes[1]
    eq_row = df_par[df_par["lambda"] == 0.50]
    if len(eq_row):
        vals = [float(eq_row[f"x{i+1}"]) for i in range(6)]
        cores = ["#2166AC", "#4DAC26", "#D01C8B", "#FDB863", "#E66101", "#7FBC41"]
        ax2.barh(POLITICAS, vals, color=cores)
        ax2.set_xlabel("Fração do canal (x_i) — λ=0.5", fontsize=10)
        ax2.set_title("Alocação Ótima de Equilíbrio (λ=0.5)\nTeto de Vidro Duplo", fontsize=11, fontweight="bold")
        ax2.set_xlim(0, 1.05); ax2.grid(alpha=0.3, axis="x")
        for i, v in enumerate(vals):
            ax2.text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(OUT_FIG / "po_politicas_pl2_pareto.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  po_politicas_pl2_pareto.csv + po_politicas_pl2_pareto.png salvos.")
    return df_par


# ══════════════════════════════════════════════════════════════════════════════
# AHP + TOPSIS: ranking multicritério das 6 políticas
# ══════════════════════════════════════════════════════════════════════════════

def ahp_topsis():
    """
    Critérios de avaliação das políticas:
        C1 Impacto no gap salarial   (maximizar) — peso AHP
        C2 Impacto no gap de acesso  (maximizar)
        C3 Velocidade de efeito      (maximizar — 1/TEMPO_EFEITO normalizado)
        C4 Custo-efetividade         (maximizar — ALPHA/CUSTOS)
        C5 Viabilidade política      (maximizar — avaliação normativa [ASSUMIDO])

    Matriz AHP de julgamento par-a-par (escala Saaty 1-9).
    """
    log.info("══ AHP + TOPSIS: ranking multicritério ══")

    # Matriz AHP 5×5 (Saaty)
    ahp_mat = np.array([
        [1,   2,   3,   2,   3  ],   # C1 vs C2,C3,C4,C5
        [1/2, 1,   2,   1,   2  ],   # C2 vs C3,C4,C5
        [1/3, 1/2, 1,   1/2, 1  ],   # C3 vs C4,C5
        [1/2, 1,   2,   1,   2  ],   # C4 vs C5
        [1/3, 1/2, 1,   1/2, 1  ],   # C5
    ])
    # Normalizar e obter pesos
    col_sums = ahp_mat.sum(axis=0)
    ahp_norm = ahp_mat / col_sums
    pesos = ahp_norm.mean(axis=1)
    pesos /= pesos.sum()

    # Consistência (razão IC/IR)
    n = 5
    lambda_max = float(np.dot(ahp_mat, pesos).mean() / pesos.mean())
    ic = (lambda_max - n) / (n - 1)
    ri = 1.12  # RI para n=5 (Saaty)
    cr = ic / ri
    log.info(f"  AHP CR = {cr:.4f} ({'OK (<0.10)' if cr < 0.10 else 'ALTA INCONSISTÊNCIA'})")

    # Matriz de desempenho das 6 políticas × 5 critérios
    viabilidade = np.array([0.70, 0.60, 0.80, 0.40, 0.90, 0.85])  # [ASSUMIDO]
    M = np.column_stack([
        G * ALPHA,                  # C1: impacto gap salarial
        np.array([                  # C2: impacto gap de acesso
            LOG_ODDS_CBO14 * 0.70 * ALPHA[0],
            LOG_ODDS_TOP20 * 0.20 * ALPHA[1],
            LOG_ODDS_TOP10 * 0.15 * ALPHA[2],
            ICC_UPA * LOG_ODDS_CBO14 * 0.50 * ALPHA[3],
            LOG_ODDS_CBO14 * 0.25 * ALPHA[4],
            LOG_ODDS_TOP20 * 0.10 * ALPHA[5],
        ]),
        1.0 / TEMPO_EFEITO,         # C3: velocidade (1/anos)
        ALPHA / CUSTOS,             # C4: custo-efetividade
        viabilidade,                # C5: viabilidade política
    ])

    # TOPSIS
    # 1. Normalização vetorial
    norms = np.linalg.norm(M, axis=0)
    M_norm = M / norms

    # 2. Matriz ponderada
    M_w = M_norm * pesos

    # 3. Solução ideal positiva e negativa
    A_pos = M_w.max(axis=0)
    A_neg = M_w.min(axis=0)

    # 4. Distâncias
    D_pos = np.sqrt(((M_w - A_pos) ** 2).sum(axis=1))
    D_neg = np.sqrt(((M_w - A_neg) ** 2).sum(axis=1))

    # 5. Coeficiente de similaridade
    CC = D_neg / (D_pos + D_neg)

    rank_order = np.argsort(-CC)             # índices que ordenam CC desc (para figuras)
    rank = np.argsort(rank_order) + 1        # rank de cada elemento no vetor original

    df_topsis = pd.DataFrame({
        "Política": POLITICAS,
        "C1_gap_sal": np.round(M[:, 0], 5),
        "C2_gap_aces": np.round(M[:, 1], 5),
        "C3_veloc":    np.round(M[:, 2], 3),
        "C4_custo_ef": np.round(M[:, 3], 3),
        "C5_viab":     np.round(M[:, 4], 2),
        "D_pos":       np.round(D_pos, 4),
        "D_neg":       np.round(D_neg, 4),
        "CC":          np.round(CC, 4),
        "Rank":        rank,
    }).sort_values("Rank")
    df_topsis.to_csv(OUT_TAB / "po_politicas_topsis.csv", index=False)

    for _, r in df_topsis.iterrows():
        log.info(f"  #{int(r['Rank'])}: {r['Política']:<45} CC={r['CC']:.4f}")

    # Figura TOPSIS
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    cores_rank = ["#1A6384", "#2196A5", "#3CB5B0", "#7FCDBB", "#C7E9B4", "#FFF4C4"]
    pol_ord = [POLITICAS[i] for i in rank_order]
    cc_ord  = [CC[i] for i in rank_order]

    ax = axes[0]
    bars = ax.barh(pol_ord, cc_ord, color=cores_rank)
    ax.set_xlabel("Coeficiente TOPSIS (CC ≈ 1 = melhor)", fontsize=10)
    ax.set_title("Ranking TOPSIS — 6 Políticas Anti-Discriminação Racial\n(AHP pesos: gap_sal>gap_aces>viab≈custo_ef>veloc)", fontsize=10, fontweight="bold")
    ax.set_xlim(0, 1.0); ax.grid(alpha=0.3, axis="x")
    for bar, v in zip(bars, cc_ord):
        ax.text(v + 0.01, bar.get_y() + bar.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=9)

    ax2 = axes[1]
    theta = np.linspace(0, 2 * np.pi, len(POLITICAS), endpoint=False)
    vals_radar = CC / CC.max()
    theta_c = np.concatenate([theta, [theta[0]]])
    vals_c  = np.concatenate([vals_radar, [vals_radar[0]]])
    ax2 = plt.subplot(1, 2, 2, polar=True)
    ax2.plot(theta_c, vals_c, "o-", color="#2166AC", lw=2)
    ax2.fill(theta_c, vals_c, alpha=0.2, color="#2166AC")
    ax2.set_xticks(theta)
    short = ["Cotas CBO", "Enforcement", "Equid. Educ.", "Desegregação", "Mentoria", "Transp. Sal."]
    ax2.set_xticklabels(short, fontsize=8)
    ax2.set_title("Perfil TOPSIS (radar)", fontsize=10, fontweight="bold", pad=20)
    ax2.set_yticklabels([])

    plt.tight_layout()
    plt.savefig(OUT_FIG / "po_politicas_topsis.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  po_politicas_topsis.csv + po_politicas_topsis.png salvos.")
    return df_topsis, pesos, cr


# ══════════════════════════════════════════════════════════════════════════════
# Análise de sensibilidade: impacto de cada política isolada
# ══════════════════════════════════════════════════════════════════════════════

def analise_sensibilidade():
    log.info("══ Sensibilidade: impacto de cada política isolada ══")
    rows = []
    for i, p in enumerate(POLITICAS):
        # Custo unitário completo (x_i = 1, custo = c_i)
        gap_sal_red  = G[i] * ALPHA[i]          # redução gap salarial
        gap_aces_red = np.array([                # redução log-odds acesso
            LOG_ODDS_CBO14 * 0.70, LOG_ODDS_TOP20 * 0.20,
            LOG_ODDS_TOP10 * 0.15, ICC_UPA * LOG_ODDS_CBO14 * 0.50,
            LOG_ODDS_CBO14 * 0.25, LOG_ODDS_TOP20 * 0.10,
        ])[i] * ALPHA[i]
        bang_for_buck = (gap_sal_red + gap_aces_red) / CUSTOS[i]
        rows.append({
            "Política": p,
            "Custo_unit": CUSTOS[i],
            "ΔGap_sal": round(gap_sal_red, 4),
            "ΔGap_acesso": round(gap_aces_red, 4),
            "ΔGap_total": round(gap_sal_red + gap_aces_red, 4),
            "BangForBuck": round(bang_for_buck, 4),
            "Tempo_efeito": TEMPO_EFEITO[i],
        })
        log.info(f"  {p:<45} ΔGap_sal={gap_sal_red:.4f}  "
                 f"ΔGap_aces={gap_aces_red:.4f}  B/B={bang_for_buck:.4f}")

    df_sens = pd.DataFrame(rows).sort_values("BangForBuck", ascending=False)
    df_sens.to_csv(OUT_TAB / "po_politicas_sensibilidade.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 5))
    x_pos = np.arange(len(POLITICAS))
    df_plot = df_sens.sort_values("BangForBuck", ascending=True)
    width = 0.35
    b1 = ax.barh(x_pos - width/2, df_plot["ΔGap_sal"],  width, label="Gap salarial",  color="#2166AC", alpha=0.85)
    b2 = ax.barh(x_pos + width/2, df_plot["ΔGap_acesso"], width, label="Gap acesso",  color="#D73027", alpha=0.85)
    ax.set_yticks(x_pos)
    ax.set_yticklabels(df_plot["Política"].tolist(), fontsize=9)
    ax.set_xlabel("Redução por unidade de custo (Δ em log)", fontsize=10)
    ax.set_title("Sensibilidade: Impacto de Cada Política Isolada\n(x_i=1, custo=c_i; ordenado por bang-for-buck total)", fontsize=11, fontweight="bold")
    ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(OUT_FIG / "po_politicas_sensibilidade.png", dpi=150, bbox_inches="tight")
    plt.close()
    log.info("  po_politicas_sensibilidade.csv + po_politicas_sensibilidade.png salvos.")
    return df_sens


# ══════════════════════════════════════════════════════════════════════════════
# LaTeX: tabela integrada de políticas
# ══════════════════════════════════════════════════════════════════════════════

def gerar_latex(df_topsis, df_pl1, pesos_ahp, cr_ahp):
    pol_labels = ["P1", "P2", "P3", "P4", "P5", "P6"]
    B5 = df_pl1[df_pl1["orcamento"] == 5.0]

    canal_rows = ""
    for i, p in enumerate(POLITICAS):
        xi = float(B5[f"x{i+1}"].values[0]) if len(B5) else 0.0
        canal_rows += (
            f"  {pol_labels[i]} & {p} & {G[i]:.4f} & {ALPHA[i]:.2f} & "
            f"{CUSTOS[i]:.1f} & {TEMPO_EFEITO[i]} & {xi:.2f} \\\\\n"
        )

    rank_rows = ""
    for _, r in df_topsis.iterrows():
        rank_rows += (
            f"  {int(r['Rank'])} & {r['Política']} & "
            f"{r['C1_gap_sal']:.4f} & {r['C2_gap_aces']:.4f} & "
            f"{r['C4_custo_ef']:.3f} & {r['CC']:.4f} \\\\\n"
        )

    peso_fmt = " & ".join([f"{p:.3f}" for p in pesos_ahp])

    tex = rf"""\begin{{table}}[H]
  \centering
  \caption{{Pesquisa Operacional aplicada a políticas anti-discriminação racial.
           Seis intervenções avaliadas por PL (alocação ótima, B=5),
           TOPSIS (ranking multicritério) e fronteira de Pareto (teto de vidro duplo).
           Efetividades $\alpha_i$ e custos $c_i$ são premissas normativas explícitas
           baseadas em literatura comparada (Holzer \& Neumark, 2000; Bertrand \& Duflo, 2017).
           CR\textsubscript{{AHP}} = {cr_ahp:.3f} (<0,10 = consistência aceitável).}}
  \label{{tab:po_politicas}}
  \small
  \begin{{tabular}}{{clrrrrr}}
    \toprule
    & \textbf{{Intervenção}} & $g_i$ & $\alpha_i$ & $c_i$ & $T$ (anos) & $x_i^*(B=5)$ \\
    \midrule
{canal_rows}    \bottomrule
  \end{{tabular}}
\end{{table}}

\begin{{table}}[H]
  \centering
  \caption{{Ranking TOPSIS das políticas: pesos AHP = [{peso_fmt}]
           (gap salarial, gap acesso, velocidade, custo-efetividade, viabilidade).
           CC próximo de 1 = política mais próxima da solução ideal.}}
  \label{{tab:po_topsis}}
  \small
  \begin{{tabular}}{{rlrrrr}}
    \toprule
    \# & \textbf{{Política}} & $C_1$ (gap sal.) & $C_2$ (gap aces.) & $C_4$ (custo-ef.) & CC (TOPSIS) \\
    \midrule
{rank_rows}    \bottomrule
  \end{{tabular}}
\end{{table}}
"""
    (OUT_TAB / "po_politicas.tex").write_text(tex, encoding="utf-8")
    log.info("  po_politicas.tex salvo.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("POLÍTICAS PÚBLICAS ANTI-DISCRIMINAÇÃO — PESQUISA OPERACIONAL")
    log.info("Parâmetros: gap=0.4229 | GLMM OR_cbo14=0.708 | QR Δ_KB=-3.6pp")
    log.info("=" * 60)

    df_pl1  = pl1_alocacao_orcamento()
    df_par  = pl2_biobjetivo()
    df_topsis, pesos, cr = ahp_topsis()
    df_sens = analise_sensibilidade()
    gerar_latex(df_topsis, df_pl1, pesos, cr)

    log.info("\n" + "=" * 60)
    log.info("TOP-3 POLÍTICAS (TOPSIS):")
    for _, r in df_topsis.head(3).iterrows():
        log.info(f"  #{int(r['Rank'])}: {r['Política']} — CC={r['CC']:.4f}")
    log.info("\nAlocação ótima com B=5 (gap salarial + acesso integrados):")
    B5 = df_pl1[df_pl1["orcamento"] == 5.0]
    if len(B5):
        row = B5.iloc[0]
        log.info(f"  Redução esperada: {row['reducao_pct']:.1f}% do gap bruto")
        for i, p in enumerate(POLITICAS):
            xi = row[f"x{i+1}"]
            if xi > 0.01:
                log.info(f"  {p}: x={xi:.2f}")
    log.info("=" * 60)
    log.info("CONCLUÍDO — outputs em outputs/tables/ e outputs/figures/")
