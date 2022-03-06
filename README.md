# Electric Waltz

> A simple deterministc model of the electric energy system of the Czech Republic.

[![Build Status][build-image]][build-url]
[![Code Coverage][coverage-image]][coverage-url]
[![Code Quality][quality-image]][quality-url]

This project aims to construct an [open-source model](https://en.m.wikipedia.org/wiki/Open_energy_system_models) of the Czech electricity system.

The basic features of the model currently include:

-   Calculating unit commitment of power sources for each hour of the year.
-   Calculating the generation of intermittent sources (photoltaic, wind) according to their assumed hourly capacity factor (supplied as part of input).
-   Dispatching flexible sources, storage and import/export in a specified merit order.
    -   The default merit order is as follows: baseload and intermittent sources (nuclear, PV, wind) → storage → hydro → biomass → natural gas → cross-border import.
-   Redirecting of surplus generation to storage units (pumped water, batteries, power-to-gas) and discharging them when demand rises.
-   Basic modelling of power plant self-consumption, storage inefficiency (only at charging time at the moment) and transmission/distribution losses in the grid.
-   Configuration of grid elements and properties using a YAML file.
-   Export of hourly data to CSV.

The model is wholly deterministic, i.e. the output is only affected by the supplied input data and there are no elements of randomness in the simulation process.

## Example output

The basic output of the model runner is the following table summarising the key flows in the model:

    Total net generation:         107,141,867 MWh
    Total flexible generation:     46,625,280 MWh
    Total inflexible generation:   60,516,587 MWh
    Total charging consumption:     2,880,642 MWh
    Total discharging:              1,986,646 MWh
    Total export:                     540,868 MWh
    Total import:                   3,189,288 MWh
    Total dump:                       274,023 MWh
    Total shortage:                 1,473,203 MWh

    Total consumption:            102,864,123 MWh

    Model output written to ‘sandbox/model_output.csv’

The runner also generates a CSV file with the generation/output of each electricity source in every hour of the modelled period. This data can be used to plot the time series of demand, power generation, import/export, etc., such as the following:

![Stacked area chart showing in two rows the progress of electricity generation in two fortnights of the hypothetical year 2050.](https://raw.githubusercontent.com/mgrabovsky/electric-waltz/main/docs/model-generation-2050.png)

## History

A first version of this model was devised by Jan Rovenský and implemented in an Excel spreadsheet. This project is a rewrite of that model in Python which provides greater flexibility and maintainability. It makes the model easier to expand and customise.

## Licence

This project is licensed under the [Blue Oak Model License 1.0.0](https://blueoakcouncil.org/license/1.0.0).

<!-- Badges -->

[build-image]: https://github.com/mgrabovsky/electric-waltz/actions/workflows/build.yml/badge.svg
[build-url]: https://github.com/mgrabovsky/electric-waltz/actions/workflows/build.yml
[coverage-image]: https://codecov.io/gh/mgrabovsky/electric-waltz/branch/main/graph/badge.svg
[coverage-url]: https://codecov.io/gh/mgrabovsky/electric-waltz
[quality-image]: https://api.codeclimate.com/v1/badges/5fa295edef142fc90ddd/maintainability
[quality-url]: https://codeclimate.com/github/mgrabovsky/electric-waltz
