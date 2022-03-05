from unittest import TestCase

from electric_waltz.cross_border import CrossBorderTerminal


class CrossBorderTerminalTestCase(TestCase):
    def test_init(self):
        term = CrossBorderTerminal(capacity=5000)
        self.assertEqual(term.net_import, 0)

    def test_export_at_zero(self):
        term = CrossBorderTerminal(capacity=5000)
        export_power = term.export_at(0)
        self.assertEqual(export_power, 0)
        self.assertEqual(term.net_import, 0)

    def test_export_at_some(self):
        term = CrossBorderTerminal(capacity=5000)
        export_power = term.export_at(1000)
        self.assertEqual(export_power, 1000)
        self.assertEqual(term.net_import, -1000)

    def test_export_at_full(self):
        term = CrossBorderTerminal(capacity=5000)
        export_power = term.export_at(5000)
        self.assertEqual(export_power, 5000)
        self.assertEqual(term.net_import, -5000)

    def test_export_at_over_capacity(self):
        term = CrossBorderTerminal(capacity=5000)
        export_power = term.export_at(6000)
        self.assertEqual(export_power, 5000)
        self.assertEqual(term.net_import, -5000)

    def test_import_at_zero(self):
        term = CrossBorderTerminal(capacity=5000)
        import_power = term.import_at(0)
        self.assertEqual(term.net_import, 0)

    def test_import_at_some(self):
        term = CrossBorderTerminal(capacity=5000)
        import_power = term.import_at(1000)
        self.assertEqual(import_power, 1000)
        self.assertEqual(term.net_import, 1000)

    def test_export_at_full(self):
        term = CrossBorderTerminal(capacity=5000)
        import_power = term.import_at(5000)
        self.assertEqual(import_power, 5000)
        self.assertEqual(term.net_import, 5000)

    def test_import_at_over_capacity(self):
        term = CrossBorderTerminal(capacity=5000)
        import_power = term.import_at(6000)
        self.assertEqual(import_power, 5000)
        self.assertEqual(term.net_import, 5000)

    def test_export_import(self):
        term = CrossBorderTerminal(capacity=5000)
        term.export_at(4000)
        term.import_at(3000)
        self.assertEqual(term.net_import, 3000)
