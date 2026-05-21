"""
reconciliar_mlflow_retornos.py
==============================
Registra no MLflow os resultados já calculados de OB decomposition e
regressão quantílica (Koenker-Bassett), que ficaram fora do tracking por
uma run interrompida anteriormente.

Lê os CSVs em outputs/tables/ e cria uma run nova no experimento
'Retornos_Raciais' com status FINISHED.

Uso:
    python reconciliar_mlflow_retornos.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
from mlflow_utils import run_context, log_params, log_metrics, log_artifacts_dir, MLFLOW_AVAILABLE

if not MLFLOW_AVAILABLE:
    print("MLflow não instalado. Instale com: pip install mlflow")
    sys.exit(1)

TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"


def main():
    ob = pd.read_csv(TABLES / "ob_decomposicao.csv").iloc[0]
    ob_melh = pd.read_csv(TABLES / "ob_melhorias.csv")
    qr_kb = pd.read_csv(TABLES / "qr_kb_test.csv").iloc[0]
    qr_melh = pd.read_csv(TABLES / "qr_melhorias.csv")

    # Extrair sub-grupos de OB
    ob_total = ob_melh[ob_melh["sub_grupo"] == "Total"].iloc[0]
    ob_homens = ob_melh[ob_melh["sub_grupo"] == "Homens"].iloc[0]
    ob_mulheres = ob_melh[ob_melh["sub_grupo"] == "Mulheres"].iloc[0]
    ob_2016 = ob_melh[ob_melh["sub_grupo"] == "2016-2018"].iloc[0]
    ob_2022 = ob_melh[ob_melh["sub_grupo"] == "2022-2025"].iloc[0]

    # Extrair quantis globais
    qr_global = qr_melh[qr_melh["grupo"] == "Global"]

    with run_context(
        run_name="OB_QR_PopCompleta_reconciliado",
        experiment="Retornos_Raciais",
        tags={
            "source": "reconciliacao",
            "data_analise": "2026-05-18",
            "sample": "populacao_completa",
            "nota": "run recriada de CSVs existentes — run anterior interrompida",
        },
    ) as run:
        log_params({
            "n_negros_ob":    int(ob["n_negros"]),
            "n_brancos_ob":   int(ob["n_brancos"]),
            "n_bootstrap_ob": int(ob["n_bootstrap"]),
            "n_boot_qr":      int(qr_kb["n_boot"]),
            "boot_frac_qr":   float(qr_kb["boot_frac"]),
            "sample_frac":    None,
            "metodo":         "OB_twin-interação + QR Koenker-Bassett",
        })

        # ── OB decomposition ──────────────────────────────────────────────────
        log_metrics({
            "ob_gap_log":           float(ob["gap_total"]),
            "ob_gap_pct":           float(ob["gap_pct"]),
            "ob_ef_dotacao_log":    float(ob["ef_dotacao"]),
            "ob_pct_dotacao":       float(ob["pct_dotacao"]),
            "ob_ef_coef_log":       float(ob["ef_coeficiente"]),
            "ob_pct_coeficiente":   float(ob["pct_coeficiente"]),

            # global (twin-interação)
            "ob_total_gap_pct":     float(ob_total["gap_pct"]),
            "ob_total_dot_pct":     float(ob_total["dot_pct"]),
            "ob_total_ret_pct":     float(ob_total["ret_pct"]),

            # por sexo
            "ob_homens_gap_pct":    float(ob_homens["gap_pct"]),
            "ob_mulheres_gap_pct":  float(ob_mulheres["gap_pct"]),
            "ob_delta_sexo_pp":     float(ob_homens["gap_pct"]) - float(ob_mulheres["gap_pct"]),

            # temporal
            "ob_2016_2018_gap_pct": float(ob_2016["gap_pct"]),
            "ob_2022_2025_gap_pct": float(ob_2022["gap_pct"]),
            "ob_delta_temporal_pp": float(ob_2022["gap_pct"]) - float(ob_2016["gap_pct"]),
            "ob_2016_2018_ret_pct": float(ob_2016["ret_pct"]),
            "ob_2022_2025_ret_pct": float(ob_2022["ret_pct"]),
        })

        # ── Koenker-Bassett (QR) ──────────────────────────────────────────────
        log_metrics({
            "qr_b_q10":         float(qr_kb["b_q10"]),
            "qr_b_q50":         float(qr_kb["b_q50"]),
            "qr_b_q90":         float(qr_kb["b_q90"]),
            "qr_diff_q90_q10":  float(qr_kb["diff_q90_q10"]),
            "qr_se_boot":       float(qr_kb["se_boot"]),
            "qr_ci_lo":         float(qr_kb["ci_lo_boot"]),
            "qr_ci_hi":         float(qr_kb["ci_hi_boot"]),
            "qr_z_stat":        float(qr_kb["z_stat"]),
            "qr_p_valor":       float(qr_kb["p_valor_z"]),
            "qr_wald_chi2":     float(qr_kb["wald_chi2_2"]),
            "qr_p_wald":        float(qr_kb["p_valor_wald"]),
        })

        # quantis globais individuais
        for _, row in qr_global.iterrows():
            q_label = f"q{int(row['quantil']*100):02d}"
            log_metrics({
                f"qr_global_{q_label}_b":       float(row["b_negro"]),
                f"qr_global_{q_label}_gap_pct": float(row["gap_pct"]),
            })

        # ── Artefatos ────────────────────────────────────────────────────────
        log_artifacts_dir(TABLES, subfolder="tables")
        if FIGURES.exists():
            log_artifacts_dir(FIGURES, subfolder="figures")

        print(f"\nRun criada: {run.info.run_id}")
        print(f"  ob_gap_pct={ob['gap_pct']:.2f}%  ob_pct_dotacao={ob['pct_dotacao']:.1f}%")
        print(f"  qr_diff_q90_q10={qr_kb['diff_q90_q10']:.4f}  z={qr_kb['z_stat']:.3f}  p={qr_kb['p_valor_z']}")
        print("MLflow tracking: reconciliação concluída.")


if __name__ == "__main__":
    main()
