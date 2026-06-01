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

    inner_lower = to_expr(inner_lower_or_text)
    inner_upper = to_expr(inner_upper_or_text)

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

def parse_definite_bounds(text: str) -> tuple[str, Optional[float], Optional[float]]:
    cleaned = text.strip()
    match = re.search(r"^(.+)\[(.+),(.+)\]$", cleaned)
    if match:
        expr = match.group(1).strip()
        lower = float(match.group(2).strip())
        upper = float(match.group(3).strip())
        return expr, lower, upper
    return cleaned, None, None
