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
    Implements the proper Path of Exile gem vendor recipe strategy:

    1. Buy 3x Level 1, Quality 0 gems (cheapest input)
    2. Level all 3 gems to Level 20, Quality 0
    3. Vendor recipe: 3x L20Q0 → 1x L1Q20 (quality upgrade)
    4. Level the L1Q20 gem to L20Q20 (final product)
    5. Optionally corrupt L20Q20 for 21/20 or 20/23 outcomes

    This strategy leverages the vendor recipe system to efficiently obtain
    high-quality gems for corruption or direct sale.
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

        # Find gems with complete vendor recipe chain
        profitable_gems = self._find_vendor_recipe_opportunities(
            gem_df, vaal_price, gem_probs
        )

        if profitable_gems.empty:
            logger.info("No profitable vendor recipe opportunities found")
            return []

        results = []
        for _, row in profitable_gems.head(15).iterrows():
            result = AnalysisResult(
                strategy_name=f"Gem Recipe: {row['name']}",
                profit_per_flip=row["vendor_recipe_profit"],
                input_cost=row["total_input_cost"],
                volatility_std_dev=0,
                risk_profile="Investment",
                profit_per_hour_est=0,
                liquidity_score=None,  # Not applicable for this type of long-term investment
                shopping_list=[f"3x {row['name']} (Level 1, 0% Quality)"],
                trade_url=utils.generate_bulk_trade_url([row["name"]], league),
                details={
                    "Input Cost (3x L1Q0)": row["total_input_cost"],
                    "Vendor Recipe Profit": row["vendor_recipe_profit"],
                    "Corruption EV": row["corruption_ev"],
                    "Total Profit": row["total_profit"],
                    "L1Q0 Price": row["l1q0_price"],
                    "L20Q20 Price": row["l20q20_price"],
                    "L21Q20 Price": row.get("l21q20_price", 0),
                    "L20Q23 Price": row.get("l20q23_price", 0),
                },
                long_term=True,
                profit_with_corruption_ev=row["total_profit"],
            )
            results.append(result)
        return results

    def _find_vendor_recipe_opportunities(
        self, gem_df: pd.DataFrame, vaal_price: float, gem_probs: dict
    ) -> pd.DataFrame:
        """Find gems with complete vendor recipe chain and calculate profitability."""

        # Filter out awakened gems (they don't follow normal vendor recipe)
        regular_gems = gem_df[~gem_df["name"].str.contains("Awakened", na=False)]

        # Get gem variants by level/quality
        l1_q0_gems = regular_gems[
            (regular_gems["gemLevel"] == 1)
            & (regular_gems["gemQuality"].isna())
            & ~regular_gems.get("corrupted", False)
        ]

        l20_q20_gems = regular_gems[
            (regular_gems["gemLevel"] == 20)
            & (regular_gems["gemQuality"] == 20)
            & ~regular_gems.get("corrupted", False)
        ]

        # Find gems that have both L1Q0 and L20Q20 variants
        l1_q0_names = set(l1_q0_gems["name"].unique())
        l20_q20_names = set(l20_q20_gems["name"].unique())
        viable_gems = l1_q0_names.intersection(l20_q20_names)

        if not viable_gems:
            return pd.DataFrame()

        # Calculate vendor recipe profitability
        results = []
        for gem_name in viable_gems:
            gem_data = self._calculate_gem_recipe_profit(
                gem_name, regular_gems, vaal_price, gem_probs
            )
            if gem_data and gem_data["total_profit"] > 10:  # Minimum profit threshold
                results.append(gem_data)

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results).sort_values("total_profit", ascending=False)

    def _calculate_gem_recipe_profit(
        self, gem_name: str, gem_df: pd.DataFrame, vaal_price: float, gem_probs: dict
    ) -> dict | None:
        """Calculate profit for a specific gem using vendor recipe strategy."""

        # Get gem variants
        gem_variants = gem_df[gem_df["name"] == gem_name]

        # L1Q0 gems (starting input)
        l1_q0 = gem_variants[
            (gem_variants["gemLevel"] == 1)
            & (gem_variants["gemQuality"].isna())
            & ~gem_variants.get("corrupted", False)
        ]

        # L20Q20 gems (final product)
        l20_q20 = gem_variants[
            (gem_variants["gemLevel"] == 20)
            & (gem_variants["gemQuality"] == 20)
            & ~gem_variants.get("corrupted", False)
        ]

        # Corrupted variants for EV calculation
        l21_q20 = gem_variants[
            (gem_variants["gemLevel"] == 21)
            & (gem_variants["gemQuality"] == 20)
            & (gem_variants.get("corrupted", True))
        ]

        l20_q23 = gem_variants[
            (gem_variants["gemLevel"] == 20)
            & (gem_variants["gemQuality"] == 23)
            & (gem_variants.get("corrupted", True))
        ]

        l19_q20 = gem_variants[
            (gem_variants["gemLevel"] == 19)
            & (gem_variants["gemQuality"] == 20)
            & (gem_variants.get("corrupted", True))
        ]

        # Check if we have the required variants
        if l1_q0.empty or l20_q20.empty:
            return None

        # Extract prices
        l1_q0_price = l1_q0.iloc[0]["chaosValue"]
        l20_q20_price = l20_q20.iloc[0]["chaosValue"]

        # Calculate vendor recipe profit
        total_input_cost = l1_q0_price * 3  # Need 3x L1Q0 gems
        vendor_recipe_profit = l20_q20_price - total_input_cost

        # Calculate corruption expected value
        corruption_ev = self._calculate_corruption_ev(
            l20_q20_price, l21_q20, l20_q23, l19_q20, vaal_price, gem_probs
        )

        total_profit = vendor_recipe_profit + corruption_ev

        return {
            "name": gem_name,
            "l1q0_price": l1_q0_price,
            "l20q20_price": l20_q20_price,
            "l21q20_price": l21_q20.iloc[0]["chaosValue"] if not l21_q20.empty else 0,
            "l20q23_price": l20_q23.iloc[0]["chaosValue"] if not l20_q23.empty else 0,
            "total_input_cost": total_input_cost,
            "vendor_recipe_profit": vendor_recipe_profit,
            "corruption_ev": corruption_ev,
            "total_profit": total_profit,
        }

    def _calculate_corruption_ev(
        self,
        base_price: float,
        l21_q20: pd.DataFrame,
        l20_q23: pd.DataFrame,
        l19_q20: pd.DataFrame,
        vaal_price: float,
        gem_probs: dict,
    ) -> float:
        """Calculate expected value from corrupting a L20Q20 gem."""

        # Corruption probabilities
        prob_plus_lvl = gem_probs.get("level_change", 0) / 2  # +1 level
        prob_minus_lvl = gem_probs.get("level_change", 0) / 2  # -1 level
        prob_qual = gem_probs.get("quality_change", 0)  # +3 quality
        prob_no_change = gem_probs.get("no_change", 0)  # No change

        # Expected value calculation
        ev_gain: float = 0

        # L21Q20 outcome
        if not l21_q20.empty:
            l21_price = l21_q20.iloc[0]["chaosValue"]
            ev_gain += prob_plus_lvl * (l21_price - base_price)

        # L20Q23 outcome
        if not l20_q23.empty:
            l20_q23_price = l20_q23.iloc[0]["chaosValue"]
            ev_gain += prob_qual * (l20_q23_price - base_price)

        # L19Q20 outcome (loss)
        if not l19_q20.empty:
            l19_price = l19_q20.iloc[0]["chaosValue"]
            ev_gain += prob_minus_lvl * (l19_price - base_price)

        # No change outcome (no gain/loss on gem value)
        ev_gain += prob_no_change * 0

        # Subtract vaal orb cost
        corruption_ev = ev_gain - vaal_price

        return corruption_ev
