# poe_trade_lib/client.py
import pandas as pd

from . import api, core, utils
from .config import settings


class PoeAnalysisClient:
    """
    A client to fetch market data and run trading strategy analyses.
    This is the primary entry point for using the library.
    """

    def __init__(self, league: str = None):
        self.league = league or settings.get("default_league")
        self.data_cache = None
        self.results = None
        print(f"PoeAnalysisClient initialized for league: '{self.league}'")

    def fetch_data(self):
        """Fetches all necessary market data from the API."""
        self.data_cache = api.fetch_all_data(self.league)

    def run_analysis(self):
        """
        Runs all implemented trading strategies on the fetched data.
        Returns a list of AnalysisResult objects.
        """
        if not self.data_cache:
            print("Data not fetched. Call fetch_data() before running analysis.")
            self.fetch_data()

        self.results = core.run_all_analyses(self.data_cache, self.league)
        return self.results

    def get_summary_dataframe(self) -> pd.DataFrame:
        """
        Returns a formatted pandas DataFrame summarizing the analysis results.
        Returns an empty DataFrame if analysis has not been run.
        """
        if not self.results:
            print("Analysis not run. Call run_analysis() first.")
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
                    r.profit_with_corruption_ev
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
