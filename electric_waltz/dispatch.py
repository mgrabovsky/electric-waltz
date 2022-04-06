"""
Objects for dispatching flexible power sources.
"""

from __future__ import annotations
from typing import Sequence

from .source import DispatchableSource
from .storage import EnergyStorage
from .types import Power

__all__ = [
    "SourceDispatcher",
    "StorageDispatcher",
]


class SourceDispatcher:
    def __init__(self, units: Sequence[DispatchableSource]) -> None:
        """
        Arguments:
            units: Finite sequence of dispatchable power sources that
                this dispatcher controls. The order of sources in the list
                determines the merit order of dispatch, i.e. the first
                source in the list is dispatched first whenever needed.
        """
        self._units = units

    def shut_down_all(self) -> None:
        for unit in self._units:
            unit.shut_down()

    def dispatch_at(self, power: Power) -> Power:
        assert power >= 0

        generation: Power = 0

        # Turn sources on until demand is satisfied.
        for unit in self._units:
            generation += unit.dispatch_at(max(0, power - generation))

        # Allow for some numeric error.
        # assert generation - power <= 1e-6
        return generation

    @property
    def net_generation(self) -> Power:
        return sum(unit.net_generation for unit in self._units)


class StorageDispatcher:
    def __init__(self, units: Sequence[EnergyStorage]) -> None:
        self._units = units

    def charge_at(self, power: Power) -> Power:
        """
        Try to charge all available storage units with 'power' MW.
        Return charging power.
        """
        assert power >= 0

        charging: Power = 0
        for unit in self._units:
            charging += unit.charge_at(max(0, power - charging))

        # Allow for some numeric error.
        assert charging - power <= 1e-6
        return charging

    def discharge_at(self, power: Power) -> Power:
        """
        Try to discharge all available storage units up to 'power' MW.
        Return discharging power.
        """
        assert power >= 0

        discharging: Power = 0
        for unit in self._units:
            discharging += unit.discharge_at(max(0, power - discharging))

        # Allow for some numeric error.
        assert discharging - power <= 1e-6
        return discharging
