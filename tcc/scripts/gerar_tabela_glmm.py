"""
gerar_tabela_glmm.py
====================
Tabela-síntese do GLMM logístico (teto de vidro ocupacional e salarial) do NÚCLEO do TCC.

Fonte principal (bloco 4): outputs/tables/glmm_glassceil_glmer.csv — lme4::glmer com
intercepto aleatório de UPA (scripts/R/glmm_glassceil.R): OR e IC de negro, AME, ICC_UPA,
LR vs. logit pooled, AUC, cutoff de Youden (sens./espec.), Hosmer-Lemeshow.
Robustez: outputs/tables/glmm_glassceil_full.csv — logit com efeitos fixos de UF e SE
agrupado por UPA (run_glmm_glassceil.py). E-value calculado aqui (VanderWeele & Ding,
2017): para OR<1, OR* = 1/OR e E = OR* + sqrt(OR*(OR*-1)); idem para o limite do IC.

Saídas: outputs/tables/glmm_glassceil.tex (tabela principal, tab:glmm_glassceil)
        outputs/tables/glmm_ajuste.tex   (ajuste/classificação, tab:glmm_ajuste)
        outputs/tables/evalues_glmm.csv  (E-values, para o texto)
"""
# --- bootstrap raiz do projeto ---
import os as _os, sys as _sys
from pathlib import Path as _Path
_os.chdir(_Path(__file__).resolve().parents[2])
_sys.path.insert(0, _os.getcwd())
# --- fim bootstrap ---
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import math
import pandas as pd
from pathlib import Path
from params import fmt, fmtN
from params_nucleo import P as _PN   # tamanhos de amostra citados nas notas

TABLES = Path("outputs") / "tables"
g = pd.read_csv(TABLES / "glmm_glassceil_glmer.csv")
fe_path = TABLES / "glmm_glassceil_full.csv"
fe = pd.read_csv(fe_path) if fe_path.exists() else None

DESF = {"ocp_qualif": r"Cargo qualificado (CBO 1--4)", "y_top20": r"Top 20\% de renda", "y_top10": r"Top 10\% de renda"}
# A chave é o código do csv e não muda; o rótulo impresso passa a A1..A4 porque
# a escada do acesso NÃO é paralela à da renda --- o "+ vínculo" que aqui é o
# terceiro degrau corresponde ao M4 do HLM, e rótulos iguais faziam o leitor
# alinhar os dois errado.
MOD = {"M1": r"A1 individual + UF", "M2": r"A2 + contexto do bairro", "M3": r"A3 + vínculo (limite inf.)",
       "M4": r"A4 + negro$\times$credencial"}
# correspondência com os modelos do logit-FE (robustez): M1 ~ M1; M2 ~ M2; M3/M4 ~ M3 (com vínculo e interação)
FE_MAP = {"M1": "M1", "M2": "M2", "M3": "M2", "M4": "M3"}


from params_nucleo import evalue   # a única implementação (√OR para desfecho comum, E2.7)


def evalue_ci(or_, lo, hi, desfecho):
    """E-value do limite do IC mais próximo de 1 (1 se o IC contém 1)."""
    if lo <= 1 <= hi:
        return 1.0
    return evalue(hi if or_ < 1 else lo, desfecho)


g["E_value"] = [evalue(o, d) for o, d in zip(g["OR_negro"], g["desfecho"])]
g["E_value_CI"] = [evalue_ci(o, lo, hi, d) for o, lo, hi, d
                   in zip(g["OR_negro"], g["CI95_lo"], g["CI95_hi"], g["desfecho"])]
g[["desfecho", "modelo", "OR_negro", "CI95_lo", "CI95_hi", "E_value", "E_value_CI"]].rename(
    columns={"desfecho": "Desfecho", "modelo": "Modelo", "OR_negro": "OR", "CI95_lo": "IC 95% lo",
             "CI95_hi": "IC 95% hi", "E_value": "E-value (OR)", "E_value_CI": "E-value (CI)"}
).to_csv(TABLES / "evalues_glmm.csv", index=False, encoding="utf-8")

N = int(g["N"].iloc[0]); G = int(g["n_upa"].iloc[0])


def or_cell(o, lo, hi):
    return f"{fmt(o, 3)} [{fmt(lo, 3)}; {fmt(hi, 3)}]"


# ── Tabela principal ─────────────────────────────────────────────────────────
L = [r"\begin{table}[!ht]", r"\centering",
     r"\caption{GLMM logístico (lme4::\texttt{glmer}, intercepto aleatório de UPA e efeitos fixos de UF) "
     r"--- teto de vidro ocupacional e salarial. \emph{Odds ratio} do coeficiente \texttt{negro} com IC~95\%, "
     r"efeito marginal médio (AME: diferença média de probabilidade predita, em pontos percentuais), "
     r"ICC da UPA $=\tau^2/(\tau^2+\pi^2/3)$ e E-value \cite{vanderweele2017}. Coluna final: "
     r"OR do logit com efeitos fixos de UF e erro-padrão agrupado por UPA (robustez). População completa "
     rf"da PEA com renda positiva ($N = {fmtN(N)}$; {fmtN(G)}~UPAs). A3 acrescenta o vínculo "
     r"(formalidade, setor público, conta própria, doméstico), que é desfecho da própria discriminação: "
     r"limite inferior. Todos os OR com $p<0{,}001$; com $N$ desta ordem, a inferência relevante está "
     r"nos IC e nos E-values.}",
     r"\label{tab:glmm_glassceil}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{llcccccc}", r"\toprule",
     r"Desfecho & Modelo & OR (IC 95\%) & AME (p.p.) & ICC$_{\text{UPA}}$ & E-value & E-value (IC) & OR logit-FE \\",
     r"\midrule"]
for d in DESF:
    sub = g[g["desfecho"] == d]
    first = True
    for _, r in sub.iterrows():
        m = r["modelo"]
        fe_or = "---"
        if fe is not None:
            fr = fe[(fe["desfecho"] == d) & (fe["modelo"] == FE_MAP[m])]
            if len(fr):
                fe_or = fmt(float(fr["OR_negro"].iloc[0]), 3)
        L.append(f"{DESF[d] if first else ''} & {MOD[m]} & {or_cell(r['OR_negro'], r['CI95_lo'], r['CI95_hi'])} & "
                 f"{fmt(r['AME_pp'], 2)} & {fmt(r['ICC_UPA'], 3)} & {fmt(r['E_value'], 2)} & "
                 f"{fmt(r['E_value_CI'], 2)} & {fe_or} \\\\")
        first = False
    L.append(r"\midrule")
L[-1] = r"\bottomrule"
L += [r"\end{tabular}}", r"\par\smallskip",
      r"\footnotesize\emph{Como ler:} OR $<1$ = menor chance de acesso para trabalhadores negros do que "
      r"para brancos de mesmo perfil \emph{e do mesmo bairro}; quanto mais perto de zero, maior a barreira. "
      r"O E-value é a força mínima de associação (razão de risco) que um confundidor não observado precisaria "
      r"ter com a raça \emph{e} com o desfecho para anular o OR; o E-value (IC) faz o mesmo para o limite do "
      r"intervalo. A coluna logit-FE mostra que a conclusão não depende da hipótese de efeitos aleatórios.",
      r"\end{table}"]
(TABLES / "glmm_glassceil.tex").write_text("\n".join(L) + "\n", encoding="utf-8")

# ── Tabela de ajuste e classificação (Fávero: LR, AUC, cutoff, Hosmer-Lemeshow) ──
A = [r"\begin{table}[!ht]", r"\centering",
     r"\caption{GLMM logístico --- ajuste e desempenho de classificação por degrau. LR vs.\ pooled: "
     r"teste de razão de verossimilhança do A2 contra o logit sem efeito aleatório (fronteira, $p/2$); "
     r"AUC com efeitos aleatórios (ajuste na amostra) e só com efeitos fixos; \emph{cutoff} de Youden "
     r"(maximiza sensibilidade $+$ especificidade) com as taxas correspondentes; Hosmer--Lemeshow em "
     r"dez decis. Modelos A1--A4 como na Tabela~\ref{tab:glmm_glassceil}. Com $N = " + fmt(_PN["N_GLMM"] / 1e6, 1).replace(",", "{,}") + r"$~milhões qualquer desvio de calibração é ``significativo'' --- o "
     r"$\chi^2$ deve ser lido como magnitude relativa entre degraus, não como teste (MHE, cap.~8).}",
     r"\label{tab:glmm_ajuste}", r"\resizebox{\textwidth}{!}{%", r"\begin{tabular}{llcccccccc}", r"\toprule",
     r"Desfecho & Modelo & $-2\,$LL & AIC & LR vs.\ pooled & AUC (RE) & AUC (FE) & Cutoff & Sens./Espec. & HL $\chi^2$ \\",
     r"\midrule"]
for d in DESF:
    sub = g[g["desfecho"] == d]
    first = True
    for _, r in sub.iterrows():
        lr = "---" if pd.isna(r["LR_vs_pooled"]) else fmtN(int(round(r["LR_vs_pooled"])))
        A.append(f"{DESF[d] if first else ''} & {r['modelo'].replace('M', 'A')} & {fmtN(int(round(-2 * r['LL'])))} & "
                 f"{fmtN(int(round(r['AIC'])))} & {lr} & {fmt(r['AUC_com_RE'], 3)} & {fmt(r['AUC_so_FE'], 3)} & "
                 f"{fmt(r['cutoff_youden'], 2)} & {fmt(r['sens'], 2)}/{fmt(r['espec'], 2)} & "
                 f"{fmtN(int(round(r['HL_chi2'])))} \\\\")
        first = False
    A.append(r"\midrule")
A[-1] = r"\bottomrule"
A += [r"\end{tabular}}", r"\end{table}"]
(TABLES / "glmm_ajuste.tex").write_text("\n".join(A) + "\n", encoding="utf-8")
print("OK -> glmm_glassceil.tex, glmm_ajuste.tex, evalues_glmm.csv")
print(g[["desfecho", "modelo", "OR_negro", "AME_pp", "ICC_UPA", "AUC_com_RE", "E_value"]].round(3).to_string(index=False))
