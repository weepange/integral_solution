from integral_solver.calculus.solvers import solve_indefinite
from integral_solver.cli.main import explain_solution

def test():
    # test sin^3(x) cos^2(x)
    res = solve_indefinite("sin(x)^3 * cos(x)^2")
    if res["ok"]:
        print(explain_solution(res))
    else:
        print("Failed:", res)

test()
