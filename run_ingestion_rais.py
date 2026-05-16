"""
run_ingestion_rais.py
=====================
Ingestão e limpeza dos microdados RAIS (arquivos brutos MTE).
Output: data/external/rais_processada.parquet

COMO OBTER OS ARQUIVOS RAIS
----------------------------
1. Acesse o FTP do MTE:
      ftp://ftp.mtecaged.gov.br/ftp/rais/
   Navegue até o ano desejado → pasta "RAIS_VINC_PUB_<UF>"

2. Alternativamente via navegador (IPEA/MTE):
      https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/rais
      → "Microdados" → selecione o ano → baixe por UF

3. Os arquivos vêm compactados como .7z (use 7-Zip para descompactar)
   Resultado: RAIS_VINC_PUB_<UF>_<ANO>.txt  (codificação cp1252)

4. Coloque TODOS os .txt descompactados em um único diretório:
      data/external/rais_raw/

5. Execute este script:
      python run_ingestion_rais.py --rais_dir data/external/rais_raw/

Período coberto: 2016-2025 (espelho da PNAD Contínua).
    Obs.: a RAIS é divulgada com ~12 meses de defasagem (em 2026, o dado
    mais recente disponível costuma ser o de 2024).

Uso:
    python run_ingestion_rais.py --rais_dir data/external/rais_raw/
    python run_ingestion_rais.py --rais_dir data/external/rais_raw/ --anos 2016 2017 2018 2019 2020 2021 2022 2023 2024
    python run_ingestion_rais.py --rais_dir data/external/rais_raw/ --ufs SP RJ MG --sample 0.10
    python run_ingestion_rais.py --rais_dir data/external/rais_raw/ --output data/external/rais_2016_2024.parquet

Após concluir:
    python run_validacao.py --rais_path data/external/rais_processada.parquet
"""
import sys
import logging
import argparse
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "src")
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("logs/ingestion_rais.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

from ingestion_rais import run_ingestion_rais

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingestão RAIS — arquivos .txt brutos do MTE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--rais_dir", type=str, required=True,
        help="Diretório com os arquivos .txt RAIS descompactados."
    )
    parser.add_argument(
        "--anos", type=int, nargs="+", default=None,
        help="Anos a processar (ex: 2016 2017 ... 2025). Default: todos os encontrados."
    )
    parser.add_argument(
        "--ufs", type=str, nargs="+", default=None,
        help="UFs a incluir (ex: SP RJ MG). Default: todas."
    )
    parser.add_argument(
        "--output", type=str, default="data/external/rais_processada.parquet",
        help="Caminho do parquet de saída. Default: data/external/rais_processada.parquet"
    )
    parser.add_argument(
        "--sample", type=float, default=None,
        help="Fração amostral para testes (ex: 0.10). Default: dados completos."
    )
    args = parser.parse_args()

    df = run_ingestion_rais(
        rais_dir=args.rais_dir,
        anos=args.anos,
        output_path=args.output,
        sample_frac=args.sample,
        ufs=args.ufs,
    )

    print("\n=== CONCLUIDO ===")
    print(f"Registros processados : {len(df):,}")
    print(f"Anos                  : {sorted(df['Ano'].unique().tolist())}")
    print(f"% negro               : {df['negro'].mean():.1%}")
    gap = df.groupby("negro")["log_renda"].mean()
    gap_val = gap[1.0] - gap[0.0]
    print(f"Gap bruto log-renda   : {gap_val:+.4f}  ({(pow(2.718281828, gap_val) - 1)*100:+.1f}%)")
    print(f"\nProximo passo:")
    print(f"  python run_validacao.py --rais_path {args.output}")
