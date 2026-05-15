"""
run_enrich_raw.py
=================
Enriquece os parquets processados com variáveis de ocupação, horas e setor
lidas diretamente dos ZIPs locais da PNAD Contínua (sem re-download).

Novas variáveis extraídas:
  VD4008  — grupo ocupacional no trabalho principal (1-dígito CBO: 1-10)
  VD4009  — posição na ocupação (formal/sem-carteira/conta-própria/etc.)
  VD4031  — total de horas trabalhadas efetivas em todos os trabalhos
  V4010   — código CBO-Domiciliar 2010 (4 dígitos)
  V4013   — CNAE-Domiciliar 2.0 (5 dígitos — setor econômico)

Saída: data/processed/ano=YYYY/trimestre=Q/extras.parquet
A feature_engineering.py fará o merge por (UPA, V1008, V2003) na reconstrução
do features.parquet.

Tempo estimado: ~30-50 min para 40 ZIPs (leitura seletiva de colunas).
"""
import sys; sys.stdout.reconfigure(encoding='utf-8')
import logging
import re
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

ROOT          = Path(r"C:\Users\user\Documents\ProjetoRacismoPNAD")
DATA_RAW      = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
LAYOUT_CACHE  = DATA_RAW / "layout"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Variáveis a extrair ────────────────────────────────────────────────────────
JOIN_VARS  = ["Ano", "Trimestre", "UPA", "V1008", "V2003"]
NEW_VARS   = ["VD4008", "VD4009", "VD4031", "V4010", "V4013"]
ALL_VARS   = JOIN_VARS + NEW_VARS

DTYPE_NEW = {
    "VD4008": "Int8",      # grupo ocupacional (1-10)
    "VD4009": "Int8",      # posição na ocupação (1-7)
    "VD4031": "Int16",     # horas trabalhadas efetivas (0-999)
    "V4010":  "category",  # CBO 4 dígitos (string)
    "V4013":  "category",  # CNAE 5 dígitos (string)
}

CHUNK_SIZE = 50_000


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_layout() -> pd.DataFrame:
    return pd.read_parquet(LAYOUT_CACHE / "layout.parquet")


def build_colspecs(layout: pd.DataFrame, variables: list):
    sub = layout[layout["name"].isin(variables)].sort_values("start")
    colspecs = [(int(r.start) - 1, int(r.end) - 1) for r in sub.itertuples()]
    names = sub["name"].tolist()
    missing = set(variables) - set(names)
    if missing:
        logger.warning(f"Variáveis ausentes no layout: {missing}")
    return colspecs, names


def get_year_quarter(zip_path: Path):
    m = re.match(r"PNADC_(\d)(\d{4})\.zip", zip_path.name)
    if m:
        return int(m.group(2)), int(m.group(1))
    return None, None


def read_zip_extras(zip_path: Path, colspecs: list, col_names: list) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        txt_files = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not txt_files:
            raise FileNotFoundError(f"Nenhum .txt em {zip_path.name}")
        with zf.open(txt_files[0]) as f:
            reader = pd.read_fwf(
                f,
                colspecs=colspecs,
                names=col_names,
                dtype=str,
                chunksize=CHUNK_SIZE,
                encoding="latin-1",
                na_values=["", " "],
            )
            chunks = [chunk for chunk in tqdm(reader, desc="  chunks", leave=False)]
    return pd.concat(chunks, ignore_index=True)


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    # Join key: match types from existing parquets
    df["Ano"]       = pd.to_numeric(df["Ano"],       errors="coerce").astype("int16")
    df["Trimestre"] = pd.to_numeric(df["Trimestre"], errors="coerce").astype("int8")
    df["UPA"]       = df["UPA"].astype(str).str.strip()
    df["V1008"]     = df["V1008"].astype(str).str.strip()
    df["V2003"]     = df["V2003"].astype(str).str.strip()

    # New variables
    for col, dtype in DTYPE_NEW.items():
        if col not in df.columns:
            continue
        if dtype == "category":
            df[col] = df[col].astype(str).str.strip().replace({"nan": None}).astype("category")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)
    return df


# ── Pipeline Principal ────────────────────────────────────────────────────────

def main():
    layout = load_layout()
    colspecs, col_names = build_colspecs(layout, ALL_VARS)
    logger.info(f"Variáveis no layout: {col_names}")
    logger.info(f"Colspecs: {list(zip(col_names, colspecs))}")

    zips = sorted(DATA_RAW.glob("PNADC_*.zip"))
    logger.info(f"ZIPs encontrados: {len(zips)}")

    ok = skip = fail = 0
    for zip_path in zips:
        year, quarter = get_year_quarter(zip_path)
        if year is None:
            logger.warning(f"Nome inesperado: {zip_path.name}")
            continue

        out_dir  = DATA_PROCESSED / f"ano={year}" / f"trimestre={quarter}"
        out_path = out_dir / "extras.parquet"

        if out_path.exists():
            logger.info(f"Já existe: ano={year}/trimestre={quarter} — pulando")
            skip += 1
            continue

        logger.info(f"Processando {year} T{quarter} ({zip_path.stat().st_size/1e6:.0f} MB)...")
        try:
            df = read_zip_extras(zip_path, colspecs, col_names)
            df = optimize_dtypes(df)
            table = pa.Table.from_pandas(df, preserve_index=False)
            pq.write_table(table, out_path, compression="snappy")
            logger.info(
                f"  Salvo: {out_path.relative_to(ROOT)} "
                f"({out_path.stat().st_size/1e6:.1f} MB | {len(df):,} linhas)"
            )
            ok += 1
        except Exception as exc:
            logger.error(f"  ERRO em {year} T{quarter}: {exc}")
            fail += 1

    logger.info(f"\nConcluído: {ok} gerados | {skip} pulados | {fail} erros")
    logger.info("Execute run_features_completo.py para reconstruir features.parquet")


if __name__ == "__main__":
    main()
