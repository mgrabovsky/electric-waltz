import csv
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast, Optional

from ruamel.yaml import YAML

from electric_waltz.cross_border import CrossBorderTerminal
from electric_waltz.dispatch import SourceDispatcher, StorageDispatcher
from electric_waltz.source import (
    DispatchableSource,
    NonDispatchableSource,
    PowerSource,
)
from electric_waltz.storage import EnergyStorage
from electric_waltz.types import Energy, Power


class Statistics:
    def __init__(self) -> None:
        self._steps: int = 0
        self._cross_border: Optional[CrossBorderTerminal] = None
        self._power_sources: list[PowerSource] = []
        self._storage_units: list[EnergyStorage] = []

        self._source_generation: dict[str, [Power]] = defaultdict(list)
        self._storage_output: dict[str, list[Power]] = defaultdict(list)
        self._net_import: list[Power] = []
        # Shortage (positive) or dump (negative).
        self._shortage: list[Power] = []

    def add_power_sources(self, sources: Sequence[PowerSource]) -> None:
        self._power_sources.extend(sources)

    def add_storage(self, units: Sequence[EnergyStorage]) -> None:
        self._storage_units.extend(units)

    def compute_total_charging(self) -> Energy:
        return -1 * sum(
            sum(output for output in self._storage_output[storage.name] if output < 0)
            for storage in self._storage_units
        )

    def compute_total_discharging(self) -> Energy:
        return sum(
            sum(output for output in self._storage_output[storage.name] if output > 0)
            for storage in self._storage_units
        )

    def compute_total_export(self) -> Energy:
        return -1 * sum(net_import for net_import in self._net_import if net_import < 0)

    def compute_total_import(self) -> Energy:
        return sum(net_import for net_import in self._net_import if net_import > 0)

    def set_cross_border(self, cross_border: CrossBorderTerminal) -> None:
        self._cross_border = cross_border

    @property
    def steps(self) -> int:
        return self._steps

    def sweep(self) -> None:
        for source in self._power_sources:
            self._source_generation[source.name].append(source.net_generation)
        for storage in self._storage_units:
            self._storage_output[storage.name].append(storage.output)
        if self._cross_border is not None:
            self._net_import.append(self._cross_border.net_import)
        self._steps += 1


@dataclass
class World:
    pv_utilisation: float
    wind_utilisation: float
    demand: Power


def make_power_plant(kind: str, config) -> PowerSource:
    """
    Create an object for power plant of given kind from the supplied
    configuration.
    """
    nominal_capacity = config["plants"]["installed"][kind]
    self_consumption = config["plants"]["self_consumption"][kind]

    if kind in ("nuclear", "pv", "wind"):
        return NonDispatchableSource(
            name=kind, nominal=nominal_capacity, self_consumption=self_consumption
        )
    return DispatchableSource(
        name=kind, nominal=nominal_capacity, self_consumption=self_consumption
    )


def make_storage(kind: str, config) -> EnergyStorage:
    """
    Create an object for storage aggregate of given kind from the supplied
    configuration.
    """
    nominal_capacity = config["storage"]["installed"][kind]
    max_energy = config["storage"]["max_energy"][kind]
    efficiency = config["storage"]["efficiency"][kind]

    return EnergyStorage(
        name=kind,
        nominal=nominal_capacity,
        max_storage=max_energy,
        efficiency=efficiency,
    )


def run(config, states: list[World]) -> Statistics:
    # Collected statistics.
    stats = Statistics()

    # Inflexible power plants.
    nuclear = make_power_plant("nuclear", config)
    pv = make_power_plant("pv", config)
    wind = make_power_plant("wind", config)

    # Flexible power plants.
    hydro = cast(DispatchableSource, make_power_plant("hydro", config))
    biomass = cast(DispatchableSource, make_power_plant("biomass", config))
    gas = cast(DispatchableSource, make_power_plant("gas", config))

    # Electricity storage.
    pumped = make_storage("pumped", config)
    battery = make_storage("battery", config)
    p2g = make_storage("p2g", config)

    # Cross-border import/export.
    cross_border = CrossBorderTerminal(config["cross_border"]["max_export"])

    stats.add_power_sources([nuclear, pv, wind, hydro, biomass, gas])
    stats.add_storage([pumped, battery, p2g])
    stats.set_cross_border(cross_border)

    loss_factor: float = (
        config["consumption"]["transmission_loss"]
        + config["consumption"]["distribution_loss"]
    )

    flexible_dispatcher = SourceDispatcher([hydro, biomass, gas])
    storage_dispatcher = StorageDispatcher([pumped, battery, p2g])

    # Transition function.
    # ----------------------------------------------------------------
    for world in states:
        # Read current state.
        # ------------------------------------------------------------
        total_consumption = world.demand * (1 + loss_factor)

        # Pass current utilisation down to `pv` and `wind`.
        pv.utilisation = world.pv_utilisation
        wind.utilisation = world.wind_utilisation

        inflexible_generation = (
            nuclear.net_generation + pv.net_generation + wind.net_generation
        )

        # Dispatch what's necessary according to some rules.
        # ------------------------------------------------------------
        if inflexible_generation >= total_consumption:
            # Turn off flexible sources (preemptively).
            flexible_dispatcher.shut_down_all()
            surplus = inflexible_generation - total_consumption
            # Try charging storage.
            if surplus > 0:
                charging = storage_dispatcher.charge_at(surplus)
                # The subtraction may sometimes underflow due to numerical instability.
                surplus = max(0, surplus - charging)
            # If storage is full, try export.
            export_power = cross_border.export_at(surplus)
            # If export capacity is full, record dump/surplus.
            stats._shortage.append(-max(0, surplus - export_power))
        else:
            assert inflexible_generation < total_consumption
            deficit = total_consumption - inflexible_generation
            # Try discharging as much storage as needed and possible.
            discharging = storage_dispatcher.discharge_at(deficit)
            # Clamp to hedge numerical instability.
            deficit = max(0, deficit - discharging)
            # If consumption still dominates, try turning on flexible sources in
            # order of merit.
            if deficit > 0:
                flexible_generation = flexible_dispatcher.dispatch_at(deficit)
                # The subtraction may sometimes underflow due to numerical instability.
                deficit = max(0, deficit - flexible_generation)
            else:
                flexible_dispatcher.shut_down_all()
            # Try import if necessary.
            import_power = cross_border.import_at(deficit)
            # Record shortage if the previous failed to satisfy demand.
            stats._shortage.append(max(0, deficit - import_power))

        stats.sweep()

    return stats


if __name__ == "__main__":
    states: list[World] = []
    with open("sandbox/input_data.csv", encoding="utf-8") as csv_file:
        for row in csv.reader(csv_file):
            states.append(
                World(
                    demand=float(row[0]),
                    pv_utilisation=float(row[1]),
                    wind_utilisation=float(row[2]),
                )
            )

    with open("sandbox/config.yml", encoding="utf-8") as config_file:
        yaml = YAML(typ="safe")
        config = yaml.load(config_file)

    stats = run(config, states)

    total_consumption = sum(s.demand for s in states)
    total_flexible_generation = (
        sum(stats._source_generation["hydro"])
        + sum(stats._source_generation["biomass"])
        + sum(stats._source_generation["gas"])
    )
    total_inflexible_generation = (
        sum(stats._source_generation["nuclear"])
        + sum(stats._source_generation["pv"])
        + sum(stats._source_generation["wind"])
    )
    total_generation = total_flexible_generation + total_inflexible_generation

    total_charging = stats.compute_total_charging()
    total_discharging = stats.compute_total_discharging()

    total_export = stats.compute_total_export()
    total_import = stats.compute_total_import()

    total_dump = -1 * sum(shortage for shortage in stats._shortage if shortage < 0)
    total_shortage = sum(shortage for shortage in stats._shortage if shortage > 0)

    print(f"Total net generation:        {total_generation:12,.0f} MWh")
    print(f"Total flexible generation:   {total_flexible_generation:12,.0f} MWh")
    print(f"Total inflexible generation: {total_inflexible_generation:12,.0f} MWh")
    print(f"Total charging consumption:  {total_charging:12,.0f} MWh")
    print(f"Total discharging:           {total_discharging:12,.0f} MWh")
    print(f"Total export:                {total_export:12,.0f} MWh")
    print(f"Total import:                {total_import:12,.0f} MWh")
    print(f"Total dump:                  {total_dump:12,.0f} MWh")
    print(f"Total shortage:              {total_shortage:12,.0f} MWh")

    print(f"\nTotal consumption:           {total_consumption:12,.0f} MWh")

    with open("sandbox/model_output.csv", "w", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "nuclear",
                "pv",
                "wind",
                "biomass",
                "hydro",
                "gas",
                "pumped",
                "battery",
                "p2g",
                "import",
                "shortage",
            ]
        )
        for i in range(stats.steps):
            writer.writerow(
                [
                    stats._source_generation["nuclear"][i],
                    stats._source_generation["pv"][i],
                    stats._source_generation["wind"][i],
                    stats._source_generation["biomass"][i],
                    stats._source_generation["hydro"][i],
                    stats._source_generation["gas"][i],
                    stats._storage_output["pumped"][i],
                    stats._storage_output["battery"][i],
                    stats._storage_output["p2g"][i],
                    stats._net_import[i],
                    stats._shortage[i],
                ]
            )

    print("\nModel output written to ‘sandbox/model_output.csv’")
