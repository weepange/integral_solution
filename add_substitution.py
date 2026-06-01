import re

with open("integral_solver/calculus/symbolic.py", "r") as f:
    content = f.read()

# 1. Update derivative to support chain rule for Pow
pow_deriv_old = """    if isinstance(expr, Pow):
        if isinstance(expr.base, Var) and expr.base.name == var and isinstance(expr.exponent, Const):
            n = expr.exponent.value
            return simplify(Mul((Const(n), Pow(expr.base, Const(n - 1)))))
        if isinstance(expr.base, Const) and isinstance(expr.exponent, Const):
            return Const(Fraction(0))
        return Const(Fraction(0))"""

pow_deriv_new = """    if isinstance(expr, Pow):
        if isinstance(expr.exponent, Const):
            n = expr.exponent.value
            if n == 0:
                return Const(Fraction(0))
            base_der = derivative(expr.base, var)
            return simplify(Mul((Const(n), Pow(expr.base, Const(n - 1)), base_der)))
        return Const(Fraction(0))"""

content = content.replace(pow_deriv_old, pow_deriv_new)


# 2. Implement substitution method
subst_code = """
def extract_subexpressions(expr: Expr, var: str) -> set[Expr]:
    \"\"\"Finds all non-trivial subexpressions that could be substitution candidates.\"\"\"
    candidates = set()
    def visit(e: Expr):
        if isinstance(e, Pow):
            if e.base.contains_var(var) and not (isinstance(e.base, Var) and e.base.name == var):
                candidates.add(e.base)
            visit(e.base)
            visit(e.exponent)
        elif isinstance(e, Func):
            if e.arg.contains_var(var) and not (isinstance(e.arg, Var) and e.arg.name == var):
                candidates.add(e.arg)
            visit(e.arg)
        elif isinstance(e, Add):
            for t in e.terms: visit(t)
        elif isinstance(e, Mul):
            for f in e.factors: visit(f)
    visit(expr)
    return candidates

def divide_expr(expr: Expr, divisor: Expr) -> Optional[Expr]:
    \"\"\"Attempts to divide expr by divisor. Returns the quotient or None.\"\"\"
    expr = simplify(expr)
    divisor = simplify(divisor)
    if expr == divisor:
        return Const(Fraction(1))
    
    # If divisor is Const*X, and expr contains X, we can cancel X
    div_const = Fraction(1)
    div_rest = divisor
    if isinstance(divisor, Mul) and isinstance(divisor.factors[0], Const):
        div_const = divisor.factors[0].value
        if len(divisor.factors) == 2:
            div_rest = divisor.factors[1]
        else:
            div_rest = Mul(divisor.factors[1:])
            
    if isinstance(divisor, Const):
        div_const = divisor.value
        div_rest = Const(Fraction(1))

    # Match in Mul
    if isinstance(expr, Mul):
        factors = list(expr.factors)
        # find div_rest
        found = False
        for i, f in enumerate(factors):
            if f == div_rest:
                factors.pop(i)
                found = True
                break
        if found:
            factors.insert(0, Const(Fraction(1, div_const)))
            return simplify(Mul(tuple(factors)))
            
    if expr == div_rest:
        return Const(Fraction(1, div_const))

    return None

def integrate_by_substitution(expr: Expr, var: str) -> Optional[tuple[Expr, list[str]]]:
    candidates = extract_subexpressions(expr, var)
    for g in candidates:
        g_prime = derivative(g, var)
        if isinstance(g_prime, Const) and g_prime.value == 0:
            continue
            
        quotient = divide_expr(expr, g_prime)
        if quotient is not None:
            # We successfully separated f(g(x)) * g'(x)
            # Now we need to express quotient entirely in terms of u = g(x)
            # We can do this by substituting g(x) with a temporary variable 'u'
            # For a simple implementation, we just replace instances of `g` in `quotient` with `Var('u')`.
            
            def replace_g(e: Expr) -> Expr:
                if e == g:
                    return Var('u')
                if isinstance(e, Add):
                    return Add(tuple(replace_g(t) for t in e.terms))
                if isinstance(e, Mul):
                    return Mul(tuple(replace_g(f) for f in e.factors))
                if isinstance(e, Pow):
                    return Pow(replace_g(e.base), replace_g(e.exponent))
                if isinstance(e, Func):
                    return Func(e.name, replace_g(e.arg))
                return e
                
            f_u = simplify(replace_g(quotient))
            if f_u.contains_var(var):
                # substitution failed to eliminate var
                continue
                
            # integrate f_u w.r.t 'u'
            F_u, notes = integrate(f_u, 'u')
            if F_u is not None:
                # substitute back u = g(x)
                F_x = simplify(F_u.substitute_expr('u', g))
                from integral_solver.core.ast import format_expr
                return F_x, [f"Замена переменной: u = {format_expr(g)}, du = {format_expr(g_prime)} dx"] + notes
                
    return None
"""

# Insert the generic substitution function before integrate_polynomial
content = content.replace("def integrate_polynomial(", subst_code + "\ndef integrate_polynomial(")

# Add the hook in integrate()
hook_code = """
    if isinstance(expr, Mul) or isinstance(expr, Func) or isinstance(expr, Pow):
        subst = integrate_by_substitution(expr, var)
        if subst is not None:
            return subst
"""

# Find where to insert it in integrate().
# After by_parts seems good.
target = """        by_parts = integrate_by_parts(expr, var)
        if by_parts is not None:
            notes.append("Интегрирование по частям: ∫u dv = u·v − ∫v du")
            return by_parts, notes"""

content = content.replace(target, target + "\n" + hook_code)

with open("integral_solver/calculus/symbolic.py", "w") as f:
    f.write(content)
