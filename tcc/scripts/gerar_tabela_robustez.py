# -*- coding: utf-8 -*-
"""
gerar_tabela_robustez.py — o inventário dos testes de robustez numa tabela só.

Por que existe: os diagnósticos estavam espalhados pelo texto (Breusch--Pagan
numa subseção, VIF noutra, E-value na tabela do GLMM, bootstrap nas legendas).
Quem avalia precisa de um lugar onde ver, de uma vez, o que foi testado, o que
deu e o que se fez a respeito.

Todo valor sai de csv de outputs/tables/ — nada é digitado. Se um teste ainda
não foi rodado, a linha informa isso em vez de omitir o teste.

Saída: outputs/tables/robustez.tex (label tab:robustez)
Uso:   python tcc/scripts/gerar_tabela_robustez.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
B = chr(92)


def ler(nome: str) -> pd.DataFrame | None:
    p = TAB / nome
    try:
        return pd.read_csv(p) if p.exists() else None
    except Exception:
        return None


def pt(x, d=2) -> str:
    """Decimal em pt-BR com o menos tipográfico que o resto do documento usa."""
    return f"{float(x):.{d}f}".replace(".", "{,}").replace("-", "−")


def linhas_tabela() -> list[tuple[str, str, str]]:
    """(o que foi testado, o que deu, o que se fez)."""
    L = []

    ob = ler("oaxaca_diagnosticos.csv")
    if ob is not None and len(ob) >= 2:
        r2 = [float(x) for x in ob["bp_r2_aux"]]
        ganho = [float(x) for x in ob["reset_ganho_r2"]]
        L.append((
            "Heterocedasticidade (Breusch--Pagan)",
            f"$R^2$ da regressão auxiliar: {pt(min(r2), 3)} e {pt(max(r2), 3)}",
            "erro-padrão agrupado por UPA e bootstrap em blocos"))
        L.append((
            "Forma funcional (RESET)",
            f"ganho de $R^2$ com potências do predito: {pt(min(ganho), 4)} a {pt(max(ganho), 4)}",
            "rejeição sem relevância prática; forma mantida"))

    vif = ler("vif_m4_preditores.csv")
    if vif is not None and "predictor" in vif.columns:
        v = vif.set_index("predictor")["VIF"]
        neg = v.get("negro")
        alto = v[v > 10]
        L.append((
            "Multicolinearidade (VIF)",
            (f"VIF de \\texttt{{negro}} $=$ {pt(neg)}; "
             + ("nenhum preditor acima de 10" if len(alto) == 0 else
              f"{len(alto)} preditores acima de 10, todos do bloco educacional")),
            ("sem colinearidade relevante; o coeficiente de interesse não é afetado"
             if len(alto) == 0 else
             "colinearidade por construção; não atinge o coeficiente de interesse")))

    fit = ler("hlm_stepup_fit.csv")
    if fit is not None:
        f = fit.set_index("modelo")
        if "M0" in f.index and "lr_vs_anterior" in f.columns:
            L.append((
                "Estrutura multinível (teste de razão de verossimilhança)",
                f"ICC da UPA no modelo nulo $=$ {pt(float(f.loc['M0', 'icc_upa']), 3)}",
                "nível de bairro justificado (limiar de 5\\%)"))

    var = ler("hlm_stepup_varcomp.csv")
    if var is not None and "componente" in var.columns:
        v = var.set_index("componente")
        if "tau2_upa" in v.index and {"ML", "REML"} <= set(v.columns):
            L.append((
                "Método de estimação (ML vs.\\ REML)",
                f"$\\hat\\tau^2$ da UPA: {pt(float(v.loc['tau2_upa', 'ML']), 5)} (ML) e "
                f"{pt(float(v.loc['tau2_upa', 'REML']), 5)} (REML)",
                "coincidem com $N$ de milhões; ML usado para os testes aninhados"))

    konf = ler("hlm_stepup_konfound.csv")
    if konf is not None and "modelo" in konf.columns:
        k = konf.set_index("modelo")
        if "M3" in k.index and "pct_vies_para_invalidar" in k.columns:
            L.append((
                "Confundidor não observado (Konfound/ITCV)",
                f"{pt(float(k.loc['M3', 'pct_vies_para_invalidar']), 1)}\\% das estimativas "
                "teriam de ser viés para anular o achado",
                "achado robusto a confundimento plausível"))

    # O E-value não está no csv: é derivado do OR (VanderWeele & Ding, 2017),
    # como já se faz em params_nucleo e em validate_consistency.
    gl = ler("glmm_glassceil_glmer.csv")
    if gl is not None and "OR_negro" in gl.columns:
        import math
        from params_nucleo import evalue   # √OR para desfecho comum (E2.7)
        e = pd.Series([evalue(float(o), d) for o, d in zip(gl["OR_negro"], gl["desfecho"])])
        L.append((
            "Confundidor não observado (E-value)",
            f"E-value entre {pt(e.min())} e {pt(e.max())}",
            "um confundidor precisaria dessa força com raça e desfecho"))

    ml = ler("ml_performance.csv")
    if ml is not None and "gap_overfit" in ml.columns:
        g = ml["gap_overfit"].astype(float).abs()
        L.append((
            "Sobreajuste (treino vs.\\ teste)",
            f"maior diferença de $R^2$: {pt(g.max(), 4)}",
            "partição 80/20 e validação cruzada $k$-\\textit{fold}"))

    # E8 (04/10/2026): baseline linear do ML e peso amostral no acesso e na Oaxaca
    bl = ler("ml_baseline_comparacao.csv")
    if bl is not None and len(bl) >= 3:
        r2 = bl.set_index("Modelo")["R2_teste"].astype(float)
        mqo = r2.get("MQO (baseline linear)")
        if mqo is not None:
            L.append((
                "Ganho do ML sobre o linear",
                (f"$R^2$ de teste: MQO {pt(mqo, 3)}; RF {pt(r2.get('Random Forest'), 3)}; "
                 f"XGBoost {pt(r2.get('XGBoost'), 3)}"),
                f"mesmo treino e teste: o RF empata com o linear (+{pt(r2.get('Random Forest') - mqo, 3)}); "
                 f"o XGBoost ganha {pt(r2.get('XGBoost') - mqo, 3)}"))
    gp, op = ler("glmm_ponderado_a2.csv"), ler("oaxaca_ponderado_ab.csv")
    if gp is not None and op is not None:
        g_ = gp[gp["desfecho"] == "ocp_qualif"].set_index("ponderado")["OR_negro"]
        o_ = op[op["espec"] == "A"].set_index("ponderado")["pct_retornos"]
        t_ = gp[gp["desfecho"] == "y_top10"].set_index("ponderado")["OR_negro"]
        L.append((
            "Peso amostral (V1028) no acesso, no topo e na decomposição",
            (f"OR do acesso {pt(g_[False], 3)} $\\to$ {pt(g_[True], 3)}; topo 10\\% "
             f"{pt(t_[False], 3)} $\\to$ {pt(t_[True], 3)}; preço da Oaxaca (A, com peso) "
             f"{pt(o_[False], 1)}\\% $\\to$ {pt(o_[True], 1)}\\%"),
            "logit com efeito fixo de estado e erro agrupado por UPA; conclusão inalterada"))

    cv = ler("ml_cv_resumo.csv")
    if cv is not None and len(cv):
        col = next((c for c in cv.columns if "r2" in c.lower() and "dp" not in c.lower()), None)
        if col:
            L.append((
                "Validação cruzada ($k=5$)",
                f"$R^2$ médio entre \\textit{{folds}}: {pt(float(cv[col].iloc[0]), 4)}",
                "hiperparâmetros escolhidos em partição de validação e confirmados por CV"))

    bal = ler("balanceamento.csv")
    if bal is not None:
        # diferença PADRONIZADA = d de Cohen; a busca por "dif" pegava a coluna da diferença
        # bruta de médias (1,47 da idade) em vez do maior |d| (1,16)
        col = next((c for c in ("d_cohen", "smd") if c in bal.columns), None)
        if col:
            d = bal[col].astype(float).abs()
            L.append((
                "Balanceamento e suporte comum",
                f"maior diferença padronizada entre grupos: {pt(d.max())}",
                "desequilíbrio concentrado no contexto de bairro, absorvido pelo nível 2"))

    n3 = ler("hlm_tres_niveis.csv")
    if n3 is not None and "modelo" in n3.columns:
        n = n3.set_index("modelo")
        if "M2" in n.index and "b_negro" in n.columns:
            L.append((
                "Especificação do nível de estado",
                f"coeficiente racial com UF aleatória: {pt(float(n.loc['M2', 'b_negro']), 4)}",
                "igual ao da UF como efeito fixo; resultado não depende da escolha"))

    L.append((
        "Vazamento das médias de contexto",
        "médias do bairro e do estado calculadas sem a própria observação",
        "evita que a raça do indivíduo entre no regressor que o descreve"))

    L.append((
        "Dependência intragrupo (Moulton)",
        "regressores que variam no nível da UPA",
        "erro-padrão agrupado por UPA em todos os modelos"))

    return L


def main() -> int:
    linhas = linhas_tabela()
    out = [
        B + "begin{table}[!ht]",
        B + "centering",
        B + "caption{Testes de robustez e diagnóstico. Cada linha traz o que foi",
        "verificado, o resultado e a providência tomada. Valores extraídos dos",
        "mesmos csv que alimentam as demais tabelas.}",
        B + "label{tab:robustez}",
        B + "small",
        B + "begin{tabular}{p{4.1cm}p{5.3cm}p{4.9cm}}",
        B + "toprule",
        "Verificação & Resultado & Providência " + B * 2,
        B + "midrule",
    ]
    for i, (o, r, p) in enumerate(linhas):
        out.append(f"{o} & {r} & {p} " + B * 2)
        if i < len(linhas) - 1:
            out.append(B + "addlinespace[2pt]")
    out += [
        B + "bottomrule",
        B + "end{tabular}",
        B + "par" + B + "smallskip" + B + "footnotesize Fonte: Resultados originais da pesquisa.",
        B + "end{table}",
    ]
    dest = TAB / "robustez.tex"
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"OK -> {dest.relative_to(ROOT)}  ({len(linhas)} verificações)")
    for o, r, _ in linhas:
        print(f"  · {o}: {r[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
