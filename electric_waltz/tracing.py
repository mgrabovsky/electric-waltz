"""
Functionality for tracing the utilisation (and other stats) of power sources
and storage over time.
"""
from collections import defaultdict
from typing import Optional

from .source import PowerSource
from .storage import EnergyStorage
from .types import Power

__all__ = ["StatsCollector"]


class StatsCollector:
    """
    Object for collecting statistics on utilisation of power sources and
    charging/discharging capacity of storage over time.
    """

    def __init__(self) -> None:
        """Create a new tracer object."""
        self._step: int = 0

        self._sources: list[PowerSource] = []
        self._storage: list[EnergyStorage] = []

        self._source_generation: dict[str, list[Power]] = defaultdict(list)
        self._storage_output: dict[str, list[Power]] = defaultdict(list)

    def add_power_sources(self, sources: list[PowerSource]) -> None:
        """
        Register multiple power sources to be traced.
        """
        self._sources.extend(sources)

    def add_storage_units(self, units: list[EnergyStorage]) -> None:
        """
        Register multiple storage units (or aggregates) to be traced.
        """
        self._storage.extend(units)

    def get_source_generation(self, name: str) -> Optional[list[Power]]:
        """Get the history of power generation for source with identifier `name`."""
        if name not in self._source_generation:
            return None
        return self._source_generation[name]

    def get_storage_output(self, name: str) -> Optional[list[Power]]:
        """Get the history of power output for storage with identifier `name`."""
        if name not in self._storage_output:
            return None
        return self._storage_output[name]

    def sweep(self) -> None:
        """
        Collect statistics from all registered objects.
        """
        for source in self._sources:
            self._source_generation[source.name].append(source.net_generation)

        for storage in self._storage:
            self._storage_output[storage.name].append(storage.output)

        self._step += 1