"""
Logging configuration and utilities for the Path of Exile trading analysis suite.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import settings


def setup_logging() -> None:
    """
    Configure logging based on settings from config.yaml.

    This function should be called once at the start of the application
    to initialize the logging system.
    """
    # Get logging configuration
    log_config = settings.get("logging", {})

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.get("level", "INFO")))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        log_config.get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
        datefmt=log_config.get("date_format", "%Y-%m-%d %H:%M:%S"),
    )

    # Setup console handler
    console_config = log_config.get("console", {})
    if console_config.get("enabled", True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_config.get("level", "INFO")))

        # Try to use colored logging if available
        if console_config.get("colored", True):
            try:
                import colorlog

                colored_formatter = colorlog.ColoredFormatter(
                    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt=log_config.get("date_format", "%Y-%m-%d %H:%M:%S"),
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red,bg_white",
                    },
                )
                console_handler.setFormatter(colored_formatter)
            except ImportError:
                # Fallback to regular formatter if colorlog not available
                console_handler.setFormatter(formatter)
        else:
            console_handler.setFormatter(formatter)

        root_logger.addHandler(console_handler)

    # Setup file handler
    file_config = log_config.get("file", {})
    if file_config.get("enabled", True):
        log_file_path = Path(file_config.get("path", "logs/poe_trading.log"))

        # Create log directory if it doesn't exist
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=file_config.get("max_size_mb", 10)
            * 1024
            * 1024,  # Convert MB to bytes
            backupCount=file_config.get("backup_count", 5),
        )
        file_handler.setLevel(getattr(logging, file_config.get("level", "DEBUG")))
        file_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)

    # Set module-specific log levels
    module_levels = log_config.get("modules", {})
    for module_name, level in module_levels.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(getattr(logging, level))


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    Args:
        name: The logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_api_request(
    url: str, status_code: int | None = None, error: str | None = None
) -> None:
    """
    Log API request details in a structured format.

    Args:
        url: The API endpoint URL
        status_code: HTTP status code (if successful)
        error: Error message (if failed)
    """
    logger = get_logger("poe_trade_lib.api")

    if error:
        logger.error(f"API request failed: {url} - {error}")
    else:
        logger.debug(f"API request successful: {url} - Status: {status_code}")


def log_strategy_execution(
    strategy_name: str, result_count: int, error: str | None = None
) -> None:
    """
    Log strategy execution results.

    Args:
        strategy_name: Name of the strategy
        result_count: Number of results found
        error: Error message (if failed)
    """
    logger = get_logger("poe_trade_lib.strategies")

    if error:
        logger.error(f"Strategy '{strategy_name}' failed: {error}")
    else:
        logger.info(
            f"Strategy '{strategy_name}' completed - Found {result_count} results"
        )


def log_database_operation(
    operation: str, count: int, error: str | None = None
) -> None:
    """
    Log database operation results.

    Args:
        operation: Type of operation (e.g., 'insert', 'select', 'update')
        count: Number of records affected
        error: Error message (if failed)
    """
    logger = get_logger("poe_trade_lib.db_utils")

    if error:
        logger.error(f"Database {operation} failed: {error}")
    else:
        logger.info(f"Database {operation} completed - {count} records affected")


def log_data_acquisition(
    data_type: str, record_count: int, cache_hit: bool = False
) -> None:
    """
    Log data acquisition results.

    Args:
        data_type: Type of data fetched (e.g., 'Currency', 'Scarab')
        record_count: Number of records retrieved
        cache_hit: Whether data was served from cache
    """
    logger = get_logger("poe_trade_lib.api")

    cache_status = "cache hit" if cache_hit else "API call"
    logger.debug(
        f"Data acquisition ({cache_status}): {data_type} - {record_count} records"
    )


# Initialize logging when module is imported
_logging_initialized = False


def ensure_logging_initialized() -> None:
    """Ensure logging is initialized exactly once."""
    global _logging_initialized
    if not _logging_initialized:
        setup_logging()
        _logging_initialized = True
