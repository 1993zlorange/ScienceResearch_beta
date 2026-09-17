"""Pydantic DTOs for the P2A native context, workflow, and card APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ContextCreateDTO(BaseModel):
    """Legacy-compatible input object; string coercion is completed at the route edge."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    type: JsonValue = "topic"
    name: JsonValue = ""
    problem: JsonValue = ""
    goal: JsonValue = ""
    owner: JsonValue = "author"


class CreatedContextDTO(BaseModel):
    """Exact fields returned by the legacy context create command."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    type: str
    name: str
    problem: str
    goal: str
    owner: str
    created_at: datetime


class ContextDTO(BaseModel):
    """Context row shape returned by the legacy list endpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    type: str
    name: str
    problem: str
    goal: str
    owner: str
    created_at: datetime
    row_version: int
    lifecycle_state: str


class ContextListDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contexts: list[ContextDTO]


class WorkflowDTO(BaseModel):
    """Complete workflow row plus the legacy achievement card projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    inputs_json: dict[str, JsonValue]
    achievement_cards: list[Annotated[dict[str, JsonValue], Field(min_length=0)]]


class ProgressDTO(BaseModel):
    """Legacy progress projection; warning variants intentionally remain JSON-typed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    total: int
    completed: int
    ratio: float | None
    expected_total: int
    snapshot_incomplete: bool
    warnings: list[dict[str, JsonValue]]
    missing_work_package_ids: list[str]
    extra_work_package_ids: list[str]
    unassigned_work_package_ids: list[str]
    areas: list[dict[str, JsonValue]]
    workflows: list[dict[str, JsonValue]]


class WorkflowListDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflows: list[WorkflowDTO]
    progress: ProgressDTO


class AchievementCardCreateDTO(BaseModel):
    """Legacy-compatible card input; optional `wp` and other extras are ignored."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    context_id: JsonValue = ""
    workflow_id: JsonValue = ""
    event_date: JsonValue = ""
    event_name: JsonValue = ""
    description: JsonValue = ""
    actor: JsonValue = "author"
    week_item_id: JsonValue | None = None
    important: JsonValue = False


class AchievementCardDTO(BaseModel):
    """Legacy card response shape including its (empty in P2A) attachment array."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    attachments: list[dict[str, JsonValue]]


class AchievementAttachmentDTO(BaseModel):
    """Safe attachment descriptor exposed by native workbench endpoints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    card_id: str
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    preview_state: str
    created_at: datetime
    row_version: int
    settings_version: int
    path_schema_version: int
    area_name_snapshot: str | None = None
    work_package_name_snapshot: str | None = None
    event_folder_snapshot: str | None = None
    preview_error: str | None = None


class AchievementAttachmentMetadataDTO(BaseModel):
    """Preview metadata without attachment file contents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attachment: AchievementAttachmentDTO
    representation: str
    preview_url: str
    download_url: str


class ContextDeletionPrepareDTO(BaseModel):
    """Prepare a session-bound, one-time Context deletion ticket."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    retain_files: JsonValue = True
    expected_version: JsonValue = 0
    session_id: JsonValue = ""


class ContextDeletionPrepareResultDTO(BaseModel):
    """Impact snapshot plus a confirmation token that is never persisted raw."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    request_id: str
    context_id: str
    context_name: str
    retain_files: bool
    expected_version: int
    confirmation: str
    expires_at: datetime
    entity_counts: dict[str, int]
    attachments: list[dict[str, JsonValue]]
    manifest_digest: str
    state: str


class ContextDeletionCommitDTO(BaseModel):
    """Consume a prepared deletion ticket exactly once."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    operation_id: JsonValue = ""
    confirmation: JsonValue = ""
    session_id: JsonValue = ""


class ContextDeletionCommitResultDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation_id: str
    state: str
    retain_files: bool
    idempotent: bool = False
    removed_attachment_count: int = 0
    manifest_ref: str | None = None
    unresolved_files: list[str] = []


class AchievementCardUpdateDTO(BaseModel):
    """Legacy-compatible edit input with route-edge string coercion."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    event_date: JsonValue = ""
    event_name: JsonValue = ""
    description: JsonValue = ""
    expected_version: JsonValue = 0
    actor: JsonValue = "author"


class AchievementCardImportanceDTO(BaseModel):
    """Importance input preserving the legacy boolean coercion boundary."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    is_important: JsonValue = False
    expected_version: JsonValue = 0
    actor: JsonValue = "author"
    idempotency_key: JsonValue | None = None


class AchievementCardDeleteDTO(BaseModel):
    """Delete input requiring the legacy explicit confirmation token."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    actor: JsonValue = "author"
    confirmation_token: JsonValue | None = None
    expected_version: JsonValue = 0


class CardImportanceResultDTO(BaseModel):
    """Exact legacy importance response fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    card_id: str
    is_important: bool
    changed: bool
    row_version: int
    updated_at: datetime
    operation_id: str


class CardDeleteResultDTO(BaseModel):
    """Exact legacy delete response fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    deleted: bool
    context_id: str
    workflow_id: str


class WorkflowSelectionDTO(BaseModel):
    """Selection input keyed by work package inside one context."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    wp_id: JsonValue = ""
    selection_status: JsonValue = ""
    reason: JsonValue | None = None
    author_confirmed: JsonValue = False
    expected_version: JsonValue = 0


class DisclosurePreferenceDTO(BaseModel):
    """One Context disclosure object and its optimistic-lock version."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    disclosure_kind: str
    stable_subject_id: str
    is_expanded: bool
    row_version: int
    created_at: datetime
    updated_at: datetime


class DisclosurePreferenceListDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    local_user_key: str
    preferences: list[DisclosurePreferenceDTO]


class DisclosurePreferenceUpsertDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    disclosure_kind: JsonValue = ""
    stable_subject_id: JsonValue = ""
    requested_is_expanded: JsonValue = False
    local_user_key: JsonValue = "_local_author_v1"
    expected_version: JsonValue = 0


class UiSessionIssueDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    actor: JsonValue = "author"
    display_label: JsonValue | None = None


class UiSessionIssueResultDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    expires_at: float
    actor: str
    display_label: str


class CompletionAuthorizationDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    expected_version: JsonValue = 0
    operation: JsonValue = ""
    session_id: JsonValue = ""


class CompletionAuthorizationResultDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nonce_id: str
    nonce_hash: str
    session_id: str
    workflow_id: str
    expected_version: int
    operation: str
    expires_at: float
    context_id: str
    work_package_id: str


class WorkflowCompletionDTO(BaseModel):
    """Completion input with mandatory UI session and one-time nonce fields."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    completed: JsonValue = False
    expected_version: JsonValue = 0
    session_id: JsonValue = ""
    nonce_id: JsonValue = ""
    nonce_hash: JsonValue = ""
    idempotency_key: JsonValue | None = None


class WorkflowRecordDTO(BaseModel):
    """Workflow row without the heavier card projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    inputs_json: dict[str, JsonValue]


class WorkflowCompletionResultDTO(BaseModel):
    """Legacy-compatible workflow projection with idempotency visibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    inputs_json: dict[str, JsonValue]
    idempotent: bool
    has_achievement_cards: bool


__all__ = [
    "AchievementCardCreateDTO",
    "AchievementCardDeleteDTO",
    "AchievementCardImportanceDTO",
    "AchievementCardUpdateDTO",
    "CardDeleteResultDTO",
    "CardImportanceResultDTO",
    "AchievementCardDTO",
    "ContextCreateDTO",
    "DisclosurePreferenceDTO",
    "DisclosurePreferenceListDTO",
    "DisclosurePreferenceUpsertDTO",
    "ContextDTO",
    "ContextListDTO",
    "CompletionAuthorizationDTO",
    "CompletionAuthorizationResultDTO",
    "CreatedContextDTO",
    "UiSessionIssueDTO",
    "UiSessionIssueResultDTO",
    "ProgressDTO",
    "WorkflowCompletionDTO",
    "WorkflowCompletionResultDTO",
    "WorkflowDTO",
    "WorkflowRecordDTO",
    "WorkflowSelectionDTO",
    "WorkflowListDTO",
]
