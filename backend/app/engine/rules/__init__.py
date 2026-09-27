"""Rules package for AST-based debt analysis."""

from app.engine.rules.base import ASTViolation, BaseRule, RefactorStatus, ViolationType
from app.engine.rules.bloat import ParameterBloatRule
from app.engine.rules.complexity import HighComplexityRule
from app.engine.rules.dead_code import DeadCodeRule
from app.engine.rules.duplicates import DuplicateSubtreeRule
from app.engine.rules.nesting import DeepNestingRule

ALL_RULES = [
    HighComplexityRule(),
    DeepNestingRule(),
    ParameterBloatRule(),
    DeadCodeRule(),
    DuplicateSubtreeRule(),
]

__all__ = [
    "ViolationType",
    "RefactorStatus",
    "ASTViolation",
    "BaseRule",
    "HighComplexityRule",
    "DeepNestingRule",
    "ParameterBloatRule",
    "DeadCodeRule",
    "DuplicateSubtreeRule",
    "ALL_RULES",
]
