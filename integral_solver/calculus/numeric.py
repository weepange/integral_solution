from __future__ import annotations
from integral_solver.core.ast import *
from integral_solver.core.parser import *
from integral_solver.calculus.numeric import *
from integral_solver.calculus.symbolic import *
from integral_solver.calculus.solvers import *

import math

import re

import ast

from dataclasses import dataclass

from fractions import Fraction

from typing import Iterable, Optional, Sequence



def evaluate(expr: Expr, var: str, value: float) -> float:
    return expr.substitute(var, value)

def to_expr(val: str | Expr | int | float) -> Expr:
    if isinstance(val, Expr):
        return val
    if isinstance(val, (int, float)):
        return Const(Fraction(str(val)).limit_denominator(1000000))
    if isinstance(val, str):
        return parse_expression(val)
    raise TypeError(f"Неподдерживаемый тип для конвертации в выражение: {type(val)}")

def evaluate_constant_expr(expr: Expr) -> float:
    if isinstance(expr, Const):
        return float(expr.value)
    if isinstance(expr, Var):
        if expr.name == "pi":
            return math.pi
        if expr.name == "e":
            return math.e
        raise ValueError(f"Неизвестная переменная при вычислении константы: {expr.name}")
    if isinstance(expr, Add):
        return sum(evaluate_constant_expr(term) for term in expr.terms)
    if isinstance(expr, Mul):
        val = 1.0
        for factor in expr.factors:
            val *= evaluate_constant_expr(factor)
        return val
    if isinstance(expr, Pow):
        return evaluate_constant_expr(expr.base) ** evaluate_constant_expr(expr.exponent)
    if isinstance(expr, Func):
        x = evaluate_constant_expr(expr.arg)
        if expr.name == "sin": return math.sin(x)
        if expr.name == "cos": return math.cos(x)
        if expr.name == "tan": return math.tan(x)
        if expr.name == "cot": return 1.0 / math.tan(x)
        if expr.name == "sec": return 1.0 / math.cos(x)
        if expr.name == "csc": return 1.0 / math.sin(x)
        if expr.name == "exp": return math.exp(x)
        if expr.name == "log": return math.log(abs(x))
        if expr.name == "sqrt": return math.sqrt(x)
        if expr.name == "abs": return abs(x)
        if expr.name == "asin": return math.asin(x)
        if expr.name == "acos": return math.acos(x)
        if expr.name == "atan": return math.atan(x)
    raise ValueError(f"Неподдерживаемая функция или выражение: {expr}")

def numerical_integrate(expr: Expr, var: str, lower: float, upper: float, steps: int = 1000) -> float:
    if steps % 2 != 0:
        steps += 1
    h = (upper - lower) / steps
    try:
        s = expr.substitute(var, lower) + expr.substitute(var, upper)
    except Exception:
        try:
            s = expr.substitute(var, lower + 1e-7) + expr.substitute(var, upper - 1e-7)
        except Exception:
            s = 0.0

    for i in range(1, steps):
        x = lower + i * h
        try:
            val = expr.substitute(var, x)
        except Exception:
            try:
                val = expr.substitute(var, x + 1e-9)
            except Exception:
                val = 0.0
        s += val * (4 if i % 2 != 0 else 2)
    return s * h / 3
