import re

with open("integral_solver/cli/main.py", "r") as f:
    content = f.read()

# Update explain_double_solution and explain_line_solution to use 2D where appropriate?
# Actually, the quickest fix is to change the interactive loop to use `pretty_print` directly instead of `format_expr`.

# Let's replace the `_print_result` arrays in the interactive loop.
# Menu 1: Indefinite
replace_1 = """                if result.get("ok"):
                    from integral_solver.core.printer import pretty_print, hstack, Block
                    expr_blk = pretty_print(result['expression'])
                    res_blk = pretty_print(result['result'])
                    
                    # Create the layout
                    int_sym = Block.text(f"∫ d{var}")
                    eq_sym = Block.text(" = ")
                    c_sym = Block.text(" + C")
                    
                    # ∫ f(x) dx
                    left = hstack(Block.text("∫ "), expr_blk, Block.text(f" d{var}"))
                    right = hstack(res_blk, c_sym)
                    
                    final_blk = hstack(left, eq_sym, right)
                    
                    _print_result([""] + ["  " + l for l in final_blk.lines] + [""])
                    _print_steps(result["notes"])"""

content = re.sub(r'if result\.get\("ok"\):\s*_print_result\(\[\s*f"∫ \{format_expr[^\]]+\]\)\s*_print_steps\(result\["notes"\]\)', replace_1, content)

# Menu 2: Definite
replace_2 = """                if result.get("ok"):
                    from integral_solver.core.printer import pretty_print, hstack, Block
                    expr_blk = pretty_print(result['expression'])
                    
                    lines = [""]
                    left = hstack(Block.text(f"∫[{lower_str}, {upper_str}] "), expr_blk, Block.text(f" d{var}"))
                    lines.extend("  " + l for l in left.lines)
                    lines.append("")
                    
                    antideriv = result.get("antiderivative")
                    if antideriv is not None:
                        res_blk = pretty_print(antideriv)
                        f_blk = hstack(Block.text(f"F({var}) = "), res_blk)
                        lines.extend("  " + l for l in f_blk.lines)
                        if "value" in result:
                            lines.append(f"  F({upper_str}) − F({lower_str}) = {format_float(result['value'])}")
                    elif "value" in result:
                        lines.append(f"  ≈ {format_float(result['value'])} (метод Симпсона)")
                    
                    _print_result(lines)
                    _print_steps(result.get("notes", []))"""

content = re.sub(r'if result\.get\("ok"\):\s*lines: list\[str\] = \[\s*f"∫[^\]]+\]\s*antideriv = result\.get\("antiderivative"\)[^\n]*(\n\s*if antideriv is not None:[^_]+)?_[^\]]*_print_result\(lines\)\s*_print_steps\(result\.get\("notes", \[\]\)\)', replace_2, content, flags=re.DOTALL)

with open("integral_solver/cli/main.py", "w") as f:
    f.write(content)
