#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verificar_analises.py — Checagens MECÂNICAS da skill /revisao-livros.

Roda em segundos, só com a biblioteca padrão, e cobre a parte automatizável
dos critérios de MHE (Angrist & Pischke), Fávero & Belfiore, Knaflic (SWD) e
apostila Alencar (ML). O julgamento qualitativo (interpretação, linguagem,
storytelling) fica com a revisão da skill — este script só levanta bandeiras.

Uso:
    python .claude/skills/revisao-livros/scripts/verificar_analises.py            # relatório completo
    python .claude/skills/revisao-livros/scripts/verificar_analises.py --quiet    # só sumário (hook)
    python .claude/skills/revisao-livros/scripts/verificar_analises.py --arquivo X # foco em X (informativo)

Saída: markdown em tcc/revisoes/verificacao_<data>.md (a menos que --no-save) e
sumário no stdout. Exit code 0 sempre (não deve bloquear o fluxo); o número de
achados ALTO/MÉDIO aparece na última linha do stdout.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]          # raiz do projeto
TEX = ROOT / "relatorio_tcc_enxuto.tex"
TABLES = ROOT / "outputs" / "tables"
NUCLEO = [                                          # tcc/run_tcc.ps1
    "run_hlm_serie_completa.py", "run_hlm_stepup.py", "run_oaxaca_blinder.py",
    "run_regressao_quantilica.py", "run_rif_decomp.py", "run_glmm_glassceil.py",
]
ROBUSTEZ = [
    "run_ml_shap.py", "run_konfound_evalues.py", "run_interseccionalidade.py",
    "run_vif_multicolinearidade.py", "run_hlm_vs_ols_justificacao.py",
]
GERADORES = [ROOT / "scripts" / "geradores" / "gerar_apresentacao_pptx.py",
             ROOT / "tcc" / "scripts" / "gerar_relatorio_enxuto.py"]
FORA_DO_NUCLEO = [   # métodos parqueados no branch mestrado-extenso (tcc/ESCOPO_TCC.md)
    (r"\bSNA\b|betweenness|co-resid[êe]ncia|rede[s]? de capital social|análise de redes", "SNA"),
    (r"\bTOPSIS\b|programa[çc][ãa]o linear|Pesquisa Operacional|\bPO\b", "Pesquisa Operacional"),
    (r"Cluster~?\d|K-means|[Cc]lustering [Ss]ocioecon|tipologia[s]? de vulnerabilidade", "Clustering"),  # "clustering" de SE é estatística, não método
    (r"seis metodologias|três metodologias|cinco metodologias", "contagem de métodos desatualizada"),
]
CAUSAL = r"\bcomprova\w*|\bprova(m|do|da)?\s+que|efeito causal|\bdetermina(m|nte)?\b|\bcausa(m|do|ndo)?\b"

achados: list[dict] = []


def add(nivel: str, crit: str, onde: str, msg: str, fix: str = "") -> None:
    achados.append(dict(nivel=nivel, crit=crit, onde=onde, msg=msg, fix=fix))


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def num(s: str) -> float | None:
    s = s.replace("{,}", ".").replace(",", ".").replace("−", "-").replace("$", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def close(a: float, b: float, tol: float = 0.0015) -> bool:
    return abs(a - b) <= tol


def csv_rows(name: str) -> list[dict]:
    p = TABLES / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_tex() -> str:
    """Lê o .tex com os \input{...} de tabelas expandidos (fonte única = csv → .tex → relatório)."""
    def sub(m: re.Match) -> str:
        p = ROOT / m.group(1)
        if p.suffix == "":
            p = p.with_suffix(".tex")
        return read(p) if p.exists() else m.group(0)
    tex = re.sub(r"\\input\{([^}]+)\}", sub, read(TEX))
    return tex.replace("−", "-").replace("{,}", ",")   # normaliza sinal e vírgula decimal


def secao_de(linha_idx: int, linhas: list[str]) -> str:
    for i in range(linha_idx, -1, -1):
        m = re.match(r"\\(sub)*section\*?\{([^}]*)\}", linhas[i])
        if m:
            return m.group(2)
    return "?"


# ──────────────────────────────────────────────────────────────────────────────
# A. Consistência numérica tex ↔ csv
# ──────────────────────────────────────────────────────────────────────────────
def check_ml(tex: str) -> None:
    rows = {r["Modelo"]: r for r in csv_rows("ml_performance.csv")}
    if not rows:
        return
    for nome, chave in (("Random Forest", "Random Forest"), ("XGBoost", "XGBoost")):
        m = re.search(rf"{nome}\}}?\s*&\s*\\?t?e?x?t?b?f?\{{?([\d.,]+)\}}?\s*&\s*\\?t?e?x?t?b?f?\{{?([\d.,]+)\}}?\s*&\s*\\?t?e?x?t?b?f?\{{?([\d.,\-]+)", tex)
        if not m:
            continue
        r2, mae, rmse = (num(m.group(1)), num(m.group(2)), num(m.group(3)))
        ref = rows[chave]
        for lab, tex_v, csv_v in (("R²", r2, num(ref["R²"])), ("MAE", mae, num(ref["MAE"])),
                                  ("RMSE", rmse, num(ref["RMSE"]))):
            if tex_v is None:
                add("ALTO", "ML-04/FAV-91", "relatorio: tab:ml_perf",
                    f"{nome}: {lab} ausente na tabela do relatório (csv = {csv_v}).",
                    "Regerar a tabela a partir de outputs/tables/ml_performance.csv.")
            elif csv_v is not None and not close(tex_v, csv_v):
                add("ALTO", "ML-04/FAV-91", "relatorio: tab:ml_perf",
                    f"{nome}: {lab} no relatório = {tex_v} vs csv = {csv_v}.",
                    "Regerar a tabela a partir de ml_performance.csv (fonte única).")
    m = re.search(r"R\^2 \\approx (\d[\d{},.]*)", tex)
    if m:
        v = num(m.group(1))
        xgb = num(rows["XGBoost"]["R²"])
        if v is not None and xgb is not None and not close(v, xgb, 0.02):
            add("ALTO", "ML-04", "relatorio: texto após tab:ml_perf",
                f"Texto diz R² ≈ {v}, mas o XGBoost tem R² = {xgb}.",
                "Alinhar o texto ao csv.")
    gap = num(rows["XGBoost"].get("gap_overfit", "") or "")
    if gap is not None and gap > 0.05:
        add("MÉDIO", "ML-05", "ml_performance.csv", f"Gap treino–teste do XGBoost = {gap:.3f} (>0,05).",
            "Reduzir max_depth/aumentar regularização.")


def check_glmm(tex: str) -> None:
    rows = csv_rows("glmm_glassceil_full.csv")
    if not rows:
        return
    ors = {num(r["OR_negro"]) for r in rows}
    extras = set()
    for f in ("glmm_glassceil_glmer.csv", "grupo_rg_glmm_ocp.csv", "grupo_rg_glmm_rs_interacao.csv",
              "glmm_odds_ratios_full.csv", "evalues_glmm.csv", "grupo_rg_4grupos_desfechos.csv",
              "interseccional_coeficientes.csv"):
        for r in csv_rows(f):
            for k, v in r.items():
                if k and re.search(r"OR|odds", k, re.I):
                    x = num(v or "")
                    if x is not None:
                        extras.add(x)
    citados = re.findall(r"OR(?:\([^)]*\))?~?\$?\s*=\s*\$?\s*(\d[\d{},.]*)", tex)
    for c in citados:
        v = num(c)
        if v is None:
            continue
        if not any(close(v, o, 0.006) for o in ors | extras if o is not None):
            atuais = ", ".join(f"{r['modelo']}={num(r['OR_negro']):.3f}" for r in rows if r["desfecho"] == "ocp_qualif")
            add("ALTO", "FAV-91/SWD-06", "relatorio", f"OR = {v} citado no texto não existe em nenhum csv de GLMM/logit "
                f"(valores atuais CBO1-4: {atuais}).",
                "Atualizar o número (provavelmente resíduo de uma rodada antiga).")


def check_qr(tex: str) -> None:
    rows = csv_rows("qr_kb_test.csv")
    if not rows:
        return
    z = num(rows[0]["z_stat"])
    z_raw = num(rows[0].get("z_stat_raw", "") or "")          # versão conservadora (sem escala m/G)
    validos = [x for x in (z, z_raw) if x is not None]
    for c in re.findall(r"Z\s*=\s*\$?\s*(-?\d[\d{},.]*)", tex):
        v = num(c)
        if v is not None and validos and not any(close(v, x, 0.05) for x in validos):
            add("ALTO", "FAV-91", "relatorio", f"Teste de heterogeneidade quantílica: texto cita Z = {v}, csv = {validos}.",
                "Alinhar ao qr_kb_test.csv.")
    frac = num(rows[0].get("boot_frac", "") or "")
    if frac is not None and frac < 1 and rows[0].get("boot_blocos", "") != "UPA":
        add("MÉDIO", "MHE-75/MHE-84", "run_regressao_quantilica / qr_kb_test.csv",
            f"SE do contraste q90−q10 por bootstrap em {frac:.0%} da amostra, sem blocos por UPA.",
            "Bootstrap em blocos (UPA) ou, no mínimo, declarar no texto que o SE é conservador por vir de subamostra.")


def check_hlm(tex: str) -> None:
    # Bloco 3: se o HLM step-up (indivíduo em UPA) existir, ele é a fonte do relatório
    stepup = csv_rows("gap_decomposicao_stepup.csv")
    if stepup:
        for r in stepup:
            b = float(r["b_negro"])
            if f"{b:.4f}" not in tex and f"{b:.4f}".replace(".", ",") not in tex                     and f"{b:.4f}".replace("-", "−").replace(".", ",") not in tex:
                add("ALTO", "FAV-91", "relatorio", f"β_negro {r['Modelo']} (step-up) = {b:.4f} não aparece no relatório.",
                    "Regerar o relatório (gerar_relatorio_tcc → gerar_relatorio_enxuto).")
        fit = csv_rows("hlm_stepup_fit.csv")
        if fit and any(r["modelo"] in ("M2", "M3") and r.get("converged", "True") == "False" for r in fit):
            add("INFO", "FAV-71", "hlm_stepup_fit.csv", "BFGS reportou converged=False em M2/M3 (tolerância de gradiente).",
                "Conferir estabilidade dos coeficientes (variam <0,1% entre degraus) ou aumentar maxiter.")
        return
    rows = csv_rows("hlm_serie_completo.csv")
    if not rows:
        return
    negro = next((r for r in rows if r.get("") == "negro"), None)
    if negro:
        for col, rotulo in (("M1_Individual", "M1"), ("M2_Localidade", "M2"), ("M4_Ocupacao", "M4")):
            m = re.match(r"(-?\d+\.\d+)", negro[col])
            if not m:
                continue
            b = float(m.group(1))
            if f"{b:.4f}" not in tex and f"{b:.4f}".replace(".", ",") not in tex:
                add("ALTO", "FAV-91", "relatorio", f"β_negro {rotulo} = {b} do csv não aparece no relatório.",
                    "Regerar tabelas/texto a partir de hlm_serie_completo.csv.")
        se_hlm = re.search(r"\((\d+\.\d+)\)", negro["M1_Individual"])
        se_ols = re.search(r"\((\d+\.\d+)\)", negro["M1_Individual_OLS"])
        linha_negro = next((l for l in tex.splitlines() if "textbf{Raça (negro)}" in l and "&" in l), "")
        publica_cluster = "[" in linha_negro          # tabela do relatório já traz SE agrupado entre colchetes
        if se_hlm and se_ols and float(se_ols.group(1)) > 3 * float(se_hlm.group(1)) and not publica_cluster:
            add("ALTO", "MHE-81/MHE-04", "hlm_serie_completo.csv",
                f"SE de β_negro: HLM (RE de UF) = {se_hlm.group(1)} vs OLS cluster-UF = {se_ols.group(1)} "
                f"({float(se_ols.group(1))/float(se_hlm.group(1)):.0f}×). O relatório publica só o menor (Moulton).",
                "Reportar SE clusterizado (UPA, e UF com correção de poucos clusters) ao lado do SE do HLM; "
                "nunca (0.0000).")
    # colinearidade UF z-scores + C(UF_str) nos OLS
    for r in rows:
        for col in ("M3_Completo_OLS", "M4_Ocupacao_OLS"):
            v = r.get(col, "")
            if re.search(r"\d{7,}", v) or "nan" in v:
                add("MÉDIO", "FAV-33/FAV-44", "hlm_serie_completo.csv",
                    f"{col}: coeficiente degenerado em '{r.get('')}' ({v[:40]}…) — z-scores de UF são colineares com C(UF_str).",
                    "Remover _UF das fórmulas OLS com dummies de UF (ou remover as dummies).")
                break
        else:
            continue
        break
    if re.search(r"AIC\s*&\s*N/D", tex):
        add("MÉDIO", "FAV-71/FAV-72", "relatorio: tab:hlm_resultados",
            "AIC/BIC 'N/D' em todos os modelos: sem LR test/critérios de informação a estratégia step-up (Fávero) fica incompleta.",
            "Reportar −2LL, AIC, BIC e LR test M0→M1→M2→M3 (REML comparável ou refit por ML).")
    if re.search(r"\(0\.0000\)", tex):
        add("BAIXO", "MHE-85/FAV-91", "relatorio: tab:hlm_resultados",
            "Erros-padrão exibidos como (0.0000).", "Mais casas decimais ou notação científica.")
    if re.search(r"interceptos fixos", tex):
        script = read(ROOT / "scripts" / "analise" / "run_hlm_serie_completa.py")
        if "C(UPA" not in script:
            add("ALTO", "FAV-70/FAV-71/MHE-56", "relatorio: subsec:hlm vs run_hlm_serie_completa.py",
                "Texto diz que a UPA entra como 'interceptos fixos (41.517 grupos)', mas o script estima "
                "intercepto aleatório de UF + covariáveis contextuais de UPA (sem C(UPA)). Com dummies de UPA, "
                "%negro-UPA seria não identificável.",
                "Reescrever a metodologia: modelo de 2 níveis (indivíduo/UF) com contexto de UPA como covariáveis; "
                "ou estimar de fato o 3º nível (run_hlm_m4 usa groups=UPA) e reportar τ²_UPA e ICC_UPA.")


def check_ob(tex: str) -> None:
    rows = {r["Componente"]: r for r in csv_rows("oaxaca_resultados.csv")}
    if not rows:
        return
    dot = num(rows["Efeito Dotacoes"]["Pct_do_gap"])
    ret = num(rows["Efeito Retornos"]["Pct_do_gap"])
    for v, lab in ((dot, "dotações"), (ret, "retornos")):
        if v is None:
            continue
        s1, s2 = f"{v:.1f}", f"{v:.1f}".replace(".", ",")
        if s1 not in tex and s2 not in tex:
            add("ALTO", "FAV-91", "relatorio", f"% {lab} do OB no csv ({v:.1f}) não aparece no texto.",
                "Regerar ob_acesso.tex/texto.")
    script = read(ROOT / "scripts" / "analise" / "run_oaxaca_blinder.py")
    if "ocp_" in script and "bootstrap" not in script.lower():
        add("MÉDIO", "MHE-81/FAV-91", "run_oaxaca_blinder.py",
            "Decomposição sem erro-padrão (nem bootstrap) no script; a legenda da tabela promete 'bootstrap 200 rep. por UF'.",
            "Confirmar de onde vêm os SE da tabela (run_ob_qr_melhorias?) e citar o script certo; bootstrap em blocos.")
    if "ocp_" in script:
        add("INFO", "MHE-25", "run_oaxaca_blinder.py",
            "OB inclui ocupação/formalidade/horas como dotações (bad controls). Correto SÓ se o texto apresentar também "
            "a versão sem ocupação e tratar 16,2% como limite inferior.", "Ver critério MHE-25 na revisão qualitativa.")


def check_gap_interno(tex: str) -> None:
    liq = {num(x) for x in re.findall(r"gap l[íi]quido[^.\n]{0,40}?(-?\d[\d{},.]*)\\%", tex)}
    res = {num(x) for x in re.findall(r"gap residual[^.\n]{0,40}?(-?\d[\d{},.]*)\\%", tex)}
    liq.discard(None); res.discard(None)
    if len(liq) > 1:
        add("ALTO", "SWD-79/FAV-91", "relatorio", f"'gap líquido' citado com valores diferentes: {sorted(liq)}.",
            "Um único número-síntese (M3 = −9,6% sem ocupação; M4 = −6,2% com ocupação) e nomear cada um.")
    if len(res) > 1:
        add("ALTO", "SWD-79/FAV-91", "relatorio", f"'gap residual' citado com valores diferentes: {sorted(res)}.",
            "Idem.")
    if liq and res and not (liq & res) and abs(min(liq) - min(res)) > 1:
        add("MÉDIO", "SWD-79", "relatorio",
            f"'gap líquido' ({sorted(liq)}) e 'gap residual' ({sorted(res)}) são usados como sinônimos com números diferentes.",
            "Fixar terminologia: líquido = M3 (sem bad controls); residual pós-ocupação = M4.")
    n_obs = set(re.findall(r"N\s*=\s*\$?([\d.]{7,})", tex))
    if len(n_obs) > 1:
        add("BAIXO", "FAV-91", "relatorio", f"Vários N citados como 'população': {sorted(n_obs)}.",
            "Declarar o N de cada modelo (filtros diferentes) em cada tabela.")


# ──────────────────────────────────────────────────────────────────────────────
# B. Escopo e linguagem
# ──────────────────────────────────────────────────────────────────────────────
def check_escopo(linhas: list[str]) -> None:
    for pat, nome in FORA_DO_NUCLEO:
        # menções em Limitações/agenda ("versão estendida", "trabalhos futuros") são legítimas
        hits = [i + 1 for i, l in enumerate(linhas)
                if not l.lstrip().startswith("%") and re.search(pat, l)
                and "Limita" not in secao_de(i, linhas)]
        if hits:
            add("ALTO", "ESCOPO/SWD-51", "relatorio",
                f"{nome} (fora do núcleo de 4) ainda citado em {len(hits)} linha(s): {hits[:12]}{'…' if len(hits) > 12 else ''}.",
                "Remover ou mover para 'trabalhos futuros'; ajustar Hipóteses, mapa das camadas, Conclusão e título.")


def check_causal(linhas: list[str]) -> None:
    hits = []
    for i, l in enumerate(linhas):
        if l.lstrip().startswith("%"):
            continue
        sec = secao_de(i, linhas)
        if "Limita" in sec:
            continue
        if re.search(CAUSAL, l, re.I):
            hits.append(i + 1)
    if hits:
        add("MÉDIO", "MHE-01/MHE-23/FAV-07", "relatorio",
            f"Linguagem causal ('comprova', 'determina', 'causa', 'efeito causal') em {len(hits)} linha(s): {hits[:15]}.",
            "Trocar por 'associa-se', 'é consistente com', 'penalidade condicional'; reservar causal para a seção de limitações.")


# ──────────────────────────────────────────────────────────────────────────────
# C. Especificação nos scripts do núcleo
# ──────────────────────────────────────────────────────────────────────────────
def check_scripts() -> None:
    sem_peso: list[str] = []
    for nome in NUCLEO + ROBUSTEZ:
        p = ROOT / "scripts" / "analise" / nome
        src = read(p)
        if not src:
            add("MÉDIO", "ESCOPO", nome, "Script do núcleo/robustez não encontrado.", "")
            continue
        code = "\n".join(re.sub(r"#.*$", "", l) for l in src.splitlines())   # sem comentários
        # amostragem (regra do projeto: nunca amostrar sem confirmação)
        m = re.search(r"^SAMPLE_FRAC\s*=\s*(0\.\d+)", code, re.M)   # só atribuição real (não docstring)
        if m:
            add("ALTO", "REGRA-AMOSTRAGEM/FAV-09", nome, f"SAMPLE_FRAC = {m.group(1)} (não é população completa).",
                "Voltar a None; amostra só com confirmação explícita do usuário.")
        if re.search(r"\.sample\(", code) and "sample_frac" not in code.lower() \
                and nome not in ("run_ml_shap.py", "run_vif_multicolinearidade.py"):
            add("MÉDIO", "REGRA-AMOSTRAGEM", nome, "Uso de .sample( no script.", "Confirmar se é só para visualização.")
        # pesos amostrais
        if not re.search(r"V1028|weights=|pweight|freq_weights|var_weights", code):
            sem_peso.append(nome)
        # OLS sem cov_type (o script de justificação compara SE ingênuo vs cluster de propósito)
        for mm in (re.finditer(r"smf\.ols\([^\n]*\)\s*\.fit\(\s*\)", code)
                   if nome != "run_hlm_vs_ols_justificacao.py" else ()):
            add("MÉDIO", "MHE-22/MHE-81", nome, f"OLS com .fit() sem cov_type: `{mm.group(0)[:70]}…`",
                "cov_type='cluster' (UPA) ou HC3; regra do máximo (MHE cap. 8).")
        if "quantreg" in code and "bootstrap" not in code.lower() and "boot" not in code.lower():
            add("INFO", "MHE-75", nome, "QR sem bootstrap: SE dependem da densidade do resíduo em zero.",
                "Bootstrap em blocos por UPA (ou declarar o kernel usado).")
        if "smf.logit" in code and not re.search(r"glmer|mixedlm|BinomialBayesMixedGLM|MixedLM", code):
            # bloco 4: o GLMM real vem de scripts/R/glmm_glassceil.R (glmer); o logit-FE é robustez
            if "glmm" in nome and not (TABLES / "glmm_glassceil_glmer.csv").exists():
                add("ALTO", "FAV-77/FAV-70", nome,
                    "Script rotulado GLMM estima logit com UF como efeito fixo + HC1 (sem efeito aleatório). "
                    "O relatório descreve 'GLMM com efeito aleatório de UPA'.",
                    "Ou alimentar a tabela com scripts/R/logit_multinivel_glmm.R (glmer, ICC UPA, LR test vs logit), "
                    "ou renomear para 'logit com efeitos fixos de UF' e citar o glmer como robustez.")
        if "train_test_split" in code and not re.search(r"cross_val|KFold|GridSearch|RandomizedSearch|optuna", code):
            add("MÉDIO", "ML-02/ML-06", nome, "Hold-out único, sem validação cruzada nem busca de hiperparâmetros.",
                "k-fold (k=5) em subamostra para escolher max_depth/lr/n_estimators; reportar CV e hold-out.")
        if re.search(r"\.pie\(|projection=['\"]3d['\"]|twinx\(\)", code):
            add("MÉDIO", "SWD-19", nome, "Gráfico de pizza / 3D / eixo secundário detectado.", "Barras ou slopegraph.")
        if nome == "run_glmm_glassceil.py" and not re.search(r"roc_auc|AUC|hosmer|confusion", code, re.I):
            add("MÉDIO", "FAV-43/ML-03", nome, "Logit sem AUC/ROC, matriz de confusão (cutoff) nem Hosmer-Lemeshow.",
                "Reportar AUC + sensibilidade/especificidade no cutoff; comparar M1→M3 (roccomp).")
    if sem_peso:
        add("INFO", "MHE-30/FAV-09/FAV-36", ", ".join(sem_peso),
            "Sem peso amostral da PNAD (V1028) em nenhum modelo.",
            "Declarar no texto que as estimativas são não ponderadas (regressão amostral, não populacional) "
            "ou reestimar um modelo-chave com pesos como robustez.")
    # geradores/relatório citam método parqueado?
    for g in GERADORES:
        if g.name == "gerar_relatorio_enxuto.py":   # cita os métodos só para removê-los
            continue
        src = read(g)
        for pat, nome in FORA_DO_NUCLEO[:3]:
            if re.search(pat, src):
                add("MÉDIO", "ESCOPO", g.relative_to(ROOT).as_posix(), f"Gerador ainda referencia {nome}.",
                    "Limpar para que a regeneração não reintroduza o método.")


# ──────────────────────────────────────────────────────────────────────────────
# D. Storytelling: figuras e slides
# ──────────────────────────────────────────────────────────────────────────────
def check_visual(tex: str) -> None:
    figs = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", tex)
    figs = [f for f in figs if "logo" not in f]
    metodos = {"HLM": r"hlm|mediacao|gap_", "Oaxaca-Blinder": r"oaxaca|ob_|cascata|waterfall_ob",
               "Regressão quantílica/RIF": r"quantreg|qr_|rif", "GLMM/logit": r"glmm|logit|odds|or_"}
    for met, pat in metodos.items():
        if not any(re.search(pat, f, re.I) for f in figs):
            add("MÉDIO", "SWD-10/SWD-18/SWD-14", "relatorio: figuras",
                f"Nenhuma figura para {met} (só tabela). Figuras atuais: {len(figs)}.",
                "Uma figura por método do núcleo: cascata (OB), coeficiente×quantil com IC (QR/RIF), "
                "barras horizontais de OR com IC (GLMM), barras do β_negro M1→M4 (HLM).")
    caps = re.findall(r"\\caption\{([^}]{0,120})", tex)
    descritivos = [c for c in caps if re.match(r"\s*(Análise|Decomposição|Modelos|Desempenho|Dependence|Razões|Razoes)", c)]
    if descritivos:
        add("BAIXO", "SWD-55", "relatorio: legendas",
            f"{len(descritivos)} legenda(s) começam por rótulo descritivo em vez de afirmar o achado (ex.: '{descritivos[0][:60]}…').",
            "Título de ação na primeira frase da legenda.")


def check_slides() -> None:
    src = read(GERADORES[0])
    if not src:
        return
    titulos = re.findall(r'header_bar\(s,\s*"([^"]+)"', src)
    nums = [int(m.group(1)) for t in titulos if (m := re.match(r"(\d+)\.", t))]
    if nums and nums != list(range(nums[0], nums[0] + len(nums))):
        add("MÉDIO", "SWD-75/SWD-51", "gerar_apresentacao_pptx.py",
            f"Numeração dos slides com lacunas: {nums} (slides removidos deixaram rastro).",
            "Renumerar ou remover números; a sequência de títulos deve contar a história sozinha.")
    descritivos = [t for t in titulos if not re.search(r"[a-záéíóúç]+(a|e|em|am|ou|ia|ram)\b.*[a-z]", t.split("—")[-1].lower())
                   or re.match(r"^\d+\.\s*[\w\-/ ]+(—|-)\s*[\w ]+$", t)]
    if len(titulos) and len(descritivos) >= len(titulos) // 2:
        add("MÉDIO", "SWD-55/SWD-75", "gerar_apresentacao_pptx.py",
            f"{len(descritivos)}/{len(titulos)} títulos de slide são tópicos ('N. Método — Tema'), não frases de ação.",
            "Ex.: '5. HLM — Decomposição do Gap' → 'Morar em bairro segregado explica metade do gap racial'.")
    cores = len(set(re.findall(r"RGBColor\(0x[0-9A-Fa-f]{2}, 0x[0-9A-Fa-f]{2}, 0x[0-9A-Fa-f]{2}\)", src)))
    if cores > 5:
        add("BAIXO", "SWD-42/SWD-40", "gerar_apresentacao_pptx.py", f"Paleta com {cores} cores nomeadas.",
            "Cinza + uma cor de destaque (azul); vermelho só para o dado que se quer destacar.")


# ──────────────────────────────────────────────────────────────────────────────
def main() -> int:
    # stdout do Windows costuma ser cp1252 — forçar UTF-8 para não quebrar no hook
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--arquivo", default="")
    args = ap.parse_args()

    tex = read_tex()
    linhas = read(TEX).splitlines()          # .tex bruto: numeração real das linhas
    if tex:
        check_ml(tex); check_glmm(tex); check_qr(tex); check_hlm(tex); check_ob(tex)
        check_gap_interno(tex); check_escopo(linhas); check_causal(linhas); check_visual(tex)
    else:
        add("ALTO", "ESCOPO", str(TEX), "relatorio_tcc_enxuto.tex não encontrado.", "")
    check_scripts(); check_slides()

    ordem = {"ALTO": 0, "MÉDIO": 1, "BAIXO": 2, "INFO": 3}
    achados.sort(key=lambda a: ordem[a["nivel"]])
    n = {k: sum(1 for a in achados if a["nivel"] == k) for k in ordem}

    hoje = dt.datetime.now()
    md = [f"# Verificação mecânica — {hoje:%Y-%m-%d %H:%M}", "",
          f"Gatilho: `{args.arquivo or 'execução manual'}`  ",
          f"Achados: **{n['ALTO']} ALTO**, {n['MÉDIO']} MÉDIO, {n['BAIXO']} BAIXO, {n['INFO']} INFO.", "",
          "| Nível | Critério | Onde | Achado | Correção |", "|---|---|---|---|---|"]
    for a in achados:
        md.append(f"| {a['nivel']} | {a['crit']} | {a['onde']} | {a['msg']} | {a['fix']} |")
    md += ["", "_Checagens mecânicas apenas. Rode `/revisao-livros` para a revisão qualitativa completa "
           "(MHE, Fávero, Knaflic, Alencar)._"]
    if not args.no_save:
        out = ROOT / "tcc" / "revisoes" / f"verificacao_{hoje:%Y-%m-%d}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(md), encoding="utf-8")
    if args.quiet:
        for a in achados:
            if a["nivel"] in ("ALTO", "MÉDIO"):
                print(f"[{a['nivel']}] {a['crit']} — {a['onde']}: {a['msg']}")
    else:
        print("\n".join(md))
    print(f"\nRESUMO: {n['ALTO']} ALTO | {n['MÉDIO']} MÉDIO | {n['BAIXO']} BAIXO | {n['INFO']} INFO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
