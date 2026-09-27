"""Duplicate Subtrees / Code Clone Rule.

Detects isomorphic AST subtrees across statements or expressions.
Replaces variable names and literals with wildcards to find structural duplicates.
Threshold: Minimum 6 AST nodes in the cloned subtree.
Remediation hours: Base 2.0 hrs + 0.2 hr * (nodes - 6).
"""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.engine.rules.base import ASTViolation, BaseRule, RefactorStatus, ViolationType


class ASTNormalizer(ast.NodeTransformer):
    """Normalizes an AST subtree by stripping identifiers, literals, and line numbers."""

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.Name(id="_VAR_", ctx=node.ctx)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.Constant(value="_LIT_")


class DuplicateSubtreeRule(BaseRule):
    rule_id = "AST-005"
    violation_type = ViolationType.DUPLICATE_SUBTREES
    base_remediation_hours = 2.0
    MIN_NODE_COUNT = 6

    def analyze(
        self,
        tree: ast.AST,
        source_code: str,
        file_path: str,
        commit_repo_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ASTViolation]:
        violations: List[ASTViolation] = []
        file_complexity = (context or {}).get("file_complexity", 1)

        # Map subtree hash -> List of (node, node_count)
        subtree_registry: Dict[str, List[Tuple[ast.AST, int]]] = defaultdict(list)
        normalizer = ASTNormalizer()

        # We look at block-level constructs and complex expressions
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.With, ast.Try, ast.Assign, ast.Expr)):
                node_count = sum(1 for _ in ast.walk(node))
                if node_count >= self.MIN_NODE_COUNT:
                    import copy
                    clone = copy.deepcopy(node)
                    normalized = normalizer.visit(clone)
                    serialized = ast.dump(normalized, include_attributes=False)
                    subtree_registry[serialized].append((node, node_count))

        # Sort serialized subtrees so larger blocks are evaluated first
        sorted_subtrees = sorted(
            [(k, occ) for k, occ in subtree_registry.items() if len(occ) > 1],
            key=lambda item: max(n_cnt for _, n_cnt in item[1]),
            reverse=True,
        )

        flagged_spans: List[Tuple[int, int]] = []

        for serialized_key, occurrences in sorted_subtrees:
            # The first occurrence is the original; subsequent occurrences are clones
            for node, node_count in occurrences[1:]:
                line_no = getattr(node, "lineno", 1)
                end_line = getattr(node, "end_lineno", line_no)

                # Check if this span is already enclosed inside a previously flagged larger span
                if any(start <= line_no and end_line <= end for start, end in flagged_spans):
                    continue

                flagged_spans.append((line_no, end_line))
                excess = node_count - self.MIN_NODE_COUNT
                hours = round(self.base_remediation_hours + (0.2 * min(excess, 15)), 2)

                violations.append(
                    ASTViolation(
                        commit_repo_id=commit_repo_id,
                        file_path=file_path,
                        violation_type=self.violation_type.value,
                        cyclomatic_complexity=file_complexity,
                        remediation_hours=hours,
                        refactor_status=RefactorStatus.FLAGGED.value,
                        start_line=line_no,
                        end_line=end_line,
                        start_col=getattr(node, "col_offset", 0),
                        end_col=getattr(node, "end_col_offset", 0),
                        node_type=node.__class__.__name__,
                        message=(
                            f"Duplicate AST subtree detected ({node_count} nodes) at lines {line_no}-{end_line}. "
                            f"Matches another code segment in the repository. Extract common subroutine."
                        ),
                    )
                )

        return violations
