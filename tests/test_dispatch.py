from unittest import TestCase
from unittest.mock import Mock

from electric_waltz.dispatch import SourceDispatcher, StorageDispatcher


class SourceDispatcherTestCase(TestCase):
    def setUp(self):
        self.biomass = Mock()
        self.ccgt = Mock()
        self.hydro = Mock()

    def test_init(self):
        dispatcher = SourceDispatcher([self.hydro, self.biomass, self.ccgt])

    def test_shut_down(self):
        dispatcher = SourceDispatcher([self.hydro, self.biomass, self.ccgt])

        dispatcher.shut_down_all()

        self.hydro.shut_down.assert_called_once()
        self.biomass.shut_down.assert_called_once()
        self.ccgt.shut_down.assert_called_once()

    def test_dispatch_zero(self):
        dispatcher = SourceDispatcher([self.hydro, self.biomass, self.ccgt])

        self.hydro.dispatch_at.return_value = 0
        self.biomass.dispatch_at.return_value = 0
        self.ccgt.dispatch_at.return_value = 0

        generation = dispatcher.dispatch_at(0)
        self.assertEqual(generation, 0)

        self.hydro.dispatch_at.assert_called_once_with(0)
        self.biomass.dispatch_at.assert_called_once_with(0)
        self.ccgt.dispatch_at.assert_called_once_with(0)

    def test_dispatch_one_unit(self):
        dispatcher = SourceDispatcher([self.hydro, self.biomass, self.ccgt])

        self.hydro.dispatch_at.return_value = 800
        self.biomass.dispatch_at.return_value = 0
        self.ccgt.dispatch_at.return_value = 0

        generation = dispatcher.dispatch_at(800)
        self.assertEqual(generation, 800)

        self.hydro.dispatch_at.assert_called_once_with(800)
        self.biomass.dispatch_at.assert_called_once_with(0)
        self.ccgt.dispatch_at.assert_called_once_with(0)

    def test_dispatch_all_units(self):
        dispatcher = SourceDispatcher([self.hydro, self.biomass, self.ccgt])

        self.hydro.dispatch_at.return_value = 400
        self.biomass.dispatch_at.return_value = 400
        self.ccgt.dispatch_at.return_value = 200

        generation = dispatcher.dispatch_at(1000)
        self.assertEqual(generation, 1000)

        self.hydro.dispatch_at.assert_called_once_with(1000)
        self.biomass.dispatch_at.assert_called_once_with(600)
        self.ccgt.dispatch_at.assert_called_once_with(200)

    def test_dispatch_all_units_over(self):
        dispatcher = SourceDispatcher([self.hydro, self.biomass, self.ccgt])

        self.hydro.dispatch_at.return_value = 100
        self.biomass.dispatch_at.return_value = 100
        self.ccgt.dispatch_at.return_value = 100

        generation = dispatcher.dispatch_at(1000)
        self.assertEqual(generation, 300)

        self.hydro.dispatch_at.assert_called_once_with(1000)
        self.biomass.dispatch_at.assert_called_once_with(900)
        self.ccgt.dispatch_at.assert_called_once_with(800)


class StorageDispatcherTestCase(TestCase):
    def setUp(self):
        self.battery = Mock()
        self.pumped = Mock()
        self.p2g = Mock()

    def test_init(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

    def test_charge_zero(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.charge_at.return_value = 0
        self.battery.charge_at.return_value = 0
        self.p2g.charge_at.return_value = 0

        charging = dispatcher.charge_at(0)
        self.assertEqual(charging, 0)

        self.pumped.charge_at.assert_called_once_with(0)
        self.battery.charge_at.assert_called_once_with(0)
        self.p2g.charge_at.assert_called_once_with(0)

    def test_charge_one_unit(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.charge_at.return_value = 500
        self.battery.charge_at.return_value = 0
        self.p2g.charge_at.return_value = 0

        charging = dispatcher.charge_at(500)
        self.assertEqual(charging, 500)

        self.pumped.charge_at.assert_called_once_with(500)
        self.battery.charge_at.assert_called_once_with(0)
        self.p2g.charge_at.assert_called_once_with(0)

    def test_charge_all_units(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.charge_at.return_value = 500
        self.battery.charge_at.return_value = 200
        self.p2g.charge_at.return_value = 300

        charging = dispatcher.charge_at(1000)
        self.assertEqual(charging, 1000)

        self.pumped.charge_at.assert_called_once_with(1000)
        self.battery.charge_at.assert_called_once_with(500)
        self.p2g.charge_at.assert_called_once_with(300)

    def test_charge_all_units_over(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.charge_at.return_value = 500
        self.battery.charge_at.return_value = 200
        self.p2g.charge_at.return_value = 300

        charging = dispatcher.charge_at(2000)
        self.assertEqual(charging, 1000)

        self.pumped.charge_at.assert_called_once_with(2000)
        self.battery.charge_at.assert_called_once_with(1500)
        self.p2g.charge_at.assert_called_once_with(1300)

    def test_discharge_zero(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.discharge_at.return_value = 0
        self.battery.discharge_at.return_value = 0
        self.p2g.discharge_at.return_value = 0

        charging = dispatcher.discharge_at(0)
        self.assertEqual(charging, 0)

        self.pumped.discharge_at.assert_called_once_with(0)
        self.battery.discharge_at.assert_called_once_with(0)
        self.p2g.discharge_at.assert_called_once_with(0)

    def test_discharge_one_unit(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.discharge_at.return_value = 500
        self.battery.discharge_at.return_value = 0
        self.p2g.discharge_at.return_value = 0

        charging = dispatcher.discharge_at(500)
        self.assertEqual(charging, 500)

        self.pumped.discharge_at.assert_called_once_with(500)
        self.battery.discharge_at.assert_called_once_with(0)
        self.p2g.discharge_at.assert_called_once_with(0)

    def test_discharge_all_units(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.discharge_at.return_value = 500
        self.battery.discharge_at.return_value = 200
        self.p2g.discharge_at.return_value = 300

        charging = dispatcher.discharge_at(1000)
        self.assertEqual(charging, 1000)

        self.pumped.discharge_at.assert_called_once_with(1000)
        self.battery.discharge_at.assert_called_once_with(500)
        self.p2g.discharge_at.assert_called_once_with(300)

    def test_discharge_all_units_over(self):
        dispatcher = StorageDispatcher([self.pumped, self.battery, self.p2g])

        self.pumped.discharge_at.return_value = 500
        self.battery.discharge_at.return_value = 200
        self.p2g.discharge_at.return_value = 300

        charging = dispatcher.discharge_at(2000)
        self.assertEqual(charging, 1000)

        self.pumped.discharge_at.assert_called_once_with(2000)
        self.battery.discharge_at.assert_called_once_with(1500)
        self.p2g.discharge_at.assert_called_once_with(1300)