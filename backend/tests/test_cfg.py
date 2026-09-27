"""Unit tests for Control Flow Graph (CFG) and Cyclomatic Complexity v(G) = E - N + 2P."""

import ast
import pytest
from app.engine.cfg import CFGBuilder


def test_straight_line_code_complexity():
    code = """
def linear():
    a = 1
    b = 2
    c = a + b
    return c
"""
    tree = ast.parse(code)
    func = tree.body[0]
    builder = CFGBuilder()
    cfg = builder.build_for_function(func)

    # v(G) must be 1 for straight-line code
    assert cfg.calculate_cyclomatic_complexity() == 1
    # Verify McCabe formula: E - N + 2P
    assert cfg.edge_count - cfg.node_count + (2 * cfg.p) == 1


def test_single_if_branch_complexity():
    code = """
def branch(x):
    if x > 0:
        return 1
    return 0
"""
    tree = ast.parse(code)
    func = tree.body[0]
    builder = CFGBuilder()
    cfg = builder.build_for_function(func)

    assert cfg.calculate_cyclomatic_complexity() == 2
    assert cfg.edge_count - cfg.node_count + (2 * cfg.p) == 2


def test_if_else_branch_complexity():
    code = """
def if_else(x):
    if x > 10:
        y = x * 2
    else:
        y = x - 2
    return y
"""
    tree = ast.parse(code)
    func = tree.body[0]
    builder = CFGBuilder()
    cfg = builder.build_for_function(func)

    assert cfg.calculate_cyclomatic_complexity() == 2
    assert cfg.edge_count - cfg.node_count + (2 * cfg.p) == 2


def test_while_loop_complexity():
    code = """
def loop(n):
    total = 0
    while n > 0:
        total += n
        n -= 1
    return total
"""
    tree = ast.parse(code)
    func = tree.body[0]
    builder = CFGBuilder()
    cfg = builder.build_for_function(func)

    assert cfg.calculate_cyclomatic_complexity() == 2
    assert cfg.edge_count - cfg.node_count + (2 * cfg.p) == 2


def test_boolean_operator_branch_expansion():
    code = """
def compound_condition(a, b, c):
    if a and b and c:
        return True
    return False
"""
    tree = ast.parse(code)
    func = tree.body[0]
    builder = CFGBuilder()
    cfg = builder.build_for_function(func)

    # 'if a and b and c' has 1 (if) + 2 (and operators) decision points = 3 branches -> v(G) = 4
    assert cfg.calculate_cyclomatic_complexity() == 4
    assert cfg.edge_count - cfg.node_count + (2 * cfg.p) == 4


def test_try_except_complexity():
    code = """
def safe_div(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return 0
"""
    tree = ast.parse(code)
    func = tree.body[0]
    builder = CFGBuilder()
    cfg = builder.build_for_function(func)

    assert cfg.calculate_cyclomatic_complexity() == 2
