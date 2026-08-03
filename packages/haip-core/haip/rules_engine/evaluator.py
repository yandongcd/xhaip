"""Expression evaluator — evaluates clinical rule conditions.

Ported from haip-0710's src/agents/rules/expr_evaluator.py.

Supports:
    - Comparison operators: ==, !=, >, <, >=, <=
    - Range expressions: 10 <= age <= 80
    - IN expressions: gender IN [M, F]
    - AND / OR composition
    - Custom callback functions ($name(args))
"""

from __future__ import annotations

import operator
import re
from collections.abc import Callable

from haip.rules_engine.models import EvaluationContext

_CALLBACKS: dict[str, Callable[..., bool]] = {}


def register_callback(name: str, fn: Callable[..., bool]):
    """Register a custom callback function for $name(args) syntax."""
    _CALLBACKS[name] = fn


def get_callback(name: str) -> Callable[..., bool] | None:
    return _CALLBACKS.get(name)


_CMP_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

_RE_IN = re.compile(r"^(?P<field>\S+)\s+IN\s+\[(?P<values>[^\]]+)\]$", re.IGNORECASE)
_RE_RANGE = re.compile(
    r"^\s*(?P<lhs>\d+(\.\d+)?)\s*(?P<op1><=|>=|<|>)\s*(?P<var>\S+)\s*(?P<op2><=|>=|<|>)\s*(?P<rhs>\d+(\.\d+)?)\s*$"
)


def _strip_context_prefix(field: str) -> str:
    if field.startswith("context."):
        return field[len("context."):]
    return field


def evaluate(expr: str, context: EvaluationContext) -> bool:
    """Evaluate a rule condition expression against a context.

    Examples:
        evaluate("age >= 65", ctx)
        evaluate("gender IN [M, F] AND crp > 100", ctx)
        evaluate("$is_diabetic(patient_id)", ctx)
    """
    expr = expr.strip()
    if not expr:
        return True

    # Callback functions: $name(args)
    if expr.startswith("$"):
        return _eval_callback(expr, context)

    # OR (lower precedence)
    if " OR " in expr.upper():
        parts = re.split(r"\s+OR\s+", expr, flags=re.IGNORECASE)
        return any(evaluate(p.strip(), context) for p in parts)

    # AND (higher precedence)
    if " AND " in expr.upper():
        parts = re.split(r"\s+AND\s+", expr, flags=re.IGNORECASE)
        return all(evaluate(p.strip(), context) for p in parts)

    # Range expression: 10 <= age <= 80
    m = _RE_RANGE.match(expr)
    if m:
        lhs_val = float(m.group("lhs"))
        var_path = _strip_context_prefix(m.group("var").strip())
        rhs_val = float(m.group("rhs"))
        op1 = m.group("op1")
        op2 = m.group("op2")
        actual = context.get(var_path)
        if actual is None:
            return False
        try:
            actual_f = float(actual)
        except (ValueError, TypeError):
            return False
        c1 = _CMP_OPS[op1](lhs_val, actual_f)
        c2 = _CMP_OPS[op2](actual_f, rhs_val)
        return c1 and c2

    # IN expression: field IN [value1, value2]
    m = _RE_IN.match(expr)
    if m:
        field = _strip_context_prefix(m.group("field").strip())
        values = [v.strip().strip("'\"") for v in m.group("values").split(",")]
        actual = context.get(field)
        if actual is None:
            return False
        return str(actual) in values

    # Simple comparison: field OP value
    for sym in ("!=", "<=", ">=", "==", ">", "<"):
        if sym in expr:
            parts = expr.split(sym, 1)
            field = _strip_context_prefix(parts[0].strip())
            rhs = parts[1].strip().strip("'\"")

            actual = context.get(field)
            if actual is None:
                return False

            try:
                actual_f = float(actual)
                rhs_f = float(rhs)
                return _CMP_OPS[sym](actual_f, rhs_f)
            except (ValueError, TypeError):
                return _CMP_OPS[sym](str(actual).lower(), rhs.lower())

    return False


def _eval_callback(expr: str, context: EvaluationContext) -> bool:
    m = re.match(r"^\$(?P<name>\w+)\((?P<args>[^)]*)\)$", expr)
    if not m:
        return False
    name = m.group("name")
    args_str = m.group("args").strip()
    fn = get_callback(name)
    if fn is None:
        return False
    args = [a.strip().strip("'\"") for a in args_str.split(",") if a.strip()]
    resolved = []
    for a in args:
        if a.startswith("$"):
            resolved.append(a)
        else:
            resolved.append(context.get(_strip_context_prefix(a)) or a)
    return fn(*resolved)
