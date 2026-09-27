#!/usr/bin/env python3
"""Entry point runner for AST-based static code analysis & technical debt evaluation."""

import os
import sys

# Ensure backend directory is in python search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app.cli import main

if __name__ == "__main__":
    main()
