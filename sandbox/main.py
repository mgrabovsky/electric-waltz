import csv
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
from electric_waltz.types import Energy, Power


class Statistics:
    total_flexible_generation: Energy = 0.0
    total_inflexible_generation: Energy = 0.0
    total_charging: Energy = 0.0
    total_discharging: Energy = 0.0
    total_export: Energy = 0.0
    total_import: Energy = 0.0
    total_dump: Energy = 0.0
    total_shortage: Energy = 0.0


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
            nominal=nominal_capacity, self_consumption=self_consumption
        )
    return DispatchableSource(
        nominal=nominal_capacity, self_consumption=self_consumption
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
        nominal=nominal_capacity,
        max_storage=max_energy,
        efficiency=efficiency,
    )


def run(config, states: list[World]) -> Statistics:
    # Set up.
    # ----------------------------------------------------------------
    # Collected statistics.
    stats = Statistics()

    # Inflexible power plants.
    nuclear = make_power_plant("nuclear", config)
    pve = make_power_plant("pv", config)
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
    total_losses: float = (
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
        total_consumption = world.demand * (1 + total_losses)

        # Pass current utilisation down to `pve` and `wind`.
        pve.utilisation = world.pv_utilisation
        wind.utilisation = world.wind_utilisation

        inflexible_generation = (
            nuclear.net_generation + pve.net_generation + wind.net_generation
        )
        stats.total_inflexible_generation += inflexible_generation

        # Dispatch what's necessary according to some rules.
        # ------------------------------------------------------------
        if inflexible_generation >= total_consumption:
            # Turn off flexible sources (preemptively).
            flexible_dispatcher.shut_down_all()
            surplus = inflexible_generation - total_consumption
            # Try charging storage.
            if surplus > 0:
                charging = storage_dispatcher.charge_at(surplus)
                stats.total_charging += charging
                surplus -= charging
            # If storage is full, try export.
            export_power = min(surplus, max_export)
            stats.total_export += export_power
            # If export capacity is full, record dump/surplus.
            stats.total_dump += max(0, surplus - export_power)
        else:
            assert inflexible_generation < total_consumption
            deficit = total_consumption - inflexible_generation
            # Try discharging as much storage as needed and possible.
            discharging = storage_dispatcher.discharge_at(deficit)
            stats.total_discharging += discharging
            deficit -= discharging
            # If consumption still dominates, try turning on flexible sources in
            # order of merit.
            if deficit > 0:
                flexible_generation = flexible_dispatcher.dispatch_at(deficit)
                stats.total_flexible_generation += flexible_generation
                deficit -= flexible_generation
            else:
                flexible_dispatcher.shut_down_all()
            # Try import if necessary.
            import_power = min(deficit, max_import)
            stats.total_import += import_power
            deficit -= import_power
            assert deficit >= 0
            # Record shortage if the previous failed to satisfy demand.
            if deficit > 0:
                stats.total_shortage += deficit

    return stats


if __name__ == '__main__':
    states: list[World] = []
    with open("sandbox/input_data.csv", encoding="utf-8") as csv_file:
        for row in csv.reader(csv_file):
            states.append(
                World(
                    demand=float(row[0]),
                    pv_utilisation=float(row[1]),
                    wind_utilisation=float(row[2])
                )
            )

    with open("sandbox/config.yml", encoding="utf-8") as config_file:
        yaml = YAML(typ="safe")
        config = yaml.load(config_file)

    stats = run(config, states)

    total_generation = (
        stats.total_flexible_generation + stats.total_inflexible_generation
    )

    print(f"Total net generation:        {total_generation:12,.0f} MWh")
    print(f"Total flexible generation:   {stats.total_flexible_generation:12,.0f} MWh")
    print(f"Total inflexible generation: {stats.total_inflexible_generation:12,.0f} MWh")
    print(f"Total charging consumption:  {stats.total_charging:12,.0f} MWh")
    print(f"Total discharging:           {stats.total_discharging:12,.0f} MWh")
    print(f"Total export:                {stats.total_export:12,.0f} MWh")
    print(f"Total import:                {stats.total_import:12,.0f} MWh")
    print(f"Total dump:                  {stats.total_dump:12,.0f} MWh")
    print(f"Total shortage:              {stats.total_shortage:12,.0f} MWh")

    print("\nTotal consumption:           {:12,.0f} MWh"
          .format(sum(s.demand for s in states)))
