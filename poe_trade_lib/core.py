# poe_trade_lib/core.py
from __future__ import annotations

import inspect
from typing import Any

from . import strategies
from .logging_config import (
    ensure_logging_initialized,
    get_logger,
    log_strategy_execution,
)
from .models import AnalysisResult
from .strategies.base_strategy import BaseStrategy

# Initialize logging
ensure_logging_initialized()
logger = get_logger(__name__)


def run_all_analyses(data_cache: dict[str, Any], league: str) -> list[AnalysisResult]:
    """
    Dynamically discovers and runs all implemented strategies.

    Returns a sorted list of all profitable AnalysisResult objects.
    """
    all_results = []

    for _name, obj in inspect.getmembers(strategies):
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseStrategy)
            and obj is not BaseStrategy
        ):
            try:
                strategy_instance = obj()
                logger.info(f"Running strategy: {strategy_instance.name}")
                results = strategy_instance.analyze(data_cache, league)
                if results:
                    all_results.extend(results)
                    log_strategy_execution(strategy_instance.name, len(results))
                else:
                    logger.debug(
                        f"Strategy '{strategy_instance.name}' found no profitable opportunities"
                    )
            except Exception as e:
                log_strategy_execution(strategy_instance.name, 0, error=str(e))

    all_results.sort(
        key=lambda r: r.profit_per_hour_est
        if not r.long_term
        else r.profit_with_corruption_ev or r.profit_per_flip,
        reverse=True,
    )
    return all_results
