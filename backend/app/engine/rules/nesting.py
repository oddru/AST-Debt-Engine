"""Deep Nesting Rule.

Detects control-flow structures nested deeper than 4 levels.
Deep nesting degrades readability, testability, and maintainability.
Remediation hours: Base 1.0 hr + 0.5 hr * (depth - 4).
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from app.engine.rules.base import ASTViolation, BaseRule, RefactorStatus, ViolationType


class DeepNestingRule(BaseRule):
    rule_id = "AST-001"
    violation_type = ViolationType.DEEP_NESTING
    base_remediation_hours = 1.0
    MAX_NESTING_DEPTH = 4

    NESTING_NODES = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.With,
        ast.AsyncWith,
    )

    def analyze(
        self,
        tree: ast.AST,
        source_code: str,
        file_path: str,
        commit_repo_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ASTViolation]:
        violations: List[ASTViolation] = []
        function_complexities = (context or {}).get("function_complexities", {})
        file_complexity = (context or {}).get("file_complexity", 1)

        def walk_node(node: ast.AST, current_depth: int, current_func: Optional[str]) -> None:
            func_name = current_func
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name

            for child in ast.iter_child_nodes(node):
                if isinstance(child, self.NESTING_NODES):
                    new_depth = current_depth + 1
                    if new_depth > self.MAX_NESTING_DEPTH:
                        # Extract complexity of enclosing function if available
                        comp = function_complexities.get(func_name, file_complexity)
                        excess = new_depth - self.MAX_NESTING_DEPTH
                        hours = round(self.base_remediation_hours + (0.5 * excess), 2)

                        start_line = getattr(child, "lineno", 1)
                        end_line = getattr(child, "end_lineno", start_line)
                        start_col = getattr(child, "col_offset", 0)
                        end_col = getattr(child, "end_col_offset", 0)

                        violations.append(
                            ASTViolation(
                                commit_repo_id=commit_repo_id,
                                file_path=file_path,
                                violation_type=self.violation_type.value,
                                cyclomatic_complexity=comp,
                                remediation_hours=hours,
                                refactor_status=RefactorStatus.FLAGGED.value,
                                start_line=start_line,
                                end_line=end_line,
                                start_col=start_col,
                                end_col=end_col,
                                node_type=child.__class__.__name__,
                                message=(
                                    f"Deep nesting detected (level {new_depth} > {self.MAX_NESTING_DEPTH}). "
                                    f"Consider inverting conditions or extracting helper functions."
                                ),
                            )
                        )
                    walk_node(child, new_depth, func_name)
                else:
                    walk_node(child, current_depth, func_name)

        walk_node(tree, 0, None)
        return violations
