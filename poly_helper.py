import math
from fractions import Fraction

class Poly:
    def __init__(self, coeffs):
        # coeffs[i] is coefficient of x^i
        # remove trailing zeros
        while len(coeffs) > 1 and coeffs[-1] == 0:
            coeffs.pop()
        self.coeffs = [Fraction(c) for c in coeffs]
    
    @property
    def degree(self):
        return len(self.coeffs) - 1

    def __str__(self):
        return " + ".join(f"{c}x^{i}" for i, c in enumerate(self.coeffs) if c != 0) or "0"

    def eval(self, x):
        return sum(c * x**i for i, c in enumerate(self.coeffs))

print(Poly([1, 2, 3]))
