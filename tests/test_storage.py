from unittest import TestCase

from electric_waltz.storage import StorageAggregate


class StorageAggregateTestCase(TestCase):
    def test_remaining_capacity_initial(self):
        battery = StorageAggregate(capacity=1200, max_energy=6000)
        self.assertEqual(battery.remaining_capacity, 6000)

    def test_fully_charged_init(self):
        battery = StorageAggregate(capacity=1200, max_energy=1200)
        self.assertFalse(battery.fully_charged)

    def test_fully_charged_full(self):
        battery = StorageAggregate(capacity=1200, max_energy=1200)
        self.assertFalse(battery.fully_charged)
        battery.try_charge(1200)
        self.assertTrue(battery.fully_charged)

    def test_try_charge_empty(self):
        battery = StorageAggregate(capacity=1200, max_energy=6000)
        self.assertEqual(battery.remaining_capacity, 6000)
        overflow = battery.try_charge(500)
        self.assertEqual(battery.remaining_capacity, 5500)
        self.assertEqual(overflow, 0)

    def test_try_charge_full(self):
        battery = StorageAggregate(capacity=500, max_energy=500)
        self.assertEqual(battery.remaining_capacity, 500)

        overflow = battery.try_charge(500)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(overflow, 0)

        overflow = battery.try_charge(500)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(overflow, 500)

    def test_try_charge_nonfull(self):
        battery = StorageAggregate(capacity=500, max_energy=500)
        self.assertEqual(battery.remaining_capacity, 500)

        overflow = battery.try_charge(300)
        self.assertEqual(battery.remaining_capacity, 200)
        self.assertEqual(overflow, 0)

        overflow = battery.try_charge(300)
        self.assertEqual(battery.remaining_capacity, 0)
        self.assertEqual(overflow, 100)
