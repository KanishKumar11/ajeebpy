"""Arithmetic and unit conversion, done without ``eval``.

``eval`` on anything a microphone heard is a remote-code-execution hole. The
expression is parsed with :mod:`ast` instead and only a whitelist of nodes is
allowed to run, so "2 + 2" works and "__import__('os').system(...)" does not.
"""

from __future__ import annotations

import ast
import math
import operator
import re

__all__ = ["CalcError", "evaluate", "convert", "UNITS", "describe_units"]


class CalcError(ValueError):
    """The expression could not be worked out (and why)."""


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
}
_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

# Spoken arithmetic -> symbols. Order matters: longest phrase first.
_SPOKEN = [
    (r"\bdivided by\b", "/"),
    (r"\bmultiplied by\b", "*"),
    (r"\bto the power of\b", "**"),
    (r"\bsquare root of\b", "sqrt"),
    (r"\bcube root of\b", "cbrt"),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\btimes\b", "*"),
    (r"\bover\b", "/"),
    (r"\bmod(?:ulo)?\b", "%"),
    (r"\bx\b", "*"),
    (r"[×✕]", "*"),
    (r"[÷]", "/"),
    (r"\^", "**"),
    (r",(?=\d{3}\b)", ""),
]

_PERCENT_OF = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s+(?:of|off)\s+")
# A bare "%" is only a percentage when a number does NOT follow it:
# "15%" is fifteen percent, but "7 % 3" is the modulo operator.
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%(?!\s*\d)|percent)")
_SQUARED = re.compile(r"(\w+|\))\s+squared\b")
_CUBED = re.compile(r"(\w+|\))\s+cubed\b")
_MAX_POWER = 10_000  # keeps 9**9**9 from wedging the process


def _prepare(expression: str) -> str:
    text = expression.strip().lower()
    text = re.sub(r"^(?:what(?:'?s| is)|calculate|compute|work out|solve)\s+", "", text)
    text = _SQUARED.sub(r"(\1)**2", text)
    text = _CUBED.sub(r"(\1)**3", text)
    text = _PERCENT_OF.sub(r"(\1/100)*", text)
    text = _PERCENT.sub(r"(\1/100)", text)
    for pattern, replacement in _SPOKEN:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"sqrt\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", text)
    text = re.sub(r"cbrt\s*(\d+(?:\.\d+)?)", r"cbrt(\1)", text)
    return text.strip(" =?")


def evaluate(expression: str) -> float:
    """Work out ``expression``. Raises :class:`CalcError` on anything unsafe."""
    prepared = _prepare(expression)
    if not prepared:
        raise CalcError("There was nothing to calculate.")
    try:
        tree = ast.parse(prepared, mode="eval")
    except SyntaxError as exc:
        raise CalcError(f"I could not read {expression.strip()!r} as a sum.") from exc

    try:
        return _eval(tree.body)
    except CalcError:
        raise
    except ZeroDivisionError as exc:
        raise CalcError("I cannot divide by zero.") from exc
    except (ValueError, OverflowError, TypeError) as exc:
        raise CalcError(f"That sum does not work out ({exc}).") from exc


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalcError("Only numbers, please.")
        return node.value
    if isinstance(node, ast.BinOp):
        handler = _BINARY.get(type(node.op))
        if handler is None:
            raise CalcError("That operator is not allowed.")
        left, right = _eval(node.left), _eval(node.right)
        if handler is operator.pow and (abs(right) > _MAX_POWER or abs(left) > _MAX_POWER):
            raise CalcError("That power is far too big for me.")
        return handler(left, right)
    if isinstance(node, ast.UnaryOp):
        handler = _UNARY.get(type(node.op))
        if handler is None:
            raise CalcError("That operator is not allowed.")
        return handler(_eval(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise CalcError(f"I do not know what {node.id!r} is.")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise CalcError("I can only use basic maths functions.")
        if node.keywords:
            raise CalcError("I cannot use keyword arguments in a sum.")
        return _FUNCTIONS[node.func.id](*(_eval(arg) for arg in node.args))
    raise CalcError("That is not a sum I can safely work out.")


# --------------------------------------------------------------------------- #
# Unit conversion (offline: a table, not a web service)
# --------------------------------------------------------------------------- #

# family -> {canonical unit: (factor to the family's base unit, spoken name)}
UNITS: dict[str, dict[str, tuple[float, str]]] = {
    "length": {
        "mm": (0.001, "millimetres"),
        "cm": (0.01, "centimetres"),
        "m": (1.0, "metres"),
        "km": (1000.0, "kilometres"),
        "in": (0.0254, "inches"),
        "ft": (0.3048, "feet"),
        "yd": (0.9144, "yards"),
        "mi": (1609.344, "miles"),
        "nmi": (1852.0, "nautical miles"),
    },
    "mass": {
        "mg": (1e-6, "milligrams"),
        "g": (0.001, "grams"),
        "kg": (1.0, "kilograms"),
        "t": (1000.0, "tonnes"),
        "oz": (0.028349523125, "ounces"),
        "lb": (0.45359237, "pounds"),
        "st": (6.35029318, "stone"),
    },
    "volume": {
        "ml": (0.001, "millilitres"),
        "l": (1.0, "litres"),
        "cup": (0.2365882365, "cups"),
        "pt": (0.473176473, "pints"),
        "qt": (0.946352946, "quarts"),
        "gal": (3.785411784, "gallons"),
    },
    "speed": {
        "mps": (1.0, "metres per second"),
        "kph": (0.2777777778, "kilometres per hour"),
        "mph": (0.44704, "miles per hour"),
        "kn": (0.5144444444, "knots"),
    },
    "data": {
        "b": (1.0, "bytes"),
        "kb": (1024.0, "kilobytes"),
        "mb": (1024.0**2, "megabytes"),
        "gb": (1024.0**3, "gigabytes"),
        "tb": (1024.0**4, "terabytes"),
    },
    "time": {
        "s": (1.0, "seconds"),
        "min": (60.0, "minutes"),
        "h": (3600.0, "hours"),
        "d": (86400.0, "days"),
        "wk": (604800.0, "weeks"),
        "yr": (31557600.0, "years"),
    },
}

_ALIASES = {
    "millimetre": "mm", "millimeter": "mm", "millimetres": "mm", "millimeters": "mm",
    "centimetre": "cm", "centimeter": "cm", "centimetres": "cm", "centimeters": "cm",
    "metre": "m", "meter": "m", "metres": "m", "meters": "m",
    "kilometre": "km", "kilometer": "km", "kilometres": "km", "kilometers": "km", "kms": "km",
    "inch": "in", "inches": "in", "foot": "ft", "feet": "ft", "yard": "yd", "yards": "yd",
    "mile": "mi", "miles": "mi", "nautical mile": "nmi", "nautical miles": "nmi",
    "milligram": "mg", "milligrams": "mg", "gram": "g", "grams": "g",
    "kilogram": "kg", "kilograms": "kg", "kilo": "kg", "kilos": "kg",
    "tonne": "t", "tonnes": "t", "ton": "t", "tons": "t",
    "ounce": "oz", "ounces": "oz", "pound": "lb", "pounds": "lb", "lbs": "lb",
    "stone": "st", "millilitre": "ml", "milliliter": "ml", "millilitres": "ml",
    "litre": "l", "liter": "l", "litres": "l", "liters": "l",
    "cups": "cup", "pint": "pt", "pints": "pt", "quart": "qt", "quarts": "qt",
    "gallon": "gal", "gallons": "gal",
    "metres per second": "mps", "meters per second": "mps", "m/s": "mps",
    "kilometres per hour": "kph", "kilometers per hour": "kph", "km/h": "kph", "kmph": "kph",
    "miles per hour": "mph", "mi/h": "mph", "knot": "kn", "knots": "kn",
    "byte": "b", "bytes": "b", "kilobyte": "kb", "kilobytes": "kb",
    "megabyte": "mb", "megabytes": "mb", "gigabyte": "gb", "gigabytes": "gb",
    "terabyte": "tb", "terabytes": "tb",
    "second": "s", "seconds": "s", "sec": "s", "secs": "s",
    "minute": "min", "minutes": "min", "mins": "min",
    "hour": "h", "hours": "h", "hr": "h", "hrs": "h",
    "day": "d", "days": "d", "week": "wk", "weeks": "wk", "year": "yr", "years": "yr",
    "celsius": "c", "centigrade": "c", "°c": "c", "fahrenheit": "f", "°f": "f",
    "kelvin": "k", "°k": "k",
}

_TEMPERATURE = {"c", "f", "k"}


def _canonical(unit: str) -> str:
    cleaned = unit.strip().lower().rstrip(".")
    return _ALIASES.get(cleaned, cleaned)


def _to_celsius(value: float, unit: str) -> float:
    return {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[unit]


def _from_celsius(value: float, unit: str) -> float:
    return {"c": value, "f": value * 9 / 5 + 32, "k": value + 273.15}[unit]


def convert(value: float, source: str, target: str) -> tuple[float, str]:
    """Convert ``value`` between units. Returns the amount and a spoken unit name."""
    src, dst = _canonical(source), _canonical(target)

    if src in _TEMPERATURE or dst in _TEMPERATURE:
        if src not in _TEMPERATURE or dst not in _TEMPERATURE:
            raise CalcError(f"I cannot turn {source} into {target}.")
        spoken = {"c": "degrees celsius", "f": "degrees fahrenheit", "k": "kelvin"}[dst]
        return _from_celsius(_to_celsius(value, src), dst), spoken

    for family in UNITS.values():
        if src in family and dst in family:
            result = value * family[src][0] / family[dst][0]
            return result, family[dst][1]

    known = src in _ALIASES.values() or any(src in family for family in UNITS.values())
    if not known:
        raise CalcError(f"I do not know the unit {source!r}.")
    raise CalcError(f"I cannot turn {source} into {target} -- they measure different things.")


def describe_units() -> str:
    """Human-readable list of what can be converted, for the help text."""
    return "; ".join(f"{family}: {', '.join(units)}" for family, units in UNITS.items())
