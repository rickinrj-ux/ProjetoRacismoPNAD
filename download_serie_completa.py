"""
download_serie_completa.py
==========================
Download e ingestao da serie historica completa da PNAD Continua (2016-2025).

36 trimestres x ~200MB = ~7.2GB raw  |  ~36 x 5MB = ~180MB Parquet processado
Tempo estimado: 30-90 min (depende da banda disponivel)

Retomada automatica: arquivos ja baixados sao ignorados (force_download=False).
Execute novamente em caso de interrupcao — o pipeline continua de onde parou.

Acompanhe o progresso em: logs/download_serie.log
"""
import sys
import logging
import time
from pathlib import Path

sys.path.insert(0, "src")

LOG_FILE = Path("logs/download_serie.log")
LOG_FILE.parent.mkdir(exist_ok=True)

# Log simultaneo para arquivo e console
handlers = [
    logging.FileHandler(LOG_FILE, encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=handlers,
)
logger = logging.getLogger(__name__)

from data_ingestion import download_layout, ingest_quarter

# Serie completa: 2016-2025, todos os trimestres disponiveis
YEARS    = list(range(2016, 2026))
QUARTERS = [1, 2, 3, 4]

# 2025 T4 pode nao estar disponivel ainda — o pipeline ignora 404 automaticamente
TOTAL = len(YEARS) * len(QUARTERS)

def run() -> None:
    logger.info("=" * 70)
    logger.info("INICIO DO DOWNLOAD — Serie PNAD Continua 2016-2025")
    logger.info(f"Alvo: {TOTAL} trimestres | Anos: {YEARS[0]}-{YEARS[-1]}")
    logger.info("=" * 70)

    layout = download_layout()
    logger.info(f"Layout IBGE carregado: {len(layout)} variaveis")

    t_inicio = time.time()
    concluidos = 0
    falhas = []

    for year in YEARS:
        for quarter in QUARTERS:
            tag = f"{year} T{quarter}"
            logger.info(f"[{concluidos+1:02d}/{TOTAL}] Processando {tag}...")
            try:
                ingest_quarter(year, quarter, layout, force_download=False)
                concluidos += 1
            except Exception as exc:
                logger.error(f"FALHA em {tag}: {exc}")
                falhas.append(tag)

            # Progresso estimado
            decorrido = time.time() - t_inicio
            if concluidos > 0:
                media = decorrido / concluidos
                restante = media * (TOTAL - concluidos)
                logger.info(
                    f"Progresso: {concluidos}/{TOTAL} | "
                    f"Decorrido: {decorrido/60:.1f}min | "
                    f"Estimativa restante: {restante/60:.1f}min"
                )

    logger.info("=" * 70)
    logger.info(f"DOWNLOAD CONCLUIDO: {concluidos}/{TOTAL} trimestres processados")
    if falhas:
        logger.warning(f"Falhas ({len(falhas)}): {falhas}")
    logger.info(f"Tempo total: {(time.time() - t_inicio)/60:.1f} minutos")
    logger.info(f"Dados em: data/processed/")
    logger.info("=" * 70)


if __name__ == "__main__":
    run()
