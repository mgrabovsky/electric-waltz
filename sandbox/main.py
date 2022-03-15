import argparse
import csv
import time
from typing import cast

from pandas import DataFrame, read_csv
from ruamel.yaml import YAML

from electric_waltz.cross_border import CrossBorderTerminal
from electric_waltz.dispatch import SourceDispatcher, StorageDispatcher
from electric_waltz.scenario import Scenario, ScenarioRun
from electric_waltz.source import (
    DispatchableSource,
    NonDispatchableSource,
    PowerSource,
)
from electric_waltz.storage import EnergyStorage
from electric_waltz.types import Energy, Power


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


def main(args: argparse.Namespace) -> None:
    world = read_csv(args.world_file)

    if "load" not in world or "solar_util" not in world or "wind_util" not in world:
        raise ValueError(
            "The world state CSV file must contain columns named ‘load’, "
            "‘solar_util’ and ‘wind_util’."
        )

    if args.year is not None:
        if "year" not in world:
            raise ValueError(
                "The world state CSV file must contain a column named ‘year’ if selection "
                "by year is used."
            )

        world = world[world["year"] == args.year].reset_index(drop=True)
        if world.empty:
            raise ValueError(
                "The world state CSV file must contain at least one row with year equal to "
                f"{args.year}."
            )

    with open(args.config_file, encoding="utf-8") as config_file:
        config = YAML(typ="safe").load(config_file)

    grid_losses: float = (
        config["consumption"]["transmission_loss"]
        + config["consumption"]["distribution_loss"]
    )

    # Inflexible power plants.
    nuclear = cast(NonDispatchableSource, make_power_plant("nuclear", config))
    pv = cast(NonDispatchableSource, make_power_plant("pv", config))
    wind = cast(NonDispatchableSource, make_power_plant("wind", config))

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

    # Construct the scenario object and run the simulation.
    scenario = Scenario(
        load=world.load,
        baseload_sources=[nuclear],
        intermittent_sources=[
            (pv, world.solar_util),
            (wind, world.wind_util),
        ],
        flexible_sources=[hydro, biomass, gas],
        storage_units=[pumped, battery, p2g],
        cross_border=cross_border,
        grid_losses=grid_losses,
    )

    start_time = time.perf_counter_ns()
    stats = scenario.run()
    finish_time = time.perf_counter_ns()

    total_consumption = sum(world.load)
    total_flexible_generation = (
        stats.compute_generation("hydro")
        + stats.compute_generation("biomass")
        + stats.compute_generation("gas")
    )
    total_inflexible_generation = (
        stats.compute_generation("nuclear")
        + stats.compute_generation("pv")
        + stats.compute_generation("wind")
    )
    total_generation = total_flexible_generation + total_inflexible_generation

    total_charging = stats.compute_total_charging()
    total_discharging = stats.compute_total_discharging()

    total_export = stats.compute_total_export()
    total_import = stats.compute_total_import()

    total_dump = stats.compute_total_dump()
    total_shortage = stats.compute_total_shortage()

    charging_hours = stats.count_charging_steps()
    discharging_hours = stats.count_discharging_steps()
    export_hours = stats.count_export_steps()
    import_hours = stats.count_import_steps()
    dump_hours = stats.count_dump_steps()
    shortage_hours = stats.count_shortage_steps()

    print(f"Total net generation         {total_generation:12,.0f} MWh")
    print(f"├─ Total inflexible          {total_inflexible_generation:12,.0f}")
    print("│  ├─ Nuclear                {:12,.0f}".format(stats.compute_generation("nuclear")))
    print("│  ├─ Solar PV               {:12,.0f}".format(stats.compute_generation("pv")))
    print("│  └─ On-shore wind          {:12,.0f}".format(stats.compute_generation("wind")))
    print(f"└─ Total flexible            {total_flexible_generation:12,.0f}")
    print("   ├─ Hydro                  {:12,.0f}".format(stats.compute_generation("hydro")))
    print("   ├─ Biomass                {:12,.0f}".format(stats.compute_generation("biomass")))
    print("   └─ Natural gas            {:12,.0f}".format(stats.compute_generation("gas")))

    print(
        f"\nTotal charging consumption   {total_charging:12,.0f} MWh "
        f"{charging_hours:6d} hrs"
    )
    print(
        f"Total discharging            {total_discharging:12,.0f}     "
        f"{discharging_hours:6d} hrs"
    )
    print(
        f"\nTotal export                 {total_export:12,.0f}     "
        f"{export_hours:6d} hrs"
    )
    print(
        f"Total import                 {total_import:12,.0f}     "
        f"{import_hours:6d} hrs"
    )
    print(f"Import balance               {total_import-total_export:12,.0f}")

    print(
        f"\nTotal surplus/dump           {total_dump:12,.0f}     "
        f"{dump_hours:6d} hrs"
    )
    print(
        f"Total shortage (EENS/LOLE)   {total_shortage:12,.0f}     "
        f"{shortage_hours:6d} hrs"
    )

    print(f"\nTotal net consumption        {total_consumption:12,.0f} MWh\n")

    if args.output_file is not None:
        model_output = DataFrame(
            data={
                "nuclear": stats._source_generation["nuclear"],
                "pv": stats._source_generation["pv"],
                "wind": stats._source_generation["wind"],
                "biomass": stats._source_generation["biomass"],
                "hydro": stats._source_generation["hydro"],
                "gas": stats._source_generation["gas"],
                "pumped": stats._storage_output["pumped"],
                "battery": stats._storage_output["battery"],
                "p2g": stats._storage_output["p2g"],
                "import": stats._net_import,
                "shortage": stats._shortage,
            }
        )
        model_output.to_csv(args.output_file, index_label="ix")
        print(f"Model output written to ‘{args.output_file}’")

    print("Calculation took {:.1f} ms".format((finish_time - start_time) / 1e6))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a simulation of the model with given parameters and input data"
    )
    parser.add_argument(
        "-o", "--output-file", help="Write model output to the given CSV file."
    )
    parser.add_argument(
        "-y",
        "--year",
        type=int,
        help="Select a specific year from the input world state to use "
        "for the simulation.",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        help="YAML file containing configuration of various elements " "of the grid.",
    )
    parser.add_argument(
        "-w",
        "--world-file",
        required=True,
        help="CSV file containing data on world state. Must contain "
        "at least the columns ‘load’, ‘solar_util’ and ‘wind_util’. "
        "If selection by year is used, a ‘year’ column must be "
        "present as well.",
    )
    args = parser.parse_args()

    main(args)
