"""Unit tests for Halstead metrics and Maintainability Index."""

import pytest
from app.engine.halstead import HalsteadCalculator
from app.engine.metrics import CodeMetricsCalculator


def test_halstead_empty_code():
    m = HalsteadCalculator.calculate("")
    assert m.vocabulary == 0
    assert m.length == 0
    assert m.volume == 0.0


def test_halstead_simple_assignment():
    code = "x = a + b"
    m = HalsteadCalculator.calculate(code)
    # Operators: '=', '+'
    # Operands: 'x', 'a', 'b'
    assert m.distinct_operators >= 2
    assert m.distinct_operands >= 3
    assert m.volume > 0.0
    assert m.vocabulary == m.distinct_operators + m.distinct_operands
    assert m.length == m.total_operators + m.total_operands


def test_line_metrics_calculation():
    code = """
# This is a comment
def foo():
    \"\"\"Docstring description\"\"\"
    x = 1

    return x
"""
    lm = CodeMetricsCalculator.calculate_line_metrics(code)
    assert lm.total_loc >= 7
    assert lm.comment_lines >= 2
    assert lm.blank_lines >= 2
    assert lm.sloc >= 3


def test_maintainability_index_bounds():
    score, category = CodeMetricsCalculator.calculate_maintainability_index(
        halstead_volume=100.0,
        cyclomatic_complexity=2,
        sloc=15,
    )
    assert 0.0 <= score <= 100.0
    assert category in ("High", "Moderate", "Low")


def test_maintainability_index_zero_sloc():
    score, category = CodeMetricsCalculator.calculate_maintainability_index(0.0, 1, 0)
    assert score == 100.0
    assert category == "High"
