"""
Objects for representing electricity storage units and aggregates within
the grid.
"""

from .types import Energy, Power

__all__ = [
    "EnergyStorage",
]


class EnergyStorage:
    """
    An object representing the aggregate storage capaciticies of a single
    kind of storage.
    """

    def __init__(
        self,
        name: str,
        nominal: Power,
        max_storage: Energy,
        efficiency: float = 1.0,
    ) -> None:
        """
        Arguments:
            name : Short textual identifier of the storage aggregate, e.g. "p2g"
                or "pumped".
            capacity : Nominal (installed) capacity of the storage unit in MW.
            max_storage : Maximum stored energy in MWh.
            efficiency : Efficiency of conversion during charging, a number in the
                interval (0.0,1.0]. In the current implementation, this is the same
                as the round-trip efficiency.
        """
        assert 0 < len(name)
        assert 0 < nominal
        assert 0 < max_storage
        assert 0 < efficiency <= 1

        self._name = name
        self._nominal_capacity = nominal
        self._max_storage = max_storage
        self._efficiency = efficiency

        self._current_energy: Energy = 0.0
        self._current_output: Power = 0.0

    def charge_at(self, power: Power) -> Power:
        """
        Try charging the storage unit with up to `power` MW.

        Arguments:
            power : Power that is available for charging in MW.

        Returns:
            Effective charging power in MW.
        """
        assert power >= 0

        # Effective charging power is limited by the lest of nominal capacity and the
        # remaining storage capacity. Note that we may treat MW = MWh as we assume
        # hourly steps.
        charging = min(power, self._nominal_capacity, self.remaining_capacity)
        self._current_energy += self._efficiency * charging
        self._current_output = -charging

        assert self._current_energy <= self._max_storage
        return charging

    def discharge_at(self, power: Power) -> Power:
        """
        Try discharging the storage unit up to `required` MW.

        Arguments:
            power : Power that is requested to be discharged in MW.

        Returns:
            Effective discharging power in MW.
        """
        assert power >= 0

        # If required energy is more than we have stored, discharge as much
        # as we can, subject to nominal power and accumulated capacity.
        # If required power is bigger than what we can provide instantaneously,
        # discharge at nominal only.
        discharging = min(power, self._current_energy, self._nominal_capacity)
        self._current_energy -= discharging
        self._current_output = discharging

        assert self._current_energy >= 0
        return discharging

    @property
    def name(self) -> str:
        """Return the storage aggregate's textual identifier."""
        return self._name

    @property
    def output(self) -> Power:
        """
        Return the current power output in MW. Negative if charging, positive if
        discharging.
        """
        return self._current_output

    @property
    def remaining_capacity(self) -> Energy:
        """Return the amount of remaining energy storage capacity in MWh."""
        return self._max_storage - self._current_energy
