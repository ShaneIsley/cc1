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
    """
    FIXME: This strategy needs to be corrected to properly implement the traditional
    3x level 1 gems → vendor recipe → level 20 quality 20 gem approach.

    Current implementation uses L1Q20 → L20Q20 which doesn't match the actual
    gem leveling strategy that requires 3 level 1 gems to vendor for quality.

    Analyzes the long-term investment of buying, leveling, and corrupting skill gems.
    """

    @property
    def name(self) -> str:
        return "Gem Leveling & Corruption"

    def analyze(self, data_cache: dict, league: str) -> list[AnalysisResult]:
        gem_df = data_cache.get("Gem")
        currency_df = data_cache.get("Currency")

        # Type narrowing: ensure we have the expected DataFrames
        if not isinstance(gem_df, pd.DataFrame) or not isinstance(
            currency_df, pd.DataFrame
        ):
            return []
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

        # FIXME: This is a workaround because poe.ninja doesn't track low-quality gems
        # The proper strategy should be:
        # 1. Buy 3x level 1, quality 0 gems (cheapest)
        # 2. Level all 3 to level 20
        # 3. Vendor recipe: 3x level 20 → 1x level 1 with +1 quality
        # 4. Repeat until 20% quality, then level to 20 and corrupt
        #
        # Current workaround: Buy level 1, quality 20 gems (already with quality from market)
        # Level to 20, then corrupt for 21/20 or 20/23 outcomes
        gems_l1_q20 = gem_df[
            (gem_df["gemLevel"] == 1)
            & (gem_df.get("gemQuality", 20) == 20)
            & (gem_df.get("corrupted", False) != True)  # noqa: E712
        ]
        gems_l20_q20_base = gem_df[
            (gem_df["gemLevel"] == 20)
            & (gem_df.get("gemQuality", 20) == 20)
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

        if gems_l1_q20.empty or gems_l20_q20_base.empty:
            logger.info(
                "No suitable gems found for leveling strategy (empty L1Q20 or L20Q20 base dataset)"
            )
            return []

        base_df = pd.merge(
            gems_l1_q20[["name", "chaosValue"]],
            gems_l20_q20_base[["name", "chaosValue"]],
            on="name",
            suffixes=("_buy_l1", "_sell_l20_base"),
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

        # Calculate profit from leveling: L1Q20 → L20Q20
        base_df["profit_level_only"] = (
            base_df["chaosValue_sell_l20_base"] - base_df["chaosValue_buy_l1"]
        )

        prob_plus_lvl = gem_probs.get("level_change", 0) / 2
        prob_minus_lvl = gem_probs.get("level_change", 0) / 2
        prob_qual = gem_probs.get("quality_change", 0)

        ev_lvl_plus = prob_plus_lvl * (
            base_df.get("chaosValue_l21", 0) - base_df["chaosValue_sell_l20_base"]
        )
        ev_lvl_minus = prob_minus_lvl * (
            base_df.get("chaosValue_l19", 0) - base_df["chaosValue_sell_l20_base"]
        )
        ev_qual = prob_qual * (
            base_df.get("chaosValue_q23", 0) - base_df["chaosValue_sell_l20_base"]
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
                input_cost=row[
                    "chaosValue_buy_l1"
                ],  # Cost of 1x level 1 quality 20 gem
                volatility_std_dev=0,
                risk_profile="Investment",
                profit_per_hour_est=0,
                liquidity_score=None,  # Not applicable for this type of long-term investment
                shopping_list=[f"{row['name']} (Level 1, 20% Quality)"],
                trade_url=utils.generate_bulk_trade_url([row["name"]], league),
                details={
                    "Buy Price (L1Q20)": row["chaosValue_buy_l1"],
                    "Profit (Level Only)": row["profit_level_only"],
                    "Corruption EV": row["corruption_ev"],
                    "Sell Price (L20Q20)": row["chaosValue_sell_l20_base"],
                    "Sell Price (L21Q20)": row.get("chaosValue_l21", 0),
                    "Sell Price (L19Q20)": row.get("chaosValue_l19", 0),
                    "Sell Price (L20Q23)": row.get("chaosValue_q23", 0),
                },
                long_term=True,
                profit_with_corruption_ev=row["profit_with_corruption_ev"],
            )
            results.append(result)
        return results
