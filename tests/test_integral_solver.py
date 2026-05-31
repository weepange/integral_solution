import unittest

from integral_solver import explain_solution, solve_definite, solve_indefinite


class IntegralSolverTests(unittest.TestCase):
    def test_polynomial(self) -> None:
        result = solve_indefinite("x^2 + 2*x + 1")
        self.assertTrue(result["ok"])
        text = explain_solution(result)
        self.assertIn("x^(3)", text)

    def test_trig(self) -> None:
        result = solve_indefinite("sin(x)")
        self.assertTrue(result["ok"])
        text = explain_solution(result)
        self.assertIn("cos(x)", text)

    def test_exponential(self) -> None:
        result = solve_indefinite("exp(3*x)")
        self.assertTrue(result["ok"])
        text = explain_solution(result)
        self.assertIn("exp(3*x)", text)

    def test_definite(self) -> None:
        result = solve_definite("x", "x", 0, 2)
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(float(result["value"]), 2.0)

    def test_log(self) -> None:
        result = solve_indefinite("log(x)")
        self.assertTrue(result["ok"])
        text = explain_solution(result)
        self.assertIn("log(|x|)", text)

    def test_by_parts(self) -> None:
        result = solve_indefinite("x*sin(x)")
        self.assertTrue(result["ok"])
        text = explain_solution(result)
        self.assertIn("cos(x)", text)
        self.assertIn("sin(x)", text)

    def test_parse_definite_bounds(self) -> None:
        from integral_solver import parse_definite_bounds
        expr, lower, upper = parse_definite_bounds("x^2[0,2]")
        self.assertEqual(expr, "x^2")
        self.assertEqual(lower, 0.0)
        self.assertEqual(upper, 2.0)

    def test_double_integral(self) -> None:
        from integral_solver import solve_double_integral
        result = solve_double_integral("x + y", "y", 0, 2, "x", 0, 1)
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(float(result["value"]), 3.0)

    def test_line_integral_1st_kind(self) -> None:
        from integral_solver import solve_line_integral_1st_kind
        result = solve_line_integral_1st_kind(
            f_text="x + y", x_t_text="cos(t)", y_t_text="sin(t)", z_t_text=None, t_var="t", t_lower=0, t_upper="pi"
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(float(result["value"]), 2.0)

    def test_line_integral_2nd_kind(self) -> None:
        from integral_solver import solve_line_integral_2nd_kind
        import math
        result = solve_line_integral_2nd_kind(
            P_text="-1*y", Q_text="x", R_text=None, x_t_text="cos(t)", y_t_text="sin(t)", z_t_text=None, t_var="t", t_lower=0, t_upper="pi"
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(float(result["value"]), math.pi, places=4)

    def test_numerical_fallback(self) -> None:
        # e^(-x^2) has no elementary antiderivative
        result = solve_definite("exp(-1*x^2)", "x", 0, 1)
        self.assertTrue(result["ok"])
        # The integral of e^(-x^2) from 0 to 1 is erf(1)*sqrt(pi)/2 ≈ 0.746824
        self.assertAlmostEqual(float(result["value"]), 0.746824, places=4)
        self.assertTrue(any("Симпсона" in note for note in result["notes"]))


if __name__ == "__main__":
    unittest.main()



