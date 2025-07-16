# poe_trade_lib/db_utils.py
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pandas as pd

from .logging_config import (
    ensure_logging_initialized,
    get_logger,
    log_database_operation,
)
from .models import AnalysisResult

# Initialize logging
ensure_logging_initialized()
logger = get_logger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "historical_trades.db"


def initialize_database() -> None:
    """Creates the database and the results table if they don't exist."""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_results (
        timestamp INTEGER NOT NULL,
        league TEXT NOT NULL,
        strategy_name TEXT NOT NULL,
        profit_per_flip REAL,
        profit_per_hour_est REAL,
        profit_with_corruption_ev REAL,
        risk_profile TEXT,
        liquidity_score REAL,
        long_term INTEGER,
        PRIMARY KEY (timestamp, strategy_name, league)
    )
    """)
    conn.commit()
    conn.close()


def log_results_to_db(results: list[AnalysisResult], league: str) -> None:
    """Logs a list of AnalysisResult objects to the SQLite database."""
    if not results:
        logger.info("No results to log to database")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = int(time.time())

    logged_count = 0
    duplicate_count = 0
    for r in results:
        try:
            cursor.execute(
                """
            INSERT INTO trade_results (
                timestamp, league, strategy_name, profit_per_flip, profit_per_hour_est,
                profit_with_corruption_ev, risk_profile, liquidity_score, long_term
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    league,
                    r.strategy_name,
                    r.profit_per_flip,
                    r.profit_per_hour_est,
                    r.profit_with_corruption_ev,
                    r.risk_profile,
                    r.liquidity_score,
                    1 if r.long_term else 0,
                ),
            )
            logged_count += 1
        except sqlite3.IntegrityError:
            duplicate_count += 1
            logger.debug(
                f"Duplicate entry for {r.strategy_name} at timestamp {timestamp} - skipping"
            )

    conn.commit()
    conn.close()

    if duplicate_count > 0:
        logger.warning(f"Skipped {duplicate_count} duplicate entries")

    log_database_operation("insert", logged_count)


def get_historical_data(strategy_name: str, league: str) -> pd.DataFrame:
    """Retrieves and formats historical data for a specific strategy from the database."""
    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    try:
        query = "SELECT * FROM trade_results WHERE strategy_name = ? AND league = ? ORDER BY timestamp"
        df = pd.read_sql_query(query, conn, params=(strategy_name, league))
    finally:
        conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    return df
