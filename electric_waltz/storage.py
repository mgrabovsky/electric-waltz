"""
Objects and functions for electricity storage.
"""


class StorageAggregate:
    """
    An object representing the aggregate storage capaciticies of a single
    kind of storage.
    """

    def __init__(
        self, capacity: float, max_energy: float, efficiency: float = 1.0
    ) -> None:
        """
        Arguments:
          capacity -- nominal installed capacity in MW
          max_energy -- maximum stored energy in MWh
          efficiency -- efficiency of round-trip conversion, a number in the
            interval (0.0,1.0]
        """
        assert 0 < capacity
        assert 0 < max_energy
        assert 0 < efficiency <= 1

        self._capacity = capacity
        self._max_energy = max_energy
        self._efficiency = efficiency

        self._energy: float = 0.0

    @property
    def fully_charged(self) -> bool:
        """Return True if the storage is charged to 100% of its capacity."""
        return self._energy == self._max_energy

    @property
    def remaining_capacity(self) -> float:
        """Return the amount of remaining energy storage capacity in MWh."""
        return self._max_energy - self._energy

    def try_charge(self, energy: float) -> float:
        """Return True if the storage is charged to 100% of its capacity."""
        # TODO: Also check self.capacity?
        if self.fully_charged:
            # We can take no more.
            return energy

        if energy > self.remaining_capacity:
            # Take what we can and return the rest.
            overflow = energy - self.remaining_capacity
            self._energy = self._max_energy
            return overflow

        assert energy <= self.remaining_capacity
        self._energy += energy
        return 0
