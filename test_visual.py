from integral_solver.calculus.solvers import solve_indefinite
from integral_solver.core.printer import pretty_print, hstack, Block

tests = [
    "sin(x)",
    "x*exp(x)",
    "x^2 + 3*x - 1",
    "1/(x^2+1)",
    "sin(x)^2",
    "cos(x)/sin(x)",
    "x*ln(x)",
]

for func in tests:
    result = solve_indefinite(func)
    if result.get("ok"):
        expr_blk = pretty_print(result['expression'])
        res_blk = pretty_print(result['result'])
        left = hstack(Block.text("\u222b "), expr_blk, Block.text(" dx"))
        right = hstack(res_blk, Block.text(" + C"))
        final = hstack(left, Block.text(" = "), right)
        print()
        for line in final.lines:
            print("  " + line)
    else:
        print(f"  FAIL: {func}")
    print()
