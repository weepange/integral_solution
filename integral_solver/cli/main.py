from __future__ import annotations
from integral_solver.core.ast import *
from integral_solver.core.parser import *
from integral_solver.calculus.solvers import *
from integral_solver.core.ast import *
from integral_solver.core.parser import *

import math

import re

import ast

from dataclasses import dataclass

from fractions import Fraction

from typing import Iterable, Optional, Sequence



import sys

import time

import threading

import shutil

def explain_double_solution(result: dict[str, object]) -> str:
    if not result.get("ok"):
        return str(result.get("error", "Ошибка"))
    lines = []
    lines.append("Двойной интеграл по области:")
    lines.append(f"  Внутренний: по {result['inner_var']} от {format_expr(result['inner_lower'])} до {format_expr(result['inner_upper'])}")
    lines.append(f"  Внешний: по {result['outer_var']} от {result['outer_lower']} до {result['outer_upper']}")
    lines.append(f"Подынтегральное выражение: {format_expr(result['expression'])}")

    lines.append("\nШаг 1: Интегрирование по " + str(result["inner_var"]))
    lines.append(f"  Результат шага 1: {format_expr(result['inner_result'])}")

    lines.append("\nШаг 2: Интегрирование по " + str(result["outer_var"]))
    lines.append(f"  Значение двойного интеграла: {format_float(result['value'])}")

    if result.get("notes"):
        lines.append("\nХод решения:")
        for note in result["notes"]:
            lines.append(f"  - {note}")
    return "\n".join(lines)

def explain_line_solution(result: dict[str, object]) -> str:
    if not result.get("ok"):
        return str(result.get("error", "Ошибка"))
    lines = []
    if result["type"] == "1st_kind":
        lines.append("Криволинейный интеграл 1-го рода (по длине дуги):")
        lines.append(f"  Функция f: {format_expr(result['f_expr'])}")
    else:
        lines.append("Криволинейный интеграл 2-го рода (по вектору):")
        lines.append(f"  Векторное поле: P = {format_expr(result['P_expr'])}, Q = {format_expr(result['Q_expr'])}" + (f", R = {format_expr(result['R_expr'])}" if result['R_expr'] else ""))

    lines.append(f"  Параметризация: x(t) = {format_expr(result['x_t'])}, y(t) = {format_expr(result['y_t'])}" + (f", z(t) = {format_expr(result['z_t'])}" if result['z_t'] else ""))

    lines.append("\nСведение к определенному интегралу по t:")
    lines.append(f"  Подынтегральное выражение: {format_expr(result['integrand'])}")

    if result.get("result_expr") is not None:
        lines.append(f"  Первообразная: {format_expr(result['result_expr'])}")
    lines.append(f"  Значение интеграла: {format_float(result['value'])}")

    if result.get("notes"):
        lines.append("\nХод решения:")
        for note in result["notes"]:
            lines.append(f"  - {note}")
    return "\n".join(lines)

def explain_solution(result: dict[str, object], definite: bool = False) -> str:
    from integral_solver.core.printer import pretty_print
    if not result.get("ok"):
        return str(result.get("error", "Ошибка"))
    lines = []
    if result.get("notes"):
        lines.append("Метод: " + "; ".join(dict.fromkeys(result["notes"])))  # type: ignore[index]
    
    expr_blk = pretty_print(result["expression"])  # type: ignore[arg-type]
    lines.append("Интеграл:\n" + "\n".join("  " + l for l in expr_blk.lines))
    
    if definite:
        res_blk = pretty_print(result["result"])  # type: ignore[arg-type]
        lines.append("Первообразная:\n" + "\n".join("  " + l for l in res_blk.lines))
        lines.append("Значение на [a, b]: " + format_float(result["value"]))  # type: ignore[index]
    else:
        res_blk = pretty_print(result["result"])  # type: ignore[arg-type]
        # Append "+ C"
        from integral_solver.core.printer import hstack, Block
        res_blk = hstack(res_blk, Block.text(" + C"))
        lines.append("Ответ:\n" + "\n".join("  " + l for l in res_blk.lines))
        
    return "\n".join(lines)

class _C:
    """ANSI colour codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    # foreground
    BLACK   = "\033[30m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    # background
    BG_BLUE = "\033[44m"
    BG_DARK = "\033[40m"

def _term_width() -> int:
    return shutil.get_terminal_size((72, 24)).columns

def _clr() -> None:
    """Clear terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def _hr(char: str = "─", color: str = _C.DIM) -> None:
    print(f"{color}{char * _term_width()}{_C.RESET}")

def _print_banner() -> None:
    w = _term_width()
    border = "═" * (w - 2)
    title = "  ∫  РЕШАТЕЛЬ ИНТЕГРАЛОВ  ∫"
    pad = " " * ((w - 2 - len(title)) // 2)
    print(f"{_C.CYAN}{_C.BOLD}╔{border}╗")
    print(f"║{pad}{title}{pad} ║")
    print(f"╚{border}╝{_C.RESET}")

def _section_header(title: str) -> None:
    w = _term_width()
    inner = f"  {title}  "
    bar = "─" * (w - len(inner) - 4)
    print(f"\n{_C.CYAN}┌─{_C.BOLD}{inner}{_C.RESET}{_C.CYAN}{bar}┐{_C.RESET}")

def _ask(prompt: str, default: str = "", hint: str = "") -> str:
    """Colour-coded input prompt."""
    dflt = f" {_C.DIM}[{default}]{_C.RESET}" if default else ""
    hnt  = f"  {_C.DIM}{hint}{_C.RESET}" if hint else ""
    full = f"{_C.CYAN}  ❯ {_C.RESET}{_C.WHITE}{prompt}{_C.RESET}{dflt}{hnt}: "
    val = input(full).strip()
    return val or default

class _Spinner:
    """Non-blocking console spinner shown while computing."""
    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, label: str = "Вычисляю…"):
        self._label = label
        self._stop  = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread:
            self._thread.join()
        # erase spinner line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def _run(self):
        i = 0
        while not self._stop.is_set():
            frame = self._FRAMES[i % len(self._FRAMES)]
            sys.stdout.write(
                f"\r  {_C.CYAN}{frame}{_C.RESET}  {_C.DIM}{self._label}{_C.RESET}"
            )
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1

def _animate_line(text: str, delay: float = 0.012) -> None:
    """Print text character-by-character (typewriter effect)."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def _print_result(lines: list[str], *, animated: bool = True) -> None:
    """Pretty-print a result box with optional animation."""
    w  = _term_width()
    iw = w - 4  # inner width
    print()
    print(f"{_C.GREEN}┌{'─' * (w - 2)}┐{_C.RESET}")
    for i, line in enumerate(lines):
        if not line:
            print(f"{_C.GREEN}│{_C.RESET}{' ' * (w - 2)}{_C.GREEN}│{_C.RESET}")
            continue
        # colour key lines differently
        if line.startswith("∫") or line.startswith("=") or line.startswith("≈"):
            color = _C.BOLD + _C.WHITE
        elif line.startswith("Метод:") or line.startswith("Шаг"):
            color = _C.DIM
        elif "Значение" in line or "=" in line:
            color = _C.YELLOW
        else:
            color = _C.RESET
        padded = f"  {line}"
        # strip colour codes for length calculation
        visible = re.sub(r"\033\[[0-9;]*m", "", padded)
        padding = " " * max(0, w - 2 - len(visible))
        row = f"{_C.GREEN}│{_C.RESET}{color}{padded}{_C.RESET}{padding}{_C.GREEN}│{_C.RESET}"
        if animated and i < 8:
            print(row)
            time.sleep(0.04)
        else:
            print(row)
    print(f"{_C.GREEN}└{'─' * (w - 2)}┘{_C.RESET}")

def _print_error(msg: str) -> None:
    print(f"\n  {_C.RED}✗  {msg}{_C.RESET}")

def _pause() -> None:
    """Wait for the user to press Enter before clearing the screen."""
    try:
        input(f"\n  {_C.DIM}Нажмите Enter для возврата в меню…{_C.RESET}")
    except (EOFError, KeyboardInterrupt):
        pass

def _print_steps(notes: list[str]) -> None:
    """Print deduped method notes as a numbered step list."""
    steps = list(dict.fromkeys(n for n in notes if n))
    if not steps:
        return
    print(f"\n  {_C.CYAN}── Метод решения:{_C.RESET}")
    for i, step in enumerate(steps, 1):
        print(f"    {_C.DIM}{i}.{_C.RESET} {step}")

def _print_syntax_help() -> None:
    _clr()
    _print_banner()
    _section_header("СПРАВКА ПО СИНТАКСИСУ")
    items = [
        ("Операторы",
         "+ − * /    сложение, вычитание, умножение, деление\n"
         "           ^ или **   степень:  x^2  или  x**2\n"
         "           ( )        скобки для группировки"),
        ("Функции",
         "sin(x)  cos(x)  tan(x)  cot(x)\n"
         "           exp(x)  log(x) = ln(x)   sqrt(x)  abs(x)\n"
         "           asin(x)  acos(x)  atan(x)"),
        ("Константы",
         "pi  →  π ≈ 3.14159…       e  →  e ≈ 2.71828…"),
        ("Неявное умножение",
         "2x  →  2*x        3sin(x)  →  3*sin(x)\n"
         "           (x+1)(x-1)  →  (x+1)*(x-1)"),
        ("Примеры",
         "x^2 + 3x - 1\n"
         "           (2x-3)*sin(x)\n"
         "           sin(2x) * exp(-x)\n"
         "           1/(x^2 + 1)\n"
         "           sqrt(1 - x^2)"),
    ]
    for title, body in items:
        print(f"\n  {_C.CYAN}{_C.BOLD}{title}:{_C.RESET}")
        for line in body.split("\n"):
            print(f"  {_C.WHITE}{line}{_C.RESET}")
    print()
    _hr()
    input(f"  {_C.DIM}Нажмите Enter для возврата в меню…{_C.RESET}")

def _menu_screen() -> None:
    _clr()
    _print_banner()
    print(f"""
  {_C.DIM}Введите номер нужного действия и нажмите Enter.
  Перед каждым вопросом показаны примеры ввода.
  Введите {_C.RESET}{_C.CYAN}?{_C.RESET}{_C.DIM} для справки по синтаксису.{_C.RESET}

  {_C.BOLD}{_C.WHITE}1{_C.RESET}  {_C.CYAN}∫ f(x) dx{_C.RESET}              Неопределённый интеграл
  {_C.BOLD}{_C.WHITE}2{_C.RESET}  {_C.CYAN}∫[a,b] f(x) dx{_C.RESET}         Определённый интеграл
  {_C.BOLD}{_C.WHITE}3{_C.RESET}  {_C.CYAN}∬ f(x,y) dA{_C.RESET}            Двойной интеграл
  {_C.BOLD}{_C.WHITE}4{_C.RESET}  {_C.CYAN}∫_C f ds{_C.RESET}               Криволинейный 1-го рода
  {_C.BOLD}{_C.WHITE}5{_C.RESET}  {_C.CYAN}∫_C P dx + Q dy{_C.RESET}        Криволинейный 2-го рода
  {_C.BOLD}{_C.WHITE}?{_C.RESET}  Справка по синтаксису
  {_C.BOLD}{_C.WHITE}0{_C.RESET}  Выход
""")
    _hr()

def interactive_cli() -> None:
    while True:
        _menu_screen()
        try:
            choice = input(
                f"  {_C.CYAN}{_C.BOLD}Ваш выбор:{_C.RESET} "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            _clr()
            print(f"\n  {_C.CYAN}До свидания!{_C.RESET}\n")
            return

        if choice in {"0", "q", "exit", "quit", "выход"}:
            _clr()
            print(f"\n  {_C.CYAN}До свидания!{_C.RESET}\n")
            return

        if choice == "?":
            _print_syntax_help()
            continue

        # ── 1. Неопределённый ──────────────────────────────────────────
        if choice == "1":
            _clr()
            _print_banner()
            _section_header("Неопределённый интеграл  ∫ f(x) dx")
            print(f"""
  {_C.DIM}Примеры подынтегральных функций:{_C.RESET}
    {_C.YELLOW}x^2 + 3x - 1{_C.RESET}          {_C.DIM}→  степенной многочлен{_C.RESET}
    {_C.YELLOW}(2x-3)*sin(x){_C.RESET}          {_C.DIM}→  интегрирование по частям{_C.RESET}
    {_C.YELLOW}sin(2x){_C.RESET}                {_C.DIM}→  замена переменной{_C.RESET}
    {_C.YELLOW}1/(x^2 + 1){_C.RESET}            {_C.DIM}→  дробно-рациональная{_C.RESET}
    {_C.YELLOW}x*exp(x){_C.RESET}               {_C.DIM}→  интегрирование по частям{_C.RESET}
""")
            try:
                raw = _ask("Функция f(x)")
                if not raw:
                    continue
                if raw == "?":
                    _print_syntax_help()
                    continue
                var = _ask("Переменная интегрирования", "x")
                print()
                with _Spinner("Вычисляю первообразную…"):
                    result = solve_indefinite(raw, var)
                if result.get("ok"):
                    from integral_solver.core.printer import pretty_print, hstack, Block
                    expr_blk = pretty_print(result['expression'])  # type: ignore[arg-type]
                    res_blk = pretty_print(result['result'])  # type: ignore[arg-type]
                    
                    # ∫ f(x) dx
                    left = hstack(Block.text("∫ "), expr_blk, Block.text(f" d{var}"))
                    right = hstack(res_blk, Block.text(" + C"))
                    
                    final_blk = hstack(left, Block.text(" = "), right)
                    
                    _print_result([""] + ["  " + l for l in final_blk.lines] + [""])
                    _print_steps(result["notes"])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 2. Определённый ───────────────────────────────────────────
        elif choice == "2":
            _clr()
            _print_banner()
            _section_header("Определённый интеграл  ∫[a,b] f(x) dx")
            print(f"""
  {_C.DIM}Примеры:{_C.RESET}
    {_C.YELLOW}x^2{_C.RESET}     a={_C.YELLOW}0{_C.RESET}  b={_C.YELLOW}2{_C.RESET}     {_C.DIM}→  8/3{_C.RESET}
    {_C.YELLOW}sin(x){_C.RESET}  a={_C.YELLOW}0{_C.RESET}  b={_C.YELLOW}pi{_C.RESET}    {_C.DIM}→  2{_C.RESET}
    {_C.YELLOW}exp(-x^2){_C.RESET} a={_C.YELLOW}0{_C.RESET} b={_C.YELLOW}1{_C.RESET}    {_C.DIM}→  численно ≈ 0.7468{_C.RESET}
""")
            try:
                raw = _ask("Функция f(x)")
                if not raw:
                    continue
                if raw == "?":
                    _print_syntax_help()
                    continue
                var = _ask("Переменная интегрирования", "x")
                lower_str = _ask("Нижний предел a", hint="число или выражение: 0, pi, e…")
                upper_str = _ask("Верхний предел b", hint="число или выражение")
                print()
                with _Spinner("Вычисляю…"):
                    try:
                        result = solve_definite(raw, var, float(lower_str), float(upper_str))
                    except ValueError:
                        result = solve_definite_symbolic(raw, var, lower_str, upper_str)
                if result.get("ok"):
                    from integral_solver.core.printer import pretty_print, hstack, Block
                    expr_blk = pretty_print(result['expression'])  # type: ignore[arg-type]
                    
                    lines: list[str] = [""]
                    left = hstack(Block.text(f"∫[{lower_str}, {upper_str}] "), expr_blk, Block.text(f" d{var}"))
                    lines.extend("  " + l for l in left.lines)
                    lines.append("")
                    
                    antideriv = result.get("antiderivative")
                    if antideriv is not None:
                        res_blk = pretty_print(antideriv)
                        f_blk = hstack(Block.text(f"F({var}) = "), res_blk)
                        lines.extend("  " + l for l in f_blk.lines)
                        if "value" in result:
                            lines.append(f"  F({upper_str}) − F({lower_str})  =  {format_float(result['value'])}")
                        else:
                            lines.append(f"  F({upper_str}) − F({lower_str})")
                    elif "value" in result:
                        lines.append(f"  ≈  {format_float(result['value'])}  (метод Симпсона)")
                    else:
                        lines.append("  (результат не вычислен)")
                    lines.append("")
                    _print_result(lines)
                    _print_steps(result.get("notes", []))
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 3. Двойной ────────────────────────────────────────────────
        elif choice == "3":
            _clr()
            _print_banner()
            _section_header("Двойной интеграл  ∬ f(x,y) dA")
            print(f"""
  {_C.DIM}Пример  ∫[0,1] ∫[0,x] (x+y) dy dx:{_C.RESET}
    f(x,y) = {_C.YELLOW}x + y{_C.RESET}
    Внутр. перем. = {_C.YELLOW}y{_C.RESET},  пределы: {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}x{_C.RESET}  {_C.DIM}(может зависеть от x){_C.RESET}
    Внешн. перем. = {_C.YELLOW}x{_C.RESET},  пределы: {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}1{_C.RESET}
""")
            try:
                expr     = _ask("Функция f(x, y)")
                if not expr:
                    continue
                iv       = _ask("Внутренняя переменная", "y")
                il       = _ask(f"Нижний предел по {iv}", hint="число или выражение")
                iu       = _ask(f"Верхний предел по {iv}", hint="число или выражение")
                ov       = _ask("Внешняя переменная", "x")
                ol_s     = _ask(f"Нижний предел по {ov}", hint="число")
                ou_s     = _ask(f"Верхний предел по {ov}", hint="число")
                print()
                with _Spinner("Вычисляю двойной интеграл…"):
                    result = solve_double_integral(
                        expr, iv, il, iu, ov, float(ol_s), float(ou_s))
                if result.get("ok"):
                    _print_result([
                        f"∫[{ol_s},{ou_s}] ∫[{il},{iu}] {format_expr(result['expression'])} d{iv} d{ov}",
                        "",
                        f"Шаг 1 — ∫ по {iv}:  {format_expr(result['inner_result'])}",
                        "",
                        f"Значение = {format_float(result['value'])}",
                    ])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 4. Криволинейный 1-го рода ────────────────────────────────
        elif choice == "4":
            _clr()
            _print_banner()
            _section_header("Криволинейный интеграл 1-го рода  ∫_C f ds")
            print(f"""
  {_C.DIM}r(t) = (x(t), y(t)),  t ∈ [a, b],  ds = √(x'²+y'²) dt{_C.RESET}

  {_C.DIM}Пример  ∫_C (x²+y²) ds,  C: x=cos(t), y=sin(t), t∈[0,pi]:{_C.RESET}
    f     = {_C.YELLOW}x^2 + y^2{_C.RESET}    x(t) = {_C.YELLOW}cos(t){_C.RESET}    y(t) = {_C.YELLOW}sin(t){_C.RESET}
    t: от {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}pi{_C.RESET}
""")
            try:
                f_text  = _ask("Функция f(x, y) [или f(x,y,z)]")
                if not f_text:
                    continue
                x_t     = _ask("Параметризация x(t)")
                y_t     = _ask("Параметризация y(t)")
                use_z   = _ask("Добавить z-координату?", "n", hint="y/n").lower() == "y"
                z_t     = _ask("Параметризация z(t)") if use_z else None
                t_var   = _ask("Параметр", "t")
                t_lo    = _ask("Нижний предел t")
                t_hi    = _ask("Верхний предел t")
                print()
                with _Spinner("Параметризую и интегрирую…"):
                    result = solve_line_integral_1st_kind(
                        f_text, x_t, y_t, z_t, t_var, t_lo, t_hi)
                if result.get("ok"):
                    coord = (f"x(t)={format_expr(result['x_t'])}, y(t)={format_expr(result['y_t'])}"
                             + (f", z(t)={format_expr(result['z_t'])}" if result["z_t"] else ""))
                    _print_result([
                        f"∫_C {format_expr(result['f_expr'])} ds",
                        f"  {coord},  t ∈ [{t_lo}, {t_hi}]",
                        "",
                        f"ds = {format_expr(result['ds'])} dt",
                        f"Подынтегральное: {format_expr(result['integrand'])}",
                        "",
                        f"Значение = {format_float(result['value'])}",
                    ])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        # ── 5. Криволинейный 2-го рода ────────────────────────────────
        elif choice == "5":
            _clr()
            _print_banner()
            _section_header("Криволинейный интеграл 2-го рода  ∫_C P dx + Q dy")
            print(f"""
  {_C.DIM}∫_C P dx + Q dy = ∫[a,b] (P·x' + Q·y') dt{_C.RESET}

  {_C.DIM}Пример  ∫_C y dx + x dy,  C: x=t, y=t², t∈[0,1]:{_C.RESET}
    P = {_C.YELLOW}y{_C.RESET}    Q = {_C.YELLOW}x{_C.RESET}    x(t) = {_C.YELLOW}t{_C.RESET}    y(t) = {_C.YELLOW}t^2{_C.RESET}    t: {_C.YELLOW}0{_C.RESET} до {_C.YELLOW}1{_C.RESET}
""")
            try:
                P      = _ask("Компонента P(x, y)")
                if not P:
                    continue
                Q      = _ask("Компонента Q(x, y)")
                use_z  = _ask("Добавить R и z(t)?", "n", hint="y/n").lower() == "y"
                R      = _ask("Компонента R(x, y, z)") if use_z else None
                x_t    = _ask("Параметризация x(t)")
                y_t    = _ask("Параметризация y(t)")
                z_t    = _ask("Параметризация z(t)") if use_z else None
                t_var  = _ask("Параметр", "t")
                t_lo   = _ask("Нижний предел t")
                t_hi   = _ask("Верхний предел t")
                print()
                with _Spinner("Параметризую и интегрирую…"):
                    result = solve_line_integral_2nd_kind(
                        P, Q, x_t, y_t, R, z_t, t_var, t_lo, t_hi)
                if result.get("ok"):
                    fs = (f"P={format_expr(result['P_expr'])}, Q={format_expr(result['Q_expr'])}"
                          + (f", R={format_expr(result['R_expr'])}" if result.get("R_expr") else ""))
                    coord = (f"x(t)={format_expr(result['x_t'])}, y(t)={format_expr(result['y_t'])}"
                             + (f", z(t)={format_expr(result['z_t'])}" if result["z_t"] else ""))
                    _print_result([
                        "∫_C P dx + Q dy" + (" + R dz" if result.get("R_expr") else ""),
                        f"  {fs}",
                        f"  {coord},  t ∈ [{t_lo}, {t_hi}]",
                        "",
                        f"Подынтегральное: {format_expr(result['integrand'])}",
                        "",
                        f"Значение = {format_float(result['value'])}",
                    ])
                else:
                    _print_error(str(result.get("error")))
                _pause()
            except Exception as exc:
                _print_error(str(exc))
                _pause()

        else:
            print(f"  {_C.RED}✗ Неверный выбор. Введите цифру 0–5 или «?».{_C.RESET}")
            time.sleep(1.2)
