# poe_trade_lib/strategies/base_strategy.py
from abc import ABC, abstractmethod

from ..models import AnalysisResult


class BaseStrategy(ABC):
    """Abstract Base Class that all trading strategies must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A unique, human-readable name for the strategy."""
        pass

    @abstractmethod
    def analyze(self, data_cache: dict, league: str) -> list[AnalysisResult]:
        """
        Analyzes market data to find profitable opportunities.
        Returns a list of AnalysisResult objects.
        """
        pass
