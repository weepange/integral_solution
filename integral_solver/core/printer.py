from __future__ import annotations
from typing import List

class Block:
    def __init__(self, lines: List[str], baseline: int):
        self.lines = lines
        self.height = len(lines)
        self.width = max((len(line) for line in lines), default=0)
        self.baseline = baseline

    @classmethod
    def text(cls, s: str) -> Block:
        return cls([s], 0)

def pad_h(block: Block, width: int) -> Block:
    if block.width >= width:
        return block
    pad = width - block.width
    left = pad // 2
    right = pad - left
    new_lines = [" " * left + line + " " * (right + block.width - len(line)) for line in block.lines]
    return Block(new_lines, block.baseline)

def hstack(*blocks: Block) -> Block:
    if not blocks:
        return Block.text("")
    
    # Find the maximum baseline and the maximum drop (height - baseline)
    max_baseline = max(b.baseline for b in blocks)
    max_drop = max(b.height - b.baseline for b in blocks)
    new_height = max_baseline + max_drop
    
    new_lines = ["" for _ in range(new_height)]
    
    for b in blocks:
        offset = max_baseline - b.baseline
        for i in range(new_height):
            if offset <= i < offset + b.height:
                line = b.lines[i - offset]
            else:
                line = ""
            new_lines[i] += line + " " * (b.width - len(line))
            
    return Block(new_lines, max_baseline)

def vstack(num: Block, den: Block) -> Block:
    width = max(num.width, den.width) + 2
    num_p = pad_h(num, width)
    den_p = pad_h(den, width)
    line = "─" * width
    new_lines = num_p.lines + [line] + den_p.lines
    return Block(new_lines, num_p.height)

def superscript(base: Block, exp: Block) -> Block:
    new_lines = []
    for line in exp.lines:
        new_lines.append(" " * base.width + line)
    for line in base.lines:
        new_lines.append(line + " " * exp.width)
    return Block(new_lines, base.baseline + exp.height)

def parenthesize(b: Block) -> Block:
    if b.height == 1:
        return hstack(Block.text("("), b, Block.text(")"))
    # Multiline parentheses
    left = []
    right = []
    for i in range(b.height):
        if i == 0:
            left.append("⎛")
            right.append("⎞")
        elif i == b.height - 1:
            left.append("⎝")
            right.append("⎠")
        else:
            left.append("│")
            right.append("│")
    return hstack(Block(left, b.baseline), b, Block(right, b.baseline))

from integral_solver.core.ast import *

def pretty_print(expr: Expr, parent_prec: int = 0) -> Block:
    if isinstance(expr, Const):
        if expr.value.denominator == 1:
            return Block.text(str(expr.value.numerator))
        return vstack(Block.text(str(expr.value.numerator)), Block.text(str(expr.value.denominator)))
    if isinstance(expr, Var):
        return Block.text(expr.name)
    if isinstance(expr, Add):
        blocks = []
        for i, term in enumerate(expr.terms):
            if i > 0:
                # heuristic for subtraction
                if isinstance(term, Mul) and len(term.factors) > 0 and isinstance(term.factors[0], Const) and term.factors[0].value < 0:
                    blocks.append(Block.text(" - "))
                    # We need to render the negated term
                    neg_term = simplify(Mul((Const(Fraction(-1)), term)))
                    blocks.append(pretty_print(neg_term, 1))
                elif isinstance(term, Const) and term.value < 0:
                    blocks.append(Block.text(" - "))
                    blocks.append(pretty_print(Const(-term.value), 1))
                else:
                    blocks.append(Block.text(" + "))
                    blocks.append(pretty_print(term, 1))
            else:
                blocks.append(pretty_print(term, 1))
        
        res = hstack(*blocks)
        if parent_prec > 1:
            return parenthesize(res)
        return res
    
    if isinstance(expr, Mul):
        # Handle fractions
        num_factors = []
        den_factors = []
        for factor in expr.factors:
            if isinstance(factor, Pow) and isinstance(factor.exponent, Const) and factor.exponent.value < 0:
                if factor.exponent.value == -1:
                    den_factors.append(factor.base)
                else:
                    den_factors.append(Pow(factor.base, Const(-factor.exponent.value)))
            elif isinstance(factor, Const) and factor.value.denominator != 1:
                if factor.value.numerator != 1:
                    num_factors.append(Const(Fraction(factor.value.numerator)))
                den_factors.append(Const(Fraction(factor.value.denominator)))
            else:
                num_factors.append(factor)
        
        if den_factors:
            num = simplify(Mul(tuple(num_factors))) if num_factors else Const(Fraction(1))
            den = simplify(Mul(tuple(den_factors))) if len(den_factors) > 1 else den_factors[0]
            
            # Special case: if num is a constant and we want to print like 1/2 * x, 
            # maybe it's cleaner to keep it as a single fraction: num / den.
            
            # Check if num is negative
            is_neg = False
            if isinstance(num, Const) and num.value < 0:
                is_neg = True
                num = Const(-num.value)
            elif isinstance(num, Mul) and isinstance(num.factors[0], Const) and num.factors[0].value < 0:
                is_neg = True
                num = simplify(Mul((Const(Fraction(-1)), num)))
            
            frac = vstack(pretty_print(num, 0), pretty_print(den, 0))
            if is_neg:
                frac = hstack(Block.text("-"), frac)
            if parent_prec > 2:
                return parenthesize(frac)
            return frac
        
        # Regular multiplication
        blocks = []
        is_neg = False
        render_factors = list(expr.factors)
        
        # Handle leading -1 coefficient
        if (render_factors and isinstance(render_factors[0], Const) 
            and render_factors[0].value == -1 and len(render_factors) > 1):
            is_neg = True
            render_factors = render_factors[1:]
        # Handle leading 1 coefficient (skip it)
        elif (render_factors and isinstance(render_factors[0], Const) 
              and render_factors[0].value == 1 and len(render_factors) > 1):
            render_factors = render_factors[1:]
        
        for factor in render_factors:
            if isinstance(factor, Add):
                blocks.append(parenthesize(pretty_print(factor, 0)))
            else:
                blocks.append(pretty_print(factor, 2))
        
        if len(blocks) == 1:
            res = blocks[0]
        else:
            parts = [blocks[0]]
            for b in blocks[1:]:
                parts.append(Block.text("\u00b7"))
                parts.append(b)
            res = hstack(*parts)
        
        if is_neg:
            res = hstack(Block.text("-"), res)
        if parent_prec > 2:
            return parenthesize(res)
        return res

    if isinstance(expr, Pow):
        base_blk = pretty_print(expr.base, 3)
        exp_blk = pretty_print(expr.exponent, 0)
        res = superscript(base_blk, exp_blk)
        return res

    if isinstance(expr, Func):
        arg_blk = pretty_print(expr.arg, 0)
        if expr.name == "abs":
            return hstack(Block.text("│"), arg_blk, Block.text("│"))
        elif expr.name == "sqrt":
            # Better sqrt representation without fraction bar
            arg_w = arg_blk.width
            line = " " + "─" * arg_w
            new_lines = [line]
            for i, arg_line in enumerate(arg_blk.lines):
                prefix = "╲" if i == arg_blk.height - 1 else "│"
                new_lines.append(prefix + arg_line + " " * (arg_w - len(arg_line)))
            return Block(new_lines, arg_blk.baseline + 1)
            
        elif expr.name == "log":
            return hstack(Block.text("ln"), parenthesize(arg_blk))
            
        return hstack(Block.text(expr.name), parenthesize(arg_blk))
    
    return Block.text(str(expr))

