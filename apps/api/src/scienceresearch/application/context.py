"""Application use cases for the P2A native context and card APIs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from ..domain.catalog import CatalogSnapshot
from ..domain.context import (
    AchievementAttachment,
    AchievementCard,
    AchievementCardCreateCommand,
    AchievementCardDeleteCommand,
    AchievementCardEvent,
    AchievementCardImportanceCommand,
    AchievementCardUpdateCommand,
    AttachmentContent,
    AttachmentPreviewResult,
    AttachmentUploadCommand,
    CardDeleteResult,
    CardImportanceResult,
    CatalogBinding,
    CompletionAuthorizationCommand,
    CompletionAuthorizationResult,
    ContextCreateCommand,
    ContextDeletionCommitCommand,
    ContextDeletionCommitResult,
    ContextDeletionPrepareCommand,
    ContextDeletionPrepareResult,
    ContextDeletionRetryCommand,
    ContextDisclosurePreference,
    ContextWorkflow,
    DisclosurePreferenceUpsertCommand,
    OperationAuditEvent,
    ResearchContext,
    UiSessionIssueCommand,
    UiSessionIssueResult,
    UploadSettings,
    WorkflowCompletionCommand,
    WorkflowCompletionEvent,
    WorkflowCompletionResult,
    WorkflowEvent,
    WorkflowSelectionCommand,
    WorkflowSnapshot,
    context_progress,
    validate_achievement_card,
    validate_achievement_card_delete,
    validate_achievement_card_importance,
    validate_achievement_card_update,
    validate_attachment_upload,
    validate_context_create,
    validate_context_deletion_commit,
    validate_context_deletion_prepare,
    validate_workflow_completion,
    validate_workflow_selection,
)
from ..domain.errors import AppError


class ContextRepository(Protocol):
    """Persistence port for the P2A aggregate slice."""

    def list_contexts(self) -> tuple[ResearchContext, ...]: ...

    def context(self, context_id: str) -> ResearchContext: ...

    def create_context(
        self,
        context: ResearchContext,
        workflows: tuple[ContextWorkflow, ...],
        audit: OperationAuditEvent,
    ) -> None: ...

    def workflows_for_context(self, context_id: str) -> WorkflowSnapshot: ...

    def workflow(self, workflow_id: str) -> ContextWorkflow: ...

    def validate_week_item(self, week_item_id: str, work_package_id: str) -> None: ...

    def create_achievement_card(
        self,
        card: AchievementCard,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> AchievementCard: ...

    def achievement_card(self, card_id: str) -> AchievementCard: ...

    def update_achievement_card(
        self,
        card: AchievementCard,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> AchievementCard: ...

    def set_achievement_card_importance(
        self,
        card: AchievementCard,
        event: AchievementCardEvent | None,
        audit: OperationAuditEvent,
    ) -> CardImportanceResult: ...

    def record_audit(self, audit: OperationAuditEvent) -> None: ...

    def delete_achievement_card(
        self,
        card: AchievementCard,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> CardDeleteResult: ...

    def upload_settings(self) -> UploadSettings: ...

    def create_achievement_attachment(
        self,
        command: AttachmentUploadCommand,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> AchievementAttachment: ...

    def achievement_attachment(self, attachment_id: str) -> AchievementAttachment: ...

    def read_attachment(self, attachment: AchievementAttachment) -> AttachmentContent: ...

    def render_attachment_preview(self, attachment: AchievementAttachment) -> AttachmentContent: ...

    def read_attachment_image(self, attachment: AchievementAttachment, index: int) -> AttachmentContent: ...

    def workflow_for_work_package(self, context_id: str, work_package_id: str) -> ContextWorkflow: ...

    def set_workflow_selection(
        self,
        workflow: ContextWorkflow,
        event: WorkflowEvent | None,
        audit: OperationAuditEvent,
    ) -> ContextWorkflow: ...

    def disclosure_preferences(
        self,
        context_id: str,
        local_user_key: str,
    ) -> tuple[ContextDisclosurePreference, ...]: ...

    def upsert_disclosure_preference(
        self,
        command: DisclosurePreferenceUpsertCommand,
    ) -> ContextDisclosurePreference: ...

    def create_ui_session(self, command: UiSessionIssueCommand) -> UiSessionIssueResult: ...

    def issue_completion_authorization(
        self,
        command: CompletionAuthorizationCommand,
    ) -> CompletionAuthorizationResult: ...

    def session_actor(self, session_id: str) -> tuple[str, str]: ...

    def set_workflow_completion(
        self,
        command: WorkflowCompletionCommand,
        workflow: ContextWorkflow,
        event: WorkflowCompletionEvent,
        audit: OperationAuditEvent,
    ) -> WorkflowCompletionResult: ...

    def prepare_context_deletion(
        self,
        command: ContextDeletionPrepareCommand,
    ) -> ContextDeletionPrepareResult: ...

    def commit_context_deletion(
        self,
        command: ContextDeletionCommitCommand,
    ) -> ContextDeletionCommitResult: ...

    def retry_context_deletion_cleanup(
        self,
        command: ContextDeletionRetryCommand,
    ) -> ContextDeletionCommitResult: ...


DISCLOSURE_KINDS = frozenset({"area", "progress", "work_package", "card", "directory"})


@dataclass(frozen=True, slots=True)
class WorkflowListResult:
    workflows: tuple[tuple[ContextWorkflow, tuple[AchievementCard, ...]], ...]
    progress: dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _legacy_identifier(prefix: str, value: str, timestamp: datetime) -> str:
    digest = hashlib.sha256(f"{prefix}:{value}:{timestamp.isoformat()}".encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


class ContextUseCase:
    """Orchestrate P2A commands while keeping HTTP and SQLAlchemy outside."""

    def __init__(
        self,
        repository: ContextRepository,
        catalog: CatalogSnapshot,
        *,
        clock: Callable[[], datetime] = _utc_now,
        identifier: Callable[[str, str, datetime], str] = _legacy_identifier,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._identifier = identifier
        self._bindings = _bindings(catalog)
        if len(self._bindings) != 68:
            raise ValueError("catalog must contain exactly 68 work packages")

    def list_contexts(self) -> tuple[ResearchContext, ...]:
        return self._repository.list_contexts()

    def context(self, context_id: str) -> ResearchContext:
        return self._repository.context(context_id)

    def create_context(self, command: ContextCreateCommand) -> ResearchContext:
        validate_context_create(command)
        created_at = self._clock()
        context = ResearchContext(
            id=self._identifier("CTX", command.name, created_at),
            type=command.type,
            name=command.name,
            problem=command.problem,
            goal=command.goal,
            owner=command.owner,
            created_at=created_at,
            row_version=1,
            lifecycle_state="Active",
        )
        workflows = tuple(
            ContextWorkflow(
                id=self._identifier("WF", f"{context.id}:{binding.work_package_id}", created_at),
                context_id=context.id,
                work_package_id=binding.work_package_id,
                status="Draft",
                created_at=created_at,
                is_completed=False,
                completion_row_version=0,
                completed_at=None,
                completed_by=None,
                area_id=binding.area_id,
                template_id=binding.template_id,
                skill_id=binding.skill_id,
                selection_status="Active",
                selection_reason=None,
                author_confirmed=False,
                mode="human",
                row_version=1,
                archived=False,
                inputs_json={},
            )
            for binding in self._bindings
        )
        audit = _audit(
            context_id=context.id,
            actor=context.owner,
            display_label=context.owner,
            action="context.create",
            target_type="context",
            target_id=context.id,
            summary={"type": context.type, "workflow_count": len(workflows)},
            timestamp=self._clock(),
        )
        self._repository.create_context(context, workflows, audit)
        return context

    def workflows(self, context_id: str) -> WorkflowListResult:
        snapshot = self._repository.workflows_for_context(context_id)
        progress = context_progress(snapshot, self._bindings)
        workflows = tuple(
            (workflow, snapshot.cards_by_workflow.get(workflow.id, ())) for workflow in snapshot.workflows
        )
        return WorkflowListResult(workflows=workflows, progress=progress)

    def create_achievement_card(self, command: AchievementCardCreateCommand) -> AchievementCard:
        workflow = self._repository.workflow(command.workflow_id)
        if workflow.context_id != command.context_id:
            raise AppError("STATE_CONFLICT", "workflow does not belong to context", 409)
        if command.week_item_id:
            self._repository.validate_week_item(command.week_item_id, workflow.work_package_id)
        validate_achievement_card(command)
        created_at = self._clock()
        updated_at = self._clock()
        card = AchievementCard(
            id=self._identifier(
                "CARD",
                f"{command.context_id}:{command.workflow_id}:{command.event_date}:{command.event_name}",
                created_at,
            ),
            context_id=command.context_id,
            workflow_id=command.workflow_id,
            work_package_id=workflow.work_package_id,
            week_item_id=command.week_item_id,
            event_date=command.event_date,
            event_name=command.event_name.strip(),
            description=command.description.strip(),
            status="Active",
            is_important=command.is_important,
            row_version=1,
            created_at=created_at,
            updated_at=updated_at,
            attachments=(),
        )
        event = AchievementCardEvent(
            id=self._identifier("ACE", card.id, updated_at),
            card_id=card.id,
            actor=command.actor,
            command="create",
            payload=_card_payload(card),
            created_at=updated_at,
            context_id=card.context_id,
            workflow_id=card.workflow_id,
            work_package_id=card.work_package_id,
            event_type="card_created",
        )
        audit = _audit(
            context_id=card.context_id,
            actor=command.actor,
            display_label=command.actor,
            action="card.create",
            target_type="achievement_card",
            target_id=card.id,
            summary={"workflow_id": card.workflow_id},
            timestamp=self._clock(),
        )
        return self._repository.create_achievement_card(card, event, audit)

    def update_achievement_card(self, command: AchievementCardUpdateCommand) -> AchievementCard:
        current = self._repository.achievement_card(command.card_id)
        validate_achievement_card_update(command)
        if current.row_version != command.expected_version:
            raise AppError("VERSION_CONFLICT", "card changed; reload and retry", 409)
        timestamp = self._clock()
        updated = replace(
            current,
            event_date=command.event_date,
            event_name=command.event_name.strip(),
            description=command.description.strip(),
            row_version=current.row_version + 1,
            updated_at=timestamp,
        )
        event = AchievementCardEvent(
            id=self._identifier("ACE", updated.id, timestamp),
            card_id=updated.id,
            actor=command.actor,
            command="update",
            payload={
                "event_date": command.event_date,
                "event_name": command.event_name,
                "description": command.description,
            },
            created_at=timestamp,
            context_id=updated.context_id,
            workflow_id=updated.workflow_id,
            work_package_id=updated.work_package_id,
            event_type="card_updated",
        )
        audit = _audit(
            context_id=updated.context_id,
            actor=command.actor,
            display_label=command.actor,
            action="card.update",
            target_type="achievement_card",
            target_id=updated.id,
            summary={"workflow_id": updated.workflow_id},
            timestamp=timestamp,
        )
        return self._repository.update_achievement_card(updated, event, audit)

    def set_achievement_card_importance(self, command: AchievementCardImportanceCommand) -> CardImportanceResult:
        validate_achievement_card_importance(command)
        card = self._repository.achievement_card(command.card_id)
        if card.context_id != command.context_id or card.workflow_id != command.workflow_id or card.status != "Active":
            audit = _audit(
                context_id=command.context_id,
                actor=command.actor,
                display_label=command.display_label,
                action="card.importance",
                target_type="achievement_card",
                target_id=command.card_id,
                summary={"workflow_id": command.workflow_id, "is_important": command.is_important},
                timestamp=self._clock(),
                result="REJECTED",
                error_code="OWNERSHIP_MISMATCH",
                request_id=command.request_id,
                idempotency_key=command.idempotency_key,
            )
            self._repository.record_audit(audit)
            raise AppError("OWNERSHIP_MISMATCH", "card does not belong to context and workflow", 404)
        if card.row_version != command.expected_version:
            audit = _audit(
                context_id=card.context_id,
                actor=command.actor,
                display_label=command.display_label,
                action="card.importance",
                target_type="achievement_card",
                target_id=card.id,
                summary={
                    "workflow_id": card.workflow_id,
                    "expected_version": command.expected_version,
                    "actual_version": card.row_version,
                },
                timestamp=self._clock(),
                result="REJECTED",
                error_code="VERSION_CONFLICT",
                request_id=command.request_id,
                idempotency_key=command.idempotency_key,
            )
            self._repository.record_audit(audit)
            raise AppError("VERSION_CONFLICT", "card changed; reload and retry", 409)

        changed = card.is_important != command.is_important
        timestamp = self._clock()
        version = card.row_version + int(changed)
        event = (
            AchievementCardEvent(
                id=self._identifier("ACE", card.id, timestamp),
                card_id=card.id,
                actor=command.actor,
                command="importance",
                payload={
                    "is_important": command.is_important,
                    "version_before": command.expected_version,
                    "version_after": version,
                },
                created_at=timestamp,
                context_id=card.context_id,
                workflow_id=card.workflow_id,
                work_package_id=card.work_package_id,
                event_type="card_importance_changed",
            )
            if changed
            else None
        )
        audit = _audit(
            context_id=card.context_id,
            actor=command.actor,
            display_label=command.display_label,
            action="card.importance",
            target_type="achievement_card",
            target_id=card.id,
            summary={"is_important": command.is_important, "changed": changed},
            timestamp=timestamp,
            request_id=command.request_id,
            idempotency_key=command.idempotency_key,
        )
        return self._repository.set_achievement_card_importance(
            replace(card, is_important=command.is_important, row_version=version, updated_at=timestamp),
            event,
            audit,
        )

    def delete_achievement_card(self, command: AchievementCardDeleteCommand) -> CardDeleteResult:
        card = self._repository.achievement_card(command.card_id)
        validate_achievement_card_delete(command)
        if card.row_version != command.expected_version:
            raise AppError("VERSION_CONFLICT", "card changed; reload and retry", 409)
        timestamp = self._clock()
        deleted = replace(
            card,
            status="Deleted",
            row_version=card.row_version + 1,
            updated_at=timestamp,
        )
        attachment_ids = [str(attachment["id"]) for attachment in card.attachments]
        event = AchievementCardEvent(
            id=self._identifier("ACE", card.id, timestamp),
            card_id=card.id,
            actor=command.actor,
            command="delete",
            payload={"attachments": attachment_ids},
            created_at=timestamp,
            context_id=card.context_id,
            workflow_id=card.workflow_id,
            work_package_id=card.work_package_id,
            event_type="card_deleted",
        )
        audit = _audit(
            context_id=card.context_id,
            actor=command.actor,
            display_label=command.actor,
            action="card.delete",
            target_type="achievement_card",
            target_id=card.id,
            summary={"attachment_count": len(attachment_ids)},
            timestamp=timestamp,
        )
        return self._repository.delete_achievement_card(deleted, event, audit)

    def upload_achievement_attachment(self, command: AttachmentUploadCommand) -> AchievementAttachment:
        if not command.actor.strip():
            raise AppError("INVALID_INPUT", "actor is required")
        if command.idempotency_key is not None and not command.idempotency_key.strip():
            raise AppError("INVALID_INPUT", "idempotency_key must be empty or non-blank")
        card = self._repository.achievement_card(command.card_id)
        settings = self._repository.upload_settings()
        validate_attachment_upload(command, settings)
        workflow = self._repository.workflow(card.workflow_id)
        area_name = next(
            (binding.area_name for binding in self._bindings if binding.area_id == workflow.area_id),
            None,
        )
        command = replace(command, area_name_snapshot=area_name)
        if card.status == "Deleted":
            raise AppError("CARD_NOT_ACTIVE", "attachment cannot be added to a deleted card", 409)
        timestamp = self._clock()
        event = AchievementCardEvent(
            id=self._identifier("ACE", card.id, timestamp),
            card_id=card.id,
            actor=command.actor,
            command="attachment_upload",
            payload={"original_name": command.original_name, "size_bytes": len(command.content)},
            created_at=timestamp,
            context_id=card.context_id,
            workflow_id=card.workflow_id,
            work_package_id=card.work_package_id,
            event_type="attachment_uploaded",
        )
        audit = _audit(
            context_id=card.context_id,
            actor=command.actor,
            display_label=command.actor,
            action="attachment.upload",
            target_type="achievement_attachment",
            target_id=card.id,
            summary={
                "original_name": command.original_name,
                "size_bytes": len(command.content),
            },
            timestamp=timestamp,
            request_id=command.request_id,
            idempotency_key=command.idempotency_key,
        )
        return self._repository.create_achievement_attachment(command, event, audit)

    def achievement_attachment(self, attachment_id: str) -> AchievementAttachment:
        return self._repository.achievement_attachment(attachment_id)

    def download_achievement_attachment(self, attachment_id: str) -> AttachmentContent:
        attachment = self._repository.achievement_attachment(attachment_id)
        return self._repository.read_attachment(attachment)

    def preview_achievement_attachment(
        self, attachment_id: str, representation: str = "document"
    ) -> AttachmentPreviewResult:
        if representation not in {"metadata", "document"}:
            raise AppError("INVALID_PREVIEW_REPRESENTATION", "preview representation is invalid", 422)
        attachment = self._repository.achievement_attachment(attachment_id)
        if representation == "metadata":
            return AttachmentPreviewResult(
                attachment,
                AttachmentContent(b"", "application/json", attachment.original_name, "inline"),
                representation,
            )
        extension = Path(attachment.original_name).suffix.lower()
        if extension in {".doc", ".ppt", ".zip", ".7z", ".rar"}:
            content = AttachmentContent(
                (
                    '<!doctype html><html lang="zh-CN"><body>'
                    "<p>当前附件仅支持下载。</p>"
                    f'<a href="/api/v1/achievement-attachments/{attachment.id}">下载原文件</a>'
                    "</body></html>"
                ).encode(),
                "text/html; charset=utf-8",
                attachment.original_name,
                "inline",
            )
        elif extension == ".pdf":
            content = self._repository.read_attachment(attachment)
        else:
            content = self._repository.render_attachment_preview(attachment)
        return AttachmentPreviewResult(attachment, content, representation)

    def preview_achievement_attachment_image(self, attachment_id: str, index: int) -> AttachmentContent:
        if index < 0:
            raise AppError("INVALID_INPUT", "image index is invalid", 422)
        attachment = self._repository.achievement_attachment(attachment_id)
        return self._repository.read_attachment_image(attachment, index)

    def set_workflow_selection(self, command: WorkflowSelectionCommand) -> ContextWorkflow:
        validate_workflow_selection(command)
        if command.work_package_id not in {binding.work_package_id for binding in self._bindings}:
            raise AppError("NOT_FOUND", "work package not found", 404)
        current = self._repository.workflow_for_work_package(command.context_id, command.work_package_id)
        if current.row_version != command.expected_version:
            raise AppError("VERSION_CONFLICT", "workflow changed; reload and retry", 409)
        changed = (
            current.selection_status != command.selection_status
            or current.selection_reason != command.reason
            or current.author_confirmed != command.author_confirmed
        )
        timestamp = self._clock()
        updated = replace(
            current,
            selection_status=command.selection_status,
            selection_reason=command.reason,
            author_confirmed=command.author_confirmed,
            row_version=current.row_version + int(changed),
        )
        event = (
            WorkflowEvent(
                id=self._identifier("WFE", current.id, timestamp),
                workflow_id=current.id,
                command="selection",
                payload={
                    "actor": "author",
                    "selection_status": command.selection_status,
                    "reason": command.reason,
                    "author_confirmed": command.author_confirmed,
                },
                created_at=timestamp,
            )
            if changed
            else None
        )
        audit = _audit(
            context_id=current.context_id,
            actor="author",
            display_label="author",
            action="workflow.selection",
            target_type="workflow",
            target_id=current.id,
            summary={
                "selection_status": command.selection_status,
                "author_confirmed": command.author_confirmed,
                "changed": changed,
            },
            timestamp=timestamp,
        )
        return self._repository.set_workflow_selection(updated, event, audit)

    def disclosure_preferences(
        self,
        context_id: str,
        local_user_key: str,
    ) -> tuple[ContextDisclosurePreference, ...]:
        if not local_user_key.strip():
            raise AppError("INVALID_INPUT", "local_user_key is required")
        self._repository.context(context_id)
        return self._repository.disclosure_preferences(context_id, local_user_key)

    def upsert_disclosure_preference(
        self,
        command: DisclosurePreferenceUpsertCommand,
    ) -> ContextDisclosurePreference:
        if command.disclosure_kind not in DISCLOSURE_KINDS:
            raise AppError("INVALID_DISCLOSURE_KIND", "unsupported Context disclosure kind", 422)
        if not command.local_user_key.strip() or not command.stable_subject_id.strip():
            raise AppError("INVALID_INPUT", "disclosure identity is required", 422)
        if command.expected_version < 0:
            raise AppError("INVALID_INPUT", "expected_version must be zero or a positive integer")
        self._repository.context(command.context_id)
        allowed_area_ids = {binding.area_id for binding in self._bindings}
        if command.disclosure_kind == "area" and command.stable_subject_id not in allowed_area_ids:
            raise AppError("OWNERSHIP_MISMATCH", "area is not part of the Context catalog", 404)
        return self._repository.upsert_disclosure_preference(command)

    def create_ui_session(self, command: UiSessionIssueCommand) -> UiSessionIssueResult:
        if not command.actor.strip():
            raise AppError("INVALID_INPUT", "actor is required")
        return self._repository.create_ui_session(command)

    def issue_completion_authorization(
        self,
        command: CompletionAuthorizationCommand,
    ) -> CompletionAuthorizationResult:
        if command.operation not in {"complete", "cancel"}:
            raise AppError("INVALID_INPUT", "operation must be complete or cancel")
        if command.expected_version < 1:
            raise AppError("INVALID_INPUT", "expected_version must be a positive integer")
        if not command.session_id.strip():
            raise AppError("UI_SESSION_REQUIRED", "completion authorization requires a valid UI session", 403)
        return self._repository.issue_completion_authorization(command)

    def set_workflow_completion(self, command: WorkflowCompletionCommand) -> WorkflowCompletionResult:
        validate_workflow_completion(command)
        workflow = self._repository.workflow(command.workflow_id)
        actor, display_label = self._repository.session_actor(command.session_id)
        timestamp = self._clock()
        event = WorkflowCompletionEvent(
            id=self._identifier("WCE", workflow.id, timestamp),
            workflow_id=workflow.id,
            actor=actor,
            from_status=str(int(workflow.is_completed)),
            to_status=str(int(command.completed)),
            created_at=timestamp,
            context_id=workflow.context_id,
            work_package_id=workflow.work_package_id,
            row_version=workflow.row_version + 1,
            actor_kind="human_user",
            version_before=workflow.completion_row_version,
            version_after=workflow.completion_row_version + 1,
            idempotency_key=command.idempotency_key,
            authorization_source="ui_session",
            nonce_id=command.nonce_id,
            nonce_hash=command.nonce_hash,
            operation="complete" if command.completed else "cancel",
            authorization_expires_at=0.0,
            display_label=display_label,
        )
        audit = _audit(
            context_id=workflow.context_id,
            actor=actor,
            display_label=display_label,
            action="workflow.complete" if command.completed else "workflow.cancel",
            target_type="workflow",
            target_id=workflow.id,
            summary={"from_completed": workflow.is_completed, "to_completed": command.completed},
            timestamp=timestamp,
            idempotency_key=command.idempotency_key,
        )
        return self._repository.set_workflow_completion(command, workflow, event, audit)

    def prepare_context_deletion(
        self,
        command: ContextDeletionPrepareCommand,
    ) -> ContextDeletionPrepareResult:
        validate_context_deletion_prepare(command)
        return self._repository.prepare_context_deletion(command)

    def commit_context_deletion(
        self,
        command: ContextDeletionCommitCommand,
    ) -> ContextDeletionCommitResult:
        validate_context_deletion_commit(command)
        return self._repository.commit_context_deletion(command)

    def retry_context_deletion_cleanup(
        self,
        command: ContextDeletionRetryCommand,
    ) -> ContextDeletionCommitResult:
        if not command.operation_id.strip():
            raise AppError("INVALID_INPUT", "operation_id is required", 422)
        return self._repository.retry_context_deletion_cleanup(command)


def _bindings(catalog: CatalogSnapshot) -> tuple[CatalogBinding, ...]:
    bindings: list[CatalogBinding] = []
    for area in catalog.areas:
        for work_package in area.work_packages:
            bindings.append(
                CatalogBinding(
                    area_id=area.id,
                    area_name=area.name,
                    work_package_id=work_package.id,
                    template_id=str(work_package.template["id"]),
                    skill_id=str(work_package.skill["id"]),
                )
            )
    return tuple(bindings)


def _card_payload(card: AchievementCard) -> dict[str, Any]:
    return {
        "id": card.id,
        "context_id": card.context_id,
        "workflow_id": card.workflow_id,
        "work_package_id": card.work_package_id,
        "week_item_id": card.week_item_id,
        "event_date": card.event_date,
        "event_name": card.event_name,
        "description": card.description,
        "status": card.status,
        "is_important": card.is_important,
        "row_version": card.row_version,
        "created_at": card.created_at.isoformat(),
        "updated_at": card.updated_at.isoformat(),
    }


__all__ = ["ContextRepository", "ContextUseCase", "WorkflowListResult"]


def _stable_identifier(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _audit(
    *,
    context_id: str | None,
    actor: str,
    display_label: str,
    action: str,
    target_type: str,
    target_id: str,
    summary: dict[str, Any],
    timestamp: datetime,
    result: str = "SUCCESS",
    error_code: str | None = None,
    request_id: str | None = None,
    idempotency_key: str | None = None,
) -> OperationAuditEvent:
    idempotency_key = idempotency_key or _legacy_identifier("IDEM", f"{action}:{target_type}:{target_id}", timestamp)
    request_id = request_id or _stable_identifier("REQ", f"{idempotency_key}:{action}:{target_type}:{target_id}")
    operation_id = _legacy_identifier(
        "AUDIT", f"{action}:{target_type}:{target_id}:{request_id}:{idempotency_key}", timestamp
    )
    digest_input = {
        "operation_id": operation_id,
        "context_id": context_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "result": result,
        "error_code": error_code,
        "summary": json.dumps(summary, ensure_ascii=False),
    }
    return OperationAuditEvent(
        operation_id=operation_id,
        request_id=request_id,
        idempotency_key=idempotency_key,
        context_id=context_id,
        actor=actor,
        display_label=display_label,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        error_code=error_code,
        summary=json.dumps(summary, ensure_ascii=False),
        summary_json=summary,
        schema_version=4,
        occurred_at=timestamp,
        content_digest=hashlib.sha256(
            json.dumps(digest_input, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
    )
