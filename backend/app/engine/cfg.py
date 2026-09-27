"""Control Flow Graph (CFG) Construction and Cyclomatic Complexity Engine.

Implements the formal McCabe cyclomatic complexity formulation:
    v(G) = E - N + 2P
where:
    E = Number of directed edges in the control flow graph.
    N = Number of basic blocks / nodes in the control flow graph.
    P = Number of connected components (P = 1 for a single subroutine).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class CFGNodeType(str, Enum):
    ENTRY = "ENTRY"
    BASIC_BLOCK = "BASIC_BLOCK"
    BRANCH = "BRANCH"
    LOOP_HEADER = "LOOP_HEADER"
    LOOP_EXIT = "LOOP_EXIT"
    EXCEPTION_HANDLER = "EXCEPTION_HANDLER"
    RETURN = "RETURN"
    RAISE = "RAISE"
    EXIT = "EXIT"


class CFGEdgeType(str, Enum):
    FALLTHROUGH = "FALLTHROUGH"
    TRUE_BRANCH = "TRUE_BRANCH"
    FALSE_BRANCH = "FALSE_BRANCH"
    LOOP_BODY = "LOOP_BODY"
    LOOP_EXIT = "LOOP_EXIT"
    LOOP_BACK = "LOOP_BACK"
    RETURN_EDGE = "RETURN_EDGE"
    EXCEPTION_EDGE = "EXCEPTION_EDGE"


@dataclass
class CFGNode:
    id: int
    node_type: CFGNodeType
    label: str
    statements: List[ast.AST] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CFGNode):
            return self.id == other.id
        return False


@dataclass
class CFGEdge:
    from_id: int
    to_id: int
    edge_type: CFGEdgeType

    def __hash__(self) -> int:
        return hash((self.from_id, self.to_id, self.edge_type))


@dataclass
class ControlFlowGraph:
    """Directed Control Flow Graph representing program execution paths."""
    name: str
    entry_id: int = 0
    exit_id: int = 0
    nodes: Dict[int, CFGNode] = field(default_factory=dict)
    edges: Set[CFGEdge] = field(default_factory=set)
    p: int = 1  # Connected components

    def add_node(self, node: CFGNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, from_id: int, to_id: int, edge_type: CFGEdgeType = CFGEdgeType.FALLTHROUGH) -> None:
        if from_id in self.nodes and to_id in self.nodes:
            self.edges.add(CFGEdge(from_id=from_id, to_id=to_id, edge_type=edge_type))

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    def calculate_cyclomatic_complexity(self) -> int:
        """Calculates v(G) = E - N + 2P."""
        e = self.edge_count
        n = self.node_count
        if n == 0:
            return 1
        complexity = e - n + (2 * self.p)
        # Minimum complexity for any existing code graph is 1
        return max(1, complexity)


class CFGBuilder:
    """Builds a Control Flow Graph from a Python function or module AST."""

    def __init__(self, name: str = "<subroutine>") -> None:
        self.name = name
        self.graph = ControlFlowGraph(name=name)
        self._next_id = 0
        self._loop_stack: List[Tuple[int, int]] = []  # (loop_header_id, loop_exit_id)

    def _create_node(self, node_type: CFGNodeType, label: str, ast_nodes: Optional[List[ast.AST]] = None) -> CFGNode:
        node_id = self._next_id
        self._next_id += 1
        stmt_list = ast_nodes or []
        start_line = stmt_list[0].lineno if stmt_list and hasattr(stmt_list[0], "lineno") else 0
        end_line = stmt_list[-1].end_lineno if stmt_list and hasattr(stmt_list[-1], "end_lineno") else start_line
        
        node = CFGNode(
            id=node_id,
            node_type=node_type,
            label=label,
            statements=stmt_list,
            start_line=start_line or 0,
            end_line=end_line or 0,
        )
        self.graph.add_node(node)
        return node

    def build_for_function(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> ControlFlowGraph:
        """Constructs a CFG for a function definition."""
        self.name = func_node.name
        self.graph.name = func_node.name
        
        # 1. Entry node
        entry = self._create_node(CFGNodeType.ENTRY, f"ENTRY: {func_node.name}", [func_node])
        self.graph.entry_id = entry.id

        # 2. Exit node
        exit_node = self._create_node(CFGNodeType.EXIT, f"EXIT: {func_node.name}")
        self.graph.exit_id = exit_node.id

        # 3. Process statements
        last_nodes = self._process_statement_list(func_node.body, [entry.id], exit_node.id)

        # 4. Connect any hanging endpoints to EXIT
        for endpoint_id in last_nodes:
            self.graph.add_edge(endpoint_id, exit_node.id, CFGEdgeType.FALLTHROUGH)

        # 5. Expand complexity for Boolean Operators (and/or) in conditionals
        self._inject_boolean_op_branches(func_node)

        return self.graph

    def build_for_module(self, mod_node: ast.Module) -> ControlFlowGraph:
        """Constructs a top-level module CFG."""
        entry = self._create_node(CFGNodeType.ENTRY, "ENTRY: <module>", [mod_node])
        self.graph.entry_id = entry.id
        exit_node = self._create_node(CFGNodeType.EXIT, "EXIT: <module>")
        self.graph.exit_id = exit_node.id

        last_nodes = self._process_statement_list(mod_node.body, [entry.id], exit_node.id)
        for endpoint_id in last_nodes:
            self.graph.add_edge(endpoint_id, exit_node.id, CFGEdgeType.FALLTHROUGH)

        self._inject_boolean_op_branches(mod_node)
        return self.graph

    def _process_statement_list(self, statements: List[ast.stmt], incoming_ids: List[int], exit_id: int) -> List[int]:
        """Sequentially processes a list of statements."""
        current_incomings = incoming_ids

        i = 0
        while i < len(statements):
            stmt = statements[i]

            # If there are no incoming execution paths, remaining statements are dead code
            if not current_incomings:
                # Still create dead nodes for inspection if needed, but not connected
                break

            if isinstance(stmt, ast.If):
                current_incomings = self._process_if(stmt, current_incomings, exit_id)
            elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                current_incomings = self._process_loop(stmt, current_incomings, exit_id)
            elif isinstance(stmt, ast.Return):
                ret_node = self._create_node(CFGNodeType.RETURN, "return", [stmt])
                for inc in current_incomings:
                    self.graph.add_edge(inc, ret_node.id, CFGEdgeType.FALLTHROUGH)
                self.graph.add_edge(ret_node.id, exit_id, CFGEdgeType.RETURN_EDGE)
                current_incomings = []  # No fallthrough after return
            elif isinstance(stmt, ast.Raise):
                raise_node = self._create_node(CFGNodeType.RAISE, "raise", [stmt])
                for inc in current_incomings:
                    self.graph.add_edge(inc, raise_node.id, CFGEdgeType.FALLTHROUGH)
                self.graph.add_edge(raise_node.id, exit_id, CFGEdgeType.EXCEPTION_EDGE)
                current_incomings = []
            elif isinstance(stmt, ast.Break):
                if self._loop_stack:
                    _, loop_exit_id = self._loop_stack[-1]
                    break_node = self._create_node(CFGNodeType.BASIC_BLOCK, "break", [stmt])
                    for inc in current_incomings:
                        self.graph.add_edge(inc, break_node.id, CFGEdgeType.FALLTHROUGH)
                    self.graph.add_edge(break_node.id, loop_exit_id, CFGEdgeType.LOOP_EXIT)
                current_incomings = []
            elif isinstance(stmt, ast.Continue):
                if self._loop_stack:
                    loop_header_id, _ = self._loop_stack[-1]
                    cont_node = self._create_node(CFGNodeType.BASIC_BLOCK, "continue", [stmt])
                    for inc in current_incomings:
                        self.graph.add_edge(inc, cont_node.id, CFGEdgeType.FALLTHROUGH)
                    self.graph.add_edge(cont_node.id, loop_header_id, CFGEdgeType.LOOP_BACK)
                current_incomings = []
            elif isinstance(stmt, ast.Try):
                current_incomings = self._process_try(stmt, current_incomings, exit_id)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Definitions are single atomic basic blocks at the parent level
                def_node = self._create_node(CFGNodeType.BASIC_BLOCK, f"def {stmt.name}", [stmt])
                for inc in current_incomings:
                    self.graph.add_edge(inc, def_node.id, CFGEdgeType.FALLTHROUGH)
                current_incomings = [def_node.id]
            else:
                # Group contiguous simple statements into a single basic block
                block_stmts = [stmt]
                while i + 1 < len(statements) and not isinstance(
                    statements[i + 1],
                    (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Return, ast.Raise, ast.Break, ast.Continue, ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    i += 1
                    block_stmts.append(statements[i])

                label = f"Block ({len(block_stmts)} stmts)"
                blk_node = self._create_node(CFGNodeType.BASIC_BLOCK, label, block_stmts)
                for inc in current_incomings:
                    self.graph.add_edge(inc, blk_node.id, CFGEdgeType.FALLTHROUGH)
                current_incomings = [blk_node.id]

            i += 1

        return current_incomings

    def _process_if(self, if_node: ast.If, incoming_ids: List[int], exit_id: int) -> List[int]:
        """Processes an If decision block."""
        branch_node = self._create_node(CFGNodeType.BRANCH, "if_condition", [if_node.test])
        for inc in incoming_ids:
            self.graph.add_edge(inc, branch_node.id, CFGEdgeType.FALLTHROUGH)

        # True path (then)
        then_endpoints = self._process_statement_list(if_node.body, [branch_node.id], exit_id)

        # False path (else or fallthrough)
        if if_node.orelse:
            else_endpoints = self._process_statement_list(if_node.orelse, [branch_node.id], exit_id)
        else:
            else_endpoints = [branch_node.id]

        return then_endpoints + else_endpoints

    def _process_loop(self, loop_node: ast.For | ast.AsyncFor | ast.While, incoming_ids: List[int], exit_id: int) -> List[int]:
        """Processes a Loop construct (While, For)."""
        header_node = self._create_node(CFGNodeType.LOOP_HEADER, "loop_header", [loop_node])
        loop_exit_node = self._create_node(CFGNodeType.LOOP_EXIT, "loop_exit")

        for inc in incoming_ids:
            self.graph.add_edge(inc, header_node.id, CFGEdgeType.FALLTHROUGH)

        # Push to loop stack for break/continue targets
        self._loop_stack.append((header_node.id, loop_exit_node.id))

        # Body execution path
        body_endpoints = self._process_statement_list(loop_node.body, [header_node.id], exit_id)
        for be in body_endpoints:
            self.graph.add_edge(be, header_node.id, CFGEdgeType.LOOP_BACK)

        self._loop_stack.pop()

        # Else branch on loop if present
        if loop_node.orelse:
            orelse_endpoints = self._process_statement_list(loop_node.orelse, [header_node.id], exit_id)
            for oe in orelse_endpoints:
                self.graph.add_edge(oe, loop_exit_node.id, CFGEdgeType.FALLTHROUGH)
        else:
            self.graph.add_edge(header_node.id, loop_exit_node.id, CFGEdgeType.LOOP_EXIT)

        return [loop_exit_node.id]

    def _process_try(self, try_node: ast.Try, incoming_ids: List[int], exit_id: int) -> List[int]:
        """Processes Try/Except/Finally blocks."""
        try_entry = self._create_node(CFGNodeType.BASIC_BLOCK, "try_body")
        for inc in incoming_ids:
            self.graph.add_edge(inc, try_entry.id, CFGEdgeType.FALLTHROUGH)

        body_endpoints = self._process_statement_list(try_node.body, [try_entry.id], exit_id)
        handler_endpoints: List[int] = []

        for handler in try_node.handlers:
            handler_node = self._create_node(CFGNodeType.EXCEPTION_HANDLER, f"except {ast.unparse(handler.type) if handler.type else '*'}")
            self.graph.add_edge(try_entry.id, handler_node.id, CFGEdgeType.EXCEPTION_EDGE)
            h_ends = self._process_statement_list(handler.body, [handler_node.id], exit_id)
            handler_endpoints.extend(h_ends)

        join_endpoints = body_endpoints + handler_endpoints

        if try_node.finalbody:
            finally_endpoints = self._process_statement_list(try_node.finalbody, join_endpoints, exit_id)
            return finally_endpoints

        return join_endpoints

    def _inject_boolean_op_branches(self, tree: ast.AST) -> None:
        """Injects decision nodes for boolean operators (and/or) in conditions,

        comprehensions, and ternary expressions per McCabe's definition.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp):
                # Each value beyond the first is an additional branch
                extra_branches = len(node.values) - 1
                for _ in range(extra_branches):
                    b_node = self._create_node(CFGNodeType.BRANCH, "bool_op_branch", [node])
                    # Represent decision by adding 1 node and 2 edges -> net change is +1 to v(G)
                    # Because delta = E - N = 2 - 1 = +1
                    aux_target = self._create_node(CFGNodeType.BASIC_BLOCK, "bool_op_target")
                    self.graph.add_edge(b_node.id, aux_target.id, CFGEdgeType.TRUE_BRANCH)
                    self.graph.add_edge(b_node.id, self.graph.exit_id, CFGEdgeType.FALSE_BRANCH)
                    self.graph.add_edge(aux_target.id, self.graph.exit_id, CFGEdgeType.FALLTHROUGH)
            elif isinstance(node, ast.IfExp):
                # Ternary expression: condition ? then : else
                t_node = self._create_node(CFGNodeType.BRANCH, "ternary_if", [node])
                aux = self._create_node(CFGNodeType.BASIC_BLOCK, "ternary_then")
                self.graph.add_edge(t_node.id, aux.id, CFGEdgeType.TRUE_BRANCH)
                self.graph.add_edge(t_node.id, self.graph.exit_id, CFGEdgeType.FALSE_BRANCH)
                self.graph.add_edge(aux.id, self.graph.exit_id, CFGEdgeType.FALLTHROUGH)
            elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for gen in node.generators:
                    for if_expr in gen.ifs:
                        c_node = self._create_node(CFGNodeType.BRANCH, "comp_filter", [if_expr])
                        aux = self._create_node(CFGNodeType.BASIC_BLOCK, "comp_pass")
                        self.graph.add_edge(c_node.id, aux.id, CFGEdgeType.TRUE_BRANCH)
                        self.graph.add_edge(c_node.id, self.graph.exit_id, CFGEdgeType.FALSE_BRANCH)
                        self.graph.add_edge(aux.id, self.graph.exit_id, CFGEdgeType.FALLTHROUGH)
