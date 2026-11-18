"""Secure out-of-process subprocess executor with resource limits, timeout, and AST security."""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

from schemas.execution import ExecutionResult
from sandbox.security import CodeSecurityAuditor, SecurityViolationError

logger = logging.getLogger(__name__)


HARNESS_TEMPLATE = '''# Autonomous Data Analyst Sandbox Execution Harness
import json
import sys
import math
import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return None if math.isnan(obj) or math.isinf(obj) else float(obj)
        elif isinstance(obj, (np.ndarray, pd.Series)):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        elif isinstance(obj, (datetime.date, datetime.datetime, pd.Timestamp)):
            return str(obj)
        return super().default(obj)

# Load dataset
dataset_path = {dataset_path_repr}
if dataset_path.endswith('.parquet'):
    df = pd.read_parquet(dataset_path)
elif dataset_path.endswith(('.xlsx', '.xls')):
    df = pd.read_excel(dataset_path)
elif dataset_path.endswith('.json'):
    df = pd.read_json(dataset_path)
else:
    try:
        df = pd.read_csv(dataset_path, low_memory=False)
    except Exception:
        df = pd.read_csv(dataset_path, encoding='latin-1', low_memory=False)

# Execution output container
OUTPUT = {{
    "tables": {{}},
    "metrics": {{}},
    "figures": []
}}

try:
    # --- USER GENERATED CODE BEGIN ---
{indented_user_code}
    # --- USER GENERATED CODE END ---
except Exception as e:
    import traceback
    sys.stderr.write(traceback.format_exc())
    sys.exit(1)

# Check if a standalone figure variable 'fig' was created
if "fig" in locals() and hasattr(locals()["fig"], "to_dict"):
    try:
        OUTPUT["figures"].append(locals()["fig"].to_dict())
    except Exception:
        pass

# Serialize output data to output.json
try:
    # Convert any pandas DataFrame in OUTPUT["tables"] to list of dicts
    clean_tables = {{}}
    for tbl_name, tbl_val in OUTPUT.get("tables", {{}}).items():
        if isinstance(tbl_val, pd.DataFrame):
            clean_tables[tbl_name] = tbl_val.to_dict(orient="records")
        elif isinstance(tbl_val, list):
            clean_tables[tbl_name] = tbl_val
        elif isinstance(tbl_val, dict):
            clean_tables[tbl_name] = [tbl_val]
        else:
            clean_tables[tbl_name] = str(tbl_val)
    OUTPUT["tables"] = clean_tables

    # Convert plotly figure objects in OUTPUT["figures"] if any
    clean_figures = []
    for fig_obj in OUTPUT.get("figures", []):
        if hasattr(fig_obj, "to_dict"):
            clean_figures.append(fig_obj.to_dict())
        elif isinstance(fig_obj, dict):
            clean_figures.append(fig_obj)
    OUTPUT["figures"] = clean_figures

    with open({output_json_repr}, "w", encoding="utf-8") as f:
        json.dump(OUTPUT, f, cls=CustomJSONEncoder, indent=2)
except Exception as e:
    sys.stderr.write(f"Failed to serialize OUTPUT: {{str(e)}}")
    sys.exit(2)
'''


class SecureSubprocessExecutor:
    """Executes generated analysis code in an isolated out-of-process subprocess.
    
    Security attributes:
    - Pre-execution AST audit for forbidden packages and dangerous builtins.
    - Isolated temporary scratch directory for every execution run.
    - Sanitized environment variables (strips API keys and host secrets).
    - Strict timeout enforcement.
    - Memory and CPU monitoring via psutil.
    - Structured output extraction.
    """

    def __init__(
        self,
        python_executable: Optional[str] = None,
        timeout_seconds: int = 30,
        max_memory_mb: int = 512,
    ):
        self.python_executable = python_executable or sys.executable
        self.timeout_seconds = timeout_seconds
        self.max_memory_mb = max_memory_mb

    def execute(self, code: str, dataset_path: str) -> ExecutionResult:
        """Audit and execute generated Python code with the specified dataset."""
        # 1. Static AST Security Audit
        is_safe, violations = CodeSecurityAuditor.audit_code(code)
        if not is_safe:
            return ExecutionResult(
                success=False,
                error="SecurityViolationError",
                stderr="Security Policy Violation:\n" + "\n".join(f"- {v}" for v in violations),
                return_code=-1,
                execution_time_seconds=0.0
            )

        # 2. Setup isolated temporary directory
        temp_dir = tempfile.mkdtemp(prefix="ada_sandbox_")
        script_path = os.path.join(temp_dir, "run_analysis.py")
        output_json_path = os.path.join(temp_dir, "output.json")

        # 3. Indent user code and assemble execution script
        indented_code = "\n".join(f"    {line}" if line.strip() else "" for line in code.split("\n"))
        full_script = HARNESS_TEMPLATE.format(
            dataset_path_repr=repr(os.path.abspath(dataset_path)),
            indented_user_code=indented_code,
            output_json_repr=repr(output_json_path)
        )

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_script)

        # 4. Construct sanitized environment (no API keys, no host tokens)
        clean_sys_path = [p for p in sys.path if p]
        sanitized_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "PATH": os.environ.get("PATH", ""),
            "APPDATA": os.environ.get("APPDATA", ""),
            "USERPROFILE": os.environ.get("USERPROFILE", ""),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "PYTHONPATH": os.pathsep.join(clean_sys_path),
            "PYTHONIOENCODING": "utf-8",
            "TEMP": temp_dir,
            "TMP": temp_dir,
        }

        # 5. Execute in isolated subprocess
        start_time = time.time()
        stdout_text = ""
        stderr_text = ""
        return_code = 0
        peak_memory_mb = 0.0

        try:
            process = subprocess.Popen(
                [self.python_executable, script_path],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=sanitized_env
            )

            # Monitor memory and wait for completion
            ps_proc = None
            try:
                ps_proc = psutil.Process(process.pid)
            except Exception:
                pass

            poll_interval = 0.1
            elapsed = 0.0
            while process.poll() is None:
                if ps_proc:
                    try:
                        mem_info = ps_proc.memory_info()
                        mem_mb = mem_info.rss / (1024 * 1024)
                        if mem_mb > peak_memory_mb:
                            peak_memory_mb = mem_mb
                        if mem_mb > self.max_memory_mb:
                            process.kill()
                            return ExecutionResult(
                                success=False,
                                error="MemoryLimitExceeded",
                                stderr=f"Process exceeded memory limit of {self.max_memory_mb} MB (used {mem_mb:.1f} MB)",
                                return_code=-9,
                                execution_time_seconds=elapsed,
                                memory_used_mb=peak_memory_mb
                            )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                time.sleep(poll_interval)
                elapsed = time.time() - start_time
                if elapsed > self.timeout_seconds:
                    process.kill()
                    return ExecutionResult(
                        success=False,
                        error="TimeoutExpired",
                        stderr=f"Execution timed out after {self.timeout_seconds} seconds.",
                        return_code=-15,
                        execution_time_seconds=elapsed,
                        memory_used_mb=peak_memory_mb
                    )

            stdout_text, stderr_text = process.communicate()
            return_code = process.returncode

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=type(e).__name__,
                stderr=f"Execution system exception: {str(e)}",
                return_code=-1,
                execution_time_seconds=time.time() - start_time
            )

        duration = round(time.time() - start_time, 3)

        # 6. Parse structured outputs if successful
        output_tables: Dict[str, List[Dict[str, Any]]] = {}
        metrics: Dict[str, Any] = {}
        figures_json: List[Dict[str, Any]] = []

        if return_code == 0 and os.path.exists(output_json_path):
            try:
                with open(output_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    output_tables = data.get("tables", {})
                    metrics = data.get("metrics", {})
                    figures_json = data.get("figures", [])
            except Exception as e:
                stderr_text += f"\nFailed to parse output.json: {str(e)}"

        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

        success = (return_code == 0)
        error_name = None
        if not success:
            # Extract main error line from stderr
            lines = [l for l in stderr_text.strip().split("\n") if l.strip()]
            error_name = lines[-1] if lines else "NonZeroExitCode"

        return ExecutionResult(
            success=success,
            stdout=stdout_text,
            stderr=stderr_text,
            return_code=return_code,
            execution_time_seconds=duration,
            memory_used_mb=round(peak_memory_mb, 2),
            output_tables=output_tables,
            metrics=metrics,
            figures_json=figures_json,
            error=error_name,
            traceback=stderr_text if not success else None
        )
