from unittest import TestCase

from electric_waltz.storage import EnergyStorage


class StorageAggregateTestCase(TestCase):
    def test_remaining_capacity_initial(self):
        battery = EnergyStorage(name="battery", nominal=1200, max_storage=6000)
        self.assertEqual(battery.remaining_capacity, 6000)
        self.assertEqual(battery.name, "battery")

    def test_charge_zero(self):
        battery = EnergyStorage(name="battery", nominal=500, max_storage=2000)
        self.assertEqual(battery.remaining_capacity, 2000)

        charging_power = battery.charge_at(0)
        self.assertEqual(battery.remaining_capacity, 2000)
        self.assertEqual(battery.output, 0)
        self.assertEqual(charging_power, 0)

    def test_charge_from_empty(self):
        battery = EnergyStorage(name="battery", nominal=1200, max_storage=6000)
        self.assertEqual(battery.remaining_capacity, 6000)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 5500)
        self.assertEqual(battery.output, -500)
        self.assertEqual(charging_power, 500)

        charging_power = battery.charge_at(1000)
        self.assertEqual(battery.remaining_capacity, 4500)
        self.assertEqual(battery.output, -1000)
        self.assertEqual(charging_power, 1000)

    def test_charge_when_full(self):
        battery = EnergyStorage(name="battery", nominal=500, max_storage=500)
        self.assertEqual(battery.remaining_capacity, 500)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(charging_power, 500)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(charging_power, 0)

    def test_charge_over_capacity(self):
        battery = EnergyStorage(name="battery", nominal=500, max_storage=2000)
        self.assertEqual(battery.remaining_capacity, 2000)

        charging_power = battery.charge_at(1000)
        self.assertEqual(battery.remaining_capacity, 1500)
        self.assertEqual(charging_power, 500)

        charging_power = battery.charge_at(1000)
        self.assertEqual(battery.remaining_capacity, 1000)
        self.assertEqual(charging_power, 500)

    def test_discharge_empty(self):
        battery = EnergyStorage(name="battery", nominal=500, max_storage=500)
        self.assertEqual(battery.remaining_capacity, 500)

        discharging_power = battery.discharge_at(100)
        self.assertEqual(battery.remaining_capacity, 500)
        self.assertEqual(battery.output, 0)
        self.assertEqual(discharging_power, 0)

    def test_discharge_full(self):
        battery = EnergyStorage(name="battery", nominal=500, max_storage=500)
        self.assertEqual(battery.remaining_capacity, 500)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(battery.output, -500)
        self.assertEqual(charging_power, 500)

        discharging_power = battery.discharge_at(500)
        self.assertEqual(battery.remaining_capacity, 500)
        self.assertEqual(battery.output, 500)
        self.assertEqual(discharging_power, 500)

    def test_discharge_over_capacity(self):
        battery = EnergyStorage(name="battery", nominal=500, max_storage=1000)
        self.assertEqual(battery.remaining_capacity, 1000)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 500)
        self.assertEqual(charging_power, 500)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(charging_power, 500)

        discharging_power = battery.discharge_at(1000)
        self.assertEqual(battery.remaining_capacity, 500)
        self.assertEqual(discharging_power, 500)

    def test_discharge_over_storage(self):
        battery = EnergyStorage(name="battery", nominal=500, max_storage=500)
        self.assertEqual(battery.remaining_capacity, 500)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(charging_power, 500)

        discharging_power = battery.discharge_at(300)
        self.assertEqual(battery.remaining_capacity, 300)
        self.assertEqual(discharging_power, 300)

        discharging_power = battery.discharge_at(300)
        self.assertEqual(battery.remaining_capacity, 500)
        self.assertEqual(discharging_power, 200)

    def test_imperfect_charge_from_empty(self):
        battery = EnergyStorage(name="battery", nominal=1000, max_storage=6000, efficiency=0.9)
        self.assertEqual(battery.remaining_capacity, 6000)

        charging_power = battery.charge_at(1000)
        self.assertEqual(battery.remaining_capacity, 5100)
        self.assertEqual(charging_power, 1000)

        charging_power = battery.charge_at(500)
        self.assertEqual(battery.remaining_capacity, 4650)
        self.assertEqual(charging_power, 500)