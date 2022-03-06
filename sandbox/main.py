import csv
from typing import cast, Optional

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


if __name__ == "__main__":
    world = read_csv("sandbox/input_data.csv", names=("demand", "solar_util", "wind_util"))

    with open("sandbox/config.yml", encoding="utf-8") as config_file:
        yaml = YAML(typ="safe")
        config = yaml.load(config_file)

    grid_losses: float = (
        config["consumption"]["transmission_loss"]
        + config["consumption"]["distribution_loss"]
    )

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

    # Construct the scenario object and run the simulation.
    scenario = Scenario(
        demand=world.demand,
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

    stats = scenario.run()

    total_consumption = sum(world.demand)
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

    print(f"\nTotal charging consumption   {total_charging:12,.0f} MWh "
          f"{charging_hours:6d} hrs")
    print(f"Total discharging            {total_discharging:12,.0f}     "
          f"{discharging_hours:6d} hrs")
    print(f"\nTotal export                 {total_export:12,.0f}     "
          f"{export_hours:6d} hrs")
    print(f"Total import                 {total_import:12,.0f}     "
          f"{import_hours:6d} hrs")
    print(f"Import balance               {total_import-total_export:12,.0f}")

    print(f"\nTotal surplus/dump           {total_dump:12,.0f}     "
          f"{dump_hours:6d} hrs")
    print(f"Total shortage (EENS/LOLE)   {total_shortage:12,.0f}     "
          f"{shortage_hours:6d} hrs")

    print(f"\nTotal net consumption        {total_consumption:12,.0f} MWh")

    breakpoint

    model_output = DataFrame(data={
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
    })
    model_output.to_csv("sandbox/model_output.csv", index_label="ix")

    print("\nModel output written to ‘sandbox/model_output.csv’")
