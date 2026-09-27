"""Base Definitions and Schema for AST Rules and Violations.

Enforces the 6 core required record fields:
1. commit_repo_id
2. file_path
3. violation_type
4. cyclomatic_complexity
5. remediation_hours
6. refactor_status
"""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ViolationType(str, Enum):
    DEEP_NESTING = "Deep Nesting"
    PARAMETER_BLOAT = "Parameter Bloat"
    DEAD_CODE = "Dead Code"
    HIGH_COMPLEXITY = "High Complexity"
    DUPLICATE_SUBTREES = "Duplicate Subtrees"


class RefactorStatus(str, Enum):
    FLAGGED = "Flagged"
    RULE_PATCHED = "Rule-Patched"
    DISMISSED = "Dismissed"


@dataclass
class ASTViolation:
    """The central 6-field record model plus source anchor coordinates."""

    # --- 6 PRIMARY REQUIRED FIELDS ---
    commit_repo_id: str             # 1. Identifier for the scanned codebase or commit
    file_path: str                  # 2. Relational path to the analyzed code artifact
    violation_type: str             # 3. AST rule violated
    cyclomatic_complexity: int      # 4. v(G) = E - N + 2P score
    remediation_hours: float        # 5. Estimated effort based on rule weights
    refactor_status: str            # 6. Flagged, Rule-Patched, Dismissed

    # --- LOCATION & REMEDIATION ANCHORS ---
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0
    node_type: str = "ast.AST"
    message: str = ""
    suggested_patch_diff: Optional[str] = None
    patched_content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_repo_id": self.commit_repo_id,
            "file_path": self.file_path,
            "violation_type": self.violation_type,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "remediation_hours": self.remediation_hours,
            "refactor_status": self.refactor_status,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_col": self.start_col,
            "end_col": self.end_col,
            "node_type": self.node_type,
            "message": self.message,
            "suggested_patch_diff": self.suggested_patch_diff,
        }


class BaseRule(ABC):
    """Abstract base class for all deterministic AST rules."""

    rule_id: str
    violation_type: ViolationType
    base_remediation_hours: float

    @abstractmethod
    def analyze(
        self,
        tree: ast.AST,
        source_code: str,
        file_path: str,
        commit_repo_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ASTViolation]:
        """Traverses the AST and yields detected violations."""
        pass
