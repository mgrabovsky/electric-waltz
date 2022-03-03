from unittest import TestCase
from unittest.mock import Mock, PropertyMock

from electric_waltz.tracing import StatsCollector


class StatsCollectorTestCase(TestCase):
    def test_init(self):
        dispatcher = StatsCollector()

    def test_add_sweep_retrieve(self):
        pumped = Mock()
        p2g = Mock()
        wind = Mock()

        type(pumped).name = PropertyMock(return_value="pumped")
        type(p2g).name = PropertyMock(return_value="p2g")
        type(wind).name = PropertyMock(return_value="wind")

        type(pumped).output = PropertyMock(return_value=100)
        type(p2g).output = PropertyMock(return_value=200)
        type(wind).net_generation = PropertyMock(return_value=500)

        collector = StatsCollector()
        collector.add_power_sources([wind])
        collector.add_storage_units([pumped, p2g])

        collector.sweep()

        self.assertEqual(collector.get_storage_output("pumped"),
                         [100])
        self.assertEqual(collector.get_storage_output("p2g"),
                         [200])
        self.assertEqual(collector.get_source_generation("wind"),
                         [500])

        collector.sweep()

        self.assertEqual(collector.get_storage_output("pumped"),
                         [100, 100])
        self.assertEqual(collector.get_storage_output("p2g"),
                         [200, 200])
        self.assertEqual(collector.get_source_generation("wind"),
                         [500, 500])

        self.assertIsNone(collector.get_storage_output("hydrogen"))
        self.assertIsNone(collector.get_source_generation("photovoltaic"))