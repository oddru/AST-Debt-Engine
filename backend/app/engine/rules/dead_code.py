"""Dead Code / Unreachable Subtrees Rule.

Detects statements that follow terminal statements (return, raise, break, continue)
within the same lexical block. These nodes can never be executed.
Remediation hours: 0.5 hr.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from app.engine.rules.base import ASTViolation, BaseRule, RefactorStatus, ViolationType


class DeadCodeRule(BaseRule):
    rule_id = "AST-003"
    violation_type = ViolationType.DEAD_CODE
    base_remediation_hours = 0.5

    TERMINATING_NODES = (ast.Return, ast.Raise, ast.Break, ast.Continue)

    def _is_terminating(self, stmt: ast.stmt) -> bool:
        """Returns True if the statement unconditionally terminates execution."""
        if isinstance(stmt, self.TERMINATING_NODES):
            return True
        if isinstance(stmt, ast.If):
            # An If is terminating if both body and orelse are present and both terminate
            if stmt.body and stmt.orelse:
                body_term = any(self._is_terminating(s) for s in stmt.body)
                else_term = any(self._is_terminating(s) for s in stmt.orelse)
                return body_term and else_term
        return False

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

        def check_body(stmts: List[ast.stmt], enclosing_func: Optional[str]) -> None:
            found_terminal = False
            first_dead_stmt: Optional[ast.stmt] = None
            last_dead_stmt: Optional[ast.stmt] = None

            for stmt in stmts:
                if found_terminal:
                    if first_dead_stmt is None:
                        first_dead_stmt = stmt
                    last_dead_stmt = stmt
                elif self._is_terminating(stmt):
                    found_terminal = True

                # Recursively check nested blocks
                for child_name, child_val in ast.iter_fields(stmt):
                    if isinstance(child_val, list):
                        new_enclosing = stmt.name if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) else enclosing_func
                        check_body([item for item in child_val if isinstance(item, ast.stmt)], new_enclosing)

            if first_dead_stmt and last_dead_stmt:
                comp = function_complexities.get(enclosing_func, file_complexity) if enclosing_func else file_complexity
                start_line = first_dead_stmt.lineno
                end_line = getattr(last_dead_stmt, "end_lineno", last_dead_stmt.lineno)

                violations.append(
                    ASTViolation(
                        commit_repo_id=commit_repo_id,
                        file_path=file_path,
                        violation_type=self.violation_type.value,
                        cyclomatic_complexity=comp,
                        remediation_hours=self.base_remediation_hours,
                        refactor_status=RefactorStatus.FLAGGED.value,
                        start_line=start_line,
                        end_line=end_line,
                        start_col=first_dead_stmt.col_offset,
                        end_col=getattr(last_dead_stmt, "end_col_offset", 0),
                        node_type=first_dead_stmt.__class__.__name__,
                        message=(
                            f"Unreachable code detected at lines {start_line}-{end_line} "
                            f"following a terminating statement. Safely prune dead statements."
                        ),
                    )
                )

        if isinstance(tree, ast.Module):
            check_body(tree.body, None)

        return violations
