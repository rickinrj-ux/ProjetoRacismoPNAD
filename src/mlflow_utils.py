"""
mlflow_utils.py
===============
Utilitários de rastreamento MLflow para os módulos de análise do TCC.

MLflow é opcional: se não estiver instalado, todas as funções são no-ops e
os módulos continuam funcionando normalmente sem nenhuma alteração de comportamento.

Instalação:
    pip install mlflow

Visualização local:
    mlflow ui --port 5000
    Acesse: http://localhost:5000

Experimentos:
    HLM_Gap_Racial    — modelos M0→M3 (multilevel_model.py)
    Analise_Regional  — HLM e quantílica por macrorregião (analise_regional.py)
    Validacao_RAIS    — comparação PNAD × RAIS (validacao_rais.py)
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.statsmodels
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False
    logger.debug("MLflow não instalado — rastreamento desativado. "
                 "Para ativar: pip install mlflow")

ROOT = Path(__file__).parent.parent


# ── Setup de experimento ───────────────────────────────────────────────────────

def setup_experiment(nome: str) -> Optional[str]:
    """Cria ou recupera experimento MLflow. Retorna experiment_id ou None."""
    if not MLFLOW_AVAILABLE:
        return None
    db_path = ROOT / "mlflow.db"
    mlflow.set_tracking_uri(f"sqlite:///{db_path.as_posix()}")
    exp = mlflow.set_experiment(nome)
    return exp.experiment_id


# ── Context manager de run ─────────────────────────────────────────────────────

@contextmanager
def run_context(run_name: str, experiment: str,
                tags: Optional[Dict[str, str]] = None,
                nested: bool = False):
    """
    Context manager que cria um MLflow run e garante encerramento correto.
    É no-op se MLflow não estiver disponível.

    Uso:
        with run_context("M3_Completo", "HLM_Gap_Racial") as run:
            log_params({"method": "lbfgs"})
    """
    if not MLFLOW_AVAILABLE:
        yield None
        return

    setup_experiment(experiment)
    with mlflow.start_run(run_name=run_name, nested=nested,
                          tags=tags or {}) as run:
        yield run


# ── Funções de log ─────────────────────────────────────────────────────────────

def log_params(params: Dict[str, Any]) -> None:
    """Log de hiperparâmetros — no-op se MLflow indisponível ou fora de run."""
    if not MLFLOW_AVAILABLE:
        return
    try:
        mlflow.log_params({k: v for k, v in params.items() if v is not None})
    except Exception as exc:
        logger.debug(f"mlflow.log_params falhou: {exc}")


def log_metrics(metrics: Dict[str, float]) -> None:
    """Log de métricas numéricas — no-op se MLflow indisponível ou fora de run."""
    if not MLFLOW_AVAILABLE:
        return
    try:
        clean = {k: float(v) for k, v in metrics.items()
                 if v is not None and str(v) not in ("nan", "inf", "-inf")}
        if clean:
            mlflow.log_metrics(clean)
    except Exception as exc:
        logger.debug(f"mlflow.log_metrics falhou: {exc}")


def log_artifact(path: str | Path) -> None:
    """Log de arquivo como artefato — no-op se MLflow indisponível ou fora de run."""
    if not MLFLOW_AVAILABLE:
        return
    try:
        mlflow.log_artifact(str(path))
    except Exception as exc:
        logger.debug(f"mlflow.log_artifact falhou: {exc}")


def log_artifacts_dir(directory: str | Path, subfolder: str = "") -> None:
    """Log de todos os arquivos de um diretório."""
    if not MLFLOW_AVAILABLE:
        return
    try:
        mlflow.log_artifacts(str(directory), artifact_path=subfolder or None)
    except Exception as exc:
        logger.debug(f"mlflow.log_artifacts falhou: {exc}")


def set_tag(key: str, value: str) -> None:
    """Define tag na run atual — no-op se MLflow indisponível."""
    if not MLFLOW_AVAILABLE:
        return
    try:
        mlflow.set_tag(key, value)
    except Exception as exc:
        logger.debug(f"mlflow.set_tag falhou: {exc}")


# ── Helpers de log para HLM ───────────────────────────────────────────────────

def log_hlm_result(result_obj, prefix: str = "") -> None:
    """
    Extrai e loga coeficientes-chave de um MixedLMResults do statsmodels.

    Loga beta_negro, se_negro, pval_negro e gap_pct com prefixo opcional,
    o que permite comparar coeficientes entre modelos na UI do MLflow.
    """
    if not MLFLOW_AVAILABLE:
        return
    import numpy as np
    try:
        b  = result_obj.params.get("negro", float("nan"))
        se = result_obj.bse.get("negro", float("nan"))
        pv = result_obj.pvalues.get("negro", float("nan"))
        p  = f"{prefix}_" if prefix else ""
        log_metrics({
            f"{p}beta_negro": b,
            f"{p}se_negro":   se,
            f"{p}pval_negro": pv,
            f"{p}gap_pct":    (np.exp(b) - 1) * 100 if not np.isnan(b) else float("nan"),
        })
    except Exception as exc:
        logger.debug(f"log_hlm_result falhou: {exc}")
