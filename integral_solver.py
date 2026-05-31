from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Optional, Sequence


Number = Fraction


def _to_fraction(value: str) -> Number:
    return Fraction(value)


def _is_number(value: object) -> bool:
    return isinstance(value, Fraction)


def _num(value: Number) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _format_float(value: float) -> str:
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
        for term in self.terms:
            term = simplify(term)
            if isinstance(term, Const):
                const += term.value
            elif isinstance(term, Add):
                terms.extend(term.terms)
            else:
                terms.append(term)
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
        for factor in self.factors:
            factor = simplify(factor)
            if isinstance(factor, Const):
                const *= factor.value
            elif isinstance(factor, Mul):
                factors.extend(factor.factors)
            else:
                factors.append(factor)
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
        return Func(self.name, simplify(self.arg))

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


def is_const(expr: Expr) -> bool:
    return isinstance(expr, Const) or not expr.contains_var("x")


def split_linear(expr: Expr, var: str) -> Optional[tuple[Number, Number]]:
    expr = simplify(expr)
    if isinstance(expr, Var) and expr.name == var:
        return Fraction(1), Fraction(0)
    if isinstance(expr, Const):
        return Fraction(0), expr.value
    if isinstance(expr, Add):
        a = Fraction(0)
        b = Fraction(0)
        for term in expr.terms:
            part = split_linear(term, var)
            if part is None:
                return None
            aa, bb = part
            a += aa
            b += bb
        return a, b
    if isinstance(expr, Mul):
        const = Fraction(1)
        var_part: Optional[Expr] = None
        for factor in expr.factors:
            if isinstance(factor, Const):
                const *= factor.value
            elif isinstance(factor, Var) and factor.name == var:
                if var_part is not None:
                    return None
                var_part = factor
            else:
                return None
        if var_part is not None:
            return const, Fraction(0)
        return Fraction(0), const
    return None


def degree(expr: Expr, var: str) -> Optional[int]:
    expr = simplify(expr)
    if not expr.contains_var(var):
        return 0
    if isinstance(expr, Var) and expr.name == var:
        return 1
    if isinstance(expr, Add):
        degrees: list[int] = []
        for term in expr.terms:
            d = degree(term, var)
            if d is None:
                return None
            degrees.append(d)
        return max(degrees) if degrees else 0
    if isinstance(expr, Mul):
        total = 0
        for factor in expr.factors:
            d = degree(factor, var)
            if d is None:
                return None
            total += d
        return total
    if isinstance(expr, Pow):
        base_deg = degree(expr.base, var)
        if base_deg is None:
            return None
        if base_deg == 1 and isinstance(expr.exponent, Const) and expr.exponent.value.denominator == 1 and expr.exponent.value >= 0:
            return int(expr.exponent.value)
    return None


def derivative(expr: Expr, var: str) -> Expr:
    expr = simplify(expr)
    if isinstance(expr, Const):
        return Const(Fraction(0))
    if isinstance(expr, Var):
        return Const(Fraction(1 if expr.name == var else 0))
    if isinstance(expr, Add):
        return simplify(Add(tuple(derivative(term, var) for term in expr.terms)))
    if isinstance(expr, Mul):
        terms = []
        for index, factor in enumerate(expr.factors):
            derived = derivative(factor, var)
            if isinstance(derived, Const) and derived.value == 0:
                continue
            new_factors = list(expr.factors)
            new_factors[index] = derived
            terms.append(Mul(tuple(new_factors)))
        return simplify(Add(tuple(terms))) if terms else Const(Fraction(0))
    if isinstance(expr, Pow):
        if isinstance(expr.base, Var) and expr.base.name == var and isinstance(expr.exponent, Const):
            n = expr.exponent.value
            return simplify(Mul((Const(n), Pow(expr.base, Const(n - 1)))))
        if isinstance(expr.base, Const) and isinstance(expr.exponent, Const):
            return Const(Fraction(0))
        return Const(Fraction(0))
    if isinstance(expr, Func):
        arg_der = derivative(expr.arg, var)
        if expr.name == "sin":
            return simplify(Mul((arg_der, Func("cos", expr.arg))))
        if expr.name == "cos":
            return simplify(Mul((Const(Fraction(-1)), arg_der, Func("sin", expr.arg))))
        if expr.name == "tan":
            return simplify(Mul((arg_der, Pow(Func("sec", expr.arg), Const(Fraction(2))))))
        if expr.name == "exp":
            return simplify(Mul((arg_der, Func("exp", expr.arg))))
        if expr.name == "log":
            return simplify(Mul((arg_der, Pow(expr.arg, Const(Fraction(-1))))))
    return Const(Fraction(0))


def expr_contains_only_var(expr: Expr, var: str) -> bool:
    return expr.contains_var(var)


def integrate(expr: Expr, var: str = "x") -> tuple[Optional[Expr], list[str]]:
    expr = simplify(expr)
    notes: list[str] = []

    if isinstance(expr, Add):
        parts: list[Expr] = []
        notes.append("Линейность ∫ : ∫(f+g)dx = ∫f dx + ∫g dx")
        for term in expr.terms:
            solved, subnotes = integrate(term, var)
            if solved is None:
                return None, notes + subnotes
            parts.append(solved)
            notes.extend(subnotes)
        return simplify(Add(tuple(parts))), notes

    if not expr.contains_var(var):
        notes.append("Правило константы: ∫c dx = c·x")
        return simplify(Mul((expr, Var(var)))), notes

    if isinstance(expr, Var) and expr.name == var:
        notes.append("Степенное правило: ∫x dx = x²/2")
        return simplify(Mul((Const(Fraction(1, 2)), Pow(Var(var), Const(Fraction(2)))))), notes

    if isinstance(expr, Mul):
        indep, rest = extract_independent_factor(expr, var)
        if indep is not None:
            solved, subnotes = integrate(rest, var)
            if solved is not None:
                notes.append("Линейность ∫ : ∫k·f dx = k·∫f dx")
                notes.extend(subnotes)
                if isinstance(indep, Const) and indep.value == 1:
                    return solved, notes
                return simplify(Mul((indep, solved))), notes

        if len(expr.factors) == 2:
            left, right = expr.factors
            solved = integrate_linear_times_function(left, right, var)
            if solved is not None:
                notes.append("Интегрирование по частям: ∫u dv = u·v − ∫v du")
                return solved, notes
            solved = integrate_linear_times_function(right, left, var)
            if solved is not None:
                notes.append("Интегрирование по частям: ∫u dv = u·v − ∫v du")
                return solved, notes

        by_parts = integrate_by_parts(expr, var)
        if by_parts is not None:
            notes.append("Интегрирование по частям: ∫u dv = u·v − ∫v du")
            return by_parts, notes

    if isinstance(expr, Pow):
        solved = integrate_power(expr, var)
        if solved is not None:
            # Detect whether linear substitution was needed
            lin = split_linear(expr.base, var) if not (isinstance(expr.base, Var) and expr.base.name == var) else None
            n = expr.exponent.value if isinstance(expr.exponent, Const) else None
            if lin and lin[0] != 0 and lin[0] != 1:
                notes.append(f"Подстановка u = {format_expr(expr.base)}, затем степенное правило")
            elif n == -1:
                notes.append("Табличный интеграл: ∫1/x dx = ln|x|")
            else:
                notes.append("Степенное правило: ∫xⁿ dx = xⁿ⁺¹/(n+1)")
            return solved, notes

    if isinstance(expr, Func):
        solved = integrate_function(expr, var)
        if solved is not None:
            # Detect linear substitution (a ≠ 1)
            lin = split_linear(expr.arg, var)
            if lin and lin[0] != 0 and lin[0] != 1:
                notes.append(f"Подстановка u = {format_expr(expr.arg)}, затем табличный интеграл")
            else:
                notes.append(f"Табличный интеграл: ∫{expr.name}(x) dx")
            return solved, notes

    if is_polynomial(expr, var):
        return integrate_polynomial(expr, var)

    return None, notes


def extract_independent_factor(expr: Mul, var: str) -> tuple[Optional[Expr], Expr]:
    indep_factors = []
    dep_factors = []
    for factor in expr.factors:
        if not factor.contains_var(var):
            indep_factors.append(factor)
        else:
            dep_factors.append(factor)
            
    if not indep_factors:
        return None, expr
    
    indep_part = Mul(tuple(indep_factors)) if len(indep_factors) > 1 else indep_factors[0]
    dep_part = Mul(tuple(dep_factors)) if len(dep_factors) > 1 else (dep_factors[0] if dep_factors else Const(Fraction(1)))
    
    return simplify(indep_part), simplify(dep_part)


def integrate_power(expr: Pow, var: str) -> Optional[Expr]:
    if isinstance(expr.base, Var) and expr.base.name == var and isinstance(expr.exponent, Const):
        n = expr.exponent.value
        if n == -1:
            return Func("log", Func("abs", Var(var)))
        if n != -1:
            return simplify(Mul((Const(Fraction(1, 1) / (n + 1)), Pow(Var(var), Const(n + 1)))))

    linear = split_linear(expr.base, var)
    if linear and isinstance(expr.exponent, Const):
        a, b = linear
        n = expr.exponent.value
        if n == -1:
            return simplify(Mul((Const(Fraction(1, a)), Func("log", Func("abs", expr.base)))))
        if a != 0:
            return simplify(Mul((Const(Fraction(1, a) / (n + 1))), Pow(expr.base, Const(n + 1))))
    return None


def integrate_function(expr: Func, var: str) -> Optional[Expr]:
    linear = split_linear(expr.arg, var)
    if linear is None:
        return None
    a, _ = linear
    if a == 0:
        return None
    inv_a = Const(Fraction(1, a))

    if expr.name == "sin":
        return simplify(Mul((Const(-1), inv_a, Func("cos", expr.arg))))
    if expr.name == "cos":
        return simplify(Mul((inv_a, Func("sin", expr.arg))))
    if expr.name == "exp":
        return simplify(Mul((inv_a, Func("exp", expr.arg))))
    if expr.name == "tan":
        return simplify(Mul((Const(-1), inv_a, Func("log", Func("abs", Func("cos", expr.arg))))))
    if expr.name == "sec":
        return None
    if expr.name == "log" and isinstance(expr.arg, Var) and expr.arg.name == var:
        return simplify(Add((Mul((Var(var), Func("log", Func("abs", Var(var))))), Mul((Const(Fraction(-1)), Var(var))))))
    if expr.name == "sqrt":
        inner = expr.arg
        if linear:
            coeff = Const(Fraction(2, 3) * Fraction(1, a))
            return simplify(Mul((coeff, Pow(inner, Const(Fraction(3, 2))))))
    if expr.name == "asin" and a == 1:
        sq = Func("sqrt", Add((Const(Fraction(1)),
                               Mul((Const(Fraction(-1)), Pow(expr.arg, Const(Fraction(2))))))))
        return simplify(Add((Mul((expr.arg, Func("asin", expr.arg))), sq)))
    if expr.name == "acos" and a == 1:
        sq = Func("sqrt", Add((Const(Fraction(1)),
                               Mul((Const(Fraction(-1)), Pow(expr.arg, Const(Fraction(2))))))))
        return simplify(Add((Mul((expr.arg, Func("acos", expr.arg))),
                             Mul((Const(Fraction(-1)), sq)))))
    if expr.name == "atan" and a == 1:
        lg = Func("log", Add((Const(Fraction(1)), Pow(expr.arg, Const(Fraction(2))))))
        return simplify(Add((Mul((expr.arg, Func("atan", expr.arg))),
                             Mul((Const(Fraction(-1, 2)), lg)))))
    return None


def integrate_linear_times_function(left: Expr, right: Expr, var: str) -> Optional[Expr]:
    if is_polynomial(left, var) and is_simple_function(right, var):
        return integrate_by_parts(Mul((left, right)), var)
    return None


def is_simple_function(expr: Expr, var: str) -> bool:
    return isinstance(expr, Func) and expr.arg.contains_var(var)


def integrate_by_parts(expr: Mul, var: str) -> Optional[Expr]:
    poly_part: Optional[Expr] = None
    func_part: Optional[Expr] = None
    for factor in expr.factors:
        if is_polynomial(factor, var) and poly_part is None:
            poly_part = factor
        elif is_simple_function(factor, var) and func_part is None:
            func_part = factor
        else:
            return None
    if poly_part is None or func_part is None:
        return None

    du = derivative(poly_part, var)
    v = integrate(func_part, var)[0]
    if v is None:
        return None
    remainder = simplify(Mul((v, du)))
    inner = integrate(remainder, var)[0]
    if inner is None:
        return None
    return simplify(Add((Mul((poly_part, v)), Mul((Const(Fraction(-1)), inner)))))


def is_polynomial(expr: Expr, var: str) -> bool:
    expr = simplify(expr)
    if not expr.contains_var(var):
        return True
    if isinstance(expr, Var):
        return expr.name == var
    if isinstance(expr, Add):
        return all(is_polynomial(term, var) for term in expr.terms)
    if isinstance(expr, Mul):
        return all(is_polynomial(factor, var) for factor in expr.factors)
    if isinstance(expr, Pow):
        return (isinstance(expr.base, Var) and expr.base.name == var
                and isinstance(expr.exponent, Const)
                and expr.exponent.value.denominator == 1
                and expr.exponent.value >= 0)
    return False


def integrate_polynomial(expr: Expr, var: str) -> tuple[Optional[Expr], list[str]]:
    expr = simplify(expr)
    if not expr.contains_var(var):
        return simplify(Mul((expr, Var(var)))), ["Правило константы: ∫c dx = c·x"]
    if isinstance(expr, Var) and expr.name == var:
        return simplify(Mul((Const(Fraction(1, 2)), Pow(Var(var), Const(Fraction(2)))))), ["Степенное правило: ∫x dx = x²/2"]
    if isinstance(expr, Pow) and isinstance(expr.base, Var) and expr.base.name == var and isinstance(expr.exponent, Const):
        n = expr.exponent.value
        if n == -1:
            return Func("log", Func("abs", Var(var))), ["Табличный интеграл: ∫1/x dx = ln|x|"]
        return simplify(Mul((Const(Fraction(1, 1) / (n + 1)), Pow(Var(var), Const(n + 1))))), ["Степенное правило: ∫xⁿ dx = xⁿ⁺¹/(n+1)"]
    if isinstance(expr, Add):
        parts: list[Expr] = []
        notes = ["Линейность ∫: ∫(f+g)dx = ∫f dx + ∫g dx"]
        for term in expr.terms:
            solved, subnotes = integrate_polynomial(term, var)
            if solved is None:
                return None, notes + subnotes
            parts.append(solved)
            notes.extend(subnotes)
        return simplify(Add(tuple(parts))), notes
    if isinstance(expr, Mul):
        indep, rest = extract_independent_factor(expr, var)
        if indep is not None:
            solved, subnotes = integrate_polynomial(rest, var)
            if solved is not None:
                return simplify(Mul((indep, solved))), ["Линейность ∫: ∫k·f dx = k·∫f dx"] + subnotes
    return None, []




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


def solve_definite_symbolic(expr_or_text: str | Expr, var: str, lower_or_text: str | Expr | int | float, upper_or_text: str | Expr | int | float) -> dict[str, object]:
    expr = to_expr(expr_or_text)
    lower = to_expr(lower_or_text)
    upper = to_expr(upper_or_text)

    antiderivative, notes = integrate(expr, var)
    if antiderivative is not None:
        f_upper = simplify(antiderivative.substitute_expr(var, upper))
        f_lower = simplify(antiderivative.substitute_expr(var, lower))
        result_expr = simplify(Add((f_upper, Mul((Const(Fraction(-1)), f_lower)))))
        out: dict[str, object] = {
            "ok": True,
            "expression": expr,
            "antiderivative": simplify(antiderivative),   # F(x) — первообразная
            "result": result_expr,                        # F(b)−F(a) — символьный
            "notes": notes + ["Формула Ньютона-Лейбница: F(b) − F(a)"],
        }
        # Всегда вычисляем числовое значение
        try:
            out["value"] = evaluate_constant_expr(result_expr)
        except Exception:
            try:
                lo = evaluate_constant_expr(lower)
                hi = evaluate_constant_expr(upper)
                out["value"] = numerical_integrate(expr, var, lo, hi)
            except Exception:
                pass
        return out

    else:
        try:
            lower_val = evaluate_constant_expr(lower)
            upper_val = evaluate_constant_expr(upper)
            val = numerical_integrate(expr, var, lower_val, upper_val)
            return {
                "ok": True,
                "expression": expr,
                "result": None,
                "value": val,
                "notes": notes + ["Численное интегрирование методом Симпсона (аналитическое решение не найдено)."],
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Аналитическое решение не найдено. Численное интегрирование невозможно: {e}",
                "expression": expr,
                "notes": notes,
            }


def solve_indefinite(expression_text: str, var: str = "x") -> dict[str, object]:
    expr = parse_expression(expression_text)
    antiderivative, notes = integrate(expr, var)
    if antiderivative is None:
        return {
            "ok": False,
            "error": "Не удалось автоматически распознать этот интеграл. Попробуйте переписать его в более стандартном виде.",
            "expression": expr,
            "notes": notes,
        }
    return {
        "ok": True,
        "expression": expr,
        "result": simplify(antiderivative),
        "notes": notes,
    }


def solve_definite(expression_text: str, var: str, lower: float, upper: float) -> dict[str, object]:
    lower_expr = Const(Fraction(str(lower)).limit_denominator(1000000))
    upper_expr = Const(Fraction(str(upper)).limit_denominator(1000000))
    res = solve_definite_symbolic(expression_text, var, lower_expr, upper_expr)
    if not res["ok"]:
        return res
    if res.get("result") is not None:
        result_expr: Expr = res["result"]  # type: ignore[assignment]
        try:
            value = evaluate_constant_expr(result_expr)
        except Exception:
            try:
                value = float(result_expr.substitute("dummy", 0.0))
            except Exception:
                value = 0.0
        res["value"] = value
    return res



def solve_double_integral(
    expr_or_text: str | Expr,
    inner_var: str,
    inner_lower_or_text: str | Expr,
    inner_upper_or_text: str | Expr,
    outer_var: str,
    outer_lower: float,
    outer_upper: float
) -> dict[str, object]:
    if isinstance(expr_or_text, str):
        expr = parse_expression(expr_or_text)
    else:
        expr = expr_or_text

    if isinstance(inner_lower_or_text, str):
        inner_lower = parse_expression(inner_lower_or_text)
    else:
        inner_lower = inner_lower_or_text

    if isinstance(inner_upper_or_text, str):
        inner_upper = parse_expression(inner_upper_or_text)
    else:
        inner_upper = inner_upper_or_text

    outer_lower_expr = Const(Fraction(str(outer_lower)).limit_denominator(1000000))
    outer_upper_expr = Const(Fraction(str(outer_upper)).limit_denominator(1000000))

    inner_res = solve_definite_symbolic(expr, inner_var, inner_lower, inner_upper)
    if not inner_res["ok"]:
        return {
            "ok": False,
            "error": f"Ошибка при вычислении внутреннего интеграла по {inner_var}: {inner_res.get('error')}",
            "notes": inner_res.get("notes", [])
        }

    inner_antideriv = inner_res.get("antiderivative")  # F_inner(inner_var)

    if inner_antideriv is not None:
        # Символьно: inner_result(outer_var) = F(upper(outer_var)) − F(lower(outer_var))
        f_upper_inner = simplify(inner_antideriv.substitute_expr(inner_var, inner_upper))
        f_lower_inner = simplify(inner_antideriv.substitute_expr(inner_var, inner_lower))
        inner_result_expr: Expr = simplify(
            Add((f_upper_inner, Mul((Const(Fraction(-1)), f_lower_inner))))
        )
    elif inner_res.get("result") is not None:
        inner_result_expr = inner_res["result"]  # type: ignore[assignment]
    elif "value" in inner_res:
        inner_result_expr = Const(Fraction(str(inner_res["value"])).limit_denominator(1000000))
    else:
        return {
            "ok": False,
            "error": "Внутренний интеграл решен только численно, но не может быть представлен символически для внешнего шага.",
            "notes": inner_res.get("notes", [])
        }

    outer_res = solve_definite_symbolic(inner_result_expr, outer_var, outer_lower_expr, outer_upper_expr)
    if not outer_res["ok"]:
        return {
            "ok": False,
            "error": f"Ошибка при вычислении внешнего интеграла по {outer_var}: {outer_res.get('error')}",
            "notes": inner_res.get("notes", []) + outer_res.get("notes", [])
        }

    val: float = outer_res.get("value", 0.0)  # type: ignore[assignment]

    return {
        "ok": True,
        "expression": expr,
        "inner_var": inner_var,
        "inner_lower": inner_lower,
        "inner_upper": inner_upper,
        "inner_result": inner_result_expr,
        "outer_var": outer_var,
        "outer_lower": outer_lower,
        "outer_upper": outer_upper,
        "value": val,
        "notes": ["Внутренний интеграл:"] + inner_res.get("notes", []) + ["Внешний интеграл:"] + outer_res.get("notes", [])
    }


def explain_double_solution(result: dict[str, object]) -> str:
    if not result.get("ok"):
        return str(result.get("error", "Ошибка"))
    lines = []
    lines.append("Двойной интеграл по области:")
    lines.append(f"  Внутренний: по {result['inner_var']} от {format_expr(result['inner_lower'])} до {format_expr(result['inner_upper'])}")
    lines.append(f"  Внешний: по {result['outer_var']} от {result['outer_lower']} до {result['outer_upper']}")
    lines.append(f"Подынтегральное выражение: {format_expr(result['expression'])}")

    lines.append("\nШаг 1: Интегрирование по " + str(result["inner_var"]))
    lines.append(f"  Результат шага 1: {format_expr(result['inner_result'])}")

    lines.append("\nШаг 2: Интегрирование по " + str(result["outer_var"]))
    lines.append(f"  Значение двойного интеграла: {_format_float(result['value'])}")

    if result.get("notes"):
        lines.append("\nХод решения:")
        for note in result["notes"]:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def solve_line_integral_1st_kind(
    f_text: str | Expr,
    x_t_text: str | Expr,
    y_t_text: str | Expr,
    z_t_text: Optional[str | Expr] = None,
    t_var: str = "t",
    t_lower: float | str | Expr = 0.0,
    t_upper: float | str | Expr = 1.0
) -> dict[str, object]:
    f_expr = parse_expression(f_text) if isinstance(f_text, str) else f_text
    x_t = parse_expression(x_t_text) if isinstance(x_t_text, str) else x_t_text
    y_t = parse_expression(y_t_text) if isinstance(y_t_text, str) else y_t_text
    z_t = None
    if z_t_text is not None:
        z_t = parse_expression(z_t_text) if isinstance(z_t_text, str) else z_t_text

    dx_dt = simplify(derivative(x_t, t_var))
    dy_dt = simplify(derivative(y_t, t_var))
    dz_dt = None if z_t is None else simplify(derivative(z_t, t_var))

    dx_dt_sq = Pow(dx_dt, Const(Fraction(2)))
    dy_dt_sq = Pow(dy_dt, Const(Fraction(2)))
    sum_sq_terms = [dx_dt_sq, dy_dt_sq]
    if dz_dt is not None:
        sum_sq_terms.append(Pow(dz_dt, Const(Fraction(2))))

    sum_sq = simplify(Add(tuple(sum_sq_terms)))
    ds = simplify(Func("sqrt", sum_sq))

    f_substituted = f_expr.substitute_expr("x", x_t)
    f_substituted = f_substituted.substitute_expr("y", y_t)
    if z_t is not None:
        f_substituted = f_substituted.substitute_expr("z", z_t)
    f_substituted = simplify(f_substituted)

    integrand = simplify(Mul((f_substituted, ds)))

    lower_expr = to_expr(t_lower)
    upper_expr = to_expr(t_upper)

    res = solve_definite_symbolic(integrand, t_var, lower_expr, upper_expr)
    if not res["ok"]:
        return {
            "ok": False,
            "error": f"Не удалось интегрировать выражение криволинейного интеграла: {res.get('error')}",
            "notes": res.get("notes", [])
        }

    if res.get("result") is not None:
        result_expr: Expr = res["result"]  # type: ignore[assignment]
        try:
            val = evaluate_constant_expr(result_expr)
        except Exception:
            try:
                val = float(result_expr.substitute("dummy", 0.0))
            except Exception:
                val = 0.0
    else:
        val = res["value"]  # type: ignore[assignment]

    return {
        "ok": True,
        "type": "1st_kind",
        "f_expr": f_expr,
        "x_t": x_t,
        "y_t": y_t,
        "z_t": z_t,
        "ds": ds,
        "integrand": integrand,
        "result_expr": res.get("result"),
        "value": val,
        "notes": [
            f"Производные: dx/dt = {format_expr(dx_dt)}, dy/dt = {format_expr(dy_dt)}" + (f", dz/dt = {format_expr(dz_dt)}" if dz_dt else ""),
            f"Элемент длины дуги ds = {format_expr(ds)}",
            f"Функция после подстановки: {format_expr(f_substituted)}",
            f"Подынтегральное выражение f(t)*ds = {format_expr(integrand)}"
        ] + res.get("notes", [])
    }


def solve_line_integral_2nd_kind(
    P_text: str | Expr,
    Q_text: str | Expr,
    x_t_text: str | Expr,
    y_t_text: str | Expr,
    R_text: Optional[str | Expr] = None,
    z_t_text: Optional[str | Expr] = None,
    t_var: str = "t",
    t_lower: float | str | Expr = 0.0,
    t_upper: float | str | Expr = 1.0
) -> dict[str, object]:
    P_expr = parse_expression(P_text) if isinstance(P_text, str) else P_text
    Q_expr = parse_expression(Q_text) if isinstance(Q_text, str) else Q_text
    R_expr = None
    if R_text is not None:
        R_expr = parse_expression(R_text) if isinstance(R_text, str) else R_text

    x_t = parse_expression(x_t_text) if isinstance(x_t_text, str) else x_t_text
    y_t = parse_expression(y_t_text) if isinstance(y_t_text, str) else y_t_text
    z_t = None
    if z_t_text is not None:
        z_t = parse_expression(z_t_text) if isinstance(z_t_text, str) else z_t_text

    dx_dt = simplify(derivative(x_t, t_var))
    dy_dt = simplify(derivative(y_t, t_var))
    dz_dt = None if z_t is None else simplify(derivative(z_t, t_var))

    P_sub = P_expr.substitute_expr("x", x_t).substitute_expr("y", y_t)
    if z_t is not None and P_sub.contains_var("z"):
        P_sub = P_sub.substitute_expr("z", z_t)
    P_sub = simplify(P_sub)

    Q_sub = Q_expr.substitute_expr("x", x_t).substitute_expr("y", y_t)
    if z_t is not None and Q_sub.contains_var("z"):
        Q_sub = Q_sub.substitute_expr("z", z_t)
    Q_sub = simplify(Q_sub)

    R_sub = None
    if R_expr is not None:
        R_sub = R_expr.substitute_expr("x", x_t).substitute_expr("y", y_t)
        if z_t is not None:
            R_sub = R_sub.substitute_expr("z", z_t)
        R_sub = simplify(R_sub)

    term_P = simplify(Mul((P_sub, dx_dt)))
    term_Q = simplify(Mul((Q_sub, dy_dt)))
    integrand_terms = [term_P, term_Q]
    if R_sub is not None and dz_dt is not None:
        integrand_terms.append(simplify(Mul((R_sub, dz_dt))))

    integrand = simplify(Add(tuple(integrand_terms)))

    lower_expr = to_expr(t_lower)
    upper_expr = to_expr(t_upper)

    res = solve_definite_symbolic(integrand, t_var, lower_expr, upper_expr)
    if not res["ok"]:
        return {
            "ok": False,
            "error": f"Не удалось интегрировать выражение криволинейного интеграла: {res.get('error')}",
            "notes": res.get("notes", [])
        }

    if res.get("result") is not None:
        result_expr: Expr = res["result"]  # type: ignore[assignment]
        try:
            val = evaluate_constant_expr(result_expr)
        except Exception:
            try:
                val = float(result_expr.substitute("dummy", 0.0))
            except Exception:
                val = 0.0
    else:
        val = res["value"]  # type: ignore[assignment]

    return {
        "ok": True,
        "type": "2nd_kind",
        "P_expr": P_expr,
        "Q_expr": Q_expr,
        "R_expr": R_expr,
        "x_t": x_t,
        "y_t": y_t,
        "z_t": z_t,
        "integrand": integrand,
        "result_expr": res.get("result"),
        "value": val,
        "notes": [
            f"Производные: dx/dt = {format_expr(dx_dt)}, dy/dt = {format_expr(dy_dt)}" + (f", dz/dt = {format_expr(dz_dt)}" if dz_dt else ""),
            f"После подстановки: P = {format_expr(P_sub)}, Q = {format_expr(Q_sub)}" + (f", R = {format_expr(R_sub)}" if R_sub else ""),
            f"Подынтегральное выражение P*dx/dt + Q*dy/dt + ... = {format_expr(integrand)}"
        ] + res.get("notes", [])
    }


def explain_line_solution(result: dict[str, object]) -> str:
    if not result.get("ok"):
        return str(result.get("error", "Ошибка"))
    lines = []
    if result["type"] == "1st_kind":
        lines.append("Криволинейный интеграл 1-го рода (по длине дуги):")
        lines.append(f"  Функция f: {format_expr(result['f_expr'])}")
    else:
        lines.append("Криволинейный интеграл 2-го рода (по вектору):")
        lines.append(f"  Векторное поле: P = {format_expr(result['P_expr'])}, Q = {format_expr(result['Q_expr'])}" + (f", R = {format_expr(result['R_expr'])}" if result['R_expr'] else ""))

    lines.append(f"  Параметризация: x(t) = {format_expr(result['x_t'])}, y(t) = {format_expr(result['y_t'])}" + (f", z(t) = {format_expr(result['z_t'])}" if result['z_t'] else ""))

    lines.append("\nСведение к определенному интегралу по t:")
    lines.append(f"  Подынтегральное выражение: {format_expr(result['integrand'])}")

    if result.get("result_expr") is not None:
        lines.append(f"  Первообразная: {format_expr(result['result_expr'])}")
    lines.append(f"  Значение интеграла: {_format_float(result['value'])}")

    if result.get("notes"):
        lines.append("\nХод решения:")
        for note in result["notes"]:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def format_expr(expr: Expr) -> str:
    return _format_expr(expr, 0)


def _format_expr(expr: Expr, parent_prec: int) -> str:
    if isinstance(expr, Const):
        return _num(expr.value)
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Add):
        parts = []
        for term in expr.terms:
            text = _format_expr(term, 1)
            parts.append(text)
        text = " + ".join(parts)
        return f"({text})" if parent_prec > 1 else text
    if isinstance(expr, Mul):
        parts = []
        for factor in expr.factors:
            text = _format_expr(factor, 2)
            parts.append(text)
        text = "*".join(parts)
        return f"({text})" if parent_prec > 2 else text
    if isinstance(expr, Pow):
        text = f"{_format_expr(expr.base, 3)}^({_format_expr(expr.exponent, 3)})"
        return f"({text})" if parent_prec > 3 else text
    if isinstance(expr, Func):
        if expr.name == "abs":
            return f"|{_format_expr(expr.arg, 0)}|"
        return f"{expr.name}({_format_expr(expr.arg, 0)})"
    return str(expr)


def explain_solution(result: dict[str, object], definite: bool = False) -> str:
    if not result.get("ok"):
        return str(result.get("error", "Ошибка"))
    lines = []
    if result.get("notes"):
        lines.append("Метод: " + "; ".join(dict.fromkeys(result["notes"])))  # type: ignore[index]
    lines.append("Интеграл: " + format_expr(result["expression"]))  # type: ignore[index]
    if definite:
        lines.append("Первообразная: " + format_expr(result["result"]))  # type: ignore[index]
        lines.append("Значение на [a, b]: " + _format_float(result["value"]))  # type: ignore[index]
    else:
        lines.append("Ответ: " + format_expr(result["result"]) + " + C")  # type: ignore[index]
    return "\n".join(lines)


def parse_definite_bounds(text: str) -> tuple[str, Optional[float], Optional[float]]:
    cleaned = text.strip()
    match = re.search(r"^(.+)\[(.+),(.+)\]$", cleaned)
    if match:
        expr = match.group(1).strip()
        lower = float(match.group(2).strip())
        upper = float(match.group(3).strip())
        return expr, lower, upper
    return cleaned, None, None


# ═══════════════════════════════════════════════════════════════
#  ANSI-терминальный интерфейс
# ═══════════════════════════════════════════════════════════════
import sys
import time
import threading
import shutil

class _C:
    """ANSI colour codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    # foreground
    BLACK   = "\033[30m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    # background
    BG_BLUE = "\033[44m"
    BG_DARK = "\033[40m"


def _term_width() -> int:
    return shutil.get_terminal_size((72, 24)).columns


def _clr() -> None:
    """Clear terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _hr(char: str = "─", color: str = _C.DIM) -> None:
    print(f"{color}{char * _term_width()}{_C.RESET}")


def _print_banner() -> None:
    w = _term_width()
    border = "═" * (w - 2)
    title = "  ∫  РЕШАТЕЛЬ ИНТЕГРАЛОВ  ∫"
    pad = " " * ((w - 2 - len(title)) // 2)
    print(f"{_C.CYAN}{_C.BOLD}╔{border}╗")
    print(f"║{pad}{title}{pad} ║")
    print(f"╚{border}╝{_C.RESET}")


def _section_header(title: str) -> None:
    w = _term_width()
    inner = f"  {title}  "
    bar = "─" * (w - len(inner) - 4)
    print(f"\n{_C.CYAN}┌─{_C.BOLD}{inner}{_C.RESET}{_C.CYAN}{bar}┐{_C.RESET}")


def _ask(prompt: str, default: str = "", hint: str = "") -> str:
    """Colour-coded input prompt."""
    dflt = f" {_C.DIM}[{default}]{_C.RESET}" if default else ""
    hnt  = f"  {_C.DIM}{hint}{_C.RESET}" if hint else ""
    full = f"{_C.CYAN}  ❯ {_C.RESET}{_C.WHITE}{prompt}{_C.RESET}{dflt}{hnt}: "
    val = input(full).strip()
    return val or default


class _Spinner:
    """Non-blocking console spinner shown while computing."""
    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, label: str = "Вычисляю…"):
        self._label = label
        self._stop  = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread:
            self._thread.join()
        # erase spinner line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _run(self):
        i = 0
        while not self._stop.is_set():
            frame = self._FRAMES[i % len(self._FRAMES)]
            sys.stdout.write(
                f"\r  {_C.CYAN}{frame}{_C.RESET}  {_C.DIM}{self._label}{_C.RESET}"
            )
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1


def _animate_line(text: str, delay: float = 0.012) -> None:
    """Print text character-by-character (typewriter effect)."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def _print_result(lines: list[str], *, animated: bool = True) -> None:
    """Pretty-print a result box with optional animation."""
    w  = _term_width()
    iw = w - 4  # inner width
    print()
    print(f"{_C.GREEN}┌{'─' * (w - 2)}┐{_C.RESET}")
    for i, line in enumerate(lines):
        if not line:
            print(f"{_C.GREEN}│{_C.RESET}{' ' * (w - 2)}{_C.GREEN}│{_C.RESET}")
            continue
        # colour key lines differently
        if line.startswith("∫") or line.startswith("=") or line.startswith("≈"):
            color = _C.BOLD + _C.WHITE
        elif line.startswith("Метод:") or line.startswith("Шаг"):
            color = _C.DIM
        elif "Значение" in line or "=" in line:
            color = _C.YELLOW
        else:
            color = _C.RESET
        padded = f"  {line}"
        # strip colour codes for length calculation
        visible = re.sub(r"\033\[[0-9;]*m", "", padded)
        padding = " " * max(0, w - 2 - len(visible))
        row = f"{_C.GREEN}│{_C.RESET}{color}{padded}{_C.RESET}{padding}{_C.GREEN}│{_C.RESET}"
        if animated and i < 8:
            print(row)
            time.sleep(0.04)
        else:
            print(row)
    print(f"{_C.GREEN}└{'─' * (w - 2)}┘{_C.RESET}")


def _print_error(msg: str) -> None:
    print(f"\n  {_C.RED}✗  {msg}{_C.RESET}")


def _pause() -> None:
    """Wait for the user to press Enter before clearing the screen."""
    try:
        input(f"\n  {_C.DIM}Нажмите Enter для возврата в меню…{_C.RESET}")
    except (EOFError, KeyboardInterrupt):
        pass


def _print_steps(notes: list[str]) -> None:
    """Print deduped method notes as a numbered step list."""
    steps = list(dict.fromkeys(n for n in notes if n))
    if not steps:
        return
    print(f"\n  {_C.CYAN}── Метод решения:{_C.RESET}")
    for i, step in enumerate(steps, 1):
        print(f"    {_C.DIM}{i}.{_C.RESET} {step}")


def _print_syntax_help() -> None:
    _clr()
    _print_banner()
    _section_header("СПРАВКА ПО СИНТАКСИСУ")
    items = [
        ("Операторы",
         "+ − * /    сложение, вычитание, умножение, деление\n"
         "           ^ или **   степень:  x^2  или  x**2\n"
         "           ( )        скобки для группировки"),
        ("Функции",
         "sin(x)  cos(x)  tan(x)  cot(x)\n"
         "           exp(x)  log(x) = ln(x)   sqrt(x)  abs(x)\n"
         "           asin(x)  acos(x)  atan(x)"),
        ("Константы",
         "pi  →  π ≈ 3.14159…       e  →  e ≈ 2.71828…"),
        ("Неявное умножение",
         "2x  →  2*x        3sin(x)  →  3*sin(x)\n"
         "           (x+1)(x-1)  →  (x+1)*(x-1)"),
        ("Примеры",
         "x^2 + 3x - 1\n"
         "           (2x-3)*sin(x)\n"
         "           sin(2x) * exp(-x)\n"
         "           1/(x^2 + 1)\n"
         "           sqrt(1 - x^2)"),
    ]
    for title, body in items:
        print(f"\n  {_C.CYAN}{_C.BOLD}{title}:{_C.RESET}")
        for line in body.split("\n"):
            print(f"  {_C.WHITE}{line}{_C.RESET}")
    print()
    _hr()
    input(f"  {_C.DIM}Нажмите Enter для возврата в меню…{_C.RESET}")


def _menu_screen() -> None:
    _clr()
    _print_banner()
    print(f"""
  {_C.DIM}Введите номер нужного действия и нажмите Enter.
  Перед каждым вопросом показаны примеры ввода.
  Введите {_C.RESET}{_C.CYAN}?{_C.RESET}{_C.DIM} для справки по синтаксису.{_C.RESET}

  {_C.BOLD}{_C.WHITE}1{_C.RESET}  {_C.CYAN}∫ f(x) dx{_C.RESET}              Неопределённый интеграл
  {_C.BOLD}{_C.WHITE}2{_C.RESET}  {_C.CYAN}∫[a,b] f(x) dx{_C.RESET}         Определённый интеграл
  {_C.BOLD}{_C.WHITE}3{_C.RESET}  {_C.CYAN}∬ f(x,y) dA{_C.RESET}            Двойной интеграл
  {_C.BOLD}{_C.WHITE}4{_C.RESET}  {_C.CYAN}∫_C f ds{_C.RESET}               Криволинейный 1-го рода
  {_C.BOLD}{_C.WHITE}5{_C.RESET}  {_C.CYAN}∫_C P dx + Q dy{_C.RESET}        Криволинейный 2-го рода
  {_C.BOLD}{_C.WHITE}?{_C.RESET}  Справка по синтаксису
  {_C.BOLD}{_C.WHITE}0{_C.RESET}  Выход
""")
    _hr()


def interactive_cli() -> None:
    while True:
        _menu_screen()
        try:
            choice = input(
                f"  {_C.CYAN}{_C.BOLD}Ваш выбор:{_C.RESET} "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            _clr()
            print(f"\n  {_C.CYAN}До свидания!{_C.RESET}\n")
            return

        if choice in {"0", "q", "exit", "quit", "выход"}:
            _clr()
            print(f"\n  {_C.CYAN}До свидания!{_C.RESET}\n")
            return

        if choice == "?":
            _print_syntax_help()
            continue

        # ── 1. Неопределённый ──────────────────────────────────────────
        if choice == "1":
            _clr()
            _print_banner()
            _section_header("Неопределённый интеграл  ∫ f(x) dx")
            print(f"""
  {_C.DIM}Примеры подынтегральных функций:{_C.RESET}
    {_C.YELLOW}x^2 + 3x - 1{_C.RESET}          {_C.DIM}→  степенной многочлен{_C.RESET}
    {_C.YELLOW}(2x-3)*sin(x){_C.RESET}          {_C.DIM}→  интегрирование по частям{_C.RESET}
    {_C.YELLOW}sin(2x){_C.RESET}                {_C.DIM}→  замена переменной{_C.RESET}
    {_C.YELLOW}1/(x^2 + 1){_C.RESET}            {_C.DIM}→  дробно-рациональная{_C.RESET}
    {_C.YELLOW}x*exp(x){_C.RESET}               {_C.DIM}→  интегрирование по частям{_C.RESET}
""")
            try:
                raw = _ask("Функция f(x)")
                if not raw:
                    continue
                if raw == "?":
                    _print_syntax_help()
                    continue
                var = _ask("Переменная интегрирования", "x")
                print()
                with _Spinner("Вычисляю первообразную…"):
                    result = solve_indefinite(raw, var)
                if result.get("ok"):
                    _print_result([
                        f"∫ {format_expr(result['expression'])} d{var}",
                        "",
                        f"= {format_expr(result['result'])} + C",
                    ])
                    _print_steps(result["notes"])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 2. Определённый ───────────────────────────────────────────
        elif choice == "2":
            _clr()
            _print_banner()
            _section_header("Определённый интеграл  ∫[a,b] f(x) dx")
            print(f"""
  {_C.DIM}Примеры:{_C.RESET}
    {_C.YELLOW}x^2{_C.RESET}     a={_C.YELLOW}0{_C.RESET}  b={_C.YELLOW}2{_C.RESET}     {_C.DIM}→  8/3{_C.RESET}
    {_C.YELLOW}sin(x){_C.RESET}  a={_C.YELLOW}0{_C.RESET}  b={_C.YELLOW}pi{_C.RESET}    {_C.DIM}→  2{_C.RESET}
    {_C.YELLOW}exp(-x^2){_C.RESET} a={_C.YELLOW}0{_C.RESET} b={_C.YELLOW}1{_C.RESET}    {_C.DIM}→  численно ≈ 0.7468{_C.RESET}
""")
            try:
                raw = _ask("Функция f(x)")
                if not raw:
                    continue
                if raw == "?":
                    _print_syntax_help()
                    continue
                var = _ask("Переменная интегрирования", "x")
                lower_str = _ask("Нижний предел a", hint="число или выражение: 0, pi, e…")
                upper_str = _ask("Верхний предел b", hint="число или выражение")
                print()
                with _Spinner("Вычисляю…"):
                    try:
                        result = solve_definite(raw, var, float(lower_str), float(upper_str))
                    except ValueError:
                        result = solve_definite_symbolic(raw, var, lower_str, upper_str)
                if result.get("ok"):
                    lines: list[str] = [
                        f"∫[{lower_str}, {upper_str}] {format_expr(result['expression'])} d{var}",
                        "",
                    ]
                    antideriv = result.get("antiderivative")
                    if antideriv is not None:
                        # Show F(x), then F(b)-F(a) = value
                        lines.append(f"Первообразная:  F({var}) = {format_expr(antideriv)}")
                        if "value" in result:
                            lines.append(f"F({upper_str}) − F({lower_str})  =  {_format_float(result['value'])}")
                        else:
                            lines.append(f"F({upper_str}) − F({lower_str})")
                    elif "value" in result:
                        # Numeric-only (no antiderivative found)
                        lines.append(f"≈  {_format_float(result['value'])}  (метод Симпсона)")
                    else:
                        lines.append("(результат не вычислен)")
                    _print_result(lines)
                    _print_steps(result.get("notes", []))
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 3. Двойной ────────────────────────────────────────────────
        elif choice == "3":
            _clr()
            _print_banner()
            _section_header("Двойной интеграл  ∬ f(x,y) dA")
            print(f"""
  {_C.DIM}Пример  ∫[0,1] ∫[0,x] (x+y) dy dx:{_C.RESET}
    f(x,y) = {_C.YELLOW}x + y{_C.RESET}
    Внутр. перем. = {_C.YELLOW}y{_C.RESET},  пределы: {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}x{_C.RESET}  {_C.DIM}(может зависеть от x){_C.RESET}
    Внешн. перем. = {_C.YELLOW}x{_C.RESET},  пределы: {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}1{_C.RESET}
""")
            try:
                expr     = _ask("Функция f(x, y)")
                if not expr:
                    continue
                iv       = _ask("Внутренняя переменная", "y")
                il       = _ask(f"Нижний предел по {iv}", hint="число или выражение")
                iu       = _ask(f"Верхний предел по {iv}", hint="число или выражение")
                ov       = _ask("Внешняя переменная", "x")
                ol_s     = _ask(f"Нижний предел по {ov}", hint="число")
                ou_s     = _ask(f"Верхний предел по {ov}", hint="число")
                print()
                with _Spinner("Вычисляю двойной интеграл…"):
                    result = solve_double_integral(
                        expr, iv, il, iu, ov, float(ol_s), float(ou_s))
                if result.get("ok"):
                    _print_result([
                        f"∫[{ol_s},{ou_s}] ∫[{il},{iu}] {format_expr(result['expression'])} d{iv} d{ov}",
                        "",
                        f"Шаг 1 — ∫ по {iv}:  {format_expr(result['inner_result'])}",
                        "",
                        f"Значение = {_format_float(result['value'])}",
                    ])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 4. Криволинейный 1-го рода ────────────────────────────────
        elif choice == "4":
            _clr()
            _print_banner()
            _section_header("Криволинейный интеграл 1-го рода  ∫_C f ds")
            print(f"""
  {_C.DIM}r(t) = (x(t), y(t)),  t ∈ [a, b],  ds = √(x'²+y'²) dt{_C.RESET}

  {_C.DIM}Пример  ∫_C (x²+y²) ds,  C: x=cos(t), y=sin(t), t∈[0,pi]:{_C.RESET}
    f     = {_C.YELLOW}x^2 + y^2{_C.RESET}    x(t) = {_C.YELLOW}cos(t){_C.RESET}    y(t) = {_C.YELLOW}sin(t){_C.RESET}
    t: от {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}pi{_C.RESET}
""")
            try:
                f_text  = _ask("Функция f(x, y) [или f(x,y,z)]")
                if not f_text:
                    continue
                x_t     = _ask("Параметризация x(t)")
                y_t     = _ask("Параметризация y(t)")
                use_z   = _ask("Добавить z-координату?", "n", hint="y/n").lower() == "y"
                z_t     = _ask("Параметризация z(t)") if use_z else None
                t_var   = _ask("Параметр", "t")
                t_lo    = _ask("Нижний предел t")
                t_hi    = _ask("Верхний предел t")
                print()
                with _Spinner("Параметризую и интегрирую…"):
                    result = solve_line_integral_1st_kind(
                        f_text, x_t, y_t, z_t, t_var, t_lo, t_hi)
                if result.get("ok"):
                    coord = (f"x(t)={format_expr(result['x_t'])}, y(t)={format_expr(result['y_t'])}"
                             + (f", z(t)={format_expr(result['z_t'])}" if result["z_t"] else ""))
                    _print_result([
                        f"∫_C {format_expr(result['f_expr'])} ds",
                        f"  {coord},  t ∈ [{t_lo}, {t_hi}]",
                        "",
                        f"ds = {format_expr(result['ds'])} dt",
                        f"Подынтегральное: {format_expr(result['integrand'])}",
                        "",
                        f"Значение = {_format_float(result['value'])}",
                    ])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 5. Криволинейный 2-го рода ────────────────────────────────
        elif choice == "5":
            _clr()
            _print_banner()
            _section_header("Криволинейный интеграл 2-го рода  ∫_C P dx + Q dy")
            print(f"""
  {_C.DIM}∫_C P dx + Q dy = ∫[a,b] (P·x' + Q·y') dt{_C.RESET}

  {_C.DIM}Пример  ∫_C y dx + x dy,  C: x=t, y=t², t∈[0,1]:{_C.RESET}
    P = {_C.YELLOW}y{_C.RESET}    Q = {_C.YELLOW}x{_C.RESET}    x(t) = {_C.YELLOW}t{_C.RESET}    y(t) = {_C.YELLOW}t^2{_C.RESET}    t: {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}1{_C.RESET}
""")
            try:
                P      = _ask("Компонента P(x, y)")
                if not P:
                    continue
                Q      = _ask("Компонента Q(x, y)")
                use_z  = _ask("Добавить R и z(t)?", "n", hint="y/n").lower() == "y"
                R      = _ask("Компонента R(x, y, z)") if use_z else None
                x_t    = _ask("Параметризация x(t)")
                y_t    = _ask("Параметризация y(t)")
                z_t    = _ask("Параметризация z(t)") if use_z else None
                t_var  = _ask("Параметр", "t")
                t_lo   = _ask("Нижний предел t")
                t_hi   = _ask("Верхний предел t")
                print()
                with _Spinner("Параметризую и интегрирую…"):
                    result = solve_line_integral_2nd_kind(
                        P, Q, x_t, y_t, R, z_t, t_var, t_lo, t_hi)
                if result.get("ok"):
                    fs = (f"P={format_expr(result['P_expr'])}, Q={format_expr(result['Q_expr'])}"
                          + (f", R={format_expr(result['R_expr'])}" if result.get("R_expr") else ""))
                    coord = (f"x(t)={format_expr(result['x_t'])}, y(t)={format_expr(result['y_t'])}"
                             + (f", z(t)={format_expr(result['z_t'])}" if result["z_t"] else ""))
                    _print_result([
                        "∫_C P dx + Q dy" + (" + R dz" if result.get("R_expr") else ""),
                        f"  {fs}",
                        f"  {coord},  t ∈ [{t_lo}, {t_hi}]",
                        "",
                        f"Подынтегральное: {format_expr(result['integrand'])}",
                        "",
                        f"Значение = {_format_float(result['value'])}",
                    ])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        else:
            print(f"  {_C.RED}✗ Неверный выбор. Введите цифру 0–5 или «?».{_C.RESET}")
            time.sleep(1.2)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Решатель интегралов для типовых школьных и вузовских случаев.")
    parser.add_argument("-e", "--expr", help="Подынтегральное выражение.")
    parser.add_argument("-v", "--var", default="x", help="Переменная интегрирования.")
    parser.add_argument("--lower", help="Нижний предел.")
    parser.add_argument("--upper", help="Верхний предел.")

    parser.add_argument("--double", action="store_true", help="Решать двойной интеграл.")
    parser.add_argument("--inner-var", default="y", help="Внутренняя переменная для двойного интеграла.")
    parser.add_argument("--inner-lower", help="Нижний предел внутреннего интеграла.")
    parser.add_argument("--inner-upper", help="Верхний предел внутреннего интеграла.")
    parser.add_argument("--outer-var", default="x", help="Внешняя переменная для двойного интеграла.")
    parser.add_argument("--outer-lower", help="Нижний предел внешнего интеграла.")
    parser.add_argument("--outer-upper", help="Верхний предел внешнего интеграла.")

    parser.add_argument("--line", choices=["1", "2"], help="Решать криволинейный интеграл 1-го или 2-го рода.")
    parser.add_argument("-P", help="Компонента P векторного поля для криволинейного интеграла 2-го рода.")
    parser.add_argument("-Q", help="Компонента Q векторного поля.")
    parser.add_argument("-R", help="Компонента R векторного поля (опционально).")
    parser.add_argument("-x", "--xt", help="Параметризация x(t).")
    parser.add_argument("-y", "--yt", help="Параметризация y(t).")
    parser.add_argument("-z", "--zt", help="Параметризация z(t) (опционально).")
    parser.add_argument("-t", "--tvar", default="t", help="Параметр кривой t.")
    parser.add_argument("--tlower", help="Нижний предел t.")
    parser.add_argument("--tupper", help="Верхний предел t.")

    args = parser.parse_args(argv)

    if args.double:
        if not (args.expr and args.inner_lower and args.inner_upper and args.outer_lower and args.outer_upper):
            print("Ошибка: Для двойного интеграла необходимо указать --expr, --inner-lower, --inner-upper, --outer-lower, --outer-upper")
            return 1
        result = solve_double_integral(
            args.expr,
            args.inner_var,
            args.inner_lower,
            args.inner_upper,
            args.outer_var,
            float(args.outer_lower),
            float(args.outer_upper)
        )
        print(explain_double_solution(result))
        return 0

    if args.line:
        if args.line == "1":
            if not (args.expr and args.xt and args.yt and args.tlower and args.tupper):
                print("Ошибка: Для криволинейного интеграла 1-го рода укажите --expr, -x, -y, --tlower, --tupper")
                return 1
            result = solve_line_integral_1st_kind(
                f_text=args.expr,
                x_t_text=args.xt,
                y_t_text=args.yt,
                z_t_text=args.zt,
                t_var=args.tvar,
                t_lower=args.tlower,
                t_upper=args.tupper
            )
            print(explain_line_solution(result))
            return 0
        else:
            if not (args.P and args.Q and args.xt and args.yt and args.tlower and args.tupper):
                print("Ошибка: Для криволинейного интеграла 2-го рода укажите -P, -Q, -x, -y, --tlower, --tupper")
                return 1
            result = solve_line_integral_2nd_kind(
                P_text=args.P,
                Q_text=args.Q,
                x_t_text=args.xt,
                y_t_text=args.yt,
                R_text=args.R,
                z_t_text=args.zt,
                t_var=args.tvar,
                t_lower=args.tlower,
                t_upper=args.tupper
            )
            print(explain_line_solution(result))
            return 0

    if args.expr:
        if args.lower is not None and args.upper is not None:
            try:
                l_val = float(args.lower)
                u_val = float(args.upper)
                result = solve_definite(args.expr, args.var, l_val, u_val)
                if result.get("result") is None and "value" in result:
                    print("Метод: " + "; ".join(dict.fromkeys(result["notes"])))
                    print(f"Интеграл: {format_expr(result['expression'])}")
                    print(f"Приблизительное значение (численно): {_format_float(result['value'])}")
                else:
                    print(explain_solution(result, definite=True))
            except ValueError:
                result = solve_definite_symbolic(args.expr, args.var, args.lower, args.upper)
                if result["ok"]:
                    print("Метод: " + "; ".join(dict.fromkeys(result["notes"])))
                    print(f"Интеграл: {format_expr(result['expression'])}")
                    if result.get("result") is not None:
                        print(f"Результат: {format_expr(result['result'])}")
                    else:
                        print(f"Приблизительное значение (численно): {_format_float(result['value'])}")
                else:
                    print(f"Ошибка: {result.get('error')}")
        else:
            result = solve_indefinite(args.expr, args.var)
            print(explain_solution(result))
        return 0

    interactive_cli()
    return 0

