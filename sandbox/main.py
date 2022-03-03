import csv
from collections import defaultdict
from dataclasses import dataclass
from typing import cast

from ruamel.yaml import YAML

from electric_waltz.dispatch import SourceDispatcher, StorageDispatcher
from electric_waltz.source import (
    DispatchableSource,
    NonDispatchableSource,
    PowerSource,
)
from electric_waltz.storage import EnergyStorage
from electric_waltz.types import Power


class Statistics:
    def __init__(self) -> None:
        self.source_generation: dict[str, [Power]] = defaultdict(list)
        self.storage_output: dict[str, list[Power]] = defaultdict(list)
        self.net_import: list[Power] = []
        # Shortage (positive) or dump (negative).
        self.shortage: list[Power] = []


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

    max_export: Power = config["cross_border"]["max_export"]
    max_import: Power = config["cross_border"]["max_import"]
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
                surplus -= charging
            # If storage is full, try export.
            export_power = min(surplus, max_export)
            stats.net_import.append(-export_power)
            # If export capacity is full, record dump/surplus.
            stats.shortage.append(-max(0, surplus - export_power))
        else:
            assert inflexible_generation < total_consumption
            deficit = total_consumption - inflexible_generation
            # Try discharging as much storage as needed and possible.
            discharging = storage_dispatcher.discharge_at(deficit)
            deficit -= discharging
            # If consumption still dominates, try turning on flexible sources in
            # order of merit.
            if deficit > 0:
                flexible_generation = flexible_dispatcher.dispatch_at(deficit)
                deficit -= flexible_generation
            else:
                flexible_dispatcher.shut_down_all()
            # Try import if necessary.
            import_power = min(deficit, max_import)
            stats.net_import.append(import_power)
            # Record shortage if the previous failed to satisfy demand.
            stats.shortage.append(max(0, deficit - import_power))

        stats.source_generation["nuclear"].append(nuclear.net_generation)
        stats.source_generation["pv"].append(pv.net_generation)
        stats.source_generation["wind"].append(wind.net_generation)
        stats.source_generation["hydro"].append(hydro.net_generation)
        stats.source_generation["biomass"].append(biomass.net_generation)
        stats.source_generation["gas"].append(gas.net_generation)

        stats.storage_output["pumped"].append(pumped.output)
        stats.storage_output["battery"].append(battery.output)
        stats.storage_output["p2g"].append(p2g.output)

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
        sum(stats.source_generation["hydro"])
        + sum(stats.source_generation["biomass"])
        + sum(stats.source_generation["gas"])
    )
    total_inflexible_generation = (
        sum(stats.source_generation["nuclear"])
        + sum(stats.source_generation["pv"])
        + sum(stats.source_generation["wind"])
    )
    total_generation = total_flexible_generation + total_inflexible_generation

    total_charging = -(
        sum(output for output in stats.storage_output["pumped"] if output < 0)
        + sum(output for output in stats.storage_output["battery"] if output < 0)
        + sum(output for output in stats.storage_output["p2g"] if output < 0)
    )
    total_discharging = (
        sum(output for output in stats.storage_output["pumped"] if output > 0)
        + sum(output for output in stats.storage_output["battery"] if output > 0)
        + sum(output for output in stats.storage_output["p2g"] if output > 0)
    )

    total_export = sum(-net_import for net_import in stats.net_import if net_import < 0)
    total_import = sum(net_import for net_import in stats.net_import if net_import > 0)

    total_dump = sum(-shortage for shortage in stats.shortage if shortage < 0)
    total_shortage = sum(shortage for shortage in stats.shortage if shortage > 0)

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
