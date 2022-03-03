"""
Objects and functions for electricity storage.
"""

from .types import Power

__all__ = [
    "DispatchableSource",
    "NonDispatchableSource",
    "PowerSource",
]


class PowerSource:
    """
    General class representing sources that generate electricity in the
    grid. These are typically conventional or renewable power plants.
    """

    def __init__(
        self,
        name: str,
        nominal: Power,
        self_consumption: float = 0.0,
        utilisation: float = 1.0,
    ) -> None:
        """
        Create an electricity source object.

        Arguments:
            name : Short textual identifier of the source, e.g. "wind" or "nuclear".
            capacity : Nominal (or nameplate, installed) capacity of the
                source in MW.
            self_consumption : Portion of generated power that is
                consumed by the source itself to keep running. A number
                in the range [0, 1].
            utilisation : Initial utilisation (or capacity factor) of
                the source. A number in the range [0, 1].
        """
        assert 0 < len(name)
        assert 0 < nominal
        assert 0 <= self_consumption < 1
        assert 0 <= utilisation <= 1

        self._name = name
        self._nominal_capacity = nominal
        self._self_consumption = self_consumption
        self._utilisation = utilisation

    @property
    def generation(self) -> Power:
        """
        Return gross power generation of the source in MWh. This is equal
        to the nominal capacity multiplied by the capacity factor.
        """
        return self._utilisation * self._nominal_capacity

    @property
    def name(self) -> str:
        """Return the source's textual identifier."""
        return self._name

    @property
    def net_generation(self) -> Power:
        """
        Return net power generation of the source in MWh. This amount
        is equal to gross generation minus the source's self-consumption.
        """
        return self.generation * (1 - self._self_consumption)

    @property
    def utilisation(self) -> float:
        """
        Return the source's capacity factor.
        """
        return self._utilisation

    @utilisation.setter
    def utilisation(self, value: float) -> None:
        """
        Set the source's capacity factor.

        Arguments:
            value : The new capacity factor. Must be a number in the
                range [0, 1].
        """
        assert 0 <= value <= 1
        self._utilisation = value


class NonDispatchableSource(PowerSource):
    """
    Class representing non-dispatchable (inflexible) power plants.
    These are typically renewable sources, such as photovoltaic power
    plants or wind turbines. This class may also be used for nuclear
    power plants that are used for a constant base load, i.e. with
    no dispatch capabilities.
    """


class DispatchableSource(PowerSource):
    """
    Class representing dispatchable (flexible) sources of
    electricity and power plants. Typically, these include coal-fired,
    hydroelectric, natural gas or biomass-fueled power plants.
    """

    def dispatch_at(self, power: Power) -> Power:
        """
        Request that the electricity source adjust its generation to at most
        `power` MW, or to its maximum capacity, if `power` is greater than
        the nominal capacity.

        Arguments:
            power : The requested power generation.

        Returns:
            Net power generation of the source after the dispatch request.
        """
        assert power >= 0

        max_net_power = self._nominal_capacity * (1 - self._self_consumption)

        # Explicitly cap the capacity factor at 1.0. An overflow might sometimes occur
        # following some ordinary floating-point manipulations.
        self._utilisation = min(power / max_net_power, 1)

        assert 0 <= self._utilisation <= 1
        return self.net_generation

    def shut_down(self) -> None:
        """
        Request the power source to shut down, i.e. turn of all electricity
        generation.
        """
        self._utilisation = 0
