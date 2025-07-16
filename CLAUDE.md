# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Path of Exile trading analysis suite that evaluates profitable trading strategies by analyzing market data from poe.ninja. The system uses a plugin-based architecture where trading strategies are implemented as classes that inherit from `BaseStrategy`.

## Core Architecture

- **`poe_trade_lib/`**: Main library containing the core trading analysis logic
  - `client.py`: `PoeAnalysisClient` - main orchestrator for data fetching and analysis
  - `core.py`: `run_all_analyses()` - dynamically discovers and runs all strategies
  - `strategies/`: Plugin directory where all trading strategies are implemented
    - `base_strategy.py`: Abstract base class that all strategies must inherit from
    - Individual strategy files (e.g., `flip_scarabs.py`, `flip_tattoos.py`, `invest_gems.py`)
  - `models.py`: Data models including `AnalysisResult`
  - `api.py`: poe.ninja API integration
  - `db_utils.py`: Database operations for historical data
  - `utils.py`: Utility functions for formatting and calculations

- **`apps/`**: Command-line applications
  - `run_analysis.py`: Interactive analysis runner with dashboard output
  - `log_results.py`: Scheduled analysis runner for data collection

## Common Commands

```bash
# Environment setup and dependency management
uv sync                    # Install/sync dependencies
uv add <package>          # Add a new dependency
uv remove <package>       # Remove a dependency

# Code quality and development tools
ruff check                # Run linting
ruff format               # Format code
ruff check --fix          # Auto-fix linting issues
ruff check --fix --unsafe-fixes  # Apply all fixes including unsafe ones
mypy poe_trade_lib/ apps/ # Run type checking
pre-commit run --all-files # Run all pre-commit hooks

# Run applications
uv run python apps/run_analysis.py    # Interactive analysis with dashboard
uv run python apps/log_results.py     # Scheduled analysis and logging

# Run the library as a module (if needed)
uv run python -m poe_trade_lib
```

## Development Workflow

The project includes automated code quality tools:

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checker
- **Pre-commit**: Git hooks for code quality

Pre-commit hooks run automatically on `git commit` and will:
- Fix code formatting issues
- Run linting checks
- Perform type checking
- Check for common issues (trailing whitespace, YAML syntax, etc.)

To run quality checks manually:
```bash
uv run ruff check --fix    # Fix linting issues
uv run ruff format         # Format code
uv run mypy poe_trade_lib/ apps/  # Type checking
```

## Configuration

- **`config.yaml`**: Main configuration file containing:
  - Default league settings
  - Analysis parameters (flips per hour, risk thresholds)
  - API settings and item blacklists
  - Strategy-specific configuration (e.g., gem corruption probabilities)

## Strategy Development

To add a new trading strategy:

1. Create a new file in `poe_trade_lib/strategies/`
2. Inherit from `BaseStrategy` and implement:
   - `name` property: unique strategy identifier
   - `analyze(data_cache, league)` method: returns list of `AnalysisResult` objects
3. The strategy will be automatically discovered and executed by `core.py`

## Data Flow

1. `PoeAnalysisClient.fetch_data()` retrieves market data from poe.ninja
2. `run_all_analyses()` dynamically discovers and runs all strategy classes
3. Results are sorted by profitability and returned as `AnalysisResult` objects
4. Historical data can be logged to database for trend analysis

## Key Dependencies

- `pandas`: Data manipulation and analysis
- `requests`: API calls to poe.ninja
- `PyYAML`: Configuration file parsing
- `streamlit`, `plotly`: Optional visualization components
