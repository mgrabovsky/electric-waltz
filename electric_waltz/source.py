"""
Objects and functions for electricity storage.
"""
from dataclasses import dataclass

from .types import Power

__all__ = [
    "DispatchableSource",
    "NonDispatchableSource",
    "PowerSource",
    "ThermalPowerPlant",
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
        *,
        self_consumption: float = 0.0,
        utilisation: float = 1.0,
    ) -> None:
        """
        Create an electricity source object.

        Arguments:
            name: Short textual identifier of the source, e.g. "wind" or "nuclear".
            nominal: Nominal (or nameplate, installed) capacity of the
                source in MW.
            self_consumption: Portion of generated power that is
                consumed by the source itself to keep running. A number
                in the range [0, 1].
            utilisation: Initial utilisation (or capacity factor) of
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
            value: The new capacity factor. Must be a number in the
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
    hydroelectric, natural gas or biomass-fuelled power plants.
    """

    def dispatch_at(self, power: Power) -> Power:
        """
        Request that the electricity source adjust its generation to at most
        `power` MW, or to its maximum capacity, if `power` is greater than
        the nominal capacity.

        Arguments:
            power: The requested power generation.

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


class ThermalPowerPlant(DispatchableSource):
    """
    A thermal-like power plant with limited flexibility capabilities. This can be
    used to model, for instance, lignite and hard coal-fired plants or OCGT/CCGT gas
    plants.
    """

    class _State:
        pass

    @dataclass
    class _ShutDown(_State):
        downtime: int

        def step(self) -> None:
            self.downtime += 1

    @dataclass
    class _StartingUp(_State):
        phase: int

        def step(self) -> None:
            self.phase += 1

    @dataclass
    class _Running(_State):
        uptime: int

        def step(self) -> None:
            self.uptime += 1

    def __init__(
        self,
        name: str,
        nominal: Power,
        *,
        self_consumption: float = 0.0,
        min_load: float = 0.0,
        min_downtime: int = 0,
        min_uptime: int = 0,
        startup_time: int = 0,
    ) -> None:
        """
        Create an electricity source object.

        Arguments:
            name: Short textual identifier of the source, e.g. "wind" or "nuclear".
            nominal: Nominal (or nameplate, installed) capacity of the
                source in MW.
            self_consumption: Portion of generated power that is
                consumed by the source itself to keep running. A number
                in the range [0, 1].
            min_load: Minimum required load when generating electricity.
                A number in the range [0, 1].
            min_downtime: ...
            min_uptime: ...
            startup_time: Number of time steps it takes to start the source from
                cold, i.e. time before it reaches `min_load` of utilisation.
        """
        super().__init__(
            name, nominal, self_consumption=self_consumption, utilisation=0.0
        )

        assert 0 <= min_load <= 1

        self._min_load = min_load
        self._min_downtime = min_downtime
        self._min_uptime = min_uptime
        self._startup_time = startup_time

        self._state: ThermalPowerPlant._State = ThermalPowerPlant._ShutDown(min_downtime)

    def dispatch_at(self, power: Power) -> Power:
        """
        Request that the electricity source adjust its generation to at most
        `power` MW, or to its maximum capacity, if `power` is greater than
        the nominal capacity.

        Arguments:
            power: The requested power generation.

        Returns:
            Net power generation of the source after the dispatch request.
        """
        assert power >= 0

        max_net_power = self._nominal_capacity * (1 - self._self_consumption)
        # Explicitly cap the capacity factor at 1.0. An overflow might sometimes occur
        # following some ordinary floating-point manipulations.
        required_factor = min(power / max_net_power, 1)

        if self.is_shut_down:
            assert self.net_generation == 0
            if (
                # We do not start firing up until the demand reaches at least
                # the minimum required load.
                power < self._min_load * self._nominal_capacity
                # Check that the required cooldown period has passed.
                or self._state.downtime < self._min_downtime
            ):
                self._state.step()
            elif self._startup_time > 0:
                self._start_up()
            else:
                self._run()
                self._utilisation = required_factor

            assert 0 <= self._utilisation <= 1
        elif self.is_starting_up:
            assert self._startup_time > 0
            if self._state.phase == self._startup_time:
                self._run()
                if power < self._min_load * self._nominal_capacity:
                    if self._min_uptime == 0:
                        self.shut_down()
                    else:
                        self._utilisation = self._min_load
                else:
                    self._utilisation = required_factor
            else:
                self._state.step()
                self._utilisation = self._state.phase / self._startup_time * self._min_load / (1 - self._self_consumption)
        else:
            assert isinstance(self._state, ThermalPowerPlant._Running)

            self._state.step()

            if power < self._min_load * self._nominal_capacity:
                if self._state.uptime < self._min_uptime:
                    self._utilisation = self._min_load
                else:
                    self.shut_down()
            else:
                self._utilisation = required_factor

        assert 0 <= self._utilisation <= 1
        return self.net_generation

    @property
    def is_shut_down(self) -> bool:
        return isinstance(self._state, ThermalPowerPlant._ShutDown)

    @property
    def is_starting_up(self) -> bool:
        return isinstance(self._state, ThermalPowerPlant._StartingUp)

    def _run(self) -> None:
        self._state = ThermalPowerPlant._Running(uptime=1)

    def shut_down(self) -> None:
        if isinstance(self._state, ThermalPowerPlant._ShutDown):
            self._state.downtime += 1
            self._utilisation = 0.0
        elif isinstance(self._state, ThermalPowerPlant._StartingUp):
            # TODO: Handle this better.
            self._state = ThermalPowerPlant._ShutDown(1)
            self._utilisation = 0.0
        else:
            assert isinstance(self._state, ThermalPowerPlant._Running)
            self._state = ThermalPowerPlant._ShutDown(1)
            self._utilisation = 0.0

    def _start_up(self) -> None:
        self._state = ThermalPowerPlant._StartingUp(phase=0)
