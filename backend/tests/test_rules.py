"""Unit tests for AST anti-pattern rules and the 6-field record schema."""

import ast
import pytest
from app.engine.analyzer import ASTDebtAnalyzer
from app.engine.rules.base import ASTViolation, RefactorStatus, ViolationType
from app.engine.rules.bloat import ParameterBloatRule
from app.engine.rules.complexity import HighComplexityRule
from app.engine.rules.dead_code import DeadCodeRule
from app.engine.rules.duplicates import DuplicateSubtreeRule
from app.engine.rules.nesting import DeepNestingRule


def test_parameter_bloat_detection():
    code = """
def bloated_func(p1, p2, p3, p4, p5, p6, p7):
    return p1 + p2
"""
    tree = ast.parse(code)
    rule = ParameterBloatRule()
    violations = rule.analyze(tree, code, "test.py", "repo-123")

    assert len(violations) == 1
    v = violations[0]
    assert v.commit_repo_id == "repo-123"
    assert v.file_path == "test.py"
    assert v.violation_type == ViolationType.PARAMETER_BLOAT.value
    assert v.remediation_hours >= 0.75
    assert v.refactor_status == RefactorStatus.FLAGGED.value
    assert v.cyclomatic_complexity >= 1


def test_deep_nesting_detection():
    code = """
def deeply_nested(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 42
    return 0
"""
    tree = ast.parse(code)
    rule = DeepNestingRule()
    violations = rule.analyze(tree, code, "test.py", "repo-123")

    assert len(violations) >= 1
    v = violations[0]
    assert v.violation_type == ViolationType.DEEP_NESTING.value
    assert v.remediation_hours >= 1.0
    assert v.refactor_status == RefactorStatus.FLAGGED.value


def test_dead_code_detection():
    code = """
def unreachable_stmt():
    x = 10
    return x
    y = 20
    print(y)
"""
    tree = ast.parse(code)
    rule = DeadCodeRule()
    violations = rule.analyze(tree, code, "test.py", "repo-123")

    assert len(violations) == 1
    v = violations[0]
    assert v.violation_type == ViolationType.DEAD_CODE.value
    assert v.remediation_hours == 0.5
    assert v.refactor_status == RefactorStatus.FLAGGED.value
    assert v.start_line == 5  # y = 20


def test_high_complexity_detection():
    # Build a function with 11 decision branches
    branches = "\n    ".join([f"if x == {i}: return {i}" for i in range(12)])
    code = f"""
def complex_fn(x):
    {branches}
    return -1
"""
    tree = ast.parse(code)
    rule = HighComplexityRule()
    violations = rule.analyze(tree, code, "test.py", "repo-123")

    assert len(violations) == 1
    v = violations[0]
    assert v.violation_type == ViolationType.HIGH_COMPLEXITY.value
    assert v.cyclomatic_complexity > 10
    assert v.remediation_hours >= 3.5
    assert v.refactor_status == RefactorStatus.FLAGGED.value


def test_duplicate_subtrees_detection():
    code = """
def func_a(x):
    if x > 10:
        a = x * 2
        b = a + 5
        c = b * 3
        return c
    return 0

def func_b(y):
    if y > 10:
        a = y * 2
        b = a + 5
        c = b * 3
        return c
    return 0
"""
    tree = ast.parse(code)
    rule = DuplicateSubtreeRule()
    violations = rule.analyze(tree, code, "test.py", "repo-123")

    assert len(violations) >= 1
    v = violations[0]
    assert v.violation_type == ViolationType.DUPLICATE_SUBTREES.value
    assert v.remediation_hours >= 2.0


def test_six_primary_fields_schema_enforced():
    analyzer = ASTDebtAnalyzer()
    sample_code = """
def sample_violation(a, b, c, d, e, f):
    return a
"""
    result = analyzer.analyze_source(sample_code, file_path="sample.py", commit_repo_id="test-commit-001")
    assert len(result.violations) >= 1

    for v in result.violations:
        # Check all 6 primary schema fields
        assert isinstance(v.commit_repo_id, str) and len(v.commit_repo_id) > 0
        assert isinstance(v.file_path, str) and len(v.file_path) > 0
        assert isinstance(v.violation_type, str) and len(v.violation_type) > 0
        assert isinstance(v.cyclomatic_complexity, int) and v.cyclomatic_complexity >= 1
        assert isinstance(v.remediation_hours, float) and v.remediation_hours > 0.0
        assert v.refactor_status in (RefactorStatus.FLAGGED.value, RefactorStatus.RULE_PATCHED.value, RefactorStatus.DISMISSED.value)
