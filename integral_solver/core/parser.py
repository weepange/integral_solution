from __future__ import annotations
from integral_solver.core.ast import *

import math

import re

import ast

from dataclasses import dataclass

from fractions import Fraction

from typing import Iterable, Optional, Sequence



FUNCTION_NAMES = {
    "sin",
    "cos",
    "tan",
    "cot",
    "sec",
    "csc",
    "exp",
    "log",
    "sqrt",
    "abs",
    "asin",
    "acos",
    "atan",
}

CONSTANT_NAMES = {
    "pi": Const(Fraction(str(math.pi)).limit_denominator(1000000)),
    "e": Const(Fraction(str(math.e)).limit_denominator(1000000)),
}

def preprocess_expression(text: str) -> str:
    _KNOWN_FUNCS = {
        "sin", "cos", "tan", "cot", "sec", "csc",
        "exp", "log", "sqrt", "abs", "asin", "acos", "atan",
    }
    cleaned = text.strip()
    cleaned = cleaned.replace("∫", "")
    cleaned = cleaned.replace("−", "-")
    cleaned = cleaned.replace("^", "**")
    # Aliases (order matters: ctg before tg, so tg doesn't match inside ctg)
    cleaned = re.sub(r"\bctg\b", "cot", cleaned)
    cleaned = re.sub(r"\bln\b",  "log", cleaned)
    cleaned = re.sub(r"\btg\b",  "tan", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)

    # ── Implicit multiplication ──────────────────────────────────────────
    # 1) digit followed by letter or '('   →  2x, 2pi, 2(x+1), 2sin(x)
    cleaned = re.sub(r"(\d)([A-Za-z(])", r"\1*\2", cleaned)
    # run twice to catch 2x^2 → 2*x**2 after ^ was already replaced
    cleaned = re.sub(r"(\d)([A-Za-z(])", r"\1*\2", cleaned)

    # 2) identifier followed by '(' — insert '*' only for non-function names
    def _ident_paren(m: re.Match) -> str:
        name = m.group(1)
        return name + "(" if name in _KNOWN_FUNCS else name + "*("
    cleaned = re.sub(r"([A-Za-z_]\w*)\(", _ident_paren, cleaned)

    # 3) ')' followed by digit, letter or '('   →  (x+1)2, (x+1)x, )(
    cleaned = re.sub(r"\)(\d)", r")*\1", cleaned)
    cleaned = re.sub(r"\)([A-Za-z])", r")*\1", cleaned)
    cleaned = re.sub(r"\)\(", r")*(", cleaned)
    return cleaned

def parse_expression(text: str) -> Expr:
    text = preprocess_expression(text)
    tree = ast.parse(text, mode="eval")
    return simplify(_from_ast(tree.body))

def _from_ast(node: ast.AST) -> Expr:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, int):
            return Const(Fraction(node.value))
        if isinstance(node.value, float):
            return Const(Fraction(str(node.value)).limit_denominator(1000000))
        raise ValueError("Поддерживаются только числовые константы.")
    if isinstance(node, ast.Name):
        if node.id in CONSTANT_NAMES:
            return CONSTANT_NAMES[node.id]
        return Var(node.id)
    if isinstance(node, ast.BinOp):
        left = _from_ast(node.left)
        right = _from_ast(node.right)
        if isinstance(node.op, ast.Add):
            return Add((left, right))
        if isinstance(node.op, ast.Sub):
            return Add((left, Mul((Const(Fraction(-1)), right))))
        if isinstance(node.op, ast.Mult):
            return Mul((left, right))
        if isinstance(node.op, ast.Div):
            return Mul((left, Pow(right, Const(Fraction(-1)))))
        if isinstance(node.op, ast.Pow):
            return Pow(left, right)
    if isinstance(node, ast.UnaryOp):
        operand = _from_ast(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return Mul((Const(Fraction(-1)), operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Поддерживаются только простые вызовы функций.")
        name = node.func.id
        if name not in FUNCTION_NAMES:
            raise ValueError(f"Неподдерживаемая функция: {name}")
        if len(node.args) != 1:
            raise ValueError(f"Функция {name} должна иметь один аргумент.")
        return Func(name, _from_ast(node.args[0]))
    raise ValueError(f"Неподдерживаемый элемент выражения: {ast.dump(node)}")
