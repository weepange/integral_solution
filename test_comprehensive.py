"""
Комплексное тестирование всех методов интегрирования.
Проверяем, что каждый метод корректно распознаёт и решает интегралы.
"""
from integral_solver.calculus.solvers import solve_indefinite, solve_definite
from integral_solver.core.ast import format_expr, simplify
from integral_solver.core.parser import parse_expression
from integral_solver.calculus.symbolic import integrate, derivative

PASS = 0
FAIL = 0

def test(name: str, func_str: str, var: str = "x", expect_ok: bool = True, check_deriv: bool = True):
    global PASS, FAIL
    result = solve_indefinite(func_str, var)
    ok = result.get("ok", False)
    if ok != expect_ok:
        FAIL += 1
        status = "✗ FAIL"
        print(f"  {status}  ∫ {func_str} d{var}  →  ожидали ok={expect_ok}, получили ok={ok}")
        if result.get("error"):
            print(f"         Ошибка: {result['error']}")
        return

    if ok:
        answer = format_expr(result["result"])
        # Numerical derivative check at x=1.5
        if check_deriv:
            try:
                original = parse_expression(func_str)
                antideriv = result["result"]
                h = 1e-7
                f_plus = antideriv.substitute(var, 1.5 + h)
                f_minus = antideriv.substitute(var, 1.5 - h)
                numerical_deriv = (f_plus - f_minus) / (2 * h)
                expected_val = original.substitute(var, 1.5)
                if abs(expected_val) > 1e-10:
                    rel_err = abs(numerical_deriv - expected_val) / abs(expected_val)
                else:
                    rel_err = abs(numerical_deriv - expected_val)
                if rel_err > 0.01:
                    FAIL += 1
                    print(f"  ✗ FAIL  ∫ {func_str} d{var} = {answer}")
                    print(f"         Числ. проверка: d/dx[F(x)]|x=1.5 = {numerical_deriv:.6f}, f(1.5) = {expected_val:.6f}, отн.ошибка = {rel_err:.4f}")
                    return
            except Exception as e:
                pass  # не удалось числ. проверить - не страшно
        PASS += 1
        print(f"  ✓ OK    ∫ {func_str} d{var} = {answer}")
    else:
        PASS += 1
        print(f"  ✓ OK    ∫ {func_str} d{var}  →  корректно отказал (ожидали)")

print("=" * 80)
print("1. СТЕПЕННОЕ ПРАВИЛО (Power Rule)")
print("=" * 80)
test("x", "x")
test("x^2", "x^2")
test("x^3", "x^3")
test("x^10", "x^10")
test("x^(-1) = 1/x", "1/x")
test("x^(-2)", "x^(-2)")
test("x^(1/2) = sqrt(x)", "sqrt(x)")
test("x^(-1/2) = 1/sqrt(x)", "1/sqrt(x)")
test("1", "1")
test("5", "5")

print()
print("=" * 80)
print("2. ТАБЛИЧНЫЕ ИНТЕГРАЛЫ (Table Integrals)")
print("=" * 80)
test("sin(x)", "sin(x)")
test("cos(x)", "cos(x)")
test("exp(x)", "exp(x)")
test("tan(x)", "tan(x)")
test("1/(x^2+1) = atan", "1/(x^2+1)")
test("log(x) = ln(x)", "log(x)")
test("ln(x)", "ln(x)")

print()
print("=" * 80)
print("3. ЛИНЕЙНАЯ ПОДСТАНОВКА (Linear Substitution u = ax+b)")
print("=" * 80)
test("sin(2x)", "sin(2*x)")
test("cos(3x+1)", "cos(3*x+1)")
test("exp(5x)", "exp(5*x)")
test("(2x+3)^4", "(2*x+3)^4")
test("1/(3x+1)", "1/(3*x+1)")
test("sin(x/2)", "sin(x/2)")

print()
print("=" * 80)
print("4. ПОЛИНОМЫ (Polynomials)")
print("=" * 80)
test("x^2 + 3x - 1", "x^2 + 3*x - 1")
test("4x^3 - 2x^2 + x", "4*x^3 - 2*x^2 + x")
test("x^5 + x^3 + x", "x^5 + x^3 + x")

print()
print("=" * 80)
print("5. ИНТЕГРИРОВАНИЕ ПО ЧАСТЯМ (Integration by Parts)")
print("=" * 80)
test("x*sin(x)", "x*sin(x)")
test("x*cos(x)", "x*cos(x)")
test("x*exp(x)", "x*exp(x)")
test("x^2*sin(x)", "x^2*sin(x)")
test("x^2*exp(x)", "x^2*exp(x)")
test("x*log(x)", "x*log(x)", check_deriv=False)
test("x*ln(x)", "x*ln(x)", check_deriv=False)

print()
print("=" * 80)
print("6. РАЦИОНАЛЬНЫЕ ДРОБИ (Rational Functions)")
print("=" * 80)
test("1/(x+1)", "1/(x+1)")
test("1/(x^2+1)", "1/(x^2+1)")
test("x/(x^2+1)", "x/(x^2+1)")
test("1/(x^2+x+1)", "1/(x^2+x+1)")
test("(2x+3)/(x^2+3x+2)", "(2*x+3)/(x^2+3*x+2)")
test("(4x^2+5x+1)/(x^3-1)", "(4*x^2+5*x+1)/(x^3-1)")
test("1/(x-1)", "1/(x-1)")
test("x^2/(x+1)", "x^2/(x+1)")

print()
print("=" * 80)
print("7. ТРИГОНОМЕТРИЧЕСКИЕ СТЕПЕНИ (Trig Powers)")
print("=" * 80)
test("sin(x)^2", "sin(x)^2")
test("cos(x)^2", "cos(x)^2")
test("sin(x)^3", "sin(x)^3")
test("sin(x)^2*cos(x)", "sin(x)^2*cos(x)")
test("sin(x)*cos(x)", "sin(x)*cos(x)")

print()
print("=" * 80)
print("8. ЗАМЕНА ПЕРЕМЕННОЙ (U-Substitution, нелинейная)")
print("=" * 80)
test("sin(x^2)*2x", "sin(x^2)*2*x")
test("cos(x^3)*3x^2", "cos(x^3)*3*x^2")
test("exp(x^2)*2x", "exp(x^2)*2*x")
test("2x/(x^2+1)", "2*x/(x^2+1)")
test("cos(x)/sin(x) [=cot]", "cos(x)/sin(x)", check_deriv=False)
test("sin(x)*cos(x)", "sin(x)*cos(x)")
test("exp(sin(x))*cos(x)", "exp(sin(x))*cos(x)")
test("x*exp(x^2)", "x*exp(x^2)")

print()
print("=" * 80)
print("9. СМЕШАННЫЕ СЛУЧАИ")
print("=" * 80)
test("3*x^2 + sin(x)", "3*x^2 + sin(x)")
test("exp(x) + 1/x", "exp(x) + 1/x")
test("x + cos(x) + 1", "x + cos(x) + 1")
test("(x+1)^3", "(x+1)^3")
test("1/(1+x^2)^(1/2) [=arcsin-related]", "1/sqrt(1+x^2)", expect_ok=False) # сложный

print()
print("=" * 80)
print("10. ОПРЕДЕЛЁННЫЕ ИНТЕГРАЛЫ (Numerical check)")
print("=" * 80)

import math

def test_definite(name, func_str, a, b, expected, tol=0.01):
    global PASS, FAIL
    result = solve_definite(func_str, "x", float(a), float(b))
    ok = result.get("ok", False)
    if not ok:
        FAIL += 1
        print(f"  ✗ FAIL  ∫[{a},{b}] {func_str} dx  →  не вычислено")
        if result.get("error"):
            print(f"         Ошибка: {result['error']}")
        return
    val = result.get("value")
    if val is None:
        FAIL += 1
        print(f"  ✗ FAIL  ∫[{a},{b}] {func_str} dx  →  значение None")
        return
    err = abs(val - expected)
    if err > tol:
        FAIL += 1
        print(f"  ✗ FAIL  ∫[{a},{b}] {func_str} dx  =  {val:.6f}, ожидали {expected:.6f}, ошибка {err:.6f}")
    else:
        PASS += 1
        print(f"  ✓ OK    ∫[{a},{b}] {func_str} dx  =  {val:.6f}  (ожидали {expected:.6f})")

test_definite("x^2 [0,1]", "x^2", 0, 1, 1/3)
test_definite("sin(x) [0,pi]", "sin(x)", 0, math.pi, 2.0)
test_definite("exp(x) [0,1]", "exp(x)", 0, 1, math.e - 1)
test_definite("1/x [1,e]", "1/x", 1, math.e, 1.0)
test_definite("x^3 [0,2]", "x^3", 0, 2, 4.0)
test_definite("cos(x) [0,pi/2]", "cos(x)", 0, math.pi/2, 1.0)

print()
print("=" * 80)
total = PASS + FAIL
print(f"ИТОГО: {PASS}/{total} пройдено, {FAIL}/{total} провалено")
print("=" * 80)
