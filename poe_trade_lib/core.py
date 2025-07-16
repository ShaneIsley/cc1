# poe_trade_lib/core.py
import inspect

from . import strategies
from .strategies.base_strategy import BaseStrategy


def run_all_analyses(data_cache: dict, league: str):
    """
    Dynamically discovers and runs all implemented strategies.

    Returns a sorted list of all profitable AnalysisResult objects.
    """
    all_results = []

    for name, obj in inspect.getmembers(strategies):
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseStrategy)
            and obj is not BaseStrategy
        ):
            try:
                strategy_instance = obj()
                print(f"--- Running Strategy: {strategy_instance.name} ---")
                results = strategy_instance.analyze(data_cache, league)
                if results:
                    all_results.extend(results)
            except Exception as e:
                print(f"ERROR: Could not run strategy '{name}'. Reason: {e}")

    all_results.sort(
        key=lambda r: r.profit_per_hour_est
        if not r.long_term
        else r.profit_with_corruption_ev or r.profit_per_flip,
        reverse=True,
    )
    return all_results
