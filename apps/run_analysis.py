# apps/run_analysis.py
from __future__ import annotations

import pandas as pd

from poe_trade_lib import db_utils, utils
from poe_trade_lib.client import PoeAnalysisClient
from poe_trade_lib.logging_config import ensure_logging_initialized, get_logger

# Initialize logging
ensure_logging_initialized()
logger = get_logger(__name__)


def main() -> None:
    """
    A command-line application demonstrating the use of the PoeAnalysisClient
    and displaying historical trends for the top strategy.
    """
    client = PoeAnalysisClient()
    client.fetch_data()
    analysis_results = client.run_analysis()
    if not analysis_results:
        logger.warning("No profitable strategies found.")
        print("No profitable strategies found.")
        return

    summary_df = client.get_summary_dataframe()

    print("\n" + "=" * 120)
    print("MASTER STRATEGY DASHBOARD")
    print("=" * 120)
    print(summary_df.to_string(index=False))
    print("=" * 120 + "\n")

    top_result = analysis_results[0]
    print("\n--- Top Strategy Breakdown ---")
    print(f"Strategy: {top_result.strategy_name}")
    print(f"Trade URL: {top_result.trade_url}")
    print("Details:")
    for key, value in top_result.details.items():
        if isinstance(value, int | float):
            print(f"  - {key}: {utils.format_currency(value)}")
        else:
            print(f"  - {key}: {value}")

    print("\n" + "=" * 120)
    print(f"HISTORICAL TREND: {top_result.strategy_name}")
    print("=" * 120)

    historical_df = db_utils.get_historical_data(
        top_result.strategy_name, client.league
    )

    if historical_df.empty:
        print(
            "No historical data found for this strategy. Run 'apps/log_results.py' to start collecting data."
        )
    else:
        profit_col = (
            "profit_with_corruption_ev"
            if top_result.long_term
            else "profit_per_hour_est"
        )
        history_view = historical_df[
            ["timestamp", profit_col, "risk_profile", "liquidity_score"]
        ].copy()
        history_view.rename(columns={profit_col: "Profit"}, inplace=True)
        history_view["Profit"] = history_view["Profit"].apply(utils.format_currency)
        history_view["liquidity_score"] = history_view["liquidity_score"].apply(
            lambda x: f"{x:.0%}" if pd.notnull(x) else "N/A"
        )
        print(history_view.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
