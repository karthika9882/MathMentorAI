import pytest
from app.solver import EquationError, solve_linear_equation

def test_basic_linear_equation():
    assert solve_linear_equation("2*x + 3 = 11")["answer"] == "4"

def test_negative_answer():
    assert solve_linear_equation("x + 4 = 1")["answer"] == "-3"

def test_reject_quadratic():
    with pytest.raises(EquationError):
        solve_linear_equation("x*x = 9")

def test_requires_equals():
    with pytest.raises(EquationError):
        solve_linear_equation("x + 1")
