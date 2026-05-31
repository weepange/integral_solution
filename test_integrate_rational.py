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

def my_integrate(expr: Expr, var: str = "x") -> tuple[Optional[Expr], list[str]]:
    # try extracting fraction
    num, den = extract_fraction(expr, var)
    if num is not None and den is not None:
        num_coeffs = get_poly_coeffs(num, var)
        den_coeffs = get_poly_coeffs(den, var)
        if num_coeffs is not None and den_coeffs is not None:
            ans, notes = integrate_rational_function(num_coeffs, den_coeffs, var)
            if ans is not None:
                return ans, notes
    return integrate(expr, var)

print("==== TEST ====")
expr = parse_expression("(4x^2 + 5x + 1)/(x^3 - 1)")
ans, notes = my_integrate(expr, "x")
print("Answer:", format_expr(ans))
print("Notes:", notes)
