"""
validate_consistency.py
=======================
Árbitro de consistência numérica do TCC PNAD.

Executa dois tipos de verificação:
  1. FONTE→params.py  : cada P['chave'] bate com o CSV de origem
  2. params.py→geradores: nenhum valor crítico aparece hardcoded nos geradores
     quando já existe em P (checa strings formatadas em pt-BR e en-US)

Uso:
    python validate_consistency.py          # retorna exit 0 se OK, 1 se falhou
    python validate_consistency.py --fix    # (futuro: auto-corrige)

Adicione ao pre-commit ou CI para garantir consistência permanente.
"""

import re
import sys
import math
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
GENERATORS = [
    ROOT / "gerar_relatorio_word.py",
    ROOT / "gerar_relatorio_tcc.py",
    ROOT / "gerar_apresentacao_pptx.py",
    ROOT / "gerar_guia_estudo.py",
    ROOT / "run_politicas_po.py",   # upstream: lê OR/OB/ICC para gerar CSVs de TOPSIS/PL
]

# ── 1. Carrega params.py ──────────────────────────────────────────────────────
sys.path.insert(0, str(ROOT))
from params import P, fmt, fmtN


# ── 2. Verifica fonte CSV → P['chave'] ───────────────────────────────────────

import pandas as pd

ERRORS: list[str] = []
WARNINGS: list[str] = []


def chk(key: str, expected, tolerance: float = 5e-3, label: str = ""):
    """Verifica que P[key] ≈ expected (tolerância relativa)."""
    actual = P.get(key)
    if actual is None:
        ERRORS.append(f"[AUSENTE]  P['{key}'] não existe em params.py")
        return
    try:
        rel = abs(float(actual) - float(expected)) / (abs(float(expected)) + 1e-12)
        if rel > tolerance:
            ERRORS.append(
                f"[DIVERGE]  P['{key}'] = {actual}  |  CSV = {expected}  |  Δrel = {rel:.2%}"
                + (f"  ({label})" if label else "")
            )
    except (TypeError, ValueError):
        if str(actual) != str(expected):
            ERRORS.append(f"[DIVERGE]  P['{key}'] = {actual!r} ≠ CSV {expected!r}")


TAB = ROOT / "outputs" / "tables"

# GLMM lme4
_g = pd.read_csv(TAB / "glmm_resumo_full.csv")
_m1 = _g.loc[_g["modelo"].str.contains("M1")].iloc[0]
_m2 = _g.loc[_g["modelo"].str.contains("M2")].iloc[0]
chk("OR_M1",      float(_m1["OR_negro"]),       label="glmm_resumo_full M1 OR")
chk("OR_M2",      float(_m2["OR_negro"]),       label="glmm_resumo_full M2 OR")
chk("AME_M1_pp",  float(_m1["AME_negro"]) * 100, label="glmm_resumo_full M1 AME*100")
chk("AME_M2_pp",  float(_m2["AME_negro"]) * 100, label="glmm_resumo_full M2 AME*100")
chk("ICC_M1_pct", float(_m1["ICC_UPA"]) * 100,  label="glmm_resumo_full M1 ICC*100")
chk("ICC_M2_pct", float(_m2["ICC_UPA"]) * 100,  label="glmm_resumo_full M2 ICC*100")
chk("N_GLMM",     int(_m1["N"]),                label="glmm_resumo_full N")

# E-values (computed from OR)
def _evalue(or_val):
    inv = 1 / or_val
    return inv + math.sqrt(inv * (inv - 1))
chk("EVAL_M1", _evalue(float(_m1["OR_negro"])), tolerance=1e-3, label="VanderWeele M1")
chk("EVAL_M2", _evalue(float(_m2["OR_negro"])), tolerance=1e-3, label="VanderWeele M2")

# Glass ceiling
_gc = pd.read_csv(TAB / "glmm_glassceil_full.csv")
def _gc_val(desfecho, modelo, col):
    row = _gc.loc[(_gc["desfecho"] == desfecho) & (_gc["modelo"] == modelo)]
    return float(row[col].values[0]) if len(row) else None
chk("OR_OCP_M1",  _gc_val("ocp_qualif","M1","OR_negro"),  label="glassceil ocp M1")
chk("OR_TOP20_M1",_gc_val("y_top20",   "M1","OR_negro"),  label="glassceil top20 M1")
chk("OR_TOP10_M1",_gc_val("y_top10",   "M1","OR_negro"),  label="glassceil top10 M1")

# OB Global
_ob = pd.read_csv(TAB / "ob_melhorias.csv")
_ob_g = _ob.loc[_ob["grupo"] == "Global"].iloc[0]
chk("GAP_LOG", float(_ob_g["gap_log"]), label="ob_melhorias Global gap_log")
chk("GAP_PCT", float(_ob_g["gap_pct"]), label="ob_melhorias Global gap_pct")
chk("DOT_LOG", float(_ob_g["dot_log"]), label="ob_melhorias Global dot_log")
chk("DOT_PCT", float(_ob_g["dot_pct"]), label="ob_melhorias Global dot_pct")
chk("RET_LOG", float(_ob_g["ret_log"]), label="ob_melhorias Global ret_log")
chk("RET_PCT", float(_ob_g["ret_pct"]), label="ob_melhorias Global ret_pct")

# KMeans
_km = pd.read_csv(TAB / "kmeans_perfis_k3.csv")
for i in range(3):
    row = _km.loc[_km["cluster"] == i].iloc[0]
    chk(f"KM_C{i}_N",         int(row["N"]),                        label=f"kmeans_perfis C{i} N")
    chk(f"KM_C{i}_PCT_NEGRO",  float(row["% Negro"]),               label=f"kmeans_perfis C{i} %negro")
    chk(f"KM_C{i}_PCT_MULHER", float(row["% Mulher"]),              label=f"kmeans_perfis C{i} %mulher")
    chk(f"KM_C{i}_LOG_RENDA",  float(row["log_Renda"]),             label=f"kmeans_perfis C{i} log_renda", tolerance=1e-3)
    chk(f"KM_C{i}_RENDA_BRL",  float(row["Renda Bruta (R$)"]),      label=f"kmeans_perfis C{i} renda", tolerance=0.01)
    chk(f"KM_C{i}_PCT_SUP",    float(row["% Superior Compl."]) * 100, label=f"kmeans_perfis C{i} %sup")

_kmg = pd.read_csv(TAB / "kmeans_gap_racial_k3.csv")
for i in range(3):
    row = _kmg.loc[_kmg["cluster"] == i].iloc[0]
    chk(f"KM_C{i}_GAP_LOG", float(row["gap_log"]), label=f"kmeans_gap C{i} gap_log", tolerance=1e-3)
    chk(f"KM_C{i}_GAP_PCT", float(row["gap_%"]),   label=f"kmeans_gap C{i} gap_%")

_kmet = pd.read_csv(TAB / "kmeans_metricas.csv")
chk("KM_SILH_K2", float(_kmet.loc[_kmet["k"]==2,"silhouette"].values[0]), label="kmeans_metricas silhouette k=2", tolerance=1e-3)
chk("KM_SILH_K3", float(_kmet.loc[_kmet["k"]==3,"silhouette"].values[0]), label="kmeans_metricas silhouette k=3", tolerance=1e-3)

# HLM variâncias
_hlm = pd.read_csv(TAB / "hlm_serie_s20pct.csv", index_col=0)
def _hv(row, col):
    v = _hlm.loc[row, col]
    return float(v) if v not in ("FE", "-", "") else None
chk("HLM_SIGMA2_M0",  _hv("sigma2 (Nivel 1)", "M0_Nulo"),        label="hlm_s20pct sigma2 M0")
chk("HLM_TAU2_M0",    _hv("tau2_UF (Nivel 3)", "M0_Nulo"),       label="hlm_s20pct tau2 M0", tolerance=1e-3)
chk("HLM_SIGMA2_M1",  _hv("sigma2 (Nivel 1)", "M1_Individual"),  label="hlm_s20pct sigma2 M1")
chk("HLM_TAU2_M1",    _hv("tau2_UF (Nivel 3)", "M1_Individual"), label="hlm_s20pct tau2 M1", tolerance=1e-3)
chk("ICC_HLM_M0_pct", _hv("ICC_UF", "M0_Nulo") * 100,           label="hlm_s20pct ICC M0")

# TOPSIS
_tp = pd.read_csv(TAB / "po_politicas_topsis.csv")
for _, row in _tp.iterrows():
    chk(f"TOPSIS_P{int(row['Rank'])}_CC", float(row["CC"]), label=f"topsis CC P{int(row['Rank'])}", tolerance=1e-3)

# PL-1
_pl1 = pd.read_csv(TAB / "po_politicas_pl1.csv")
chk("PL1_B5_PCT", float(_pl1.loc[_pl1["orcamento"]==5.0,"reducao_pct"].values[0]), label="pl1 B=5 reducao_pct")

# SNA
_ar = pd.read_csv(TAB / "sna_arestas.csv")
_intra = _ar.loc[~_ar["inter_racial"],"weight_jaccard"].sum()
_inter = _ar.loc[ _ar["inter_racial"],"weight_jaccard"].sum()
chk("SNA_H", _intra / (_intra + _inter), tolerance=1e-3, label="sna_arestas homofilia")


# ── 3. Verifica geradores: nenhum P-value crítico hardcoded ──────────────────

def _pt_br(v: float, dec: int) -> str:
    """Formata número como pt-BR."""
    return f"{v:.{dec}f}".replace(".", ",")

def _all_reprs(key: str, val) -> list[str]:
    """Gera todas as representações textuais de um valor que NÃO devem aparecer hardcoded."""
    reprs = set()
    try:
        f = float(val)
        # pt-BR/en-US 1-4 casas decimais; 1 casa só para valores >= 1 (evita "0,7" ambíguo)
        start_dec = 1 if abs(f) >= 1 else 2
        for d in range(start_dec, 5):
            reprs.add(_pt_br(f, d))
            reprs.add(f"{f:.{d}f}")
        # inteiro grande pt-BR (ponto milhar)
        if abs(f) > 999:
            reprs.add(f"{int(f):,}".replace(",", "."))
            reprs.add(f"{int(f):,}")
    except (TypeError, ValueError):
        pass
    # Remove representações muito curtas (ambíguas)
    return [r for r in reprs if len(r) >= 4]


# Valores que SÃO permitidos hardcoded (constantes sem fonte CSV: z-scores, limiares, etc.)
WHITELIST_PATTERNS = {
    # Limiar metodológico padrão
    r"5%",
    # Valores do LRT boundary test z=3,61 (sem CSV)
    r"3,61",
    r"3.61",
    # SE do tau² (sem CSV próprio)
    r"0,02314", r"0,01694", r"0,00933", r"0,00694",
    # AIC HLM OLS (de hlm_serie_completo, não mapeado em P)
    r"3.588.684", r"3.684.833", r"16.692.113", r"14.361.583",
    # N amostras secundárias (OB 4grupos, hold-out ML) sem CSV rastreável
    r"2.357.851", r"307.768", r"150.267",
    # Percentis/quantis fixos
    r"20%", r"50%", r"80%", r"90%",
    # Oster bounds delta* nos modelos OLS auxiliares (contexto OB) — coincide com GAP_LOG 2 dec
    r"0,43", r"0.43",
    # Razão de representação CBO (11,5%/25,6%) — contexto segregação, coincide com OR_TOP10_M1 2 dec
    r"0,45", r"0.45",
    # Gap OB contrafactual em R$ (brancos R$1.273 vs negros R$927) — coincide com KM_C2_PCT_TOTAL
    r"37,4", r"37.4",
    # Gap de gênero bruto no setor público (análise setorial) — coincide com KM_C1_GAP_PCT
    r"24,1", r"24.1",
    # Faixa HLM 50,8%–53,0% (Konfound) — o 53,0 coincide com GAP_PCT, mas está em intervalo
    r"50,8", r"50.8",
    # Coeficientes de efetividade ASSUMIDOS em run_politicas_po.py (0.70, 0.20 etc.) —
    # coincide com OR_OCP_M2=0.7023 e outros ORs em 2 casas, mas são premissas normativas
    r"0,70", r"0.70",
}

# Mapeia chave → representações a checar nos geradores
CRITICAL_PARAMS: dict[str, list[str]] = {}
SKIP_KEYS = {
    # Inteiros pequenos que aparecem em muitos contextos
    "KM_C0_PCT_MULHER", "KM_C2_PCT_MULHER",  # 100.0 e 0.0 — muito ambíguos
    "OR_M2_menor_pct",  # 30.9 — pode aparecer em outros contextos
    # tau² HLM_M3 = 0.01520 → "0,015" coincide com estimativa DiD τ=+0.015 do event study
    "HLM_TAU2_M3",
    # SNA_H = 0.4382 → "0,44" coincide com R² do Random Forest em prosa
    "SNA_H",
    # KM_C2_PCT_TOTAL → "37,4" coincide com gap OB contrafactual em R$ (contexto diferente)
    "KM_C2_PCT_TOTAL",
    # KM_C1_GAP_PCT → "24,1" coincide com gap de gênero bruto no setor público (análise setorial)
    "KM_C1_GAP_PCT",
}

for key, val in P.items():
    if key in SKIP_KEYS:
        continue
    reprs = _all_reprs(key, val)
    if reprs:
        CRITICAL_PARAMS[key] = reprs


def _is_comment_or_pdict(line: str) -> bool:
    """Linha é comentário, usa P[...] ou é o próprio params.py."""
    s = line.strip()
    return (
        s.startswith("#")
        or "P['" in line
        or 'P["' in line
        or "params" in line
        or "_load()" in line
        or "chk(" in line        # próprio validator
        or "expected" in line    # próprio validator
        or "In(" in line         # coordenadas de layout PPTX em polegadas
        or "textwidth" in line   # frações de coluna LaTeX (\begin{subfigure}[b]{0.49\textwidth})
    )


hardcode_hits: list[tuple[str, int, str, str]] = []  # (file, line, key, snippet)

for gen_path in GENERATORS:
    if not gen_path.exists():
        WARNINGS.append(f"[AUSENTE] Gerador não encontrado: {gen_path.name}")
        continue
    lines = gen_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for lineno, line in enumerate(lines, 1):
        if _is_comment_or_pdict(line):
            continue
        for key, reprs in CRITICAL_PARAMS.items():
            for r in reprs:
                if r in WHITELIST_PATTERNS:
                    continue
                # Busca a representação como palavra delimitada (não como parte de outra)
                pattern = r"(?<![0-9,.])" + re.escape(r) + r"(?![0-9,.])"
                if re.search(pattern, line):
                    snippet = line.strip()[:90]
                    hardcode_hits.append((gen_path.name, lineno, key, r, snippet))
                    break  # uma hit por chave por linha é suficiente


# Deduplica: mesma (file, line) com chaves diferentes → mantém só a mais específica
seen_lines: set[tuple[str, int]] = set()
deduped_hits = []
for h in sorted(hardcode_hits, key=lambda x: -len(x[3])):  # maior repr primeiro
    k = (h[0], h[1])
    if k not in seen_lines:
        seen_lines.add(k)
        deduped_hits.append(h)
deduped_hits.sort(key=lambda x: (x[0], x[1]))


# ── 4. Relatório ─────────────────────────────────────────────────────────────

print("=" * 70)
print("  VALIDATE_CONSISTENCY — TCC PNAD")
print("=" * 70)

if ERRORS:
    print(f"\n{'─'*70}")
    print(f"  DIVERGÊNCIAS CSV → params.py  ({len(ERRORS)} encontradas)")
    print(f"{'─'*70}")
    for e in ERRORS:
        print(f"  {e}")

if deduped_hits:
    print(f"\n{'─'*70}")
    print(f"  HARDCODES CRÍTICOS NOS GERADORES  ({len(deduped_hits)} encontrados)")
    print(f"{'─'*70}")
    for fname, lineno, key, repr_val, snippet in deduped_hits:
        print(f"  {fname}:{lineno}  [{key}={repr_val}]")
        print(f"    → {snippet}")

if WARNINGS:
    print(f"\n{'─'*70}")
    print(f"  AVISOS  ({len(WARNINGS)})")
    for w in WARNINGS:
        print(f"  {w}")

total_issues = len(ERRORS) + len(deduped_hits)
print(f"\n{'─'*70}")
if total_issues == 0:
    print(f"  STATUS: ✓ CONSISTENTE — 0 divergências, 0 hardcodes críticos")
else:
    print(f"  STATUS: ✗ FALHOU — {len(ERRORS)} divergências CSV + {len(deduped_hits)} hardcodes")
print("=" * 70)

sys.exit(0 if total_issues == 0 else 1)
