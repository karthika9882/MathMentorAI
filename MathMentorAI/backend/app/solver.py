import re
import sympy as sp

x = sp.Symbol("x")
_ALLOWED = re.compile(r"^[0-9xX+*/().=\s-]+$")

class EquationError(ValueError):
    pass

def parse_side(side: str):
    side = side.strip().lower()
    if not side or not _ALLOWED.fullmatch(side):
        raise EquationError("Use only x, numbers, +, -, *, /, parentheses and spaces.")
    try:
        expr = sp.sympify(side, locals={"x": x}, evaluate=True)
    except Exception as exc:
        raise EquationError("I couldn't read that expression. Check symbols and brackets.") from exc
    if not expr.free_symbols.issubset({x}):
        raise EquationError("Only variable x is supported.")
    return expr

def solve_linear_equation(equation: str, language: str = "en") -> dict:
    if equation.count("=") != 1:
        raise EquationError("Enter exactly one equals sign, e.g. 2*x + 3 = 11.")
    left_text, right_text = equation.split("=", 1)
    expr = sp.expand(parse_side(left_text) - parse_side(right_text))
    if sp.degree(expr, x) is None or sp.degree(expr, x) > 1:
        raise EquationError("Only linear equations are supported, e.g. 2*x + 3 = 11.")
    coefficient = sp.simplify(expr.coeff(x))
    constant = sp.simplify(expr.subs(x, 0))
    if coefficient == 0:
        raise EquationError("This equation does not have one unique solution.")
    answer = sp.simplify(-constant / coefficient)
    steps_en = [
        f"Start with: {equation.strip()}",
        f"Move all terms to one side: {sp.sstr(expr)} = 0",
        f"Keep the x term and constant separate: {sp.sstr(coefficient*x)} = {sp.sstr(-constant)}",
        f"Divide both sides by {sp.sstr(coefficient)}: x = {sp.sstr(answer)}",
    ]
    steps_ta = [
        f"கொடுக்கப்பட்ட சமன்பாடு: {equation.strip()}",
        f"அனைத்து உறுப்புகளையும் ஒரு பக்கத்திற்கு மாற்றவும்: {sp.sstr(expr)} = 0",
        f"x உள்ள உறுப்பையும் மாறிலியையும் பிரிக்கவும்: {sp.sstr(coefficient*x)} = {sp.sstr(-constant)}",
        f"இரு பக்கங்களையும் {sp.sstr(coefficient)} ஆல் வகுக்கவும்: x = {sp.sstr(answer)}",
    ]
    return {"answer":sp.sstr(answer),"answer_numeric":float(answer) if answer.is_number else None,
            "steps":steps_ta if language=="ta" else steps_en,"steps_en":steps_en,"steps_ta":steps_ta,
            "topic":"linear_equations",
            "note":"Prototype solver. Ask a maths teacher to verify worked steps before classroom use."}
