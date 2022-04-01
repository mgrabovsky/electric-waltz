"""
Structures for working with clearly defined scenarios.
"""
from __future__ import annotations
from collections import defaultdict
from typing import cast, List, Optional, Sequence

from .cross_border import CrossBorderTerminal
from .dispatch import (
    SourceDispatcher,
    StorageDispatcher,
)
from .source import (
    DispatchableSource,
    NonDispatchableSource,
    PowerSource,
)
from .storage import EnergyStorage
from .types import Energy, Power

__all__ = ["Scenario", "ScenarioRun"]


class ScenarioRun:
    def __init__(
        self,
        power_sources: Sequence[PowerSource],
        storage_units: Sequence[EnergyStorage],
        cross_border: Optional[CrossBorderTerminal] = None,
    ) -> None:
        """
        Arguments:
            power_sources: Sequence of electricity sources in the grid.
            storage_units: Sequence of electricity storage units/aggregates
                in the grid.
            cross_border: Optional facility for cross-border export/import of
                electric power.
        """
        self._power_sources = power_sources
        self._storage_units = storage_units
        self._cross_border = cross_border

        self._steps: int = 0
        self._source_generation: dict[str, List[Power]] = defaultdict(list)
        self._storage_output: dict[str, List[Power]] = defaultdict(list)
        self._net_import: list[Power] = []
        # Shortage (positive) or dump (negative).
        self._shortage: list[Power] = []

    def compute_generation(self, source_name: str) -> Energy:
        return sum(self._source_generation[source_name])

    def compute_total_charging(self) -> Energy:
        return -1.0 * sum(
            sum(output for output in self._storage_output[storage.name] if output < 0)
            for storage in self._storage_units
        )

    def compute_total_discharging(self) -> Energy:
        return sum(
            sum(output for output in self._storage_output[storage.name] if output > 0)
            for storage in self._storage_units
        )

    def compute_total_dump(self) -> Energy:
        return -sum(shortage for shortage in self._shortage if shortage < 0)

    def compute_total_export(self) -> Energy:
        return -1.0 * sum(
            net_import for net_import in self._net_import if net_import < 0
        )

    def compute_total_import(self) -> Energy:
        return sum(net_import for net_import in self._net_import if net_import > 0)

    def compute_total_shortage(self) -> Energy:
        return sum(shortage for shortage in self._shortage if shortage > 0)

    def count_charging_steps(self) -> int:
        return sum(
            1
            for step in range(self._steps)
            if any(output[step] < 0 for output in self._storage_output.values())
        )

    def count_discharging_steps(self) -> int:
        return sum(
            1
            for step in range(self._steps)
            if any(output[step] > 0 for output in self._storage_output.values())
        )

    def count_dump_steps(self) -> int:
        return sum(1 for shortage in self._shortage if shortage < 0)

    def count_export_steps(self) -> int:
        return sum(1 for net_import in self._net_import if net_import < 0)

    def count_generation_steps(self, source_name: str) -> int:
        return sum(
            1 for generation in self._source_generation[source_name] if generation > 0
        )

    def count_import_steps(self) -> int:
        return sum(1 for net_import in self._net_import if net_import > 0)

    def count_shortage_steps(self) -> int:
        return sum(1 for shortage in self._shortage if shortage > 0)

    @property
    def steps(self) -> int:
        return self._steps

    def sweep(self) -> None:
        """Collect statistics from all registered objects."""
        for source in self._power_sources:
            self._source_generation[source.name].append(source.net_generation)
        for storage in self._storage_units:
            self._storage_output[storage.name].append(storage.output)
        if self._cross_border:
            self._net_import.append(self._cross_border.net_import)
        self._steps += 1


class Scenario:
    def __init__(
        self,
        *,
        load: Sequence[Power],
        baseload_sources: list[NonDispatchableSource],
        flexible_sources: list[DispatchableSource],
        intermittent_sources: list[tuple[NonDispatchableSource, Sequence[float]]],
        storage_units: list[EnergyStorage],
        cross_border: Optional[CrossBorderTerminal] = None,
        grid_losses: float = 0.0,
    ) -> None:
        """
        Arguments:
            load: Time series of net load for each time step in MW.
            baseload_sources: List of baseload power sources, e.g. nuclear power
                plants.
            flexible_sources: List of dispatchable (flexible) power sources or peaking
                power plants, e.g. biomass or natural gas-fuelled power plants. Merit
                order (order of dispatch) is given by the position of the source in
                the sequence.
            intermittent_sources: List of intermittent (inflexible) power sources,
                e.g. wind or solar photovoltaic power plants. The second entry in the
                tuple is a time series of capacity factor for the source in each time
                step.
            storage_units: List of electricity storage units.
            cross_border: A single cross-border export/import facility.
            grid_losses: Losses in the grid (transmission and distribution) as a
                portion of net load. A number in the interval [0, 1).
        """
        assert 0 <= grid_losses < 1

        self._num_steps = len(load)

        # Check that the input has the correct dimensions.
        if any(len(ts) != self._num_steps for _, ts in intermittent_sources):
            raise ValueError(
                "Wrong dimensions of intermittent capacity factor time series. "
                f"Expected {self._num_steps} cells for each source."
            )

        # Check that the capacity factor of intermittents is valid, i.e. between zero
        # and one (inclusive), in each time step.
        if any(not all(0 <= f <= 1 for f in ts) for _, ts in intermittent_sources):
            raise ValueError(
                "Invalid capacity factor value for intermittents. Make sure all "
                "values are in the interval [0, 1]."
            )

        self._load = load
        self._baseloads = baseload_sources
        self._flexibles = flexible_sources
        self._intermittents = intermittent_sources
        self._storages = storage_units
        self._cross_border = cross_border
        self._losses = grid_losses

        self._flexibles_dispatcher = SourceDispatcher(self._flexibles)
        self._storage_dispatcher = StorageDispatcher(self._storages)

    @property
    def num_steps(self) -> int:
        """Return the number of discrete time steps in this simulated scenario."""
        return self._num_steps

    def run(self) -> ScenarioRun:
        """
        Run the scenario and return time series of statistics on each object in
        the grid.

        Returns:
            Object containing time series of electricity source utilisation,
                storage utilisation, export/import statistics, etc.
        """
        num_steps = len(self._load)

        power_sources = (
            cast(List[PowerSource], self._baseloads)
            + cast(List[PowerSource], [source for source, _ in self._intermittents])
            + cast(List[PowerSource], self._flexibles)
        )
        
        stats = ScenarioRun(
            power_sources=power_sources,
            storage_units=self._storages,
            cross_border=self._cross_border,
        )

        for i in range(num_steps):
            gross_consumption = self._load[i] * (1 + self._losses)

            # Pass current utilisation down to the individual intermittent sources.
            for source, cap_factor in self._intermittents:
                source.utilisation = cap_factor[i]

            shortage = self._step(gross_consumption)
            stats.sweep()
            # FIXME: Make this more reasonable. Create some interface perhaps?
            stats._shortage.append(shortage)  # pylint: disable=protected-access

        return stats

    def _step(self, consumption: Power) -> Power:
        """
        Returns:
            Electricity shortage, i.e. amount of load not met by the grid (positive)
                or excess generation (negative).
        """
        # Net power generated by inflexible sources (baseload + intermittents).
        inflexible_generation = sum(
            source.net_generation for source in self._baseloads
        ) + sum(source.net_generation for source, _ in self._intermittents)

        # Dispatch whatever is necessary according to some rules.
        if inflexible_generation >= consumption:
            # Preemptively turn off flexible sources.
            self._flexibles_dispatcher.shut_down_all()

            surplus = inflexible_generation - consumption

            # Try charging storage if necessary.
            charging = self._storage_dispatcher.charge_at(surplus)
            # The subtraction may sometimes underflow due to numerical instability.
            surplus = max(0, surplus - charging)

            # If storage is full, try export.
            export_power = (
                self._cross_border.export_at(surplus) if self._cross_border else 0
            )
            # If export capacity is full, return dump/generation surplus.
            # FIXME: What to do about this?
            return -max(0, surplus - export_power)

        assert inflexible_generation < consumption
        deficit = consumption - inflexible_generation

        # Try discharging as much storage as needed and possible.
        discharging = self._storage_dispatcher.discharge_at(deficit)
        # Clamp to hedge numerical instability.
        deficit = max(0, deficit - discharging)

        # If consumption still dominates, try turning on flexible sources in
        # order of merit.
        if deficit > 0:
            flexible_generation = self._flexibles_dispatcher.dispatch_at(deficit)
            # The subtraction may sometimes underflow due to numerical instability.
            deficit = max(0, deficit - flexible_generation)
        else:
            self._flexibles_dispatcher.shut_down_all()

        # Try import if necessary.
        import_power = (
            self._cross_border.import_at(deficit) if self._cross_border else 0
        )
        # Return shortage if the previous failed to satisfy load.
        # FIXME: What to do about this?
        return max(0, deficit - import_power)
