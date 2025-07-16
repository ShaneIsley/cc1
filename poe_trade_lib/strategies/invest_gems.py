# poe_trade_lib/strategies/invest_gems.py

import pandas as pd

from .. import utils
from ..config import settings
from ..logging_config import ensure_logging_initialized, get_logger
from ..models import AnalysisResult
from .base_strategy import BaseStrategy

# Initialize logging
ensure_logging_initialized()
logger = get_logger(__name__)


class GemLevelingStrategy(BaseStrategy):
    """Analyzes the long-term investment of buying, leveling, and corrupting skill gems."""

    @property
    def name(self) -> str:
        return "Gem Leveling & Corruption"

    def analyze(self, data_cache: dict, league: str) -> list[AnalysisResult]:
        gem_df = data_cache.get("Gem")
        currency_df = data_cache.get("Currency")
        gem_probs = settings.get("strategies.gem_corruption.probabilities", {})

        if any(df is None or df.empty for df in [gem_df, currency_df]) or not gem_probs:
            return []

        try:
            vaal_price = currency_df[currency_df["currencyTypeName"] == "Vaal Orb"][
                "chaosEquivalent"
            ].iloc[0]
        except (IndexError, KeyError):
            logger.warning("Could not find Vaal Orb price. Skipping Gem strategy.")
            return []

        gems_l1_q0 = gem_df[
            (gem_df["gemLevel"] == 1)
            & (gem_df.get("gemQuality", 0) == 0)
            & (gem_df.get("corrupted", False) != True)  # noqa: E712
        ]
        gems_l20_q0 = gem_df[
            (gem_df["gemLevel"] == 20)
            & (gem_df.get("gemQuality", 0) == 0)
            & (gem_df.get("corrupted", False) != True)  # noqa: E712
        ]
        gems_l19_q20 = gem_df[
            (gem_df["gemLevel"] == 19)
            & (gem_df.get("gemQuality", 20) == 20)
            & (gem_df.get("corrupted", True))
        ]
        gems_l21_q20 = gem_df[
            (gem_df["gemLevel"] == 21)
            & (gem_df.get("gemQuality", 20) == 20)
            & (gem_df.get("corrupted", True))
        ]
        gems_l20_q23 = gem_df[
            (gem_df["gemLevel"] == 20)
            & (gem_df.get("gemQuality", 23) == 23)
            & (gem_df.get("corrupted", True))
        ]

        if gems_l1_q0.empty or gems_l20_q0.empty:
            return []

        base_df = pd.merge(
            gems_l1_q0[["name", "chaosValue"]],
            gems_l20_q0[["name", "chaosValue"]],
            on="name",
            suffixes=("_buy", "_sell_l20"),
        )

        for df, suffix in [
            (gems_l19_q20, "_l19"),
            (gems_l21_q20, "_l21"),
            (gems_l20_q23, "_q23"),
        ]:
            if not df.empty:
                base_df = pd.merge(
                    base_df,
                    df[["name", "chaosValue"]],
                    on="name",
                    how="left",
                    suffixes=("", suffix),
                )

        for col in [
            c for c in base_df.columns if "_l19" in c or "_l21" in c or "_q23" in c
        ]:
            base_df[col] = base_df[col].fillna(0)

        base_df["profit_level_only"] = (
            base_df["chaosValue_sell_l20"] - base_df["chaosValue_buy"]
        )

        prob_plus_lvl = gem_probs.get("level_change", 0) / 2
        prob_minus_lvl = gem_probs.get("level_change", 0) / 2
        prob_qual = gem_probs.get("quality_change", 0)

        ev_lvl_plus = prob_plus_lvl * (
            base_df.get("chaosValue_l21", 0) - base_df["chaosValue_sell_l20"]
        )
        ev_lvl_minus = prob_minus_lvl * (
            base_df.get("chaosValue_l19", 0) - base_df["chaosValue_sell_l20"]
        )
        ev_qual = prob_qual * (
            base_df.get("chaosValue_q23", 0) - base_df["chaosValue_sell_l20"]
        )

        base_df["corruption_ev"] = ev_lvl_plus + ev_lvl_minus + ev_qual - vaal_price
        base_df["profit_with_corruption_ev"] = (
            base_df["profit_level_only"] + base_df["corruption_ev"]
        )

        profitable_gems = base_df[
            base_df["profit_with_corruption_ev"] > 10
        ].sort_values("profit_with_corruption_ev", ascending=False)

        results = []
        for _, row in profitable_gems.head(15).iterrows():
            result = AnalysisResult(
                strategy_name=f"Gem Invest: {row['name']}",
                profit_per_flip=row["profit_level_only"],
                input_cost=row["chaosValue_buy"],
                volatility_std_dev=0,
                risk_profile="Investment",
                profit_per_hour_est=0,
                liquidity_score=None,  # Not applicable for this type of long-term investment
                shopping_list=[row["name"]],
                trade_url=utils.generate_bulk_trade_url([row["name"]], league),
                details={
                    "Profit (Level Only)": row["profit_level_only"],
                    "Corruption EV": row["corruption_ev"],
                    "Sell Price (L20)": row["chaosValue_sell_l20"],
                    "Sell Price (L21)": row.get("chaosValue_l21", 0),
                    "Sell Price (L19)": row.get("chaosValue_l19", 0),
                    "Sell Price (Q23)": row.get("chaosValue_q23", 0),
                },
                long_term=True,
                profit_with_corruption_ev=row["profit_with_corruption_ev"],
            )
            results.append(result)
        return results
