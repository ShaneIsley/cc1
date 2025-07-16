# poe_trade_lib/models.py
from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """A standardized object for holding the result of a single trading strategy analysis."""

    strategy_name: str
    profit_per_flip: float
    input_cost: float
    volatility_std_dev: float
    risk_profile: str
    profit_per_hour_est: float
    liquidity_score: float | None = None
    shopping_list: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    long_term: bool = False
    trade_url: str | None = None
    profit_with_corruption_ev: float | None = None
