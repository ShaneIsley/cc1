# poe_trade_lib/client.py
from __future__ import annotations

from typing import Any

import pandas as pd

from . import api, core, utils
from .config import settings
from .logging_config import ensure_logging_initialized, get_logger
from .models import AnalysisResult

# Initialize logging
ensure_logging_initialized()
logger = get_logger(__name__)


class PoeAnalysisClient:
    """
    A client to fetch market data and run trading strategy analyses.
    This is the primary entry point for using the library.
    """

    def __init__(self, league: str | None = None) -> None:
        self.league = league or settings.get("default_league", "Standard")
        self.data_cache: dict[str, Any] | None = None
        self.results: list[AnalysisResult] | None = None
        logger.info(f"PoeAnalysisClient initialized for league: '{self.league}'")

    def fetch_data(self) -> None:
        """Fetches all necessary market data from the API."""
        self.data_cache = api.fetch_all_data(self.league)

    def run_analysis(self) -> list[AnalysisResult]:
        """
        Runs all implemented trading strategies on the fetched data.
        Returns a list of AnalysisResult objects.
        """
        if not self.data_cache:
            logger.info("Data not cached. Fetching data before running analysis.")
            self.fetch_data()

        assert (
            self.data_cache is not None
        )  # After fetch_data(), data_cache should not be None
        self.results = core.run_all_analyses(self.data_cache, self.league)
        logger.info(
            f"Analysis complete - {len(self.results)} profitable strategies found"
        )
        return self.results

    def get_summary_dataframe(self) -> pd.DataFrame:
        """
        Returns a formatted pandas DataFrame summarizing the analysis results.
        Returns an empty DataFrame if analysis has not been run.
        """
        if not self.results:
            logger.warning("Analysis not run. Call run_analysis() first.")
            return pd.DataFrame()

        results_dict_list = []
        for r in self.results:
            res_dict = {
                "Strategy": r.strategy_name,
                "Liquidity": f"{r.liquidity_score:.0%}"
                if r.liquidity_score is not None
                else "N/A",
                "Input Cost": utils.format_currency(r.input_cost),
                "Risk Profile": r.risk_profile,
            }
            if r.long_term:
                res_dict["Profit (Level)"] = utils.format_currency(r.profit_per_flip)
                res_dict["Profit w/ EV"] = utils.format_currency(
                    r.profit_with_corruption_ev or 0
                )
            else:
                res_dict["Profit/Flip"] = utils.format_currency(r.profit_per_flip)
                res_dict["Profit/Hour (Est.)"] = utils.format_currency(
                    r.profit_per_hour_est
                )
            results_dict_list.append(res_dict)

        summary_df = pd.DataFrame(results_dict_list)
        sort_key = (
            "Profit/Hour (Est.)"
            if "Profit/Hour (Est.)" in summary_df.columns
            else "Profit w/ EV"
        )
        summary_df = summary_df.sort_values(by=sort_key, ascending=False).fillna("")
        return summary_df
