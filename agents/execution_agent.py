"""Agent 6: Code Execution Agent."""

import logging
from typing import Optional
from sandbox import SandboxExecutorProtocol, get_sandbox_executor
from schemas.execution import ExecutionResult

logger = logging.getLogger(__name__)


class ExecutionAgent:
    """The sole authorized component responsible for dispatching code to the isolated execution sandbox."""

    def __init__(self, sandbox_executor: Optional[SandboxExecutorProtocol] = None):
        self.sandbox = sandbox_executor or get_sandbox_executor()

    def run(self, code: str, dataset_path: str) -> ExecutionResult:
        """Submit generated code for isolated execution and collect structured artifacts."""
        logger.info(f"ExecutionAgent submitting code to sandbox for dataset: {dataset_path}")
        result = self.sandbox.execute(code=code, dataset_path=dataset_path)
        
        if result.success:
            logger.info(
                f"Execution successful in {result.execution_time_seconds:.2f}s. "
                f"Tables extracted: {list(result.output_tables.keys())}, "
                f"Metrics: {len(result.metrics)}, Figures: {len(result.figures_json)}"
            )
        else:
            logger.warning(
                f"Execution failed with return code {result.return_code}: {result.error}\n"
                f"Stderr preview: {result.stderr[:200]}"
            )

        return result
