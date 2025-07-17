# Path of Exile Trading Analysis Suite

A comprehensive Python library for analyzing Path of Exile trading opportunities using real-time market data from poe.ninja.

## 🎯 Features

- **Real-time Market Data**: Fetches live prices from poe.ninja API
- **Multiple Trading Strategies**: Gem corruption, scarab flipping, tattoo trading
- **Historical Analysis**: SQLite database for tracking profit trends over time
- **Risk Assessment**: Automated risk profiling based on price volatility
- **Trade URL Generation**: Direct links to Path of Exile trade site
- **Automated Monitoring**: GitHub Actions for continuous market analysis
- **Type Safe**: Full mypy compliance with comprehensive type annotations

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/ShaneIsley/cc1.git
cd cc1
uv sync
```

### Basic Usage

```python
from poe_trade_lib.client import PoeAnalysisClient

# Initialize client for current league
client = PoeAnalysisClient("Mercenaries")

# Fetch market data and run analysis
client.fetch_data()
results = client.run_analysis()

# Get summary of profitable strategies
summary_df = client.get_summary_dataframe()
print(summary_df)
```

### Command Line Usage

```bash
# Run analysis and log results to database
uv run python -m apps.log_results

# Run analysis for specific league
uv run python -c "
from poe_trade_lib.client import PoeAnalysisClient
client = PoeAnalysisClient('Standard')
results = client.run_analysis()
print(f'Found {len(results)} profitable strategies')
"
```

## 📊 Trading Strategies

### 1. Gem Leveling & Corruption
- **Strategy**: Buy level 1 quality 20% gems, level to 20, corrupt with Vaal Orbs
- **Target**: 21/20 or 20/23 gem outcomes
- **Risk**: Medium (corruption outcomes are probabilistic)
- **Timeline**: Long-term investment (leveling required)

### 2. Scarab Flipping
- **Strategy**: Buy low-tier scarabs, use currency to upgrade
- **Target**: Higher-tier scarabs with better profit margins
- **Risk**: Low to Medium (depends on upgrade costs)
- **Timeline**: Short-term (immediate flips possible)

### 3. Tattoo Trading
- **Strategy**: Identify undervalued tattoos based on market inefficiencies
- **Target**: Quick arbitrage opportunities
- **Risk**: Low (direct market price differences)
- **Timeline**: Immediate

## 🏗️ Architecture

```
poe_trade_lib/
├── api.py              # Market data fetching and caching
├── client.py           # Main client interface
├── config.py           # Configuration management
├── core.py             # Strategy execution engine
├── db_utils.py         # Database operations
├── models.py           # Data models and types
├── utils.py            # Utility functions
├── logging_config.py   # Logging setup
└── strategies/         # Trading strategy implementations
    ├── base_strategy.py
    ├── flip_scarabs.py
    ├── flip_tattoos.py
    └── invest_gems.py
```

## ⚙️ Configuration

Configuration is managed through `config.yaml`:

```yaml
# Core Settings
default_league: "Mercenaries"

# File Paths (relative to project root)
paths:
  cache_dir: "cache"
  database_file: "data/historical_trades.db"

# Analysis Configuration
analysis:
  assumed_flips_per_hour: 120
  profit_volatility_risk_thresholds:
    Low: 15
    Medium: 50
    High: 150
    Extreme: 500

# API Configuration
api:
  base_url: "https://poe.ninja/api/data/"
  trade_url_base: "https://www.pathofexile.com/trade/exchange/"
  minimum_listings: 10
  item_blacklist:
    - "Vaal Gem"
    - "Portal"
```

## 🤖 Automated Analysis

The repository includes a GitHub Action that:

- Runs analysis every hour at 30 minutes past the hour
- Collects and stores historical market data
- Provides rich reporting and monitoring
- Supports manual execution with force options
- Includes smart skip logic to avoid redundant runs

View the workflow: `.github/workflows/run_analyzer.yml`

## 📈 Data & Analytics

### Database Schema

Historical results are stored in SQLite with the following structure:

```sql
CREATE TABLE trade_results (
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
);
```

### Risk Profiling

Strategies are automatically categorized by volatility:

- **Low**: ≤15 chaos standard deviation
- **Medium**: 16-50 chaos standard deviation
- **High**: 51-150 chaos standard deviation
- **Extreme**: >150 chaos standard deviation

## 🛠️ Development

### Setup Development Environment

```bash
# Install dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run python -m pytest

# Type checking
uv run mypy poe_trade_lib/

# Linting and formatting
uv run ruff check .
uv run ruff format .
```

### Adding New Strategies

1. Create a new strategy class inheriting from `BaseStrategy`
2. Implement the `analyze()` method
3. Add strategy to `STRATEGIES` list in `core.py`

Example:

```python
from .base_strategy import BaseStrategy
from ..models import AnalysisResult

class MyStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "My Custom Strategy"

    def analyze(self, data_cache: dict, league: str) -> list[AnalysisResult]:
        # Implementation here
        return results
```

## 📊 Example Output

```
Strategy                    Liquidity  Input Cost  Risk Profile  Profit/Flip  Profit/Hour (Est.)
Gem Invest: Anomalous Grace     N/A      156.0c    Investment       89.2c              N/A
Scarab: Harbinger (Rusted)       85%       2.1c          Low        1.8c            216.0c
Tattoo: Warrior's Tale           72%      12.3c       Medium        4.2c            504.0c
```

## ⚠️ Known Limitations

### Gem Strategy Implementation
The current gem corruption strategy has a documented limitation (see `FIXME` in `invest_gems.py`):

- **Current**: Uses L1Q20 → L20Q20 approach (market availability limitation)
- **Proper**: Should implement 3x L1Q0 → vendor recipe → L1Q20 → L20Q20 approach
- **Reason**: poe.ninja doesn't track low-quality gems consistently

This is marked for future improvement when better data sources become available.

## 🔒 Security & Privacy

- No personal data collection
- Public market data only
- No Path of Exile account integration required
- Rate limiting respects poe.ninja API guidelines

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚡ Performance

- **API Caching**: 15-minute cache for market data
- **Smart Analysis**: Skip logic prevents redundant calculations
- **Efficient Storage**: SQLite for minimal overhead
- **Type Safety**: Zero-runtime-cost type annotations

## 🎮 Disclaimer

This tool is for educational and analysis purposes only. Path of Exile trading carries inherent risks, and past performance doesn't guarantee future results. Always do your own research before making trading decisions.

---

**Made with ❤️ for the Path of Exile community**
