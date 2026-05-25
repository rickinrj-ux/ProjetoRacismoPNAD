"""
run_analises_complementares.py
==============================
Runner combinado para as três análises complementares do TCC:

  1. Oster bounds         — robustez a variáveis omitidas
  2. Interseccionalidade  — OB 4 grupos + HLM interseccional (raça × gênero × educação)
  3. RIF-OB               — decomposição do glass ceiling por quantil incondicional

Uso:
    python run_analises_complementares.py
    python run_analises_complementares.py --sample 0.10   # rápido para teste
    python run_analises_complementares.py --skip-hlm      # pula HLM interseccional (lento)
"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import argparse
import logging
import time
from pathlib import Path

sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/analises_complementares.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

from oster_bounds     import run_oster_bounds
from interseccionalidade import run_interseccionalidade
from rif_decomp       import run_rif_decomp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=float, default=None,
                        help="Fração da amostra para TODAS as análises. "
                             "Default: população completa (Oster + OB 4g); "
                             "10%% para RIF (ajustável separadamente).")
    parser.add_argument("--rif-sample", type=float, default=0.10,
                        help="Fração específica para RIF-OB. Default: 10%%.")
    parser.add_argument("--skip-hlm", action="store_true",
                        help="Pula o HLM interseccional (mais lento).")
    args = parser.parse_args()

    t0 = time.time()

    # ── 1. Oster bounds ────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  [1/3] OSTER BOUNDS — Robustez a Variáveis Omitidas")
    print("="*65)
    t1 = time.time()
    res_oster = run_oster_bounds(sample_frac=args.sample)
    logger.info(f"Oster concluído em {(time.time()-t1)/60:.1f} min")

    # ── 2. Interseccionalidade ─────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  [2/3] INTERSECCIONALIDADE — OB 4 Grupos + HLM Interseccional")
    print("="*65)
    t2 = time.time()
    sample_inter = args.sample if not args.skip_hlm else args.sample
    res_inter = run_interseccionalidade(sample_frac=sample_inter)
    logger.info(f"Interseccionalidade concluída em {(time.time()-t2)/60:.1f} min")

    # ── 3. RIF-OB ──────────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  [3/3] RIF-OB — Decomposição por Quantil Incondicional")
    print("="*65)
    t3 = time.time()
    rif_sample = args.rif_sample if args.sample is None else args.sample
    res_rif = run_rif_decomp(sample_frac=rif_sample)
    logger.info(f"RIF-OB concluído em {(time.time()-t3)/60:.1f} min")

    # ── Sumário final ──────────────────────────────────────────────────────────
    elapsed = (time.time() - t0) / 60
    print(f"\n{'='*65}")
    print(f"  ANÁLISES COMPLEMENTARES CONCLUÍDAS em {elapsed:.1f} min")
    print(f"{'='*65}")
    print("  Outputs gerados:")
    outputs = [
        "outputs/tables/oster_bounds.{csv,tex}",
        "outputs/figures/oster_bounds.png",
        "outputs/tables/interseccional_ob4grupos.csv",
        "outputs/tables/interseccional_{eme,coeficientes}.{csv,tex}",
        "outputs/figures/interseccional_{eme_grupos,coeficientes,ob4grupos}.png",
        "outputs/tables/rif_ob_decomposicao.{csv,tex}",
        "outputs/figures/rif_ob_{decomposicao,retornos_quantis}.png",
    ]
    for o in outputs:
        print(f"    {o}")


if __name__ == "__main__":
    main()
