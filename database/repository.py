"""Repository pattern for database storage and retrieval operations."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings
from database.models import Base, DatasetModel, AnalysisSessionModel, ChatMessageModel, ExecutionTraceModel
from schemas.dataset import DatasetProfile


class Repository:
    """Manages transactional database operations for the application."""

    def __init__(self, db_url: Optional[str] = None):
        settings = get_settings()
        self.db_url = db_url or settings.database_url
        
        # Ensure parent directory exists for SQLite
        if self.db_url.startswith("sqlite:///"):
            sqlite_path = Path(self.db_url.replace("sqlite:///", ""))
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(self.db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    # Datasets
    def save_dataset(self, dataset_id: str, filename: str, file_path: str, profile: DatasetProfile) -> DatasetModel:
        with self.get_session() as session:
            record = session.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()
            if not record:
                record = DatasetModel(
                    id=dataset_id,
                    filename=filename,
                    file_path=file_path,
                    row_count=profile.row_count,
                    column_count=profile.column_count,
                    health_score=profile.health_score,
                    profile_json=profile.model_dump_json()
                )
                session.add(record)
            else:
                record.filename = filename
                record.file_path = file_path
                record.row_count = profile.row_count
                record.column_count = profile.column_count
                record.health_score = profile.health_score
                record.profile_json = profile.model_dump_json()
            session.commit()
            return record

    def get_dataset(self, dataset_id: str) -> Optional[DatasetModel]:
        with self.get_session() as session:
            return session.query(DatasetModel).filter(DatasetModel.id == dataset_id).first()

    def list_datasets(self) -> List[DatasetModel]:
        with self.get_session() as session:
            return session.query(DatasetModel).order_by(DatasetModel.created_at.desc()).all()

    # Analysis Sessions
    def create_analysis_session(self, session_id: str, dataset_id: str, title: str = "New Analysis") -> AnalysisSessionModel:
        with self.get_session() as session:
            s = AnalysisSessionModel(id=session_id, dataset_id=dataset_id, title=title)
            session.add(s)
            session.commit()
            return s

    def get_analysis_session(self, session_id: str) -> Optional[AnalysisSessionModel]:
        with self.get_session() as session:
            return session.query(AnalysisSessionModel).filter(AnalysisSessionModel.id == session_id).first()

    # Chat Messages
    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        code_generated: Optional[str] = None, 
        execution_success: Optional[bool] = None
    ) -> ChatMessageModel:
        with self.get_session() as session:
            msg = ChatMessageModel(
                session_id=session_id,
                role=role,
                content=content,
                code_generated=code_generated,
                execution_success=execution_success
            )
            session.add(msg)
            session.commit()
            return msg

    def get_session_messages(self, session_id: str) -> List[ChatMessageModel]:
        with self.get_session() as session:
            return session.query(ChatMessageModel).filter(
                ChatMessageModel.session_id == session_id
            ).order_by(ChatMessageModel.created_at.asc()).all()

    # Execution Traces
    def record_trace(
        self,
        session_id: str,
        attempt_number: int,
        code_executed: str,
        success: bool,
        return_code: int = 0,
        execution_time_seconds: float = 0.0,
        error_message: Optional[str] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None
    ) -> ExecutionTraceModel:
        with self.get_session() as session:
            trace = ExecutionTraceModel(
                session_id=session_id,
                attempt_number=attempt_number,
                code_executed=code_executed,
                success=success,
                return_code=return_code,
                execution_time_seconds=execution_time_seconds,
                error_message=error_message,
                stdout=stdout,
                stderr=stderr
            )
            session.add(trace)
            session.commit()
            return trace

    def get_session_traces(self, session_id: str) -> List[ExecutionTraceModel]:
        with self.get_session() as session:
            return session.query(ExecutionTraceModel).filter(
                ExecutionTraceModel.session_id == session_id
            ).order_by(ExecutionTraceModel.created_at.asc()).all()
