"""Arithmetic and unit conversion, including the things that must NOT run."""

from __future__ import annotations

import unittest

from ajeeb.calc import CalcError, convert, evaluate


class ArithmeticTests(unittest.TestCase):
    def test_plain_sums(self):
        for expression, expected in [
            ("2+2", 4),
            ("(3+4)*2", 14),
            ("10 - 3 - 2", 5),
            ("2 ** 5", 32),
            ("7 % 3", 1),
        ]:
            with self.subTest(expression=expression):
                self.assertEqual(evaluate(expression), expected)

    def test_spoken_arithmetic(self):
        self.assertEqual(evaluate("12 times 8"), 96)
        self.assertEqual(evaluate("100 divided by 4"), 25)
        self.assertEqual(evaluate("7 plus 3 minus 2"), 8)
        self.assertEqual(evaluate("5 squared"), 25)
        self.assertEqual(evaluate("square root of 144"), 12)

    def test_percentages(self):
        self.assertEqual(evaluate("15% of 240"), 36)
        self.assertAlmostEqual(evaluate("20 percent of 50"), 10)

    def test_leading_question_words_are_ignored(self):
        self.assertEqual(evaluate("what is 6 * 7"), 42)
        self.assertEqual(evaluate("calculate 6*7"), 42)

    def test_thousands_separators(self):
        self.assertEqual(evaluate("1,234 + 1"), 1235)

    def test_constants_and_functions(self):
        self.assertAlmostEqual(evaluate("round(pi, 2)"), 3.14)
        self.assertEqual(evaluate("max(3, 9)"), 9)


class SafetyTests(unittest.TestCase):
    """The expression comes from a microphone; ``eval`` would be a hole."""

    def test_imports_and_calls_are_refused(self):
        for hostile in [
            "__import__('os').system('echo pwned')",
            "open('/etc/passwd').read()",
            "().__class__.__bases__",
            "exec('x=1')",
            "[x for x in range(10)]",
        ]:
            with self.subTest(hostile=hostile), self.assertRaises(CalcError):
                evaluate(hostile)

    def test_a_huge_power_is_refused_rather_than_hanging(self):
        with self.assertRaises(CalcError):
            evaluate("9 ** 9 ** 9")

    def test_division_by_zero_is_explained(self):
        with self.assertRaises(CalcError) as caught:
            evaluate("1/0")
        self.assertIn("divide by zero", str(caught.exception))

    def test_prose_is_rejected(self):
        with self.assertRaises(CalcError):
            evaluate("hello world")

    def test_empty_input_is_rejected(self):
        with self.assertRaises(CalcError):
            evaluate("   ")


class ConversionTests(unittest.TestCase):
    def test_length(self):
        value, unit = convert(10, "km", "miles")
        self.assertAlmostEqual(value, 6.2137, places=3)
        self.assertEqual(unit, "miles")

    def test_temperature_is_not_a_simple_factor(self):
        self.assertAlmostEqual(convert(100, "f", "c")[0], 37.7778, places=3)
        self.assertAlmostEqual(convert(0, "c", "k")[0], 273.15, places=2)
        self.assertAlmostEqual(convert(0, "c", "f")[0], 32.0, places=2)

    def test_aliases_and_plurals(self):
        self.assertAlmostEqual(convert(5, "kilograms", "pounds")[0], 11.0231, places=3)
        self.assertAlmostEqual(convert(2, "hours", "minutes")[0], 120)

    def test_data_sizes_use_binary_multiples(self):
        self.assertEqual(convert(1, "gb", "mb")[0], 1024)

    def test_mixing_families_is_refused(self):
        with self.assertRaises(CalcError) as caught:
            convert(1, "km", "kg")
        self.assertIn("different things", str(caught.exception))

    def test_unknown_units_are_reported(self):
        with self.assertRaises(CalcError) as caught:
            convert(1, "blorps", "m")
        self.assertIn("do not know", str(caught.exception))

    def test_temperature_cannot_become_a_length(self):
        with self.assertRaises(CalcError):
            convert(1, "c", "km")


if __name__ == "__main__":
    unittest.main()
