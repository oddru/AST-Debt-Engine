"""Parameter Bloat Rule.

Detects functions or methods with excessive parameters (> 5).
Long parameter lists reduce cohesion and increase API fragility.
Remediation hours: Base 0.75 hr + 0.25 hr * (params - 5).
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from app.engine.rules.base import ASTViolation, BaseRule, RefactorStatus, ViolationType


class ParameterBloatRule(BaseRule):
    rule_id = "AST-002"
    violation_type = ViolationType.PARAMETER_BLOAT
    base_remediation_hours = 0.75
    MAX_PARAMETERS = 5

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

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                # Calculate total formal parameters (positional, keyword-only, varargs)
                # Exclude 'self' or 'cls' if first parameter in method
                param_names = [a.arg for a in args.posonlyargs + args.args]
                if param_names and param_names[0] in ("self", "cls"):
                    param_count = len(param_names) - 1
                else:
                    param_count = len(param_names)

                param_count += len(args.kwonlyargs)
                if args.vararg:
                    param_count += 1
                if args.kwarg:
                    param_count += 1

                if param_count > self.MAX_PARAMETERS:
                    excess = param_count - self.MAX_PARAMETERS
                    comp = function_complexities.get(node.name, file_complexity)
                    hours = round(self.base_remediation_hours + (0.25 * excess), 2)

                    violations.append(
                        ASTViolation(
                            commit_repo_id=commit_repo_id,
                            file_path=file_path,
                            violation_type=self.violation_type.value,
                            cyclomatic_complexity=comp,
                            remediation_hours=hours,
                            refactor_status=RefactorStatus.FLAGGED.value,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            start_col=node.col_offset,
                            end_col=getattr(node, "end_col_offset", 0),
                            node_type=node.__class__.__name__,
                            message=(
                                f"Function '{node.name}' has {param_count} parameters "
                                f"(threshold: {self.MAX_PARAMETERS}). "
                                f"Consider refactoring into a dataclass, config object, or options dict."
                            ),
                        )
                    )

        return violations
