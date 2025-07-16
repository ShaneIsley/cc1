# apps/log_results.py
from poe_trade_lib import db_utils
from poe_trade_lib.client import PoeAnalysisClient


def main():
    """
    This script runs the full analysis and logs the results to the database.
    It is designed to be run automatically by a scheduler (e.g., cron).
    """
    print("--- Starting Scheduled Analysis Run ---")

    db_utils.initialize_database()
    client = PoeAnalysisClient()
    client.fetch_data()
    results = client.run_analysis()

    if results:
        db_utils.log_results_to_db(results, client.league)
    else:
        print("No profitable strategies found to log.")

    print("--- Scheduled Run Complete ---")


if __name__ == "__main__":
    main()
