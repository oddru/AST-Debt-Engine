# AST-Based Static Code Analysis & Technical Debt Evaluation Engine

An enterprise-grade, deterministic AST static code analysis and technical debt evaluation engine. Operates strictly using compiler AST parsing, Control Flow Graph (CFG) analysis, and deterministic mathematical metric formulas (zero probabilistic LLM inference).

## Core Formulas

1. **McCabe Cyclomatic Complexity**:
   $$v(G) = E - N + 2P$$
   - $E$: Directed edges in the control flow graph.
   - $N$: Basic block nodes in the control flow graph.
   - $P$: Connected components ($P = 1$ for a single subroutine).

2. **Halstead Software Science**:
   - $\eta = \eta_1 + \eta_2$ (Program Vocabulary: distinct operators + operands)
   - $N = N_1 + N_2$ (Program Length: total operators + operands)
   - $V = N \times \log_2(\eta)$ (Halstead Volume)

3. **Maintainability Index ($MI$)**:
   $$MI_{\text{raw}} = 171 - 5.2 \times \ln(V) - 0.23 \times v(G) - 16.2 \times \ln(\text{SLOC})$$
   $$MI = \max\left(0, \min\left(100, \frac{MI_{\text{raw}}}{171} \times 100\right)\right)$$

4. **The 6 Primary Record Fields**:
   - `commit_repo_id`: Codebase/commit identifier.
   - `file_path`: Relational file path.
   - `violation_type`: Deep Nesting, Parameter Bloat, Dead Code, High Complexity, Duplicate Subtrees.
   - `cyclomatic_complexity`: Integer $v(G)$ score.
   - `remediation_hours`: Rule-weighted effort estimate.
   - `refactor_status`: `Flagged`, `Rule-Patched`, `Dismissed`.

---

## Quickstart (Phase 1 CLI)

### 1. Activate Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Run Analysis on a File or Directory
```bash
python backend/run_analysis.py backend/samples/sample_complex.py
python backend/run_analysis.py backend/samples/sample_clean.py
python backend/run_analysis.py backend/samples/
```

### 3. Run Unit Tests
```bash
pytest backend/tests -v
```

---

## Phased Roadmap
- [x] **Phase 1 (Core Engine)**: Standalone AST parser, CFG $v(G) = E - N + 2P$, Halstead volume, Maintainability Index, 5 AST anti-pattern rules, and Rich console dashboard.
- [ ] **Phase 2 (Database & API)**: FastAPI server, SQLAlchemy 2.0 schemas (`repositories`, `file_artifacts`, `ast_violations`, `audit_logs`), file/zip upload, and REST endpoints.
- [ ] **Phase 3 (Frontend Dashboard)**: React 19 + TypeScript + Tailwind UI featuring KPI cards, the interactive 6-field record table with inline status toggles, and syntax-highlighted code viewer.
- [ ] **Phase 4 (AST Mutation/Auto-Patching)**: Programmatic code refactoring engine generating unified diffs and applying safe syntax transformations.
