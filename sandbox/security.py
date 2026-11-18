"""Static code security auditor and AST validator for generated Python code."""

import ast
from typing import List, Set, Tuple


class SecurityViolationError(Exception):
    """Raised when generated code contains unsafe AST nodes, forbidden imports, or dangerous calls."""
    pass


class CodeSecurityAuditor:
    """Performs strict Abstract Syntax Tree (AST) inspection to prevent unsafe operations."""

    # Allowed analytical packages and modules
    ALLOWED_MODULES: Set[str] = {
        "pandas",
        "pd",
        "numpy",
        "np",
        "scipy",
        "sklearn",
        "plotly",
        "plotly.express",
        "px",
        "plotly.graph_objects",
        "go",
        "plotly.subplots",
        "math",
        "datetime",
        "time",
        "collections",
        "itertools",
        "re",
        "json",
    }

    # Explicitly forbidden dangerous modules
    FORBIDDEN_MODULES: Set[str] = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "http",
        "urllib",
        "requests",
        "builtins",
        "posix",
        "nt",
        "pty",
        "commands",
        "ctypes",
        "threading",
        "multiprocessing",
        "signal",
        "asyncio",
        "webbrowser",
        "pdb",
        "inspect",
        "importlib",
        "pickle",
        "shelve",
        "tempfile",
        "pathlib",
        "ftplib",
        "poplib",
        "imaplib",
        "smtplib",
        "telnetlib",
    }

    # Dangerous built-ins and dunder attributes that could allow sandbox escapes
    FORBIDDEN_NAMES: Set[str] = {
        "exec",
        "eval",
        "compile",
        "__import__",
        "open",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "input",
        "breakpoint",
        "exit",
        "quit",
        "help",
    }

    FORBIDDEN_ATTRIBUTES: Set[str] = {
        "__subclasses__",
        "__bases__",
        "__mro__",
        "__code__",
        "__globals__",
        "__builtins__",
        "__class__",
        "__dict__",
    }

    @classmethod
    def audit_code(cls, code: str) -> Tuple[bool, List[str]]:
        """Inspect code syntax tree. Return (is_safe, list_of_violations)."""
        violations: List[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"SyntaxError in code: {e.msg} at line {e.lineno}"]

        for node in ast.walk(tree):
            # Check import statements: import foo
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES or root_pkg not in cls.ALLOWED_MODULES:
                        violations.append(
                            f"Line {node.lineno}: Prohibited module import '{alias.name}'. Only analytics libraries are permitted."
                        )

            # Check from foo import bar
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_pkg = node.module.split(".")[0]
                    if root_pkg in cls.FORBIDDEN_MODULES or root_pkg not in cls.ALLOWED_MODULES:
                        violations.append(
                            f"Line {node.lineno}: Prohibited module import 'from {node.module} import ...'. Only analytics libraries are permitted."
                        )

            # Check forbidden function calls
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in cls.FORBIDDEN_NAMES:
                    violations.append(
                        f"Line {node.lineno}: Prohibited call to built-in function '{func.id}()'."
                    )
                elif isinstance(func, ast.Attribute) and func.attr in cls.FORBIDDEN_NAMES:
                    violations.append(
                        f"Line {node.lineno}: Prohibited call to function '{func.attr}()'."
                    )

            # Check forbidden attribute access (e.g., obj.__subclasses__)
            elif isinstance(node, ast.Attribute):
                if node.attr in cls.FORBIDDEN_ATTRIBUTES:
                    violations.append(
                        f"Line {node.lineno}: Prohibited access to dunder attribute '{node.attr}'."
                    )

        is_safe = len(violations) == 0
        return is_safe, violations

    @classmethod
    def validate_code_or_raise(cls, code: str) -> None:
        """Validate code and raise SecurityViolationError if unsafe."""
        is_safe, violations = cls.audit_code(code)
        if not is_safe:
            raise SecurityViolationError(
                "Security Policy Violation: Generated code contains restricted operations:\n"
                + "\n".join(f"- {v}" for v in violations)
            )
