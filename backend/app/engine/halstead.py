"""Halstead Software Science Metrics Engine.

Computes Halstead Program Vocabulary, Length, Volume, Difficulty, and Effort
via deterministic token-stream analysis.
"""

from __future__ import annotations

import io
import math
import tokenize
from collections import Counter
from dataclasses import dataclass
from typing import Set


@dataclass
class HalsteadMetrics:
    distinct_operators: int  # eta1
    distinct_operands: int   # eta2
    total_operators: int      # N1
    total_operands: int       # N2
    vocabulary: int           # eta = eta1 + eta2
    length: int               # N = N1 + N2
    volume: float             # V = N * log2(eta)
    difficulty: float         # D = (eta1 / 2) * (N2 / eta2)
    effort: float             # E = D * V

    @classmethod
    def empty(cls) -> HalsteadMetrics:
        return cls(
            distinct_operators=0,
            distinct_operands=0,
            total_operators=0,
            total_operands=0,
            vocabulary=0,
            length=0,
            volume=0.0,
            difficulty=0.0,
            effort=0.0,
        )


class HalsteadCalculator:
    """Calculates Halstead metrics on a Python source code string."""

    # Set of Python keywords that act as operators
    KEYWORD_OPERATORS: Set[str] = {
        "and", "as", "assert", "async", "await", "break", "class", "continue",
        "def", "del", "elif", "else", "except", "finally", "for", "from",
        "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
        "or", "pass", "raise", "return", "try", "while", "with", "yield"
    }

    @classmethod
    def calculate(cls, source_code: str) -> HalsteadMetrics:
        if not source_code.strip():
            return HalsteadMetrics.empty()

        operator_counts: Counter[str] = Counter()
        operand_counts: Counter[str] = Counter()

        try:
            tokens = tokenize.tokenize(io.BytesIO(source_code.encode("utf-8")).readline)
            for tok in tokens:
                tok_type = tok.type
                tok_str = tok.string

                # Ignore comments, whitespace/indentation, and encoding markers
                if tok_type in (
                    tokenize.COMMENT,
                    tokenize.NL,
                    tokenize.NEWLINE,
                    tokenize.INDENT,
                    tokenize.DEDENT,
                    tokenize.ENCODING,
                    tokenize.ENDMARKER,
                ):
                    continue

                if tok_type == tokenize.OP:
                    operator_counts[tok_str] += 1
                elif tok_type == tokenize.NAME:
                    if tok_str in cls.KEYWORD_OPERATORS:
                        operator_counts[tok_str] += 1
                    elif tok_str in ("True", "False", "None"):
                        operand_counts[tok_str] += 1
                    else:
                        operand_counts[tok_str] += 1
                elif tok_type in (tokenize.NUMBER, tokenize.STRING):
                    operand_counts[tok_str] += 1
        except tokenize.TokenError:
            # Fallback if tokenizer encounters incomplete quotes
            pass

        eta1 = len(operator_counts)
        eta2 = len(operand_counts)
        n1 = sum(operator_counts.values())
        n2 = sum(operand_counts.values())

        vocabulary = eta1 + eta2
        length = n1 + n2

        if vocabulary > 0 and length > 0:
            volume = float(length * math.log2(vocabulary))
        else:
            volume = 0.0

        if eta2 > 0:
            difficulty = float((eta1 / 2.0) * (n2 / eta2))
        else:
            difficulty = 0.0

        effort = float(difficulty * volume)

        return HalsteadMetrics(
            distinct_operators=eta1,
            distinct_operands=eta2,
            total_operators=n1,
            total_operands=n2,
            vocabulary=vocabulary,
            length=length,
            volume=round(volume, 2),
            difficulty=round(difficulty, 2),
            effort=round(effort, 2),
        )
