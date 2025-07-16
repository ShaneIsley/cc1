# poe_trade_lib/utils.py
import json
from urllib.parse import quote

import numpy as np

from .config import settings

DIVINE_TO_CHAOS = 200


def format_currency(chaos_value: float) -> str:
    """Formats a chaos value into a readable string."""
    if not isinstance(chaos_value, int | float | np.number) or np.isnan(chaos_value):
        return "N/A"
    if abs(chaos_value) >= DIVINE_TO_CHAOS:
        return f"{chaos_value / DIVINE_TO_CHAOS:.2f} div"
    return f"{chaos_value:.1f}c"


def generate_bulk_trade_url(
    item_names_list: list, league: str, currency_to_have: str = "chaos"
) -> str:
    """Generates a clickable PoE trade URL for bulk item exchange."""
    trade_url_base = settings.get("api.trade_url_base")
    if not item_names_list:
        return "N/A"
    query = {
        "exchange": {
            "status": {"option": "online"},
            "have": [currency_to_have],
            "want": item_names_list,
        }
    }
    encoded_query = quote(json.dumps(query))
    return f"{trade_url_base}{league}?q={encoded_query}"


def get_risk_profile(std_dev: float) -> str:
    """Assigns a risk profile string based on profit volatility."""
    risk_thresholds = settings.get("analysis.profit_volatility_risk_thresholds", {})
    if np.isnan(std_dev) or std_dev == 0:
        return "None"
    for profile, threshold in sorted(risk_thresholds.items(), key=lambda item: item[1]):
        if std_dev <= threshold:
            return profile
    return "Extreme"
