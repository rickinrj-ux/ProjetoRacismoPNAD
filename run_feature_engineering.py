"""
run_feature_engineering.py
===========================
Reconstrói features.parquet com todas as variáveis atuais, incluindo
log_horas (VD4031), urbano (V1022) e Ano — necessárias para os modelos
HLM, Oaxaca-Blinder e análises regionais.

Deve ser rodado antes de qualquer script de modelagem sempre que
feature_engineering.py for alterado.

Uso completo (todos os anos disponíveis):
    python run_feature_engineering.py

Teste rápido (10% da amostra, não salva):
    python run_feature_engineering.py --sample 0.10 --no_save

Anos específicos:
    python run_feature_engineering.py --anos 2021 2022 2023 2024
"""
import sys, logging, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/feature_engineering.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from feature_engineering import build_features, FEATURES_PATH

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reconstrói features.parquet com variáveis atualizadas"
    )
    parser.add_argument(
        "--anos",
        type=int,
        nargs="+",
        default=None,
        help="Anos a incluir (ex: 2021 2022 2023). Default: todos disponíveis.",
    )
    parser.add_argument(
        "--sample",
        type=float,
        default=None,
        help="Fração da amostra para teste (ex: 0.10). Default: dados completos.",
    )
    parser.add_argument(
        "--no_save",
        action="store_true",
        help="Não sobrescreve features.parquet (apenas valida o pipeline).",
    )
    args = parser.parse_args()

    df = build_features(
        years=args.anos,
        sample_frac=args.sample,
        save=not args.no_save,
    )

    print("\n=== CONCLUÍDO ===")
    print(f"Registros: {len(df):,}")
    print(f"Anos: {sorted(df['Ano'].unique().tolist())}")
    print(f"UFs: {df['UF'].nunique()} | UPAs: {df['UPA'].nunique():,}")
    print(f"Colunas novas presentes: "
          f"log_horas={'log_horas' in df.columns} | "
          f"urbano={'urbano' in df.columns}")
    if not args.no_save:
        print(f"Salvo em: {FEATURES_PATH}")
