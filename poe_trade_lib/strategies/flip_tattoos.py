# poe_trade_lib/strategies/flip_tattoos.py


from .. import utils
from ..config import settings
from ..models import AnalysisResult
from .base_strategy import BaseStrategy


class TattooFlipStrategy(BaseStrategy):
    """Analyzes the 3-to-1 vendor recipe for Tattoos by tribe."""

    @property
    def name(self) -> str:
        return "Tattoo Flip"

    def analyze(self, data_cache: dict, league: str) -> list[AnalysisResult]:
        tattoo_df = data_cache.get("Tattoo")
        if tattoo_df is None or tattoo_df.empty:
            return []

        df = tattoo_df[~tattoo_df["name"].str.contains("Journey", na=False)].copy()
        if not df["name"].str.contains(" of the ", na=False).any():
            return []

        df["tribe"] = df["name"].apply(lambda x: x.split(" of the ")[1].split(" ")[0])

        tribe_analysis = (
            df.groupby("tribe")["chaosValue"]
            .agg(
                cheapest_price="min",
                average_return_ev="mean",
                jackpot="max",
                pool_size="count",
                profit_volatility_std_dev="std",
            )
            .reset_index()
            .fillna({"profit_volatility_std_dev": 0})
        )

        tribe_analysis["cost"] = 3 * tribe_analysis["cheapest_price"]
        tribe_analysis["profit_average_ev"] = (
            tribe_analysis["average_return_ev"] - tribe_analysis["cost"]
        )

        profitable_tribes = tribe_analysis[tribe_analysis["profit_average_ev"] > 0]

        results = []
        tolerance = settings.get("analysis.shopping_list_price_tolerance_chaos", 2.0)
        flips_per_hour = settings.get("analysis.assumed_flips_per_hour", 120)

        for _, row in profitable_tribes.iterrows():
            tribe = row["tribe"]
            shopping_list = df[
                (df["tribe"] == tribe)
                & (df["chaosValue"] <= row["cheapest_price"] + tolerance)
            ]["name"].tolist()
            liquidity = (
                row["cheapest_price"] / row["average_return_ev"]
                if row["average_return_ev"] > 0
                else 0
            )

            result = AnalysisResult(
                strategy_name=f"Tattoo: {tribe}",
                profit_per_flip=row["profit_average_ev"],
                input_cost=row["cheapest_price"],
                volatility_std_dev=row["profit_volatility_std_dev"],
                risk_profile=utils.get_risk_profile(row["profit_volatility_std_dev"]),
                profit_per_hour_est=row["profit_average_ev"] * flips_per_hour,
                liquidity_score=liquidity,
                shopping_list=shopping_list,
                trade_url=utils.generate_bulk_trade_url(shopping_list, league),
                details={
                    "Jackpot": row["jackpot"],
                    "Pool Size": row["pool_size"],
                    "Cost per Flip": row["cost"],
                },
            )
            results.append(result)

        return results
