from integral_solver.core.ast import *
from integral_solver.calculus.symbolic import split_linear

def extract_trig_power(expr: Expr, func_name: str, var: str) -> Optional[tuple[int, Fraction]]:
    # Extracts (power, a) for func_name(a*x)
    expr = simplify(expr)
    if isinstance(expr, Func) and expr.name == func_name:
        lin = split_linear(expr.arg, var)
        if lin and lin[0] != 0 and lin[1] == 0:
            return 1, lin[0]
    if isinstance(expr, Pow) and isinstance(expr.exponent, Const) and expr.exponent.value.denominator == 1 and expr.exponent.value >= 1:
        n = int(expr.exponent.value)
        base = simplify(expr.base)
        if isinstance(base, Func) and base.name == func_name:
            lin = split_linear(base.arg, var)
            if lin and lin[0] != 0 and lin[1] == 0:
                return n, lin[0]
    return None

def extract_sin_cos_powers(expr: Expr, var: str) -> Optional[tuple[int, int, Fraction]]:
    expr = simplify(expr)
    sin_p = extract_trig_power(expr, "sin", var)
    if sin_p is not None: return sin_p[0], 0, sin_p[1]
    cos_p = extract_trig_power(expr, "cos", var)
    if cos_p is not None: return 0, cos_p[0], cos_p[1]
    
    if isinstance(expr, Mul) and len(expr.factors) == 2:
        sin_p = extract_trig_power(expr.factors[0], "sin", var)
        cos_p = extract_trig_power(expr.factors[1], "cos", var)
        if sin_p and cos_p and sin_p[1] == cos_p[1]:
            return sin_p[0], cos_p[0], sin_p[1]
        
        sin_p = extract_trig_power(expr.factors[1], "sin", var)
        cos_p = extract_trig_power(expr.factors[0], "cos", var)
        if sin_p and cos_p and sin_p[1] == cos_p[1]:
            return sin_p[0], cos_p[0], sin_p[1]
    return None

def integrate_sin_cos_powers(n: int, m: int, a: Fraction, var: str) -> Optional[Expr]:
    # Integrates sin(ax)^n * cos(ax)^m
    # Using simple recursive/reduction approach or substitution
    # For now, let's handle cases where at least one is odd, or both are even and small.
    # Actually, we can just return None if we don't support it yet.
    # If m is odd (m = 2k + 1):
    # int sin(ax)^n (1 - sin(ax)^2)^k cos(ax) dx
    # Let u = sin(ax), du = a cos(ax) dx
    # => 1/a int u^n (1 - u^2)^k du
    # If n is odd (n = 2k + 1):
    # int (1 - cos(ax)^2)^k cos(ax)^m sin(ax) dx
    # Let u = cos(ax), du = -a sin(ax) dx
    # => -1/a int (1 - u^2)^k u^m du
    from integral_solver.calculus.symbolic import integrate_polynomial
    from integral_solver.calculus.symbolic import make_poly_expr

    def expand_binom(k):
        # returns coeffs for (1 - u^2)^k = sum_{i=0}^k C(k,i) (-1)^i u^{2i}
        import math
        coeffs = [Fraction(0)] * (2*k + 1)
        for i in range(k + 1):
            c = Fraction(math.comb(k, i) * ((-1)**i))
            coeffs[2*i] = c
        return coeffs

    if m % 2 == 1:
        k = (m - 1) // 2
        coeffs = expand_binom(k)
        # multiply by u^n
        new_coeffs = [Fraction(0)] * (len(coeffs) + n)
        for i, c in enumerate(coeffs):
            new_coeffs[i + n] = c
        poly = make_poly_expr(new_coeffs, "u")
        # integrate w.r.t u
        ans_u, _ = integrate_polynomial(poly, "u")
        if ans_u is None: return None
        # substitute u = sin(ax)
        u_expr = Func("sin", Mul((Const(a), Var(var))) if a != 1 else Var(var))
        ans = ans_u.substitute_expr("u", u_expr)
        return simplify(Mul((Const(Fraction(1, a)), ans)))
    
    if n % 2 == 1:
        k = (n - 1) // 2
        coeffs = expand_binom(k)
        new_coeffs = [Fraction(0)] * (len(coeffs) + m)
        for i, c in enumerate(coeffs):
            new_coeffs[i + m] = c
        poly = make_poly_expr(new_coeffs, "u")
        ans_u, _ = integrate_polynomial(poly, "u")
        if ans_u is None: return None
        u_expr = Func("cos", Mul((Const(a), Var(var))) if a != 1 else Var(var))
        ans = ans_u.substitute_expr("u", u_expr)
        return simplify(Mul((Const(Fraction(-1, a)), ans)))

    return None
