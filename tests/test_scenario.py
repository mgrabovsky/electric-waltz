from unittest import TestCase
from unittest.mock import Mock, PropertyMock

from electric_waltz.scenario import Scenario, ScenarioRun


class ScenarioTestCase(TestCase):
    def setUp(self):
        self.battery = Mock()
        self.nuclear = Mock()
        self.peaker = Mock()
        self.pv = Mock()

    def test_init(self):
        scenario = Scenario(
            demand=[],
            baseload_sources=[],
            flexible_sources=[],
            intermittent_sources=[],
            storage_units=[],
        )

        self.assertEqual(scenario.num_steps, 0)

    def test_init_nonempty(self):
        scenario = Scenario(
            demand=[111, 132, 145],
            baseload_sources=[],
            flexible_sources=[],
            intermittent_sources=[
                (self.pv, [0, .5, .4]),
            ],
            storage_units=[],
        )

        self.assertEqual(scenario.num_steps, 3)

    def test_init_wrong_dimensions(self):
        with self.assertRaises(ValueError):
            scenario = Scenario(
                demand=[111, 132, 145],
                baseload_sources=[],
                flexible_sources=[],
                intermittent_sources=[
                    (self.pv, [0, 0]),
                ],
                storage_units=[],
            )

    def test_init_invalid_cap_factor(self):
        with self.assertRaises(ValueError):
            scenario = Scenario(
                demand=[111, 132, 145],
                baseload_sources=[],
                flexible_sources=[],
                intermittent_sources=[
                    (self.pv, [0, .1, 50]),
                ],
                storage_units=[],
            )


class ScenarioRunTestCase(TestCase):
    def setUp(self):
        self.battery = Mock()
        self.nuclear = Mock()
        self.peaker = Mock()
        self.pv = Mock()

        self.out_battery = PropertyMock()
        self.ng_nuclear = PropertyMock()
        self.ng_peaker = PropertyMock()
        self.ng_pv = PropertyMock()

        type(self.battery).output = self.out_battery
        type(self.nuclear).net_generation = self.ng_nuclear
        type(self.peaker).net_generation = self.ng_peaker
        type(self.pv).net_generation = self.ng_pv

        type(self.battery).name = PropertyMock(return_value="battery")
        type(self.nuclear).name = PropertyMock(return_value="nuclear")
        type(self.peaker).name = PropertyMock(return_value="peaker")
        type(self.pv).name = PropertyMock(return_value="pv")

    def test_init(self):
        run = ScenarioRun([], [])
        self.assertEqual(run.steps, 0)

    def test_sweep_empty(self):
        run = ScenarioRun([], [])
        run.sweep()
        self.assertEqual(run.steps, 1)

    def test_sweep_nonempty(self):
        run = ScenarioRun(
            power_sources=[self.nuclear, self.pv, self.peaker],
            storage_units=[self.battery]
        )

        self.ng_nuclear.return_value = 100
        self.ng_pv.return_value = 50
        self.ng_peaker.return_value = 0
        self.out_battery.return_value = 20

        run.sweep()

        self.assertEqual(run.steps, 1)
        self.ng_nuclear.assert_called_once()
        self.ng_pv.assert_called_once()
        self.ng_peaker.assert_called_once()
        self.out_battery.assert_called_once()

    def test_compute_total_charging(self):
        run = ScenarioRun(
            power_sources=[self.nuclear, self.pv, self.peaker],
            storage_units=[self.battery]
        )

        self.ng_nuclear.return_value = 100
        self.ng_pv.return_value = 50
        self.ng_peaker.return_value = 0
        self.out_battery.side_effect = [0, -10, 5]

        run.sweep()
        run.sweep()
        run.sweep()

        self.assertEqual(run.steps, 3)
        self.assertEqual(run.compute_total_charging(), 10)

    def test_compute_total_discharging(self):
        run = ScenarioRun(
            power_sources=[self.nuclear, self.pv, self.peaker],
            storage_units=[self.battery]
        )

        self.ng_nuclear.return_value = 100
        self.ng_pv.return_value = 50
        self.ng_peaker.return_value = 0
        self.out_battery.side_effect = [0, -10, 5]

        run.sweep()
        run.sweep()
        run.sweep()

        self.assertEqual(run.steps, 3)
        self.assertEqual(run.compute_total_discharging(), 5)

    def test_count_charging_steps(self):
        run = ScenarioRun(
            power_sources=[self.nuclear, self.pv, self.peaker],
            storage_units=[self.battery]
        )

        battery_output = [0, 100, 50, 40, -20, -40, -100, 20]
        self.ng_nuclear.return_value = 100
        self.ng_pv.return_value = 50
        self.ng_peaker.return_value = 0
        self.out_battery.side_effect = battery_output

        for _ in battery_output:
            run.sweep()

        self.assertEqual(run.steps, len(battery_output))
        self.assertEqual(run.count_charging_steps(), 3)

    def test_count_discharging_steps(self):
        run = ScenarioRun(
            power_sources=[self.nuclear, self.pv, self.peaker],
            storage_units=[self.battery]
        )

        battery_output = [0, 100, 50, 40, -20, -40, -100, 20]
        self.ng_nuclear.return_value = 100
        self.ng_pv.return_value = 50
        self.ng_peaker.return_value = 0
        self.out_battery.side_effect = battery_output

        for _ in battery_output:
            run.sweep()

        self.assertEqual(run.steps, len(battery_output))
        self.assertEqual(run.count_discharging_steps(), 4)

    def test_count_generation_steps(self):
        run = ScenarioRun(
            power_sources=[self.nuclear, self.pv, self.peaker],
            storage_units=[self.battery]
        )

        self.ng_nuclear.side_effect = [100, 100, 100]
        self.ng_pv.side_effect = [50, 0, 40]
        self.ng_peaker.side_effect = [0, 20, 0]
        self.out_battery.return_value = 0

        run.sweep()
        run.sweep()
        run.sweep()

        self.assertEqual(run.count_generation_steps("nuclear"), 3)
        self.assertEqual(run.count_generation_steps("pv"), 2)
        self.assertEqual(run.count_generation_steps("peaker"), 1)
