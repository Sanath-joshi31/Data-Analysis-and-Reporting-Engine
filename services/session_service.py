"""Session management service for conversational context and analytical trace logs."""

import uuid
from typing import Dict, List, Optional
from database.repository import Repository
from database.models import AnalysisSessionModel, ChatMessageModel, ExecutionTraceModel


class SessionService:
    """Coordinates chat session state, multi-turn message history, and execution logs."""

    def __init__(self, repository: Optional[Repository] = None):
        self.repo = repository or Repository()

    def create_session(self, dataset_id: str, title: str = "New Analysis") -> str:
        """Create a new conversational analytical session."""
        session_id = str(uuid.uuid4())
        self.repo.create_analysis_session(session_id=session_id, dataset_id=dataset_id, title=title)
        return session_id

    def get_messages(self, session_id: str) -> List[ChatMessageModel]:
        """Fetch all messages for the specified session in chronological order."""
        return self.repo.get_session_messages(session_id)

    def add_user_message(self, session_id: str, content: str) -> ChatMessageModel:
        """Record a user question or follow-up prompt."""
        return self.repo.add_message(session_id=session_id, role="user", content=content)

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        code_generated: Optional[str] = None,
        execution_success: Optional[bool] = None
    ) -> ChatMessageModel:
        """Record the assistant's analytical explanation and metadata."""
        return self.repo.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            code_generated=code_generated,
            execution_success=execution_success
        )

    def record_trace(
        self,
        session_id: str,
        attempt_number: int,
        code: str,
        success: bool,
        return_code: int = 0,
        execution_time: float = 0.0,
        error_msg: Optional[str] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None
    ) -> ExecutionTraceModel:
        """Record code execution attempt for observability and debugging."""
        return self.repo.record_trace(
            session_id=session_id,
            attempt_number=attempt_number,
            code_executed=code,
            success=success,
            return_code=return_code,
            execution_time_seconds=execution_time,
            error_message=error_msg,
            stdout=stdout,
            stderr=stderr
        )

    def get_traces(self, session_id: str) -> List[ExecutionTraceModel]:
        """Fetch all execution traces for a session."""
        return self.repo.get_session_traces(session_id)
