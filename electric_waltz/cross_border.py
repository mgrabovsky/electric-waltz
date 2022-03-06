"""
Objects for cross-border electricity transmission, i.e. import and export.
"""

from .types import Power

__all__ = ["CrossBorderTerminal"]

class CrossBorderTerminal:
    """
    General class for any kind of cross-border transmission device.
    Used for accounting for cross-border import and export of electricity.
    """

    def __init__(self, capacity: Power) -> None:
        """
        Arguments:
            capacity : Nominal maximum capacity of the terminal in MW.
        """
        self._capacity = capacity
        self._net_import: Power = 0

    def export_at(self, power: Power) -> Power:
        """
        Request the export of at most `power` MW of electricity through the terminal.

        Arguments:
            power : Requested power in MW.

        Returns:
            Net exported power after the adjustment.
        """
        assert power >= 0

        self._net_import = -min(self._capacity, power)
        return -self._net_import

    def import_at(self, power: Power) -> Power:
        """
        Request the import of at most `power` MW of electricity through the terminal.

        Arguments:
            power : Requested power in MW.

        Returns:
            Net imported power after the adjustment.
        """
        assert power >= 0

        self._net_import = min(self._capacity, power)
        return self._net_import

    @property
    def net_import(self) -> Power:
        """
        Return net imported power. This value is negative if export dominates.
        """
        return self._net_import
