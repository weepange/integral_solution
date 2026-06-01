from integral_solver.calculus.solvers import solve_indefinite
from integral_solver.cli.main import explain_solution

res = solve_indefinite("(4*x^2 + 5*x + 1)/(x^3 - 1)")
print(explain_solution(res))
