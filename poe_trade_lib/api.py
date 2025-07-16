# poe_trade_lib/api.py
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

from . import utils
from .config import settings
from .logging_config import (
    ensure_logging_initialized,
    get_logger,
    log_api_request,
    log_data_acquisition,
)

# Initialize logging
ensure_logging_initialized()
logger = get_logger(__name__)

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
                df = pd.DataFrame(data)
                log_data_acquisition(item_type, len(df), cache_hit=True)
                return df

    base_url = settings.get("api.base_url")
    url = f"{base_url}{overview_type}?league={league}&type={item_type}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json().get("lines", [])

        log_api_request(url, response.status_code)

        if not data:
            logger.warning(f"No data returned for {item_type} in {league}")
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
            blacklisted_count = len(df[df[name_field].isin(item_blacklist)])
            df = df[~df[name_field].isin(item_blacklist)]
            if blacklisted_count > 0:
                logger.debug(
                    f"Filtered out {blacklisted_count} blacklisted items for {item_type}"
                )

        if "count" in df.columns:
            low_liquidity_count = len(df[df["count"] < min_listings])
            df = df[df["count"] >= min_listings]
            if low_liquidity_count > 0:
                logger.debug(
                    f"Filtered out {low_liquidity_count} low-liquidity items for {item_type}"
                )

        log_data_acquisition(item_type, len(df), cache_hit=False)
        return df
    except requests.exceptions.RequestException as e:
        log_api_request(url, error=str(e))
        return pd.DataFrame()


def fetch_all_data(league: str) -> dict[str, pd.DataFrame]:
    """Fetches all required data types and updates global divine price."""
    logger.info(f"Starting data acquisition for league: {league}")

    data_cache = {
        "Currency": get_poe_ninja_data("currencyoverview", "Currency", league),
        "Tattoo": get_poe_ninja_data("itemoverview", "Tattoo", league),
        "Scarab": get_poe_ninja_data("itemoverview", "Scarab", league),
        "Essence": get_poe_ninja_data("itemoverview", "Essence", league),
        "Gem": get_poe_ninja_data("itemoverview", "SkillGem", league),
    }

    total_records = sum(len(df) for df in data_cache.values())
    logger.info(f"Data acquisition complete - {total_records} total records retrieved")

    if not data_cache["Currency"].empty:
        try:
            div_price = data_cache["Currency"][
                data_cache["Currency"]["currencyTypeName"] == "Divine Orb"
            ]["chaosEquivalent"].iloc[0]
            utils.DIVINE_TO_CHAOS = div_price
            logger.info(
                f"Live rates updated: 1 Divine Orb = {utils.DIVINE_TO_CHAOS:.0f} Chaos"
            )
        except (IndexError, TypeError):
            logger.warning("Could not update Divine Orb price. Using default value.")

    return data_cache
