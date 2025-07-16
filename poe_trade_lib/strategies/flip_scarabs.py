# poe_trade_lib/strategies/flip_scarabs.py


from .. import utils
from ..config import settings
from ..models import AnalysisResult
from .base_strategy import BaseStrategy


class ScarabFullGambleStrategy(BaseStrategy):
    """Analyzes the 3-to-1 recipe for ALL scarabs as a single pool (steady income)."""

    @property
    def name(self) -> str:
        return "Scarab Full Gamble"

    def analyze(self, data_cache: dict, league: str) -> list[AnalysisResult]:
        scarab_df = data_cache.get("Scarab")
        if scarab_df is None or scarab_df.empty:
            return []

        cheapest_price = scarab_df["chaosValue"].min()
        avg_return = scarab_df["chaosValue"].mean()
        std_dev = scarab_df["chaosValue"].std()
        cost = 3 * cheapest_price
        profit = avg_return - cost

        if profit <= 0:
            return []

        liquidity = cheapest_price / avg_return if avg_return > 0 else 0
        shopping_list = scarab_df[scarab_df["chaosValue"] < avg_return / 3][
            "name"
        ].tolist()
        num_jackpots = settings.get("analysis.num_jackpots_to_display", 5)
        flips_per_hour = settings.get("analysis.assumed_flips_per_hour", 120)
        jackpots = scarab_df.sort_values(by="chaosValue", ascending=False).head(
            num_jackpots
        )

        result = AnalysisResult(
            strategy_name="Scarab: Full Gamble",
            profit_per_flip=profit,
            input_cost=cheapest_price,
            volatility_std_dev=std_dev,
            risk_profile=utils.get_risk_profile(std_dev),
            profit_per_hour_est=profit * flips_per_hour,
            liquidity_score=liquidity,
            shopping_list=shopping_list,
            trade_url=utils.generate_bulk_trade_url(shopping_list, league),
            details={
                "Jackpots": jackpots[["name", "chaosValue"]].to_dict("records"),
                "Pool Size": len(scarab_df),
                "Recommended Max Buy Price": avg_return / 3,
            },
        )
        return [result]


class ScarabByTypeStrategy(BaseStrategy):
    """Analyzes the 3-to-1 recipe for scarabs by type (high-risk gambles)."""

    @property
    def name(self) -> str:
        return "Scarab Flip by Type"

    def analyze(self, data_cache: dict, league: str) -> list[AnalysisResult]:
        scarab_df = data_cache.get("Scarab")
        if scarab_df is None or scarab_df.empty:
            return []

        df = scarab_df.copy()
        extracted_types = df["name"].str.extract(r"(\w+)\sScarab|Scarab\sof\s(\w+)")
        df["type"] = extracted_types[0].fillna(extracted_types[1])
        df = df.dropna(subset=["type"])

        type_analysis = (
            df.groupby("type")["chaosValue"]
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

        type_analysis["cost"] = 3 * type_analysis["cheapest_price"]
        type_analysis["profit_average_ev"] = (
            type_analysis["average_return_ev"] - type_analysis["cost"]
        )

        profitable_types = type_analysis[
            (type_analysis["profit_average_ev"] > 0) & (type_analysis["pool_size"] > 1)
        ]

        results = []
        tolerance = settings.get("analysis.shopping_list_price_tolerance_chaos", 2.0)
        flips_per_hour = settings.get("analysis.assumed_flips_per_hour", 120)

        for _, row in profitable_types.iterrows():
            scarab_type = row["type"]
            shopping_list = df[
                (df["type"] == scarab_type)
                & (df["chaosValue"] <= row["cheapest_price"] + tolerance)
            ]["name"].tolist()
            liquidity = (
                row["cheapest_price"] / row["average_return_ev"]
                if row["average_return_ev"] > 0
                else 0
            )

            result = AnalysisResult(
                strategy_name=f"Scarab Type: {scarab_type}",
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
