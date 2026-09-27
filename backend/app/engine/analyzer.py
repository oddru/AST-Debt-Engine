"""AST Debt Analyzer Pipeline.

Coordinates deterministic AST traversal, Control Flow Graph analysis,
Halstead Software Science metrics, Maintainability Index, and rule evaluations.
"""

from __future__ import annotations

import ast
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.engine.cfg import CFGBuilder
from app.engine.halstead import HalsteadCalculator, HalsteadMetrics
from app.engine.metrics import CodeLineMetrics, CodeMetricsCalculator
from app.engine.rules import ALL_RULES, ASTViolation, BaseRule, RefactorStatus


@dataclass
class FunctionMetrics:
    name: str
    start_line: int
    end_line: int
    cyclomatic_complexity: int
    is_high_risk: bool  # v(G) > 10


@dataclass
class FileAnalysisResult:
    commit_repo_id: str
    file_path: str
    content: str
    line_metrics: CodeLineMetrics
    halstead: HalsteadMetrics
    cyclomatic_complexity: int
    maintainability_index: float
    maintainability_category: str
    is_high_risk: bool
    functions: List[FunctionMetrics] = field(default_factory=list)
    violations: List[ASTViolation] = field(default_factory=list)

    @property
    def total_remediation_hours(self) -> float:
        return round(sum(v.remediation_hours for v in self.violations if v.refactor_status == RefactorStatus.FLAGGED.value), 2)


@dataclass
class RepositoryAnalysisResult:
    commit_repo_id: str
    name: str
    files: List[FileAnalysisResult] = field(default_factory=list)
    total_files: int = 0
    total_loc: int = 0
    total_sloc: int = 0
    avg_cyclomatic_complexity: float = 0.0
    overall_maintainability_index: float = 0.0
    high_risk_file_ratio: float = 0.0  # Percentage of files with v(G) > 10
    total_debt_backlog_hours: float = 0.0  # Sum of Flagged remediation_hours
    all_violations: List[ASTViolation] = field(default_factory=list)


class ASTDebtAnalyzer:
    """Deterministic analyzer engine for files and repositories."""

    def __init__(self, rules: Optional[List[BaseRule]] = None) -> None:
        self.rules = rules or ALL_RULES

    def analyze_source(
        self,
        source_code: str,
        file_path: str = "source.py",
        commit_repo_id: Optional[str] = None,
    ) -> FileAnalysisResult:
        """Analyzes a single source code string."""
        repo_id = commit_repo_id or str(uuid.uuid4())[:8]

        # 1. Line metrics
        line_metrics = CodeMetricsCalculator.calculate_line_metrics(source_code)

        # 2. Halstead metrics
        halstead = HalsteadCalculator.calculate(source_code)

        # 3. Parse AST
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            # Create a syntax violation
            syntax_violation = ASTViolation(
                commit_repo_id=repo_id,
                file_path=file_path,
                violation_type="Syntax Error",
                cyclomatic_complexity=1,
                remediation_hours=1.0,
                refactor_status=RefactorStatus.FLAGGED.value,
                start_line=e.lineno or 1,
                end_line=e.lineno or 1,
                start_col=e.offset or 0,
                end_col=e.offset or 0,
                node_type="SyntaxError",
                message=f"Syntax Error: {e.msg}",
            )
            return FileAnalysisResult(
                commit_repo_id=repo_id,
                file_path=file_path,
                content=source_code,
                line_metrics=line_metrics,
                halstead=halstead,
                cyclomatic_complexity=1,
                maintainability_index=0.0,
                maintainability_category="Low",
                is_high_risk=False,
                violations=[syntax_violation],
            )

        # 4. CFG Analysis for each function and module
        func_complexities: Dict[str, int] = {}
        function_records: List[FunctionMetrics] = []
        max_func_complexity = 1

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                builder = CFGBuilder(name=node.name)
                cfg = builder.build_for_function(node)
                vg = cfg.calculate_cyclomatic_complexity()
                func_complexities[node.name] = vg
                max_func_complexity = max(max_func_complexity, vg)
                function_records.append(
                    FunctionMetrics(
                        name=node.name,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        cyclomatic_complexity=vg,
                        is_high_risk=vg > 10,
                    )
                )

        # Module-level CFG
        mod_builder = CFGBuilder(name="<module>")
        mod_cfg = mod_builder.build_for_module(tree)
        module_vg = mod_cfg.calculate_cyclomatic_complexity()

        # The effective cyclomatic complexity for the file artifact is the maximum of function complexities or module base
        effective_vg = max(max_func_complexity, module_vg)
        is_high_risk = effective_vg > 10

        # 5. Maintainability Index
        mi_score, mi_category = CodeMetricsCalculator.calculate_maintainability_index(
            halstead_volume=halstead.volume,
            cyclomatic_complexity=effective_vg,
            sloc=line_metrics.sloc,
        )

        # 6. Evaluate Rule Engine
        violations: List[ASTViolation] = []
        context = {
            "function_complexities": func_complexities,
            "file_complexity": effective_vg,
        }

        for rule in self.rules:
            detected = rule.analyze(
                tree=tree,
                source_code=source_code,
                file_path=file_path,
                commit_repo_id=repo_id,
                context=context,
            )
            violations.extend(detected)

        return FileAnalysisResult(
            commit_repo_id=repo_id,
            file_path=file_path,
            content=source_code,
            line_metrics=line_metrics,
            halstead=halstead,
            cyclomatic_complexity=effective_vg,
            maintainability_index=mi_score,
            maintainability_category=mi_category,
            is_high_risk=is_high_risk,
            functions=function_records,
            violations=violations,
        )

    def analyze_file(self, file_path: str | Path, commit_repo_id: Optional[str] = None) -> FileAnalysisResult:
        """Analyzes a file from disk."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        return self.analyze_source(code, file_path=str(path.as_posix()), commit_repo_id=commit_repo_id)

    def analyze_repository(
        self,
        directory_path: str | Path,
        repo_name: Optional[str] = None,
        commit_repo_id: Optional[str] = None,
    ) -> RepositoryAnalysisResult:
        """Traverses a directory and analyzes all Python source files."""
        root_dir = Path(directory_path)
        repo_id = commit_repo_id or str(uuid.uuid4())[:8]
        name = repo_name or root_dir.name

        file_results: List[FileAnalysisResult] = []
        all_violations: List[ASTViolation] = []

        for root, _, files in os.walk(root_dir):
            for file in sorted(files):
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(root_dir).as_posix()
                    file_res = self.analyze_file(full_path, commit_repo_id=repo_id)
                    file_res.file_path = rel_path
                    # Update repo_id and file_path in violations
                    for v in file_res.violations:
                        v.commit_repo_id = repo_id
                        v.file_path = rel_path
                    file_results.append(file_res)
                    all_violations.extend(file_res.violations)

        total_files = len(file_results)
        total_loc = sum(f.line_metrics.total_loc for f in file_results)
        total_sloc = sum(f.line_metrics.sloc for f in file_results)

        if total_files > 0:
            avg_complexity = round(sum(f.cyclomatic_complexity for f in file_results) / total_files, 2)
            overall_mi = round(sum(f.maintainability_index for f in file_results) / total_files, 2)
            high_risk_files = sum(1 for f in file_results if f.is_high_risk)
            high_risk_ratio = round((high_risk_files / total_files) * 100.0, 2)
        else:
            avg_complexity = 0.0
            overall_mi = 100.0
            high_risk_ratio = 0.0

        total_debt_hours = round(
            sum(v.remediation_hours for v in all_violations if v.refactor_status == RefactorStatus.FLAGGED.value),
            2
        )

        return RepositoryAnalysisResult(
            commit_repo_id=repo_id,
            name=name,
            files=file_results,
            total_files=total_files,
            total_loc=total_loc,
            total_sloc=total_sloc,
            avg_cyclomatic_complexity=avg_complexity,
            overall_maintainability_index=overall_mi,
            high_risk_file_ratio=high_risk_ratio,
            total_debt_backlog_hours=total_debt_hours,
            all_violations=all_violations,
        )
