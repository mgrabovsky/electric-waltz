from unittest import TestCase

from electric_waltz import call_me


class CallMeTestCase(TestCase):
    def test_call_me(self):
        self.assertEqual(call_me("Jára"), 12345)
