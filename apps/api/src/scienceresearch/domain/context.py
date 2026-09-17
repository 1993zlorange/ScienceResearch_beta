"""Pure domain values and invariants for contexts, workflows, and cards."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .errors import AppError

_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True, slots=True)
class ContextCreateCommand:
    type: str
    name: str
    problem: str
    goal: str
    owner: str


@dataclass(frozen=True, slots=True)
class ResearchContext:
    id: str
    type: str
    name: str
    problem: str
    goal: str
    owner: str
    created_at: datetime
    row_version: int
    lifecycle_state: str


@dataclass(frozen=True, slots=True)
class ContextWorkflow:
    id: str
    context_id: str
    work_package_id: str
    status: str
    created_at: datetime
    is_completed: bool
    completion_row_version: int
    completed_at: datetime | None
    completed_by: str | None
    area_id: str | None
    template_id: str | None
    skill_id: str | None
    selection_status: str
    selection_reason: str | None
    author_confirmed: bool
    mode: str
    row_version: int
    archived: bool
    inputs_json: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AchievementCard:
    id: str
    context_id: str
    workflow_id: str
    work_package_id: str
    week_item_id: str | None
    event_date: str
    event_name: str
    description: str
    status: str
    is_important: bool
    row_version: int
    created_at: datetime
    updated_at: datetime
    attachments: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AchievementCardEvent:
    id: str
    card_id: str
    actor: str
    command: str
    payload: dict[str, Any]
    created_at: datetime
    context_id: str
    workflow_id: str
    work_package_id: str
    event_type: str


@dataclass(frozen=True, slots=True)
class OperationAuditEvent:
    operation_id: str
    request_id: str
    idempotency_key: str
    context_id: str | None
    actor: str
    display_label: str
    action: str
    target_type: str
    target_id: str
    result: str
    error_code: str | None
    summary: str
    summary_json: dict[str, Any]
    schema_version: int
    occurred_at: datetime
    content_digest: str


@dataclass(frozen=True, slots=True)
class AchievementCardCreateCommand:
    context_id: str
    workflow_id: str
    event_date: str
    event_name: str
    description: str
    actor: str
    week_item_id: str | None
    is_important: bool


@dataclass(frozen=True, slots=True)
class AchievementCardUpdateCommand:
    card_id: str
    event_date: str
    event_name: str
    description: str
    expected_version: int
    actor: str


@dataclass(frozen=True, slots=True)
class AchievementCardImportanceCommand:
    context_id: str
    workflow_id: str
    card_id: str
    is_important: bool
    expected_version: int
    actor: str
    idempotency_key: str | None
    request_id: str | None
    display_label: str


@dataclass(frozen=True, slots=True)
class AchievementCardDeleteCommand:
    card_id: str
    actor: str
    confirmation_token: str | None
    expected_version: int


@dataclass(frozen=True, slots=True)
class WorkflowSelectionCommand:
    context_id: str
    work_package_id: str
    selection_status: str
    reason: str | None
    author_confirmed: bool
    expected_version: int


@dataclass(frozen=True, slots=True)
class WorkflowCompletionCommand:
    workflow_id: str
    completed: bool
    expected_version: int
    session_id: str
    nonce_id: str
    nonce_hash: str
    actor: str
    idempotency_key: str | None


@dataclass(frozen=True, slots=True)
class CardImportanceResult:
    card_id: str
    is_important: bool
    changed: bool
    row_version: int
    updated_at: datetime
    operation_id: str


@dataclass(frozen=True, slots=True)
class CardDeleteResult:
    id: str
    deleted: bool
    context_id: str
    workflow_id: str


@dataclass(frozen=True, slots=True)
class ContextDisclosurePreference:
    context_id: str
    disclosure_kind: str
    stable_subject_id: str
    is_expanded: bool
    row_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DisclosurePreferenceUpsertCommand:
    context_id: str
    local_user_key: str
    disclosure_kind: str
    stable_subject_id: str
    requested_is_expanded: bool
    expected_version: int


@dataclass(frozen=True, slots=True)
class UiSessionIssueCommand:
    actor: str
    display_label: str | None


@dataclass(frozen=True, slots=True)
class UiSessionIssueResult:
    session_id: str
    expires_at: float
    actor: str
    display_label: str


@dataclass(frozen=True, slots=True)
class CompletionAuthorizationCommand:
    workflow_id: str
    expected_version: int
    operation: str
    session_id: str


@dataclass(frozen=True, slots=True)
class CompletionAuthorizationResult:
    nonce_id: str
    nonce_hash: str
    session_id: str
    workflow_id: str
    expected_version: int
    operation: str
    expires_at: float
    context_id: str
    work_package_id: str


@dataclass(frozen=True, slots=True)
class ContextDeletionPrepareCommand:
    context_id: str
    session_id: str
    retain_files: bool
    expected_version: int


@dataclass(frozen=True, slots=True)
class ContextDeletionPrepareResult:
    operation_id: str
    request_id: str
    context_id: str
    context_name: str
    retain_files: bool
    expected_version: int
    confirmation: str
    expires_at: datetime
    entity_counts: dict[str, int]
    attachments: tuple[dict[str, Any], ...]
    manifest_digest: str
    state: str


@dataclass(frozen=True, slots=True)
class ContextDeletionCommitCommand:
    context_id: str
    operation_id: str
    confirmation: str
    session_id: str


@dataclass(frozen=True, slots=True)
class ContextDeletionCommitResult:
    operation_id: str
    state: str
    retain_files: bool
    idempotent: bool = False
    removed_attachment_count: int = 0
    manifest_ref: str | None = None
    unresolved_files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextDeletionRetryCommand:
    operation_id: str


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    id: str
    workflow_id: str
    command: str
    payload: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowCompletionEvent:
    id: str
    workflow_id: str
    actor: str
    from_status: str
    to_status: str
    created_at: datetime
    context_id: str
    work_package_id: str
    row_version: int
    actor_kind: str
    version_before: int
    version_after: int
    idempotency_key: str | None
    authorization_source: str
    nonce_id: str
    nonce_hash: str
    operation: str
    authorization_expires_at: float
    display_label: str


@dataclass(frozen=True, slots=True)
class WorkflowCompletionResult:
    workflow: ContextWorkflow
    idempotent: bool
    has_achievement_cards: bool


@dataclass(frozen=True, slots=True)
class WorkflowSnapshot:
    context_id: str
    workflows: tuple[ContextWorkflow, ...]
    cards_by_workflow: dict[str, tuple[AchievementCard, ...]]
    card_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class UploadSettings:
    max_file_bytes: int
    max_attachments_per_card: int
    allowed_extensions: tuple[str, ...]
    version: int


@dataclass(frozen=True, slots=True)
class AchievementAttachment:
    id: str
    card_id: str
    original_name: str
    storage_name: str
    relative_path: str
    mime_type: str
    size_bytes: int
    sha256: str
    preview_state: str
    created_at: datetime
    preview_error: str | None = None
    settings_version: int = 1
    row_version: int = 1
    path_schema_version: int = 1
    original_name_key: str | None = None
    area_name_snapshot: str | None = None
    work_package_name_snapshot: str | None = None
    event_folder_snapshot: str | None = None
    before_size_bytes: int | None = None
    before_sha256: str | None = None
    after_size_bytes: int | None = None
    after_sha256: str | None = None
    staging_path: str | None = None


@dataclass(frozen=True, slots=True)
class AttachmentUploadCommand:
    card_id: str
    original_name: str
    mime_type: str
    content: bytes
    area_name_snapshot: str | None = None
    actor: str = "author"
    request_id: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class AttachmentContent:
    data: bytes
    media_type: str
    filename: str
    disposition: str = "attachment"


@dataclass(frozen=True, slots=True)
class AttachmentPreviewResult:
    attachment: AchievementAttachment
    content: AttachmentContent
    representation: str


@dataclass(frozen=True, slots=True)
class CatalogBinding:
    area_id: str
    area_name: str
    work_package_id: str
    template_id: str
    skill_id: str


ATTACHMENT_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".doc": "application/msword",
    ".ppt": "application/vnd.ms-powerpoint",
    ".zip": "application/zip",
    ".7z": "application/x-7z-compressed",
    ".rar": "application/vnd.rar",
}

ATTACHMENT_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".docx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".ppt": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".7z": (b"7z\xbc\xaf\x27\x1c",),
    ".rar": (b"Rar!\x1a\x07",),
}


def validate_attachment_upload(command: AttachmentUploadCommand, settings: UploadSettings) -> str:
    """Validate client metadata and return the normalized extension."""
    name = command.original_name.strip()
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or any(ord(char) < 32 for char in name)
        or name.endswith((".", " "))
        or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL"}
    ):
        raise AppError("INVALID_FILENAME", "filename is invalid", 422)
    extension = Path(name).suffix.lower()
    if extension not in settings.allowed_extensions:
        raise AppError("EXTENSION_NOT_ALLOWED", "file extension is not allowed", 422)
    if command.mime_type != ATTACHMENT_MIME_TYPES[extension]:
        raise AppError("MIME_TYPE_NOT_ALLOWED", "file content type does not match the extension", 422)
    if len(command.content) < 1 or len(command.content) > settings.max_file_bytes:
        raise AppError("FILE_TOO_LARGE", "file exceeds configured limit", 422)
    signatures = ATTACHMENT_SIGNATURES.get(extension)
    if signatures and not command.content.startswith(signatures):
        raise AppError("SIGNATURE_MISMATCH", "file signature does not match extension", 422)
    return extension


def validate_context_create(command: ContextCreateCommand) -> None:
    """Preserve the legacy create-context validation boundary."""
    if not command.problem.strip():
        raise AppError("INVALID_INPUT", "problem is required")


def validate_achievement_card(command: AchievementCardCreateCommand) -> None:
    """Preserve the legacy card date and event-name contract."""
    if not _DATE_PATTERN.fullmatch(command.event_date) or not command.event_name.strip():
        raise AppError("INVALID_INPUT", "date and event name are required")


def validate_achievement_card_update(command: AchievementCardUpdateCommand) -> None:
    """Keep the legacy edit validation independent of HTTP models."""
    if command.expected_version < 1:
        raise AppError("INVALID_INPUT", "expected_version must be a positive integer")
    if not _DATE_PATTERN.fullmatch(command.event_date) or not command.event_name.strip():
        raise AppError("INVALID_INPUT", "date and event name are required")


def validate_achievement_card_importance(command: AchievementCardImportanceCommand) -> None:
    if command.expected_version < 1:
        raise AppError("INVALID_INPUT", "expected_version must be a positive integer")


def validate_achievement_card_delete(command: AchievementCardDeleteCommand) -> None:
    if command.confirmation_token != "DELETE":
        raise AppError("DELETE_CONFIRMATION_REQUIRED", "confirmation token DELETE is required", 409)
    if command.expected_version < 1:
        raise AppError("INVALID_INPUT", "expected_version must be a positive integer")


def validate_context_deletion_prepare(command: ContextDeletionPrepareCommand) -> None:
    """Keep destructive saga entry validation explicit and stable."""
    if not command.context_id.strip():
        raise AppError("INVALID_INPUT", "context_id is required", 422)
    if not command.session_id.strip():
        raise AppError("UI_SESSION_REQUIRED", "deletion preparation requires a valid session", 403)
    if command.expected_version < 1:
        raise AppError("INVALID_INPUT", "expected_version must be a positive integer", 422)


def validate_context_deletion_commit(command: ContextDeletionCommitCommand) -> None:
    """Require ticket identity before any repository access."""
    if not command.context_id.strip():
        raise AppError("INVALID_INPUT", "context_id is required", 422)
    if not command.operation_id.strip():
        raise AppError("INVALID_INPUT", "operation_id is required", 422)
    if not command.session_id.strip() or not command.confirmation.strip():
        raise AppError("DELETE_CONFIRMATION_REQUIRED", "one-time deletion confirmation is required", 409)


def validate_workflow_selection(command: WorkflowSelectionCommand) -> None:
    allowed = {"Active", "Deferred", "NotApplicable"}
    if command.selection_status not in allowed:
        raise AppError("INVALID_INPUT", "selection status must be Active, Deferred, or NotApplicable")
    if command.selection_status == "NotApplicable" and (
        command.reason is None or not command.reason.strip() or not command.author_confirmed
    ):
        raise AppError("AUTHOR_CONFIRMATION_REQUIRED", "NotApplicable requires a reason and author confirmation")
    if command.expected_version < 1:
        raise AppError("INVALID_INPUT", "expected_version must be a positive integer")


def validate_workflow_completion(command: WorkflowCompletionCommand) -> None:
    if command.expected_version < 1:
        raise AppError("INVALID_INPUT", "expected_version must be a positive integer")
    if not command.session_id:
        raise AppError("UI_SESSION_REQUIRED", "interactive completion requires a valid session-bound UI session", 403)
    if not command.nonce_id or not command.nonce_hash:
        raise AppError(
            "COMPLETION_NONCE_REQUIRED", "interactive completion requires a session-bound one-time nonce", 403
        )


def context_progress(
    snapshot: WorkflowSnapshot,
    bindings: tuple[CatalogBinding, ...],
) -> dict[str, Any]:
    """Derive progress from actual workflow rows, including snapshot warnings."""

    card_counts = {workflow_id: sum(1 for _ in cards) for workflow_id, cards in snapshot.cards_by_workflow.items()}
    areas: dict[str, dict[str, Any]] = {}
    for workflow in snapshot.workflows:
        area_id = workflow.area_id or "UNASSIGNED"
        item = areas.setdefault(
            area_id,
            {"area_id": area_id, "total": 0, "completed": 0, "card_count": 0, "ratio": None},
        )
        item["total"] += 1
        item["completed"] += int(workflow.is_completed)
        item["card_count"] += card_counts.get(workflow.id, 0)
    for item in areas.values():
        item["ratio"] = round(item["completed"] / item["total"] * 100, 2) if item["total"] else None

    area_names = {binding.area_id: binding.area_name for binding in bindings}
    for area_id, item in areas.items():
        item["area_name"] = "未分配方面" if area_id == "UNASSIGNED" else area_names.get(area_id, area_id)

    expected_ids = [binding.work_package_id for binding in bindings]
    actual_ids = [workflow.work_package_id for workflow in snapshot.workflows]
    missing_ids = [work_package_id for work_package_id in expected_ids if work_package_id not in actual_ids]
    extra_ids = [work_package_id for work_package_id in actual_ids if work_package_id not in expected_ids]
    unassigned_ids = [workflow.work_package_id for workflow in snapshot.workflows if not workflow.area_id]
    warnings: list[dict[str, Any]] = []
    if missing_ids or extra_ids:
        warnings.append(
            {
                "code": "SNAPSHOT_CATALOG_MISMATCH",
                "actual_total": len(actual_ids),
                "expected_total": len(expected_ids),
                "missing_work_package_ids": missing_ids,
                "extra_work_package_ids": extra_ids,
            }
        )
    if unassigned_ids:
        warnings.append(
            {"code": "UNASSIGNED_WORKFLOWS", "count": len(unassigned_ids), "work_package_ids": unassigned_ids}
        )

    total = len(snapshot.workflows)
    completed = sum(workflow.is_completed for workflow in snapshot.workflows)
    return {
        "context_id": snapshot.context_id,
        "total": total,
        "completed": completed,
        "ratio": round(completed / total * 100, 2) if total else None,
        "expected_total": len(expected_ids),
        "snapshot_incomplete": bool(missing_ids or extra_ids),
        "warnings": warnings,
        "missing_work_package_ids": missing_ids,
        "extra_work_package_ids": extra_ids,
        "unassigned_work_package_ids": unassigned_ids,
        "areas": list(areas.values()),
        "workflows": [
            {
                "work_package_id": workflow.work_package_id,
                "completed": workflow.is_completed,
                "card_count": card_counts.get(workflow.id, 0),
                "ratio": 100 if workflow.is_completed else 0,
            }
            for workflow in snapshot.workflows
        ],
    }
