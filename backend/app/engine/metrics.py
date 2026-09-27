"""Source Code Metrics and Maintainability Index (MI) Engine.

Calculates:
- LOC (Total lines of code)
- SLOC (Source lines of code, excluding comments & blanks)
- Maintainability Index:
    MI_raw = 171 - 5.2 * ln(V) - 0.23 * v(G) - 16.2 * ln(SLOC)
    MI = max(0, min(100, (MI_raw / 171) * 100))
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class CodeLineMetrics:
    total_loc: int
    sloc: int
    comment_lines: int
    blank_lines: int


class CodeMetricsCalculator:
    """Computes line metrics and maintainability indices."""

    @classmethod
    def calculate_line_metrics(cls, source_code: str) -> CodeLineMetrics:
        lines = source_code.splitlines()
        total_loc = len(lines)
        blank_lines = 0
        comment_lines = 0
        sloc = 0

        in_multiline_docstring = False
        docstring_delim = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
                continue

            # Check multiline docstrings
            if in_multiline_docstring:
                comment_lines += 1
                if docstring_delim and docstring_delim in stripped:
                    in_multiline_docstring = False
                    docstring_delim = None
                continue

            if stripped.startswith(('"""', "'''")):
                comment_lines += 1
                delim = stripped[:3]
                # If opening and closing on same line (and not empty)
                if stripped.count(delim) == 1:
                    in_multiline_docstring = True
                    docstring_delim = delim
                continue

            if stripped.startswith("#"):
                comment_lines += 1
                continue

            sloc += 1

        return CodeLineMetrics(
            total_loc=total_loc,
            sloc=sloc,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
        )

    @classmethod
    def calculate_maintainability_index(
        cls,
        halstead_volume: float,
        cyclomatic_complexity: int,
        sloc: int,
    ) -> Tuple[float, str]:
        """Calculates normalized Maintainability Index [0, 100] and category."""
        if sloc <= 0:
            return 100.0, "High"

        # Prevent domain error on log(0)
        ln_v = math.log(halstead_volume) if halstead_volume > 0 else 0.0
        ln_sloc = math.log(sloc) if sloc > 0 else 0.0

        # Standard SEI / Coleman-Oman formula
        mi_raw = 171.0 - (5.2 * ln_v) - (0.23 * cyclomatic_complexity) - (16.2 * ln_sloc)

        # Normalize to 0 - 100
        mi_normalized = max(0.0, min(100.0, (mi_raw / 171.0) * 100.0))
        mi_score = round(mi_normalized, 2)

        if mi_score >= 80.0:
            category = "High"
        elif mi_score >= 65.0:
            category = "Moderate"
        else:
            category = "Low"

        return mi_score, category
