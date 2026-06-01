from integral_solver.core.printer import pretty_print
from integral_solver.core.parser import parse_expression

expr = parse_expression("(4*x^2 + 5*x + 1)/(x^3 - 1)")
block = pretty_print(expr)

for line in block.lines:
    print(line)

print("\nAnother one:")
expr2 = parse_expression("sin(x)^3 * cos(x)^2")
b2 = pretty_print(expr2)
for line in b2.lines:
    print(line)
