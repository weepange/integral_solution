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

def integrate_rational_function(num_coeffs: list[Fraction], den_coeffs: list[Fraction], var: str) -> tuple[Optional[Expr], list[str]]:
    while den_coeffs and den_coeffs[-1] == 0: den_coeffs.pop()
    while num_coeffs and num_coeffs[-1] == 0: num_coeffs.pop()
    if not den_coeffs: return None, []
    if not num_coeffs: return Const(Fraction(0)), []

    notes = []
    quot, rem = poly_div(num_coeffs, den_coeffs)
    
    res_expr = None
    if any(c != 0 for c in quot):
        quot_expr = make_poly_expr(quot, var)
        res_expr, n = integrate_polynomial(quot_expr, var)
        notes.extend(["Выделение целой части:"] + n)
    
    if not any(c != 0 for c in rem):
        return res_expr, notes

    c_num = rem + [Fraction(0)] * (3 - len(rem))
    c_den = den_coeffs + [Fraction(0)] * (4 - len(den_coeffs))
    
    deg = len(den_coeffs) - 1
    if deg == 1:
        c0 = c_num[0]
        d0, d1 = c_den[0], c_den[1]
        part = simplify(Mul((Const(c0 / d1), Func("log", Func("abs", Add((Mul((Const(d1), Var(var))), Const(d0))))))))
        res_expr = part if res_expr is None else simplify(Add((res_expr, part)))
        notes.append("Интегрирование дроби с линейным знаменателем")
        return res_expr, notes

    if deg == 2:
        C, B = c_num[0], c_num[1]
        e, d, c = c_den[0], c_den[1], c_den[2]
        
        part = None
        if B != 0:
            part1 = simplify(Mul((Const(B / (2*c)), Func("log", Func("abs", make_poly_expr(den_coeffs, var))))))
            part = part1
        
        C_rem = C - B*d / (2*c)
        if C_rem != 0:
            k = e - d**2 / (4*c)
            if k > 0:
                k_c_expr = Func("sqrt", Const(Fraction(k)/c))
                inv_k_c_expr = Func("sqrt", Const(Fraction(c)/k))
                u = Add((Var(var), Const(d / (2*c))))
                atan_arg = Mul((u, inv_k_c_expr))
                part2 = Mul((Const(C_rem / c), inv_k_c_expr, Func("atan", atan_arg)))
                part = part2 if part is None else simplify(Add((part, part2)))
            else:
                return None, []
                
        res_expr = part if res_expr is None else simplify(Add((res_expr, part)))
        notes.append("Интегрирование дроби с квадратичным знаменателем (выделение полного квадрата)")
        return res_expr, notes

    if deg == 3:
        d0, d1, d2, d3 = c_den[0], c_den[1], c_den[2], c_den[3]
        if d1 == 0 and d2 == 0 and d3 != 0:
            a_cubed = -d0 / d3
            a_val = None
            if a_cubed.denominator == 1:
                a_float = float(a_cubed.numerator) ** (1/3)
                if abs(a_float - round(a_float)) < 1e-7:
                    a_val = Fraction(int(round(a_float)))
            
            if a_val is not None:
                c0, c1, c2 = c_num[0] / d3, c_num[1] / d3, c_num[2] / d3
                a = a_val
                
                A = (c0 + a * c1 + a**2 * c2) / (3 * a**2)
                B = c2 - A
                C = c1 + a * c2 - 2 * a * A
                
                part1 = simplify(Mul((Const(A), Func("log", Func("abs", Add((Var(var), Const(-a))))))))
                p2_expr, n2 = integrate_rational_function([C, B], [a**2, a, Fraction(1)], var)
                if p2_expr is None: return None, []
                
                part = simplify(Add((part1, p2_expr)))
                res_expr = part if res_expr is None else simplify(Add((res_expr, part)))
                notes.append("Разложение на простейшие дроби (знаменатель x^3 - a^3)")
                notes.extend(n2)
                return res_expr, notes

    return None, []

def integrate(expr: Expr, var: str = "x") -> tuple[Optional[Expr], list[str]]:
    expr = simplify(expr)
    notes: list[str] = []

    # === РАЦИОНАЛЬНЫЕ ФУНКЦИИ ===
    num, den = extract_fraction(expr, var)
    if num is not None and den is not None:
        num_coeffs = get_poly_coeffs(num, var)
        den_coeffs = get_poly_coeffs(den, var)
        if num_coeffs is not None and den_coeffs is not None:
            ans, subnotes = integrate_rational_function(num_coeffs, den_coeffs, var)
            if ans is not None:
                return ans, notes + subnotes
    # ============================

    # === ТРИГОНОМЕТРИЯ ===
    from integral_solver.calculus.trig_utils import extract_sin_cos_powers, integrate_sin_cos_powers
    trig_powers = extract_sin_cos_powers(expr, var)
    if trig_powers is not None:
        n, m, a = trig_powers
        ans = integrate_sin_cos_powers(n, m, a, var)
        if ans is not None:
            notes.append(f"Интеграл от комбинации степеней синуса и косинуса: sin^({n}) cos^({m})")
            return ans, notes
    # ============================

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

def expr_contains_only_var(expr: Expr, var: str) -> bool:
    return expr.contains_var(var)

def get_poly_coeffs(expr: Expr, var: str) -> Optional[list[Fraction]]:
    expr = simplify(expr)
    if not expr.contains_var(var):
        if isinstance(expr, Const): return [expr.value]
        try:
            return [Fraction(evaluate_constant_expr(expr)).limit_denominator(1000000)]
        except:
            return None
    if isinstance(expr, Var) and expr.name == var:
        return [Fraction(0), Fraction(1)]
    if isinstance(expr, Add):
        res = []
        for term in expr.terms:
            c = get_poly_coeffs(term, var)
            if c is None: return None
            while len(res) < len(c): res.append(Fraction(0))
            for i, val in enumerate(c):
                res[i] += val
        return res
    if isinstance(expr, Mul):
        res = [Fraction(1)]
        for factor in expr.factors:
            c = get_poly_coeffs(factor, var)
            if c is None: return None
            new_res = [Fraction(0)] * (len(res) + len(c) - 1)
            for i, v1 in enumerate(res):
                for j, v2 in enumerate(c):
                    new_res[i+j] += v1 * v2
            res = new_res
        return res
    if isinstance(expr, Pow):
        if isinstance(expr.exponent, Const) and expr.exponent.value.denominator == 1 and expr.exponent.value >= 0:
            n = int(expr.exponent.value)
            base_c = get_poly_coeffs(expr.base, var)
            if base_c is None: return None
            res = [Fraction(1)]
            for _ in range(n):
                new_res = [Fraction(0)] * (len(res) + len(base_c) - 1)
                for i, v1 in enumerate(res):
                    for j, v2 in enumerate(base_c):
                        new_res[i+j] += v1 * v2
                res = new_res
            return res
    return None

def extract_fraction(expr: Expr, var: str) -> tuple[Optional[Expr], Optional[Expr]]:
    if isinstance(expr, Pow) and isinstance(expr.exponent, Const) and expr.exponent.value < 0:
        if expr.exponent.value == -1:
            return Const(Fraction(1)), expr.base
        else:
            return Const(Fraction(1)), Pow(expr.base, Const(-expr.exponent.value))
    if isinstance(expr, Mul):
        num_factors = []
        den_factors = []
        for factor in expr.factors:
            if isinstance(factor, Pow) and isinstance(factor.exponent, Const) and factor.exponent.value < 0:
                if factor.exponent.value == -1:
                    den_factors.append(factor.base)
                else:
                    den_factors.append(Pow(factor.base, Const(-factor.exponent.value)))
            else:
                num_factors.append(factor)
        if not den_factors:
            return None, None
        num = simplify(Mul(tuple(num_factors))) if num_factors else Const(Fraction(1))
        den = simplify(Mul(tuple(den_factors))) if len(den_factors) > 1 else den_factors[0]
        return num, den
    return None, None

def poly_div(num: list[Fraction], den: list[Fraction]) -> tuple[list[Fraction], list[Fraction]]:
    num = list(num)
    den = list(den)
    while den and den[-1] == 0: den.pop()
    if not den: raise ValueError("Division by zero polynomial")
    while num and num[-1] == 0: num.pop()
    
    if len(num) < len(den):
        return [Fraction(0)], num
    
    quot = [Fraction(0)] * (len(num) - len(den) + 1)
    for i in range(len(num) - len(den), -1, -1):
        quot[i] = num[i + len(den) - 1] / den[-1]
        for j in range(len(den)):
            num[i + j] -= quot[i] * den[j]
    while quot and quot[-1] == 0: quot.pop()
    while num and num[-1] == 0: num.pop()
    return quot, num

def make_poly_expr(coeffs: list[Fraction], var: str) -> Expr:
    terms = []
    for i, c in enumerate(coeffs):
        if c == 0: continue
        if i == 0: terms.append(Const(c))
        elif i == 1: terms.append(Mul((Const(c), Var(var))))
        else: terms.append(Mul((Const(c), Pow(Var(var), Const(Fraction(i))))))
    if not terms: return Const(Fraction(0))
    if len(terms) == 1: return terms[0]
    return Add(tuple(terms))

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
