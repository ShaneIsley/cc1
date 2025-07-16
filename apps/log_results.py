# apps/log_results.py
from poe_trade_lib import db_utils
from poe_trade_lib.client import PoeAnalysisClient
from poe_trade_lib.logging_config import ensure_logging_initialized, get_logger

# Initialize logging
ensure_logging_initialized()
logger = get_logger(__name__)


def main():
    """
    This script runs the full analysis and logs the results to the database.
    It is designed to be run automatically by a scheduler (e.g., cron).
    """
    logger.info("Starting scheduled analysis run")

    db_utils.initialize_database()
    client = PoeAnalysisClient()
    client.fetch_data()
    results = client.run_analysis()

    if results:
        db_utils.log_results_to_db(results, client.league)
    else:
        logger.info("No profitable strategies found to log.")

    logger.info("Scheduled analysis run complete")


if __name__ == "__main__":
    main()
