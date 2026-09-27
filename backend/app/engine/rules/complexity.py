"""High Cyclomatic Complexity Rule.

Detects functions or methods where v(G) = E - N + 2P exceeds the threshold of 10.
Functions with v(G) > 10 exhibit exponential test path combinations and high defect rates.
Remediation hours: Base 3.5 hrs + 0.25 hr * (v(G) - 10).
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from app.engine.cfg import CFGBuilder
from app.engine.rules.base import ASTViolation, BaseRule, RefactorStatus, ViolationType


class HighComplexityRule(BaseRule):
    rule_id = "AST-004"
    violation_type = ViolationType.HIGH_COMPLEXITY
    base_remediation_hours = 3.5
    COMPLEXITY_THRESHOLD = 10

    def analyze(
        self,
        tree: ast.AST,
        source_code: str,
        file_path: str,
        commit_repo_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ASTViolation]:
        violations: List[ASTViolation] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                builder = CFGBuilder(name=node.name)
                cfg = builder.build_for_function(node)
                vg = cfg.calculate_cyclomatic_complexity()

                if vg > self.COMPLEXITY_THRESHOLD:
                    excess = vg - self.COMPLEXITY_THRESHOLD
                    hours = round(self.base_remediation_hours + (0.25 * excess), 2)

                    violations.append(
                        ASTViolation(
                            commit_repo_id=commit_repo_id,
                            file_path=file_path,
                            violation_type=self.violation_type.value,
                            cyclomatic_complexity=vg,
                            remediation_hours=hours,
                            refactor_status=RefactorStatus.FLAGGED.value,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            start_col=node.col_offset,
                            end_col=getattr(node, "end_col_offset", 0),
                            node_type=node.__class__.__name__,
                            message=(
                                f"Function '{node.name}' has high cyclomatic complexity v(G) = {vg} "
                                f"(threshold: {self.COMPLEXITY_THRESHOLD}). "
                                f"Requires decomposing into modular subroutines."
                            ),
                        )
                    )

        return violations
