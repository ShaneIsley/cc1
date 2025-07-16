# poe_trade_lib/api.py
import json
import time
from pathlib import Path

import pandas as pd
import requests

from . import utils
from .config import settings

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_EXPIRATION_SECONDS = 15 * 60


def get_poe_ninja_data(overview_type: str, item_type: str, league: str) -> pd.DataFrame:
    """Fetches and cleans item data, using a local file-based cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{league}_{item_type}.json"

    if cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < CACHE_EXPIRATION_SECONDS:
            with open(cache_file) as f:
                data = json.load(f)
                return pd.DataFrame(data)

    base_url = settings.get("api.base_url")
    url = f"{base_url}{overview_type}?league={league}&type={item_type}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get("lines", [])
        if not data:
            return pd.DataFrame()

        with open(cache_file, "w") as f:
            json.dump(data, f)

        df = pd.DataFrame(data)
        item_blacklist = settings.get("api.item_blacklist", [])
        min_listings = settings.get("api.minimum_listings", 10)

        # Check if 'name' column exists, otherwise use alternative field
        name_field = (
            "name"
            if "name" in df.columns
            else "currencyTypeName"
            if "currencyTypeName" in df.columns
            else None
        )

        if name_field:
            df = df[~df[name_field].isin(item_blacklist)]

        if "count" in df.columns:
            df = df[df["count"] >= min_listings]

        return df
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for '{item_type}' in {league}: {e}")
        return pd.DataFrame()


def fetch_all_data(league: str) -> dict:
    """Fetches all required data types and updates global divine price."""
    print("Fetching all required data from poe.ninja (using cache where possible)...")
    data_cache = {
        "Currency": get_poe_ninja_data("currencyoverview", "Currency", league),
        "Tattoo": get_poe_ninja_data("itemoverview", "Tattoo", league),
        "Scarab": get_poe_ninja_data("itemoverview", "Scarab", league),
        "Essence": get_poe_ninja_data("itemoverview", "Essence", league),
        "Gem": get_poe_ninja_data("itemoverview", "SkillGem", league),
    }
    print("Data acquisition complete.")

    if not data_cache["Currency"].empty:
        try:
            div_price = data_cache["Currency"][
                data_cache["Currency"]["currencyTypeName"] == "Divine Orb"
            ]["chaosEquivalent"].iloc[0]
            utils.DIVINE_TO_CHAOS = div_price
            print(
                f"Live rates updated: 1 Divine Orb = {utils.DIVINE_TO_CHAOS:.0f} Chaos\n"
            )
        except (IndexError, TypeError):
            print("Warning: Could not update Divine Orb price. Using default.\n")

    return data_cache
