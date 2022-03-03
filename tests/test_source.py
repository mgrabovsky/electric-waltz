from unittest import TestCase

from electric_waltz.source import (
    DispatchableSource,
    NonDispatchableSource,
    PowerSource,
)


class DispatchableTestCase(TestCase):
    def test_init(self):
        ccgt = DispatchableSource(name="ccgt", nominal=500, self_consumption=0.2)
        self.assertEqual(ccgt.generation, 500)
        self.assertEqual(ccgt.name, "ccgt")

    def test_dispatch_zero(self):
        ccgt = DispatchableSource(name="ccgt", nominal=500, self_consumption=0.2)
        self.assertEqual(ccgt.generation, 500)
        self.assertEqual(ccgt.utilisation, 1)

        generation = ccgt.dispatch_at(0)
        self.assertEqual(generation, 0)
        self.assertEqual(ccgt.generation, 0)
        self.assertEqual(ccgt.utilisation, 0)

    def test_dispatch_midrange(self):
        ccgt = DispatchableSource(name="ccgt", nominal=500, self_consumption=0.2)
        self.assertEqual(ccgt.generation, 500)
        self.assertEqual(ccgt.utilisation, 1)

        generation = ccgt.dispatch_at(200)
        self.assertEqual(generation, 200)
        self.assertEqual(ccgt.generation, 250)
        self.assertEqual(ccgt.utilisation, 0.5)

    def test_dispatch_over_capacity(self):
        ccgt = DispatchableSource(name="ccgt", nominal=500, self_consumption=0.2)
        self.assertEqual(ccgt.generation, 500)
        self.assertEqual(ccgt.utilisation, 1)

        generation = ccgt.dispatch_at(999)
        self.assertEqual(generation, 400)
        self.assertEqual(ccgt.generation, 500)
        self.assertEqual(ccgt.utilisation, 1)

    def test_shut_down(self):
        ccgt = DispatchableSource(name="ccgt", nominal=500, self_consumption=0.1)
        self.assertEqual(ccgt.generation, 500)
        self.assertEqual(ccgt.utilisation, 1)

        ccgt.shut_down()
        self.assertEqual(ccgt.generation, 0)
        self.assertEqual(ccgt.utilisation, 0)


class NonDispatchableTestCase(TestCase):
    def test_init(self):
        pve = NonDispatchableSource(name="pve", nominal=500, self_consumption=0.2)
        self.assertEqual(pve.generation, 500)
        self.assertEqual(pve.net_generation, 400)


class PowerSourceTestCase(TestCase):
    def test_init_util_zero(self):
        source = PowerSource(name="generic", nominal=500, self_consumption=0, utilisation=0)
        self.assertEqual(source.generation, 0)
        self.assertEqual(source.net_generation, 0)
        self.assertEqual(source.utilisation, 0)

    def test_init_perfect_util_half(self):
        source = PowerSource(name="generic", nominal=500, self_consumption=0, utilisation=0.5)
        self.assertEqual(source.generation, 250)
        self.assertEqual(source.net_generation, 250)
        self.assertEqual(source.utilisation, 0.5)

    def test_init_perfect_util_full(self):
        source = PowerSource(name="generic", nominal=500, self_consumption=0, utilisation=1)
        self.assertEqual(source.generation, 500)
        self.assertEqual(source.net_generation, 500)
        self.assertEqual(source.utilisation, 1)

    def test_init_imperfect_util_half(self):
        source = PowerSource(name="generic", nominal=1000, self_consumption=0.1, utilisation=0.5)
        self.assertEqual(source.generation, 500)
        self.assertEqual(source.net_generation, 450)
        self.assertEqual(source.utilisation, 0.5)

    def test_init_imperfect_util_full(self):
        source = PowerSource(name="generic", nominal=1000, self_consumption=0.1, utilisation=1)
        self.assertEqual(source.generation, 1000)
        self.assertEqual(source.net_generation, 900)
        self.assertEqual(source.utilisation, 1)

    def test_utilisation_setter(self):
        source = PowerSource(name="generic", nominal=1000, self_consumption=0.1, utilisation=1)
        self.assertEqual(source.generation, 1000)

        source.utilisation = 0.2
        self.assertEqual(source.generation, 200)
        self.assertEqual(source.net_generation, 180)

        source.utilisation = 0.9
        self.assertEqual(source.generation, 900)
        self.assertEqual(source.net_generation, 810)