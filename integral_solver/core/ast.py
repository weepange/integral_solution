from __future__ import annotations

import math

import re

import ast

from dataclasses import dataclass

from fractions import Fraction

from typing import Iterable, Optional, Sequence



Number = Fraction

def to_fraction(value: str) -> Number:
    return Fraction(value)

def is_number(value: object) -> bool:
    return isinstance(value, Fraction)

def format_num(value: Number) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"

def format_float(value: float) -> str:
    if abs(value - round(value)) < 1e-12:
        return str(int(round(value)))
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return text

@dataclass(frozen=True)
class Expr:
    def simplify(self) -> "Expr":
        return self

    def contains_var(self, name: str) -> bool:
        raise NotImplementedError

    def substitute(self, name: str, value: float) -> float:
        raise NotImplementedError

    def substitute_expr(self, name: str, value: "Expr") -> "Expr":
        raise NotImplementedError

@dataclass(frozen=True)
class Const(Expr):
    value: Number

    def contains_var(self, name: str) -> bool:
        return False

    def substitute(self, name: str, value: float) -> float:
        return float(self.value)

    def substitute_expr(self, name: str, value: "Expr") -> "Expr":
        return self

@dataclass(frozen=True)
class Var(Expr):
    name: str

    def contains_var(self, name: str) -> bool:
        return self.name == name

    def substitute(self, name: str, value: float) -> float:
        return float(value if self.name == name else 0.0)

    def substitute_expr(self, name: str, value: "Expr") -> "Expr":
        return value if self.name == name else self

@dataclass(frozen=True)
class Add(Expr):
    terms: tuple[Expr, ...]

    def simplify(self) -> Expr:
        terms: list[Expr] = []
        const = Fraction(0)
        
        def add_term(t: Expr):
            nonlocal const
            if isinstance(t, Const):
                const += t.value
            elif isinstance(t, Add):
                for sub in t.terms:
                    add_term(sub)
            else:
                terms.append(t)

        for term in self.terms:
            add_term(simplify(term))
            
        if const:
            terms.append(Const(const))
        if not terms:
            return Const(Fraction(0))
        if len(terms) == 1:
            return terms[0]
        return Add(tuple(terms))

    def contains_var(self, name: str) -> bool:
        return any(term.contains_var(name) for term in self.terms)

    def substitute(self, name: str, value: float) -> float:
        return sum(term.substitute(name, value) for term in self.terms)

    def substitute_expr(self, name: str, value: Expr) -> Expr:
        return Add(tuple(term.substitute_expr(name, value) for term in self.terms))

@dataclass(frozen=True)
class Mul(Expr):
    factors: tuple[Expr, ...]

    def simplify(self) -> Expr:
        factors: list[Expr] = []
        const = Fraction(1)
        
        def add_factor(f: Expr):
            nonlocal const
            if isinstance(f, Const):
                const *= f.value
            elif isinstance(f, Mul):
                for sub in f.factors:
                    add_factor(sub)
            else:
                factors.append(f)

        for factor in self.factors:
            add_factor(simplify(factor))
            
        if const == 0:
            return Const(Fraction(0))
        if const != 1 or not factors:
            factors.insert(0, Const(const))
        if len(factors) == 1:
            return factors[0]
        return Mul(tuple(factors))

    def contains_var(self, name: str) -> bool:
        return any(factor.contains_var(name) for factor in self.factors)

    def substitute(self, name: str, value: float) -> float:
        result = 1.0
        for factor in self.factors:
            result *= factor.substitute(name, value)
        return result

    def substitute_expr(self, name: str, value: Expr) -> Expr:
        return Mul(tuple(factor.substitute_expr(name, value) for factor in self.factors))

@dataclass(frozen=True)
class Pow(Expr):
    base: Expr
    exponent: Expr

    def simplify(self) -> Expr:
        base = simplify(self.base)
        exponent = simplify(self.exponent)
        if isinstance(exponent, Const):
            if exponent.value == 0:
                return Const(Fraction(1))
            if exponent.value == 1:
                return base
        # sqrt(x)^n → x^(n/2)
        if isinstance(base, Func) and base.name == "sqrt" and isinstance(exponent, Const):
            new_exp = exponent.value * Fraction(1, 2)
            return simplify(Pow(base.arg, Const(new_exp)))
        # (x^a)^b → x^(a*b)
        if isinstance(base, Pow) and isinstance(base.exponent, Const) and isinstance(exponent, Const):
            new_exp = base.exponent.value * exponent.value
            return simplify(Pow(base.base, Const(new_exp)))
        if isinstance(base, Const) and isinstance(exponent, Const):
            if exponent.value.denominator == 1:
                return Const(base.value ** exponent.value.numerator)
            return Const(Fraction(float(base.value) ** float(exponent.value)).limit_denominator(1000000))
        return Pow(base, exponent)

    def contains_var(self, name: str) -> bool:
        return self.base.contains_var(name) or self.exponent.contains_var(name)

    def substitute(self, name: str, value: float) -> float:
        return self.base.substitute(name, value) ** self.exponent.substitute(name, value)

    def substitute_expr(self, name: str, value: Expr) -> Expr:
        return Pow(self.base.substitute_expr(name, value), self.exponent.substitute_expr(name, value))

@dataclass(frozen=True)
class Func(Expr):
    name: str
    arg: Expr

    def simplify(self) -> Expr:
        arg = simplify(self.arg)
        if self.name == "sqrt" and isinstance(arg, Const) and arg.value >= 0:
            # Check for perfect square first
            if arg.value == 1:
                return Const(Fraction(1))
            if arg.value == 0:
                return Const(Fraction(0))
            import math
            n = arg.value.numerator
            d = arg.value.denominator
            
            def extract_square(val: int) -> tuple[int, int]:
                a = 1
                b = val
                if val == 0:
                    return 0, 1
                for i in range(2, int(math.sqrt(val)) + 1):
                    while b % (i * i) == 0:
                        a *= i
                        b //= (i * i)
                return a, b
            
            a_n, b_n = extract_square(n)
            a_d, b_d = extract_square(d)
            
            coef = Fraction(a_n, a_d)
            rem = Fraction(b_n, b_d)
            if rem == 1:
                return Const(coef)
            if coef != 1:
                return simplify(Mul((Const(coef), Func("sqrt", Const(rem)))))
        return Func(self.name, arg)

    def contains_var(self, name: str) -> bool:
        return self.arg.contains_var(name)

    def substitute(self, name: str, value: float) -> float:
        x = self.arg.substitute(name, value)
        if self.name == "sin":
            return math.sin(x)
        if self.name == "cos":
            return math.cos(x)
        if self.name == "tan":
            return math.tan(x)
        if self.name == "cot":
            return 1.0 / math.tan(x)
        if self.name == "sec":
            return 1.0 / math.cos(x)
        if self.name == "csc":
            return 1.0 / math.sin(x)
        if self.name == "exp":
            return math.exp(x)
        if self.name == "log":
            return math.log(abs(x))
        if self.name == "sqrt":
            return math.sqrt(x)
        if self.name == "abs":
            return abs(x)
        if self.name == "asin":
            return math.asin(x)
        if self.name == "acos":
            return math.acos(x)
        if self.name == "atan":
            return math.atan(x)
        raise ValueError(f"Неподдерживаемая функция для численной подстановки: {self.name}")

    def substitute_expr(self, name: str, value: Expr) -> Expr:
        return Func(self.name, self.arg.substitute_expr(name, value))

def simplify(expr: Expr) -> Expr:
    return expr.simplify()

def format_expr(expr: Expr) -> str:
    return format_expr_internal(expr, 0)

def format_expr_internal(expr: Expr, parent_prec: int) -> str:
    if isinstance(expr, Const):
        return format_num(expr.value)
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Add):
        parts = []
        for i, term in enumerate(expr.terms):
            if i > 0:
                # Check for negative term
                if isinstance(term, Mul) and term.factors and isinstance(term.factors[0], Const) and term.factors[0].value < 0:
                    neg_term = simplify(Mul((Const(Fraction(-1)), term)))
                    parts.append(" - " + format_expr_internal(neg_term, 1))
                elif isinstance(term, Const) and term.value < 0:
                    parts.append(" - " + format_num(-term.value))
                else:
                    parts.append(" + " + format_expr_internal(term, 1))
            else:
                parts.append(format_expr_internal(term, 1))
        text = "".join(parts)
        return f"({text})" if parent_prec > 1 else text
    if isinstance(expr, Mul):
        factors = list(expr.factors)
        prefix = ""
        # Handle -1 coefficient
        if factors and isinstance(factors[0], Const) and factors[0].value == -1 and len(factors) > 1:
            prefix = "-"
            factors = factors[1:]
        # Handle 1 coefficient
        elif factors and isinstance(factors[0], Const) and factors[0].value == 1 and len(factors) > 1:
            factors = factors[1:]
        parts = []
        for factor in factors:
            text = format_expr_internal(factor, 2)
            parts.append(text)
        text = prefix + "*".join(parts)
        return f"({text})" if parent_prec > 2 else text
    if isinstance(expr, Pow):
        text = f"{format_expr_internal(expr.base, 3)}^({format_expr_internal(expr.exponent, 3)})"
        return f"({text})" if parent_prec > 3 else text
    if isinstance(expr, Func):
        if expr.name == "abs":
            return f"|{format_expr_internal(expr.arg, 0)}|"
        if expr.name == "log":
            return f"ln({format_expr_internal(expr.arg, 0)})"
        return f"{expr.name}({format_expr_internal(expr.arg, 0)})"
    return str(expr)

