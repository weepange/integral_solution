from fractions import Fraction
from integral_solver import *

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

def test():
    expr = parse_expression("(4x^2 + 5x + 1)/(x^3 - 1)")
    num, den = extract_fraction(expr, "x")
    print("Num:", num)
    print("Den:", den)
    nc = get_poly_coeffs(num, "x")
    dc = get_poly_coeffs(den, "x")
    print("Num coeffs:", nc)
    print("Den coeffs:", dc)

test()
