"""Typed ORM mappings aligned with the Alembic PostgreSQL v6 baseline."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .session import Base


class ContextRecord(Base):
    """Target mapping for contexts; schema truth remains Alembic."""

    __tablename__ = "contexts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    type: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(Text)
    problem: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    lifecycle_state: Mapped[str] = mapped_column(Text, default="Active", server_default=text("'Active'"))


class WorkflowRecord(Base):
    """Target mapping for workflows used by application ports."""

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    context_id: Mapped[str] = mapped_column(String(128), ForeignKey("contexts.id"))
    work_package_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    completion_row_version: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[str | None] = mapped_column(Text)
    area_id: Mapped[str | None] = mapped_column(String(128))
    template_id: Mapped[str | None] = mapped_column(String(128))
    skill_id: Mapped[str | None] = mapped_column(String(128))
    selection_status: Mapped[str] = mapped_column(Text, default="Active", server_default=text("'Active'"))
    selection_reason: Mapped[str | None] = mapped_column(Text)
    author_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    mode: Mapped[str] = mapped_column(String(64), default="human", server_default=text("'human'"))
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))


class WeekItemRecord(Base):
    """Minimal target mapping needed to validate card ownership."""

    __tablename__ = "week_items"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    week_id: Mapped[str] = mapped_column(String(128), ForeignKey("weeks.id"))
    wp_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(Text)
    deliverable: Mapped[str] = mapped_column(Text)
    relation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64))
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AchievementCardRecord(Base):
    """Target mapping for achievement cards."""

    __tablename__ = "achievement_cards"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    context_id: Mapped[str] = mapped_column(String(128), ForeignKey("contexts.id"))
    workflow_id: Mapped[str] = mapped_column(String(128), ForeignKey("workflows.id"))
    work_package_id: Mapped[str] = mapped_column(String(128))
    event_date: Mapped[str] = mapped_column(Text)
    event_name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    status: Mapped[str] = mapped_column(String(64), default="Active", server_default=text("'Active'"))
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    week_item_id: Mapped[str | None] = mapped_column(String(128))
    is_important: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class AchievementCardEventRecord(Base):
    """Append-only target mapping for achievement card events."""

    __tablename__ = "achievement_card_events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    card_id: Mapped[str] = mapped_column(String(128), ForeignKey("achievement_cards.id", ondelete="CASCADE"))
    actor: Mapped[str] = mapped_column(Text)
    command: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    context_id: Mapped[str | None] = mapped_column(String(128))
    workflow_id: Mapped[str | None] = mapped_column(String(128))
    work_package_id: Mapped[str | None] = mapped_column(String(128))
    week_item_id: Mapped[str | None] = mapped_column(String(128))
    attachment_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str | None] = mapped_column(Text)


class AchievementAttachmentRecord(Base):
    """Target mapping used to preserve workflow card response attachment arrays."""

    __tablename__ = "achievement_attachments"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    card_id: Mapped[str] = mapped_column(String(128), ForeignKey("achievement_cards.id", ondelete="CASCADE"))
    original_name: Mapped[str] = mapped_column(Text)
    storage_name: Mapped[str] = mapped_column(Text)
    relative_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(Text)
    preview_state: Mapped[str] = mapped_column(Text, default="available", server_default=text("'available'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    preview_error: Mapped[str | None] = mapped_column(Text)
    settings_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    path_schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    original_name_key: Mapped[str | None] = mapped_column(Text)
    area_name_snapshot: Mapped[str | None] = mapped_column(Text)
    work_package_name_snapshot: Mapped[str | None] = mapped_column(Text)
    event_folder_snapshot: Mapped[str | None] = mapped_column(Text)
    before_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    before_sha256: Mapped[str | None] = mapped_column(Text)
    after_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    after_sha256: Mapped[str | None] = mapped_column(Text)
    staging_path: Mapped[str | None] = mapped_column(Text)


class OperationAuditRecord(Base):
    """Target mapping for append-only operation audit events."""

    __tablename__ = "operation_audit_events"

    operation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True)
    context_id: Mapped[str | None] = mapped_column(String(128))
    actor: Mapped[str] = mapped_column(Text)
    display_label: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(Text)
    target_id: Mapped[str] = mapped_column(String(128))
    result: Mapped[str] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    schema_version: Mapped[int] = mapped_column(Integer, default=4, server_default=text("4"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_digest: Mapped[str] = mapped_column(Text)


class ArtifactRecord(Base):
    """Target mapping for generated catalog and run artifacts."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    item_id: Mapped[str | None] = mapped_column(String(128))
    wp_id: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    context_id: Mapped[str | None] = mapped_column(String(128))
    workflow_id: Mapped[str | None] = mapped_column(String(128))
    run_id: Mapped[str | None] = mapped_column(String(128))
    catalog_version: Mapped[str | None] = mapped_column(Text)
    step_no: Mapped[int | None] = mapped_column(Integer)


class WorkflowEventRecord(Base):
    """Target mapping for workflow command events used by P3A1 selection."""

    __tablename__ = "workflow_events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(128))
    command: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WorkflowCompletionEventRecord(Base):
    """Target mapping for the append-only completion event stream."""

    __tablename__ = "workflow_completion_events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(128))
    actor: Mapped[str] = mapped_column(Text)
    from_status: Mapped[str] = mapped_column(Text)
    to_status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    context_id: Mapped[str | None] = mapped_column(String(128))
    work_package_id: Mapped[str | None] = mapped_column(String(128))
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    actor_kind: Mapped[str] = mapped_column(Text, default="human_user", server_default=text("'human_user'"))
    version_before: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    version_after: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    authorization_source: Mapped[str | None] = mapped_column(Text)
    nonce_id: Mapped[str | None] = mapped_column(String(128))
    nonce_hash: Mapped[str | None] = mapped_column(Text)
    operation: Mapped[str | None] = mapped_column(Text)
    authorization_expires_at: Mapped[float | None]
    display_label: Mapped[str | None] = mapped_column(Text)


class ContextDisclosurePreferenceRecord(Base):
    """Target mapping for Context object-level disclosure preferences."""

    __tablename__ = "context_disclosure_preferences"

    local_user_key: Mapped[str] = mapped_column(Text, primary_key=True)
    context_id: Mapped[str] = mapped_column(String(128), ForeignKey("contexts.id"), primary_key=True)
    disclosure_kind: Mapped[str] = mapped_column(Text, primary_key=True)
    stable_subject_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    is_expanded: Mapped[bool] = mapped_column(Boolean)
    row_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UiSessionRecord(Base):
    """Target mapping for browser sessions required by completion nonce checks."""

    __tablename__ = "ui_sessions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    nonce_hash: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[float] = mapped_column(Float)
    revoked_at: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    token_hash: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(Text)
    display_label: Mapped[str | None] = mapped_column(Text)


class UiNonceRecord(Base):
    """Target mapping for one-time completion nonces."""

    __tablename__ = "ui_nonces"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), ForeignKey("ui_sessions.id"))
    workflow_id: Mapped[str] = mapped_column(String(128))
    expected_version: Mapped[str] = mapped_column(Text)
    operation: Mapped[str] = mapped_column(String(64))
    nonce_hash: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[float] = mapped_column(Float)
    used_at: Mapped[float | None]
    consume_request_id: Mapped[str | None] = mapped_column(String(128))
    context_id: Mapped[str | None] = mapped_column(String(128))
    work_package_id: Mapped[str | None] = mapped_column(String(128))
    issued_at: Mapped[float | None]


class UploadSettingRecord(Base):
    """Singleton target mapping for attachment upload limits."""

    __tablename__ = "upload_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    max_file_bytes: Mapped[int] = mapped_column(BigInteger)
    max_attachments_per_card: Mapped[int] = mapped_column(Integer)
    allowed_extensions: Mapped[list[str]] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str | None] = mapped_column(Text)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContextDeletionOperationRecord(Base):
    """Existing v6 saga ledger for prepared Context deletion operations."""

    __tablename__ = "context_deletion_operations"

    operation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    context_id: Mapped[str] = mapped_column(String(128))
    context_version: Mapped[int] = mapped_column(Integer)
    retain_files: Mapped[bool] = mapped_column(Boolean)
    state: Mapped[str] = mapped_column(String(64))
    manifest_ref: Mapped[str | None] = mapped_column(Text)
    trash_ref: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    row_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    confirmation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_nonce_hash: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(128))
    session_id: Mapped[str | None] = mapped_column(String(128))
    entity_counts_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    file_manifest_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    manifest_digest: Mapped[str | None] = mapped_column(Text)
    archive_relative_path: Mapped[str | None] = mapped_column(Text)
    trash_relative_path: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)


class DeletedContextArchiveRecord(Base):
    """Existing v6 archive metadata for retained attachment branches."""

    __tablename__ = "deleted_context_archives"

    archive_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(128))
    context_id: Mapped[str] = mapped_column(String(128))
    manifest_relative_path: Mapped[str] = mapped_column(Text)
    attachment_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_digest: Mapped[str] = mapped_column(Text)


class AchievementFileOutboxRecord(Base):
    """Target mapping for card-delete file compensation rows; workers remain P3A2."""

    __tablename__ = "achievement_file_outbox"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation: Mapped[str] = mapped_column(Text)
    relative_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


__all__ = [
    "AchievementAttachmentRecord",
    "AchievementFileOutboxRecord",
    "AchievementCardEventRecord",
    "AchievementCardRecord",
    "ArtifactRecord",
    "ContextDeletionOperationRecord",
    "ContextDisclosurePreferenceRecord",
    "DeletedContextArchiveRecord",
    "ContextRecord",
    "WeekItemRecord",
    "OperationAuditRecord",
    "UiNonceRecord",
    "UiSessionRecord",
    "UploadSettingRecord",
    "WorkflowCompletionEventRecord",
    "WorkflowEventRecord",
    "WorkflowRecord",
]
