"""
data_ingestion.py
=================
Pipeline de download e ingestão dos microdados da PNAD Contínua (IBGE).

Fluxo:
    1. Download do dicionário de layout (SAS INPUT) do FTP do IBGE
    2. Parsing das especificações de colunas (fixed-width format)
    3. Download dos arquivos trimestrais comprimidos (.zip → .txt)
    4. Leitura em chunks para controle de memória (32GB RAM disponíveis)
    5. Otimização de tipos de dados (categoricals, int16, float32)
    6. Exportação em Parquet particionado por Ano/Trimestre

Justificativa do formato Parquet:
    Compressão snappy reduz ~5-10x o tamanho vs. TXT original.
    Predicate pushdown aplica filtros durante leitura — I/O seletivo
    no NVMe Samsung 990 PRO, relevante para a série histórica completa.

Referências:
    IBGE. (2023). PNAD Contínua — Notas Metodológicas. Rio de Janeiro: IBGE.
    McKinney, W. (2022). Python for Data Analysis (3rd ed.). O'Reilly.
"""

import io
import logging
import re
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
from tqdm import tqdm

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────
IBGE_BASE_URL = (
    "https://ftp.ibge.gov.br/Trabalho_e_Rendimento/"
    "Pesquisa_Nacional_por_Amostra_de_Domicilios_continua/"
    "Trimestral/Microdados"
)
DOCS_URL = f"{IBGE_BASE_URL}/Documentacao"

# Dicionários de layout conhecidos — tentados em ordem até o primeiro sucesso
KNOWN_DICT_URLS = [
    f"{DOCS_URL}/Dicionario_e_input_20221031.zip",
    f"{DOCS_URL}/Dicionario_e_input_20200220.zip",
    f"{DOCS_URL}/Dicionario_e_input_20190529.zip",
]

# Variáveis de interesse para o projeto (subconjunto mínimo necessário)
# Limitar colunas carregadas reduz I/O e memória proporcionalmente
TARGET_VARIABLES = [
    "Ano", "Trimestre", "UF", "Capital", "RM_RIDE", "UPA",
    "Estrato", "V1008",
    "V1022",              # situação do domicílio: 1=urbano, 2=rural
    "V1023",              # tipo de área
    "V1027", "V1028", "V1033",  # pesos amostrais (layout 2022+): projeção, sem calib., com calib.
    "V2003",              # número de ordem do morador
    "V2005",              # condição no domicílio (chefe, cônjuge, etc.)
    "V2007",              # sexo
    "V2009",              # idade
    "V2010",              # cor ou raça (variável central do projeto)
    "V3009A",             # nível de instrução mais elevado
    "VD4002",             # condição de ocupação (ocupado/desocupado)
    "VD4016",             # rendimento habitual do trabalho principal
    "VD4019",             # rendimento habitual de todos os trabalhos
    "VD4020",             # rendimento efetivo de todos os trabalhos (variável dependente)
]

# Tipos otimizados por variável
# Estratégia: Int8/Int16 (nullable pandas) para inteiros com NaN possível;
# int16 puro apenas onde NaN é impossível (Ano, Trimestre — sempre presentes);
# float32 para rendimentos; float64 para pesos (sensíveis a arredondamento)
DTYPE_MAP: Dict[str, str] = {
    "Ano":        "int16",
    "Trimestre":  "int8",
    "UF":         "category",
    "Capital":    "Int8",    # nullable — pode ser NaN fora de capitais
    "RM_RIDE":    "Int8",    # nullable — ausente fora de regiões metropolitanas
    "V1022":      "Int8",
    "V1023":      "Int8",
    "V2005":      "Int8",
    "V2007":      "Int8",
    "V2009":      "Int16",   # nullable — menores de 14 podem ter NaN
    "V2010":      "Int8",    # nullable — raça pode ser ignorada (código 9)
    "V3009A":     "Int8",    # nullable — crianças sem instrução declarada
    "VD4002":     "Int8",    # nullable — apenas para PEA (14+)
    "VD4016":     "float32",
    "VD4019":     "float32",
    "VD4020":     "float32",
    "V1027":      "float32",  # projeção populacional
    "V1028":      "float64",  # peso sem calibração
    "V1033":      "float64",  # peso final calibrado para pessoas (usar nas análises)
}

# Calibrado para 32GB RAM: cada chunk de 50k linhas usa ~150-250MB,
# deixando espaço para múltiplos processos paralelos
CHUNK_SIZE = 50_000
REQUEST_TIMEOUT = 180
MAX_RETRIES = 3

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
LAYOUT_CACHE = DATA_RAW / "layout"

for _p in [DATA_RAW, DATA_PROCESSED, LAYOUT_CACHE]:
    _p.mkdir(parents=True, exist_ok=True)


# ── Download Utilitário ───────────────────────────────────────────────────────

def _download_bytes(url: str, desc: str = "") -> Optional[bytes]:
    """Download com retry e exponential backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
            resp.raise_for_status()
            chunks: List[bytes] = []
            total = int(resp.headers.get("content-length", 0))
            with tqdm(total=total, unit="B", unit_scale=True, desc=desc, leave=False) as pbar:
                for chunk in resp.iter_content(chunk_size=65_536):
                    chunks.append(chunk)
                    pbar.update(len(chunk))
            return b"".join(chunks)
        except requests.RequestException as exc:
            wait = 2 ** attempt
            logger.warning(f"Tentativa {attempt}/{MAX_RETRIES} falhou ({exc}). Aguardando {wait}s...")
            time.sleep(wait)
    logger.error(f"Falha total ao baixar: {url}")
    return None


# ── Parsing do Dicionário SAS ─────────────────────────────────────────────────

def parse_sas_input(sas_text: str) -> pd.DataFrame:
    """
    Extrai especificações de colunas do INPUT statement SAS do IBGE.

    Formato do IBGE: @posição_inicial  NomeVar  largura[.$]
    Regex captura: posição (1-indexed), nome, largura e se é string.

    Preferimos regex sobre um parser SAS completo porque o IBGE usa
    subconjunto fixo e previsível da sintaxe — mais robusto a variações
    de formatação entre versões do dicionário.
    """
    pattern = re.compile(r"@(\d+)\s+(\w+)\s+(\$?)(\d+)\.", re.MULTILINE)
    records = [
        {
            "name":    m.group(2),
            "start":   int(m.group(1)),   # 1-indexed (convenção SAS)
            "width":   int(m.group(4)),
            "is_char": m.group(3) == "$",
        }
        for m in pattern.finditer(sas_text)
    ]
    if not records:
        raise ValueError(
            "Nenhuma variável encontrada no SAS INPUT. Verifique o formato do dicionário."
        )
    df = pd.DataFrame(records)
    df["end"] = df["start"] + df["width"]  # end exclusivo, para pandas read_fwf
    logger.info(f"Layout SAS parseado: {len(df)} variáveis encontradas.")
    return df


def download_layout(force: bool = False) -> pd.DataFrame:
    """
    Baixa e faz cache local do dicionário de layout da PNAD Contínua.

    Tenta URLs conhecidas em ordem de recência. Em falha total, usa
    fallback hardcoded verificado contra o dicionário IBGE 2022-10-31.
    """
    cache_path = LAYOUT_CACHE / "layout.parquet"
    if cache_path.exists() and not force:
        logger.info("Layout carregado do cache local.")
        return pd.read_parquet(cache_path)

    for url in KNOWN_DICT_URLS:
        logger.info(f"Buscando dicionário: {url}")
        data = _download_bytes(url, desc="Dicionário IBGE")
        if data is None:
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                sas_files = [n for n in zf.namelist() if n.lower().endswith(".sas")]
                if not sas_files:
                    logger.warning("Nenhum arquivo .sas encontrado no ZIP.")
                    continue
                sas_text = zf.read(sas_files[0]).decode("latin-1")
            layout = parse_sas_input(sas_text)
            layout.to_parquet(cache_path, index=False)
            return layout
        except Exception as exc:
            logger.warning(f"Erro ao processar ZIP: {exc}")

    logger.warning(
        "Download do dicionário falhou. Usando fallback hardcoded. "
        "Verifique manualmente se as posições VD4xxx estão corretas para seu ano."
    )
    return _fallback_layout()


def _fallback_layout() -> pd.DataFrame:
    """
    Layout hardcoded das variáveis de interesse.

    Posições verificadas contra o dicionário IBGE 2022-10-31.
    As posições das variáveis VD (derivadas) variam entre versões —
    use este fallback apenas como ponto de partida e valide contra
    o dicionário oficial antes de análises definitivas.
    """
    cols = [
        # (nome, início_1indexed, largura)
        ("Ano",       1,  4), ("Trimestre",  5,  1), ("UF",       6,  2),
        ("Capital",   8,  1), ("RM_RIDE",    9,  1), ("UPA",     10,  9),
        ("Estrato",  19,  6), ("V1008",     25,  3), ("V1014",   28,  2),
        ("V1016",    30,  1), ("V1022",     31,  1), ("V1023",   32,  1),
        ("V1030",    33, 10), ("V1031",     43, 10), ("V1032",   53, 10),
        ("V2001",    63,  2), ("V2003",     65,  2), ("V2005",   67,  2),
        ("V2007",    69,  1), ("V2009",     78,  3), ("V2010",   81,  1),
        ("V3009A",   95,  2),
        # Posições aproximadas para variáveis derivadas (VD) — confirmar com layout oficial
        ("VD4002",  776,  1), ("VD4016",   789,  9),
        ("VD4019",  798,  9), ("VD4020",   807,  9),
    ]
    records = [
        {"name": n, "start": s, "width": w, "is_char": False, "end": s + w}
        for n, s, w in cols
    ]
    return pd.DataFrame(records)


def build_colspecs(
    layout: pd.DataFrame,
    variables: List[str],
) -> Tuple[List[Tuple[int, int]], List[str]]:
    """
    Converte o layout para colspecs do pandas.read_fwf.

    pandas.read_fwf usa índices 0-based (start, end) exclusivo no end.
    SAS usa 1-based no start — subtraímos 1 na conversão.
    """
    sub = layout[layout["name"].isin(variables)].sort_values("start")
    colspecs = [(int(r.start) - 1, int(r.end) - 1) for r in sub.itertuples()]
    names = sub["name"].tolist()
    missing = set(variables) - set(names)
    if missing:
        logger.warning(f"Variáveis não encontradas no layout: {missing}")
    return colspecs, names


# ── Download e Leitura dos Dados Trimestrais ──────────────────────────────────

def _discover_quarter_url(year: int, quarter: int) -> Optional[str]:
    """
    Descobre a URL exata do arquivo trimestral listando o diretório do IBGE.

    Suporta dois formatos de nomenclatura:
        - Com sufixo de data (2016-2024): PNADC_0{q}{year}_{YYYYMMDD}.zip
        - Sem sufixo de data (2025+):     PNADC_0{q}{year}.zip
    A descoberta dinâmica evita hardcodar datas que mudam a cada republicação.
    """
    dir_url = f"{IBGE_BASE_URL}/{year}/"
    try:
        resp = requests.get(dir_url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"Não foi possível listar diretório {year}: {exc}")
        return None

    prefix = f"PNADC_0{quarter}{year}"

    # Tenta primeiro com sufixo de data (formato predominante 2016-2024)
    matches_with_date = re.findall(rf"{re.escape(prefix)}_\d+\.zip", resp.text)
    if matches_with_date:
        filename = sorted(matches_with_date)[-1]   # mais recente se houver múltiplas versões
        logger.info(f"Arquivo descoberto: {filename}")
        return f"{IBGE_BASE_URL}/{year}/{filename}"

    # Fallback: formato sem sufixo de data (2025+)
    matches_no_date = re.findall(rf"{re.escape(prefix)}\.zip", resp.text)
    if matches_no_date:
        filename = matches_no_date[0]
        logger.info(f"Arquivo descoberto (sem sufixo de data): {filename}")
        return f"{IBGE_BASE_URL}/{year}/{filename}"

    logger.warning(f"Nenhum arquivo encontrado para {year} T{quarter} em {dir_url}")
    return None


def download_quarter(year: int, quarter: int, force: bool = False) -> Optional[Path]:
    """Baixa o arquivo trimestral e salva em data/raw/."""
    out_path = DATA_RAW / f"PNADC_{quarter:01d}{year}.zip"
    if out_path.exists() and not force:
        logger.info(f"Já existe: {out_path.name}")
        return out_path

    url = _discover_quarter_url(year, quarter)
    if url is None:
        return None

    logger.info(f"Baixando {year} T{quarter}: {url}")
    data = _download_bytes(url, desc=f"{year}-T{quarter}")
    if data is None:
        return None

    out_path.write_bytes(data)
    logger.info(f"Salvo: {out_path.name} ({out_path.stat().st_size / 1e6:.1f} MB)")
    return out_path


def read_pnadc_zip(
    zip_path: Path,
    colspecs: List[Tuple[int, int]],
    col_names: List[str],
) -> pd.DataFrame:
    """
    Lê o TXT de largura fixa dentro do ZIP em chunks e concatena.

    Leitura inicial como string (dtype=str) evita erros de inferência
    de tipo em campos com espaços ou códigos especiais — a conversão
    de tipo ocorre depois em optimize_dtypes().
    """
    with zipfile.ZipFile(zip_path) as zf:
        txt_files = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not txt_files:
            raise FileNotFoundError(f"Nenhum .txt em {zip_path.name}")
        txt_name = txt_files[0]
        logger.info(f"Lendo {txt_name} em chunks de {CHUNK_SIZE:,} linhas...")
        with zf.open(txt_name) as f:
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

    df = pd.concat(chunks, ignore_index=True)
    logger.info(f"  {len(df):,} registros lidos.")
    return df


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte colunas para tipos de menor footprint de memória.

    Redução esperada: ~75% do uso de memória vs. object/float64 padrão.
    Valores não-convertíveis viram NaN (coerce) em vez de levantar exceção —
    preserva a estrutura amostral da PNAD mesmo com eventuais inconsistências.
    """
    for col, dtype in DTYPE_MAP.items():
        if col not in df.columns:
            continue
        try:
            if dtype == "category":
                df[col] = df[col].astype("category")
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)
        except Exception as exc:
            logger.warning(f"Conversão falhou para {col} → {dtype}: {exc}")
    return df


# ── Pipeline Principal ────────────────────────────────────────────────────────

def ingest_quarter(
    year: int,
    quarter: int,
    layout: pd.DataFrame,
    force_download: bool = False,
) -> None:
    """Ingere um trimestre: download → parse → otimização → Parquet."""
    zip_path = download_quarter(year, quarter, force=force_download)
    if zip_path is None:
        logger.error(f"Pulando {year} T{quarter}: falha no download.")
        return

    colspecs, col_names = build_colspecs(layout, TARGET_VARIABLES)
    df = read_pnadc_zip(zip_path, colspecs, col_names)
    df = optimize_dtypes(df)

    # Particionamento Hive-style: compatível com DuckDB, Spark e PyArrow
    out_dir = DATA_PROCESSED / f"ano={year}" / f"trimestre={quarter}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "data.parquet"

    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, out_path, compression="snappy")

    logger.info(
        f"Parquet salvo: {out_path.relative_to(ROOT)} "
        f"({out_path.stat().st_size / 1e6:.1f} MB | {len(df):,} linhas)"
    )
    # Libera RAM explicitamente antes do próximo quarter
    del df, table


def run_ingestion(
    years: Optional[List[int]] = None,
    quarters: Optional[List[int]] = None,
    force_download: bool = False,
) -> None:
    """
    Ponto de entrada principal do pipeline de ingestão.

    Args:
        years: Anos a processar. Default: 2019-2024 (série histórica recente).
        quarters: Trimestres [1,2,3,4]. Default: todos.
        force_download: Re-baixa mesmo se arquivo já existir localmente.

    Estimativa de tempo/espaço:
        ~48 arquivos × ~300MB/arquivo = ~14GB raw
        ~48 arquivos × ~60MB Parquet  = ~3GB processado
        Tempo: ~2-4h dependendo da banda disponível
    """
    if years is None:
        years = list(range(2019, 2025))
    if quarters is None:
        quarters = [1, 2, 3, 4]

    layout = download_layout()

    total = len(years) * len(quarters)
    logger.info(
        f"Iniciando ingestão: {total} arquivo(s) | "
        f"Anos: {years[0]}-{years[-1]} | Trimestres: {quarters}"
    )

    for year in years:
        for quarter in quarters:
            logger.info(f"─── {year} T{quarter} ───")
            ingest_quarter(year, quarter, layout, force_download=force_download)

    logger.info(f"Ingestão concluída. Dados em: {DATA_PROCESSED}")


if __name__ == "__main__":
    # Para testar o pipeline antes da ingestão completa, comece com 1 trimestre
    run_ingestion(years=[2023], quarters=[1])
