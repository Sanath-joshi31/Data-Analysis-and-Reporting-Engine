"""Unit tests for AST static code security and policy violation detection."""

import pytest
from sandbox.security import CodeSecurityAuditor, SecurityViolationError


def test_clean_analytical_code_passes():
    """Verify standard data analysis scripts pass security audit without warnings."""
    clean_code = """
import pandas as pd
import numpy as np
import plotly.express as px

df_clean = df.dropna()
summary = df_clean.groupby('Region')['Sales'].sum().reset_index()
OUTPUT['tables']['summary'] = summary
OUTPUT['metrics']['total_sales'] = float(summary['Sales'].sum())
fig = px.bar(summary, x='Region', y='Sales')
OUTPUT['figures'].append(fig.to_dict())
"""
    is_safe, violations = CodeSecurityAuditor.audit_code(clean_code)
    assert is_safe is True
    assert len(violations) == 0


def test_forbidden_module_import_fails():
    """Verify attempts to import os, subprocess, socket, or requests are blocked."""
    prohibited_snippets = [
        "import os\nos.system('dir')",
        "import subprocess\nsubprocess.run(['ls'])",
        "import socket\ns = socket.socket()",
        "import requests\nrequests.get('https://example.com')",
        "from os.path import exists",
        "import sys\nsys.exit(0)"
    ]

    for snippet in prohibited_snippets:
        is_safe, violations = CodeSecurityAuditor.audit_code(snippet)
        assert is_safe is False, f"Expected unsafe for: {snippet}"
        assert len(violations) > 0


def test_dangerous_builtin_calls_blocked():
    """Verify built-in execution functions like exec, eval, open, __import__ are blocked."""
    forbidden_calls = [
        "exec('print(123)')",
        "eval('2 + 2')",
        "f = open('secret.txt', 'r')",
        "mod = __import__('os')",
        "getattr(df, '__class__')"
    ]

    for call_code in forbidden_calls:
        is_safe, violations = CodeSecurityAuditor.audit_code(call_code)
        assert is_safe is False, f"Expected unsafe for call: {call_code}"


def test_dunder_attribute_traversal_blocked():
    """Verify sandbox escape via __subclasses__ traversal is blocked."""
    escape_code = """
subclasses = ().__class__.__bases__[0].__subclasses__()
"""
    is_safe, violations = CodeSecurityAuditor.audit_code(escape_code)
    assert is_safe is False
    assert any("__subclasses__" in v or "__class__" in v for v in violations)


def test_validate_or_raise():
    """Verify helper raises SecurityViolationError on unsafe code."""
    with pytest.raises(SecurityViolationError):
        CodeSecurityAuditor.validate_code_or_raise("import shutil\nshutil.rmtree('/')")
