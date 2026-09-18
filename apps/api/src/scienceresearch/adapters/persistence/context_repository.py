"""SQLAlchemy 2 repository for the P2A native context slice."""

from __future__ import annotations

import hashlib
import html
import json
import re
import secrets
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ...domain.context import (
    AchievementAttachment,
    AchievementCard,
    AchievementCardEvent,
    AttachmentContent,
    AttachmentUploadCommand,
    CardDeleteResult,
    CardImportanceResult,
    CompletionAuthorizationCommand,
    CompletionAuthorizationResult,
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
    WorkflowSnapshot,
)
from ...domain.errors import AppError
from .models import (
    AchievementAttachmentRecord,
    AchievementCardEventRecord,
    AchievementCardRecord,
    AchievementFileOutboxRecord,
    ArtifactRecord,
    ContextDeletionOperationRecord,
    ContextDisclosurePreferenceRecord,
    ContextRecord,
    DeletedContextArchiveRecord,
    OperationAuditRecord,
    UiNonceRecord,
    UiSessionRecord,
    UploadSettingRecord,
    WeekItemRecord,
    WorkflowCompletionEventRecord,
    WorkflowEventRecord,
    WorkflowRecord,
)
from .session import PostgresUnitOfWork


class PostgresContextRepository:
    """Translate P2A aggregate values to the PostgreSQL baseline schema."""

    def __init__(self, unit_of_work: PostgresUnitOfWork, artifact_root: Path | None = None) -> None:
        self._unit_of_work = unit_of_work
        self._artifact_root = (artifact_root or Path("storage/artifacts")).resolve()

    def list_contexts(self) -> tuple[ResearchContext, ...]:
        with self._unit_of_work.session() as session:
            records = session.scalars(select(ContextRecord).order_by(ContextRecord.created_at.desc())).all()
            return tuple(_context_from_record(record) for record in records)

    def context(self, context_id: str) -> ResearchContext:
        with self._unit_of_work.session() as session:
            record = session.get(ContextRecord, context_id)
            if record is None:
                raise AppError("NOT_FOUND", "context not found", 404)
            return _context_from_record(record)

    def create_context(
        self,
        context: ResearchContext,
        workflows: tuple[ContextWorkflow, ...],
        audit: OperationAuditEvent,
    ) -> None:
        with self._unit_of_work.session() as session:
            session.add(_context_record(context))
            session.add_all(_workflow_record(workflow) for workflow in workflows)
            session.add(_operation_audit_record(audit))

    def workflows_for_context(self, context_id: str) -> WorkflowSnapshot:
        with self._unit_of_work.session() as session:
            if session.get(ContextRecord, context_id) is None:
                raise AppError("NOT_FOUND", "context not found", 404)
            workflow_records = list(
                session.scalars(
                    select(WorkflowRecord)
                    .where(WorkflowRecord.context_id == context_id)
                    .order_by(WorkflowRecord.work_package_id)
                )
            )
            card_records = list(
                session.scalars(
                    select(AchievementCardRecord)
                    .where(AchievementCardRecord.context_id == context_id, AchievementCardRecord.status == "Active")
                    .order_by(AchievementCardRecord.event_date.desc(), AchievementCardRecord.created_at.desc())
                )
            )
            card_counts = {
                str(workflow_id): int(count)
                for workflow_id, count in session.execute(
                    select(AchievementCardRecord.workflow_id, func.count())
                    .where(AchievementCardRecord.context_id == context_id)
                    .group_by(AchievementCardRecord.workflow_id)
                )
            }
            cards_by_workflow: dict[str, tuple[AchievementCard, ...]] = {}
            for workflow in workflow_records:
                cards_by_workflow[workflow.id] = ()
            for card in card_records:
                cards_by_workflow.setdefault(card.workflow_id, ())
                cards = list(cards_by_workflow[card.workflow_id])
                cards.append(_card_from_record(card, _attachments(session, card.id)))
                cards_by_workflow[card.workflow_id] = tuple(cards)
            return WorkflowSnapshot(
                context_id=context_id,
                workflows=tuple(_workflow_from_record(record) for record in workflow_records),
                cards_by_workflow=cards_by_workflow,
                card_counts=card_counts,
            )

    def workflow(self, workflow_id: str) -> ContextWorkflow:
        with self._unit_of_work.session() as session:
            record = session.get(WorkflowRecord, workflow_id)
            if record is None:
                raise AppError("NOT_FOUND", "workflow not found", 404)
            return _workflow_from_record(record)

    def validate_week_item(self, week_item_id: str, work_package_id: str) -> None:
        with self._unit_of_work.session() as session:
            record = session.get(WeekItemRecord, week_item_id)
            if record is None or record.wp_id != work_package_id:
                raise AppError("STATE_CONFLICT", "week item does not belong to work package", 409)

    def create_achievement_card(
        self,
        card: AchievementCard,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> AchievementCard:
        with self._unit_of_work.session() as session:
            workflow = session.get(WorkflowRecord, card.workflow_id)
            if workflow is None:
                raise AppError("NOT_FOUND", "workflow not found", 404)
            if workflow.context_id != card.context_id:
                raise AppError("STATE_CONFLICT", "workflow does not belong to context", 409)
            if card.week_item_id:
                week_item = session.get(WeekItemRecord, card.week_item_id)
                if week_item is None or week_item.wp_id != workflow.work_package_id:
                    raise AppError("STATE_CONFLICT", "week item does not belong to work package", 409)
            session.add(_card_record(card))
            session.flush()
            session.add(_card_event_record(event))
            session.add(_operation_audit_record(audit))
            session.flush()
            return card

    def achievement_card(self, card_id: str) -> AchievementCard:
        with self._unit_of_work.session() as session:
            record = session.get(AchievementCardRecord, card_id)
            if record is None:
                raise AppError("NOT_FOUND", "achievement card not found", 404)
            return _card_from_record(record, _attachments(session, card_id))

    def update_achievement_card(
        self,
        card: AchievementCard,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> AchievementCard:
        with self._unit_of_work.session() as session:
            expected_version = card.row_version - 1
            updated = session.execute(
                update(AchievementCardRecord)
                .where(
                    AchievementCardRecord.id == card.id,
                    AchievementCardRecord.row_version == expected_version,
                )
                .values(
                    event_date=card.event_date,
                    event_name=card.event_name,
                    description=card.description,
                    row_version=card.row_version,
                    updated_at=card.updated_at,
                )
            )
            if int(getattr(updated, "rowcount", 0)) != 1:
                if session.get(AchievementCardRecord, card.id) is None:
                    raise AppError("NOT_FOUND", "achievement card not found", 404)
                raise AppError("VERSION_CONFLICT", "card changed; reload and retry", 409)
            session.add(_card_event_record(event))
            session.add(_operation_audit_record(audit))
            session.flush()
            return card

    def set_achievement_card_importance(
        self,
        card: AchievementCard,
        event: AchievementCardEvent | None,
        audit: OperationAuditEvent,
    ) -> CardImportanceResult:
        with self._unit_of_work.session() as session:
            record = session.get(AchievementCardRecord, card.id)
            if record is None:
                raise AppError("NOT_FOUND", "achievement card not found", 404)
            changed = event is not None
            expected_version = card.row_version - int(changed)
            result = session.execute(
                update(AchievementCardRecord)
                .where(
                    AchievementCardRecord.id == card.id,
                    AchievementCardRecord.row_version == expected_version,
                )
                .values(
                    is_important=card.is_important,
                    row_version=card.row_version,
                    updated_at=card.updated_at,
                )
            )
            if int(getattr(result, "rowcount", 0)) != 1:
                raise AppError("VERSION_CONFLICT", "card changed; reload and retry", 409)
            if event is not None:
                session.add(_card_event_record(event))
            session.add(_operation_audit_record(audit))
            session.flush()
            return CardImportanceResult(
                card_id=card.id,
                is_important=card.is_important,
                changed=changed,
                row_version=card.row_version,
                updated_at=card.updated_at,
                operation_id=audit.operation_id,
            )

    def record_audit(self, audit: OperationAuditEvent) -> None:
        with self._unit_of_work.session() as session:
            session.add(_operation_audit_record(audit))

    def delete_achievement_card(
        self,
        card: AchievementCard,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> CardDeleteResult:
        with self._unit_of_work.session() as session:
            expected_version = card.row_version - 1
            record = session.scalars(
                select(AchievementCardRecord)
                .where(
                    AchievementCardRecord.id == card.id,
                    AchievementCardRecord.row_version == expected_version,
                )
                .with_for_update()
            ).first()
            if record is None:
                if session.get(AchievementCardRecord, card.id) is None:
                    raise AppError("NOT_FOUND", "achievement card not found", 404)
                raise AppError("VERSION_CONFLICT", "card changed; reload and retry", 409)
            attachments = list(
                session.scalars(
                    select(AchievementAttachmentRecord).where(AchievementAttachmentRecord.card_id == card.id)
                )
            )
            for attachment in attachments:
                session.add(
                    AchievementFileOutboxRecord(
                        id=_outbox_id(attachment.id),
                        operation="delete",
                        relative_path=attachment.relative_path,
                        status="DB_COMMITTED",
                        created_at=card.updated_at,
                    )
                )
                session.delete(attachment)
            updated = session.execute(
                update(AchievementCardRecord)
                .where(
                    AchievementCardRecord.id == card.id,
                    AchievementCardRecord.row_version == expected_version,
                )
                .values(
                    status=card.status,
                    row_version=card.row_version,
                    updated_at=card.updated_at,
                )
            )
            if int(getattr(updated, "rowcount", 0)) != 1:
                raise AppError("VERSION_CONFLICT", "card changed; reload and retry", 409)
            session.add(_card_event_record(event))
            session.add(_operation_audit_record(audit))
            session.flush()
            return CardDeleteResult(
                id=card.id,
                deleted=True,
                context_id=card.context_id,
                workflow_id=card.workflow_id,
            )

    def upload_settings(self) -> UploadSettings:
        with self._unit_of_work.session() as session:
            return self._read_upload_settings(session)

    def create_achievement_attachment(
        self,
        command: AttachmentUploadCommand,
        event: AchievementCardEvent,
        audit: OperationAuditEvent,
    ) -> AchievementAttachment:
        attachment_id = f"ATT-{secrets.token_hex(6)}"
        extension = Path(command.original_name).suffix.lower()
        relative_path = f"achievement-cards/{attachment_id}{extension}"
        candidate = self._artifact_path(relative_path)
        written = False
        try:
            with self._unit_of_work.session() as session:
                settings = self._read_upload_settings(session)
                card = session.scalars(
                    select(AchievementCardRecord).where(AchievementCardRecord.id == command.card_id).with_for_update()
                ).first()
                if card is None:
                    raise AppError("NOT_FOUND", "achievement card not found", 404)
                if card.status == "Deleted":
                    raise AppError("CARD_NOT_ACTIVE", "attachment cannot be added to a deleted card", 409)
                count = int(
                    session.execute(
                        select(func.count())
                        .select_from(AchievementAttachmentRecord)
                        .where(AchievementAttachmentRecord.card_id == card.id)
                    ).scalar_one()
                )
                if count >= settings.max_attachments_per_card:
                    raise AppError("ATTACHMENT_LIMIT", "attachment limit reached", 422)
                normalized_name = command.original_name.strip()
                duplicate = session.execute(
                    select(func.count())
                    .select_from(AchievementAttachmentRecord)
                    .where(
                        AchievementAttachmentRecord.card_id == card.id,
                        func.lower(AchievementAttachmentRecord.original_name) == normalized_name.lower(),
                    )
                ).scalar_one()
                if int(duplicate):
                    raise AppError("DUPLICATE_FILENAME", "same filename already exists on this card", 409)
                digest = hashlib.sha256(command.content).hexdigest()
                created_at = event.created_at
                record = AchievementAttachmentRecord(
                    id=attachment_id,
                    card_id=card.id,
                    original_name=normalized_name,
                    storage_name=f"{attachment_id}{extension}",
                    relative_path=relative_path,
                    mime_type=command.mime_type,
                    size_bytes=len(command.content),
                    sha256=digest,
                    preview_state="download_only"
                    if extension in {".doc", ".ppt", ".zip", ".7z", ".rar"}
                    else "available",
                    created_at=created_at,
                    original_name_key=normalized_name.casefold(),
                    area_name_snapshot=command.area_name_snapshot,
                    work_package_name_snapshot=self._package_snapshot(session, card),
                    event_folder_snapshot="achievement-cards",
                    before_size_bytes=len(command.content),
                    before_sha256=digest,
                    after_size_bytes=len(command.content),
                    after_sha256=digest,
                )
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_bytes(command.content)
                written = True
                session.add(record)
                session.add(_card_event_record(event))
                session.add(_operation_audit_record(audit))
                # Flush before domain conversion so ORM defaults (row/version/path
                # metadata) are populated and the committed response is contract-valid.
                session.flush()
                return _attachment_domain(record)
        except Exception:
            if written:
                try:
                    candidate.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def achievement_attachment(self, attachment_id: str) -> AchievementAttachment:
        with self._unit_of_work.session() as session:
            record = session.get(AchievementAttachmentRecord, attachment_id)
            if record is None:
                raise AppError("NOT_FOUND", "attachment not found", 404)
            return _attachment_domain(record)

    def read_attachment(self, attachment: AchievementAttachment) -> AttachmentContent:
        candidate = self._artifact_path(attachment.relative_path)
        if not candidate.is_file():
            raise AppError("NOT_FOUND", "attachment file not found", 404)
        data = candidate.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != attachment.size_bytes or digest != attachment.sha256:
            raise AppError("ATTACHMENT_INTEGRITY", "attachment size or hash mismatch", 409)
        return AttachmentContent(data, attachment.mime_type, attachment.original_name, "attachment")

    def render_attachment_preview(self, attachment: AchievementAttachment) -> AttachmentContent:
        candidate = self._artifact_path(attachment.relative_path)
        if not candidate.is_file():
            raise AppError("NOT_FOUND", "attachment file not found", 404)
        data = candidate.read_bytes()
        if len(data) != attachment.size_bytes or hashlib.sha256(data).hexdigest() != attachment.sha256:
            raise AppError("ATTACHMENT_INTEGRITY", "attachment size or hash mismatch", 409)
        extension = Path(attachment.original_name).suffix.lower()
        if extension in {".md", ".markdown"}:
            body = _render_markdown(data.decode("utf-8", errors="replace"))
            return AttachmentContent(
                _preview_document(attachment.original_name, body).encode("utf-8"),
                "text/html; charset=utf-8",
                attachment.original_name,
                "inline",
            )
        try:
            with zipfile.ZipFile(candidate) as archive:
                infos = archive.infolist()
                if (
                    len(infos) > 500
                    or any(info.file_size > 10_000_000 for info in infos)
                    or sum(info.file_size for info in infos) > 50_000_000
                    or any(info.compress_size and info.file_size / info.compress_size > 1000 for info in infos)
                ):
                    raise ValueError("OOXML resource limits exceeded")
                names = archive.namelist()
                if any(
                    name.startswith("vbaProject")
                    or name.startswith("word/vbaProject")
                    or name.startswith("ppt/vbaProject")
                    or name.startswith("externalLinks/")
                    for name in names
                ):
                    raise ValueError("macros or external links are not allowed")
                if any(name.endswith(".rels") and b'TargetMode="External"' in archive.read(name) for name in names):
                    raise ValueError("external relationships are not allowed")
                if "[Content_Types].xml" not in names:
                    raise ValueError("OOXML content types are missing")
                required = "word/" if extension == ".docx" else "ppt/"
                if not any(name.startswith(required) for name in names):
                    raise ValueError("office package structure is invalid")
                prefixes = ("word/",) if extension == ".docx" else ("ppt/slides/", "ppt/notesSlides/")
                fragments: list[str] = []
                for name in sorted(names):
                    if not name.endswith(".xml") or not name.startswith(prefixes):
                        continue
                    root = ElementTree.fromstring(archive.read(name))
                    values = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
                    if values:
                        fragments.append(html.escape(" ".join(values)))
                image_count = sum(
                    1
                    for name in names
                    if (name.startswith("word/media/") or name.startswith("ppt/media/")) and not name.endswith("/")
                )
                if image_count:
                    fragments.append(f"嵌入图片：{min(image_count, 20)} 张")
                body = "<br>".join(fragments) or "文档中没有可提取文本。"
                return AttachmentContent(
                    _preview_document(attachment.original_name, body).encode("utf-8"),
                    "text/html; charset=utf-8",
                    attachment.original_name,
                    "inline",
                )
        except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise AppError("PREVIEW_FAILED", "attachment preview is unavailable", 422) from exc

    def read_attachment_image(self, attachment: AchievementAttachment, index: int) -> AttachmentContent:
        candidate = self._artifact_path(attachment.relative_path)
        extension = Path(attachment.original_name).suffix.lower()
        if extension not in {".docx", ".pptx"} or not candidate.is_file():
            raise AppError("NOT_FOUND", "preview image not found", 404)
        try:
            with zipfile.ZipFile(candidate) as archive:
                infos = archive.infolist()
                if (
                    len(infos) > 500
                    or any(info.file_size > 10_000_000 for info in infos)
                    or sum(info.file_size for info in infos) > 50_000_000
                ):
                    raise ValueError("OOXML resource limits exceeded")
                if any(
                    name.startswith("vbaProject")
                    or name.startswith("word/vbaProject")
                    or name.startswith("ppt/vbaProject")
                    for name in archive.namelist()
                ):
                    raise ValueError("macros are not allowed")
                images = []
                for name in archive.namelist():
                    if not (name.startswith("word/media/") or name.startswith("ppt/media/")) or name.endswith("/"):
                        continue
                    data = archive.read(name)
                    media_type = (
                        "image/png"
                        if data.startswith(b"\x89PNG\r\n\x1a\n")
                        else "image/jpeg"
                        if data.startswith(b"\xff\xd8\xff")
                        else "image/gif"
                        if data.startswith(b"GIF8")
                        else None
                    )
                    if media_type and len(data) <= 5_000_000:
                        images.append((data, media_type))
            if index >= len(images):
                raise AppError("NOT_FOUND", "preview image not found", 404)
            data, media_type = images[index]
            return AttachmentContent(
                data,
                media_type,
                f"attachment-image-{index + 1}",
                "inline",
            )
        except (OSError, KeyError, zipfile.BadZipFile) as exc:
            raise AppError("PREVIEW_FAILED", "attachment preview is unavailable", 422) from exc

    def _artifact_path(self, relative_path: str) -> Path:
        candidate = (self._artifact_root / relative_path).resolve()
        if self._artifact_root not in candidate.parents:
            raise AppError("PATH_OUTSIDE_ROOT", "attachment path escapes configured root", 422)
        return candidate

    def _package_snapshot(self, session: Session, card: AchievementCardRecord) -> str | None:
        return (
            session.scalar(
                select(WeekItemRecord.title)
                .where(WeekItemRecord.wp_id == card.work_package_id)
                .order_by(WeekItemRecord.created_at)
                .limit(1)
            )
            or card.work_package_id
        )

    def _read_upload_settings(self, session: Session) -> UploadSettings:
        record = session.scalars(select(UploadSettingRecord).limit(1)).first()
        if record is None:
            return _DEFAULT_UPLOAD_SETTINGS
        return UploadSettings(
            max_file_bytes=int(record.max_file_bytes),
            max_attachments_per_card=int(record.max_attachments_per_card),
            allowed_extensions=tuple(str(value) for value in record.allowed_extensions),
            version=int(record.version),
        )

    def workflow_for_work_package(self, context_id: str, work_package_id: str) -> ContextWorkflow:
        with self._unit_of_work.session() as session:
            record = session.scalars(
                select(WorkflowRecord)
                .where(
                    WorkflowRecord.context_id == context_id,
                    WorkflowRecord.work_package_id == work_package_id,
                )
                .limit(1)
            ).first()
            if record is None:
                raise AppError("NOT_FOUND", "workflow package not found", 404)
            return _workflow_from_record(record)

    def set_workflow_selection(
        self,
        workflow: ContextWorkflow,
        event: WorkflowEvent | None,
        audit: OperationAuditEvent,
    ) -> ContextWorkflow:
        with self._unit_of_work.session() as session:
            record = session.scalars(
                select(WorkflowRecord)
                .where(
                    WorkflowRecord.context_id == workflow.context_id,
                    WorkflowRecord.work_package_id == workflow.work_package_id,
                )
                .with_for_update()
                .limit(1)
            ).first()
            if record is None:
                raise AppError("NOT_FOUND", "workflow package not found", 404)
            if record.row_version != workflow.row_version - int(event is not None):
                raise AppError("VERSION_CONFLICT", "workflow version changed", 409)
            record.selection_status = workflow.selection_status
            record.selection_reason = workflow.selection_reason
            record.author_confirmed = workflow.author_confirmed
            record.row_version = workflow.row_version
            if event is not None:
                session.add(_workflow_event_record(event))
            session.add(_operation_audit_record(audit))
            session.flush()
            return _workflow_from_record(record)

    def disclosure_preferences(
        self,
        context_id: str,
        local_user_key: str,
    ) -> tuple[ContextDisclosurePreference, ...]:
        with self._unit_of_work.session() as session:
            if session.get(ContextRecord, context_id) is None:
                raise AppError("NOT_FOUND", "context not found", 404)
            records = session.scalars(
                select(ContextDisclosurePreferenceRecord)
                .where(
                    ContextDisclosurePreferenceRecord.context_id == context_id,
                    ContextDisclosurePreferenceRecord.local_user_key == local_user_key,
                )
                .order_by(
                    ContextDisclosurePreferenceRecord.disclosure_kind,
                    ContextDisclosurePreferenceRecord.stable_subject_id,
                )
            ).all()
            return tuple(_disclosure_from_record(record) for record in records)

    def upsert_disclosure_preference(
        self,
        command: DisclosurePreferenceUpsertCommand,
    ) -> ContextDisclosurePreference:
        timestamp = datetime.now(UTC)
        with self._unit_of_work.session() as session:
            context_record = session.get(ContextRecord, command.context_id)
            if context_record is None:
                raise AppError("NOT_FOUND", "context not found", 404)
            _validate_disclosure_subject(session, command)
            key = (
                command.local_user_key,
                command.context_id,
                command.disclosure_kind,
                command.stable_subject_id,
            )
            record = session.scalars(
                select(ContextDisclosurePreferenceRecord)
                .where(
                    ContextDisclosurePreferenceRecord.local_user_key == key[0],
                    ContextDisclosurePreferenceRecord.context_id == key[1],
                    ContextDisclosurePreferenceRecord.disclosure_kind == key[2],
                    ContextDisclosurePreferenceRecord.stable_subject_id == key[3],
                )
                .with_for_update()
            ).first()
            if record is None:
                if command.expected_version != 0:
                    raise AppError("VERSION_CONFLICT", "disclosure preference was created; reload and retry", 409)
                record = ContextDisclosurePreferenceRecord(
                    local_user_key=key[0],
                    context_id=key[1],
                    disclosure_kind=key[2],
                    stable_subject_id=key[3],
                    is_expanded=command.requested_is_expanded,
                    row_version=1,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                session.add(record)
                session.flush()
            elif record.row_version != command.expected_version:
                raise AppError("VERSION_CONFLICT", "disclosure preference changed; reload and retry", 409)
            elif record.is_expanded != command.requested_is_expanded:
                record.is_expanded = command.requested_is_expanded
                record.row_version += 1
                record.updated_at = timestamp
                session.add(_operation_audit_record(_disclosure_audit(command, record, timestamp)))
            return _disclosure_from_record(record)

    def prepare_context_deletion(
        self,
        command: ContextDeletionPrepareCommand,
    ) -> ContextDeletionPrepareResult:
        now = datetime.now(UTC)
        with self._unit_of_work.session() as session:
            context_record = session.scalars(
                select(ContextRecord).where(ContextRecord.id == command.context_id).with_for_update()
            ).first()
            if context_record is None:
                raise AppError("NOT_FOUND", "context not found", 404)
            if context_record.row_version != command.expected_version:
                raise AppError("VERSION_CONFLICT", "context changed; reload and retry", 409)
            active_states = ("PREPARED", "FILES_STAGED", "DB_COMMITTED", "CLEANUP_PENDING")
            active = session.scalars(
                select(ContextDeletionOperationRecord)
                .where(
                    ContextDeletionOperationRecord.context_id == context_record.id,
                    ContextDeletionOperationRecord.state.in_(active_states),
                )
                .with_for_update()
            ).first()
            if active is not None:
                raise AppError("DELETION_ALREADY_PREPARED", "a deletion operation is already active", 409)
            manifest = _deletion_manifest(context_record.id, context_record.name, context_record.row_version, session)
            digest = _canonical_digest(manifest)
            confirmation = secrets.token_urlsafe(32)
            operation_id = f"CTXDEL-{hashlib.sha256(f'{context_record.id}:{command.session_id}:{now.isoformat()}'.encode()).hexdigest()[:20]}"
            request_id = f"REQ-{hashlib.sha256(f'{operation_id}:{confirmation}'.encode()).hexdigest()[:24]}"
            record = ContextDeletionOperationRecord(
                operation_id=operation_id,
                context_id=context_record.id,
                context_version=context_record.row_version,
                retain_files=command.retain_files,
                state="PREPARED",
                idempotency_key=f"prepare:{operation_id}",
                created_at=now,
                updated_at=now,
                confirmation_expires_at=datetime.fromtimestamp(now.timestamp() + 900, UTC),
                confirmation_nonce_hash=hashlib.sha256(f"{command.session_id}:{confirmation}".encode()).hexdigest(),
                request_id=request_id,
                session_id=command.session_id,
                entity_counts_json=manifest["entity_counts"],
                file_manifest_json=manifest,
                manifest_digest=digest,
            )
            session.add(record)
            return ContextDeletionPrepareResult(
                operation_id=operation_id,
                request_id=request_id,
                context_id=context_record.id,
                context_name=context_record.name,
                retain_files=command.retain_files,
                expected_version=context_record.row_version,
                confirmation=confirmation,
                expires_at=record.confirmation_expires_at or now,
                entity_counts=manifest["entity_counts"],
                attachments=tuple(manifest["attachments"]),
                manifest_digest=digest,
                state="PREPARED",
            )

    def commit_context_deletion(
        self,
        command: ContextDeletionCommitCommand,
    ) -> ContextDeletionCommitResult:
        operation, manifest, context_id, context_name, version, retain = self._load_commit_ticket(command)
        if operation.state in {"DONE", "CLEANUP_PENDING", "DB_COMMITTED"}:
            if operation.state in {"DB_COMMITTED", "CLEANUP_PENDING"}:
                operation, manifest = self._refresh_operation(operation.operation_id)
                return self._finalize_context_deletion(operation, manifest)
            return ContextDeletionCommitResult(
                operation_id=operation.operation_id,
                state=operation.state,
                retain_files=operation.retain_files,
                idempotent=True,
                manifest_ref=operation.manifest_ref,
                removed_attachment_count=len(manifest["attachments"]),
            )

        archive_relative = f"archived-contexts/{operation.operation_id}" if operation.retain_files else None
        trash_relative = f"trash/{operation.operation_id}" if not operation.retain_files else None
        staging = self._artifact_path((archive_relative or trash_relative or "") + "/.saga-staging")
        final_root = self._artifact_path(archive_relative or trash_relative or "")
        self._stage_deletion_files(manifest, staging, final_root)
        now = datetime.now(UTC)
        try:
            with self._unit_of_work.session() as session:
                record = session.scalars(
                    select(ContextDeletionOperationRecord)
                    .where(ContextDeletionOperationRecord.operation_id == operation.operation_id)
                    .with_for_update()
                ).one()
                if record.state != "PREPARED":
                    raise AppError("DELETION_OPERATION_CHANGED", "deletion operation changed; prepare again", 409)
                record.state = "FILES_STAGED"
                record.confirmation_consumed_at = now
                record.archive_relative_path = archive_relative
                record.trash_relative_path = trash_relative
                record.updated_at = now
        except Exception:
            self._restore_staged_files(manifest, staging)
            raise

        try:
            with self._unit_of_work.session() as session:
                record = session.scalars(
                    select(ContextDeletionOperationRecord)
                    .where(ContextDeletionOperationRecord.operation_id == operation.operation_id)
                    .with_for_update()
                ).one()
                context_record = session.scalars(
                    select(ContextRecord).where(ContextRecord.id == context_id).with_for_update()
                ).first()
                if context_record is None or context_record.row_version != version:
                    raise AppError("VERSION_CONFLICT", "context changed; deletion was not committed", 409)
                current = _deletion_manifest(context_id, context_name, version, session)
                if _canonical_digest(current) != record.manifest_digest:
                    raise AppError("MANIFEST_CHANGED", "deletion snapshot changed; prepare again", 409)
                self._delete_context_rows(session, context_id)
                manifest_ref = f"{archive_relative}/manifest.json" if archive_relative else None
                record.state = "DB_COMMITTED"
                record.manifest_ref = manifest_ref
                record.updated_at = datetime.now(UTC)
                if archive_relative:
                    session.add(
                        DeletedContextArchiveRecord(
                            archive_id=f"ARCH-{hashlib.sha256(operation.operation_id.encode()).hexdigest()[:20]}",
                            operation_id=operation.operation_id,
                            context_id=context_id,
                            manifest_relative_path=manifest_ref or "",
                            attachment_count=len(manifest["attachments"]),
                            created_at=record.updated_at,
                            content_digest=record.manifest_digest or "",
                        )
                    )
                outbox_path = archive_relative or trash_relative or ""
                outbox_id = (
                    f"OUT-{hashlib.sha256(f'context-delete:{operation.operation_id}'.encode()).hexdigest()[:24]}"
                )
                if session.get(AchievementFileOutboxRecord, outbox_id) is None:
                    session.add(
                        AchievementFileOutboxRecord(
                            id=outbox_id,
                            operation="context_delete_archive" if retain else "context_delete_cleanup",
                            relative_path=outbox_path,
                            status="PENDING",
                            created_at=record.updated_at,
                        )
                    )
                session.add(
                    _operation_audit_record(
                        _saga_audit(
                            context_id=context_id,
                            actor="author",
                            action="context.delete",
                            target_id=context_id,
                            retain=retain,
                            attachment_count=len(manifest["attachments"]),
                            operation_id=operation.operation_id,
                            timestamp=record.updated_at,
                        )
                    )
                )
        except Exception as exc:
            self._restore_staged_files(manifest, staging)
            with self._unit_of_work.session() as session:
                rollback_record = session.get(
                    ContextDeletionOperationRecord,
                    operation.operation_id,
                )
                if rollback_record is not None and rollback_record.state == "FILES_STAGED":
                    rollback_record.state = "ROLLED_BACK"
                    rollback_record.error_code = getattr(exc, "code", "DB_COMMIT_FAILED")
                    rollback_record.error_detail = str(exc)
                    rollback_record.updated_at = datetime.now(UTC)
            raise

        refreshed, refreshed_manifest = self._refresh_operation(operation.operation_id)
        return self._finalize_context_deletion(refreshed, refreshed_manifest)

    def retry_context_deletion_cleanup(
        self,
        command: ContextDeletionRetryCommand,
    ) -> ContextDeletionCommitResult:
        operation, manifest = self._refresh_operation(command.operation_id)
        return self._finalize_context_deletion(operation, manifest)

    def _load_commit_ticket(
        self,
        command: ContextDeletionCommitCommand,
    ) -> tuple[ContextDeletionOperationRecord, dict[str, Any], str, str, int, bool]:
        now = datetime.now(UTC)
        if not command.confirmation.strip() or not command.session_id.strip():
            raise AppError("DELETE_CONFIRMATION_REQUIRED", "one-time deletion confirmation is required", 409)
        with self._unit_of_work.session() as session:
            operation = session.scalars(
                select(ContextDeletionOperationRecord)
                .where(ContextDeletionOperationRecord.operation_id == command.operation_id)
                .with_for_update()
            ).first()
            if operation is None:
                raise AppError("NOT_FOUND", "deletion operation not found", 404)
            if operation.context_id != command.context_id:
                raise AppError("OWNERSHIP_MISMATCH", "deletion ticket does not belong to this context", 403)
            if (
                operation.session_id != command.session_id
                or operation.confirmation_nonce_hash
                != hashlib.sha256(f"{command.session_id}:{command.confirmation}".encode()).hexdigest()
            ):
                raise AppError(
                    "DELETE_CONFIRMATION_INVALID", "deletion ticket is invalid or bound to another session", 403
                )
            if operation.state in {"FAILED", "ROLLED_BACK"}:
                raise AppError("DELETE_TICKET_INVALID", "deletion must be prepared again", 409)
            if operation.state == "PREPARED" and (
                operation.confirmation_expires_at is None or operation.confirmation_expires_at < now
            ):
                raise AppError("DELETE_CONFIRMATION_EXPIRED", "deletion ticket has expired", 409)
            if operation.state == "PREPARED":
                context_record = session.scalars(
                    select(ContextRecord).where(ContextRecord.id == operation.context_id).with_for_update()
                ).first()
                if context_record is None:
                    raise AppError("NOT_FOUND", "context not found", 404)
                if context_record.row_version != operation.context_version:
                    raise AppError("VERSION_CONFLICT", "context changed; prepare deletion again", 409)
                manifest = _deletion_manifest(
                    context_record.id, context_record.name, context_record.row_version, session
                )
                if _canonical_digest(manifest) != operation.manifest_digest:
                    raise AppError("MANIFEST_CHANGED", "deletion snapshot changed; prepare again", 409)
            else:
                stored = operation.file_manifest_json
                manifest = dict(stored) if isinstance(stored, dict) else {}
            return (
                operation,
                manifest,
                operation.context_id,
                str((operation.file_manifest_json or {}).get("context_name", "")),
                operation.context_version,
                operation.retain_files,
            )

    def _refresh_operation(
        self,
        operation_id: str,
    ) -> tuple[ContextDeletionOperationRecord, dict[str, Any]]:
        with self._unit_of_work.session() as session:
            operation = session.get(ContextDeletionOperationRecord, operation_id)
            if operation is None:
                raise AppError("NOT_FOUND", "deletion operation not found", 404)
            stored = operation.file_manifest_json
            manifest = dict(stored) if isinstance(stored, dict) else {}
            return operation, manifest

    def _finalize_context_deletion(
        self,
        operation: ContextDeletionOperationRecord,
        manifest: dict[str, Any],
    ) -> ContextDeletionCommitResult:
        root_relative = operation.archive_relative_path or operation.trash_relative_path
        if not root_relative:
            raise AppError("DELETION_STATE_INVALID", "deletion staging path is missing", 409)
        root = self._artifact_path(root_relative)
        staging = root / ".saga-staging"
        try:
            if operation.retain_files:
                for entry in manifest["attachments"]:
                    staged = staging / f"{entry['id']}__{Path(entry['original_name']).name}"
                    final = root / f"{entry['id']}__{Path(entry['original_name']).name}"
                    if staged.is_file():
                        final.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(staged), str(final))
                    if not final.is_file():
                        raise AppError("ARCHIVE_INCOMPLETE", "archived attachment is missing", 409)
                    data = final.read_bytes()
                    if len(data) != int(entry["size_bytes"]) or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                        raise AppError("ATTACHMENT_INTEGRITY", "archived attachment failed integrity check", 409)
                staged_manifest = staging / "manifest.json"
                final_manifest = root / "manifest.json"
                if staged_manifest.is_file():
                    final_manifest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(staged_manifest), str(final_manifest))
                if staging.exists():
                    shutil.rmtree(staging)
            elif root.exists():
                shutil.rmtree(root)
        except AppError:
            self._mark_cleanup_failed(operation.operation_id, root_relative, "ARCHIVE_FINALIZE_FAILED")
            raise
        except OSError as exc:
            self._mark_cleanup_failed(operation.operation_id, root_relative, "ARTIFACT_CLEANUP_FAILED", str(exc))
            return ContextDeletionCommitResult(
                operation_id=operation.operation_id,
                state="CLEANUP_PENDING",
                retain_files=operation.retain_files,
                idempotent=True,
                manifest_ref=operation.manifest_ref,
                removed_attachment_count=len(manifest["attachments"]),
                unresolved_files=(root_relative,),
            )

        now = datetime.now(UTC)
        with self._unit_of_work.session() as session:
            record = session.get(ContextDeletionOperationRecord, operation.operation_id)
            if record is not None:
                record.state = "DONE"
                record.updated_at = now
            outbox_id = f"OUT-{hashlib.sha256(f'context-delete:{operation.operation_id}'.encode()).hexdigest()[:24]}"
            outbox = session.get(AchievementFileOutboxRecord, outbox_id)
            if outbox is not None:
                outbox.status = "DONE"
                outbox.completed_at = now
                outbox.error = None
        return ContextDeletionCommitResult(
            operation_id=operation.operation_id,
            state="DONE",
            retain_files=operation.retain_files,
            idempotent=operation.state != "PREPARED",
            manifest_ref=operation.manifest_ref,
            removed_attachment_count=len(manifest["attachments"]),
        )

    def _mark_cleanup_failed(
        self,
        operation_id: str,
        relative_path: str,
        code: str,
        detail: str = "",
    ) -> None:
        now = datetime.now(UTC)
        with self._unit_of_work.session() as session:
            record = session.get(ContextDeletionOperationRecord, operation_id)
            if record is not None:
                record.state = "CLEANUP_PENDING"
                record.error_code = code
                record.error_detail = detail
                record.updated_at = now
            outbox_id = f"OUT-{hashlib.sha256(f'context-delete:{operation_id}'.encode()).hexdigest()[:24]}"
            outbox = session.get(AchievementFileOutboxRecord, outbox_id)
            if outbox is not None:
                outbox.status = "PENDING"
                outbox.error = code

    def _stage_deletion_files(
        self,
        manifest: dict[str, Any],
        staging: Path,
        final_root: Path,
    ) -> None:
        if self._artifact_root not in staging.parents or self._artifact_root not in final_root.parents:
            raise AppError("PATH_OUTSIDE_ROOT", "deletion artifact path escapes configured root", 422)
        moved: list[tuple[Path, Path]] = []
        try:
            staging.mkdir(parents=True, exist_ok=True)
            for entry in manifest["attachments"]:
                source = self._artifact_path(entry["relative_path"])
                target = staging / f"{entry['id']}__{Path(entry['original_name']).name}"
                if not source.is_file():
                    raise AppError("ATTACHMENT_FILE_MISSING", "attachment file is missing", 409)
                data = source.read_bytes()
                if len(data) != int(entry["size_bytes"]) or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise AppError("ATTACHMENT_INTEGRITY", "attachment changed during deletion staging", 409)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
                moved.append((source, target))
            (staging / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2),
                encoding="utf-8",
            )
        except Exception:
            for source, target in reversed(moved):
                if target.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(target), str(source))
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise

    def _restore_staged_files(self, manifest: dict[str, Any], staging: Path) -> None:
        for entry in manifest["attachments"]:
            staged = staging / f"{entry['id']}__{Path(entry['original_name']).name}"
            source = self._artifact_path(entry["relative_path"])
            if staged.is_file():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staged), str(source))
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

    def _delete_context_rows(self, session: Session, context_id: str) -> None:
        workflow_ids = select(WorkflowRecord.id).where(WorkflowRecord.context_id == context_id).scalar_subquery()
        session.execute(delete(ArtifactRecord).where(ArtifactRecord.context_id == context_id))
        session.execute(
            delete(WorkflowCompletionEventRecord).where(WorkflowCompletionEventRecord.context_id == context_id)
        )
        session.execute(delete(AchievementCardEventRecord).where(AchievementCardEventRecord.context_id == context_id))
        session.execute(
            delete(AchievementAttachmentRecord).where(
                AchievementAttachmentRecord.card_id.in_(
                    select(AchievementCardRecord.id).where(AchievementCardRecord.context_id == context_id)
                )
            )
        )
        session.execute(delete(AchievementCardRecord).where(AchievementCardRecord.context_id == context_id))
        session.execute(delete(WorkflowEventRecord).where(WorkflowEventRecord.workflow_id.in_(workflow_ids)))
        session.execute(
            delete(ContextDisclosurePreferenceRecord).where(ContextDisclosurePreferenceRecord.context_id == context_id)
        )
        session.execute(delete(UiNonceRecord).where(UiNonceRecord.context_id == context_id))
        session.execute(delete(WorkflowRecord).where(WorkflowRecord.context_id == context_id))
        session.execute(delete(ContextRecord).where(ContextRecord.id == context_id))
        remaining = (
            int(
                session.execute(
                    select(func.count()).select_from(ContextRecord).where(ContextRecord.id == context_id)
                ).scalar_one()
            )
            + int(
                session.execute(
                    select(func.count()).select_from(WorkflowRecord).where(WorkflowRecord.context_id == context_id)
                ).scalar_one()
            )
            + int(
                session.execute(
                    select(func.count())
                    .select_from(AchievementCardRecord)
                    .where(AchievementCardRecord.context_id == context_id)
                ).scalar_one()
            )
        )
        if remaining:
            raise AppError("CLOSURE_INCOMPLETE", "context-owned records remain after deletion", 409)

    def create_ui_session(self, command: UiSessionIssueCommand) -> UiSessionIssueResult:
        now = datetime.now(UTC)
        session_id = secrets.token_urlsafe(32)
        expires_at = now.timestamp() + 1_800
        display_label = command.display_label or command.actor
        with self._unit_of_work.session() as session:
            session.add(
                UiSessionRecord(
                    id=session_id,
                    nonce_hash=hashlib.sha256(session_id.encode()).hexdigest(),
                    expires_at=expires_at,
                    created_at=now,
                    actor=command.actor,
                    display_label=display_label,
                )
            )
        return UiSessionIssueResult(
            session_id=session_id,
            expires_at=expires_at,
            actor=command.actor,
            display_label=display_label,
        )

    def issue_completion_authorization(
        self,
        command: CompletionAuthorizationCommand,
    ) -> CompletionAuthorizationResult:
        now = datetime.now(UTC)
        operation = command.operation
        with self._unit_of_work.session() as session:
            session_record = session.scalars(
                select(UiSessionRecord).where(UiSessionRecord.id == command.session_id).with_for_update()
            ).first()
            if (
                session_record is None
                or session_record.revoked_at is not None
                or session_record.expires_at < now.timestamp()
                or not session_record.actor
            ):
                raise AppError("UI_SESSION_REQUIRED", "UI session is expired, revoked, or unknown", 403)
            workflow_record = session.scalars(
                select(WorkflowRecord).where(WorkflowRecord.id == command.workflow_id).with_for_update()
            ).first()
            if workflow_record is None:
                raise AppError("NOT_FOUND", "workflow not found", 404)
            if workflow_record.row_version != command.expected_version:
                raise AppError("VERSION_CONFLICT", "workflow changed; reload and retry", 409)
            nonce_id = f"NON-{secrets.token_hex(16)}"
            nonce_hash = hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
            expires_at = now.timestamp() + 600
            session.add(
                UiNonceRecord(
                    id=nonce_id,
                    session_id=session_record.id,
                    workflow_id=workflow_record.id,
                    expected_version=str(command.expected_version),
                    operation=operation,
                    nonce_hash=nonce_hash,
                    expires_at=expires_at,
                    used_at=None,
                    context_id=workflow_record.context_id,
                    work_package_id=workflow_record.work_package_id,
                    issued_at=now.timestamp(),
                )
            )
        return CompletionAuthorizationResult(
            nonce_id=nonce_id,
            nonce_hash=nonce_hash,
            session_id=session_record.id,
            workflow_id=workflow_record.id,
            expected_version=command.expected_version,
            operation=operation,
            expires_at=expires_at,
            context_id=workflow_record.context_id,
            work_package_id=workflow_record.work_package_id,
        )

    def session_actor(self, session_id: str) -> tuple[str, str]:
        with self._unit_of_work.session() as session:
            record = session.get(UiSessionRecord, session_id)
            if record is None or not record.actor:
                raise AppError("UI_SESSION_REQUIRED", "session actor is unavailable", 403)
            return record.actor, record.display_label or record.actor

    def set_workflow_completion(
        self,
        command: WorkflowCompletionCommand,
        workflow: ContextWorkflow,
        event: WorkflowCompletionEvent,
        audit: OperationAuditEvent,
    ) -> WorkflowCompletionResult:
        operation = "complete" if command.completed else "cancel"
        with self._unit_of_work.session() as session:
            workflow_record = session.scalars(
                select(WorkflowRecord).where(WorkflowRecord.id == command.workflow_id).with_for_update()
            ).first()
            if workflow_record is None:
                raise AppError("NOT_FOUND", "workflow not found", 404)
            if workflow_record.row_version != command.expected_version:
                raise AppError("VERSION_CONFLICT", "workflow changed; reload and retry", 409)
            session_record = session.scalars(
                select(UiSessionRecord).where(UiSessionRecord.id == command.session_id).with_for_update()
            ).first()
            if (
                session_record is None
                or session_record.revoked_at is not None
                or session_record.expires_at < _unix_now()
                or not session_record.actor
            ):
                raise AppError("UI_SESSION_REQUIRED", "session is expired or revoked", 403)

            nonce = session.scalars(
                select(UiNonceRecord).where(UiNonceRecord.id == command.nonce_id).with_for_update()
            ).first()
            if nonce is None:
                raise AppError("COMPLETION_NONCE_INVALID", "completion nonce is unknown", 403)
            if nonce.used_at is not None:
                raise AppError("COMPLETION_NONCE_REPLAYED", "completion nonce was already consumed", 403)
            if nonce.expires_at < _unix_now():
                raise AppError("COMPLETION_NONCE_EXPIRED", "COMPLETION_NONCE_EXPIRED: completion nonce is expired", 403)
            if (
                nonce.session_id != command.session_id
                or nonce.workflow_id != command.workflow_id
                or nonce.expected_version != str(command.expected_version)
                or nonce.operation != operation
                or nonce.nonce_hash != command.nonce_hash
                or nonce.context_id != workflow_record.context_id
                or nonce.work_package_id != workflow_record.work_package_id
            ):
                raise AppError("COMPLETION_NONCE_BINDING_MISMATCH", "completion nonce binding does not match", 403)
            nonce.used_at = _unix_now()
            nonce.consume_request_id = audit.request_id

            if workflow_record.is_completed == command.completed:
                return WorkflowCompletionResult(
                    workflow=_workflow_from_record(workflow_record),
                    idempotent=True,
                    has_achievement_cards=_has_cards(session, command.workflow_id),
                )
            updated = session.execute(
                update(WorkflowRecord)
                .where(
                    WorkflowRecord.id == command.workflow_id,
                    WorkflowRecord.row_version == command.expected_version,
                )
                .values(
                    is_completed=command.completed,
                    completed_at=event.created_at if command.completed else None,
                    completed_by=session_record.actor if command.completed else None,
                    completion_row_version=workflow_record.completion_row_version + 1,
                    row_version=workflow_record.row_version + 1,
                )
            )
            if int(getattr(updated, "rowcount", 0)) != 1:
                raise AppError("VERSION_CONFLICT", "workflow changed; reload and retry", 409)
            session.add(_workflow_completion_event_record(event, nonce.expires_at))
            session.add(_operation_audit_record(audit))
            session.flush()
            session.refresh(workflow_record)
            return WorkflowCompletionResult(
                workflow=_workflow_from_record(workflow_record),
                idempotent=False,
                has_achievement_cards=_has_cards(session, command.workflow_id),
            )


def _disclosure_from_record(record: ContextDisclosurePreferenceRecord) -> ContextDisclosurePreference:
    return ContextDisclosurePreference(
        context_id=record.context_id,
        disclosure_kind=record.disclosure_kind,
        stable_subject_id=record.stable_subject_id,
        is_expanded=record.is_expanded,
        row_version=record.row_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _validate_disclosure_subject(session: Session, command: DisclosurePreferenceUpsertCommand) -> None:
    if command.disclosure_kind == "progress":
        if command.stable_subject_id != "context-progress":
            raise AppError("OWNERSHIP_MISMATCH", "invalid progress disclosure subject", 404)
        return
    if command.disclosure_kind == "directory":
        if command.stable_subject_id != "context-directory":
            raise AppError("OWNERSHIP_MISMATCH", "invalid directory disclosure subject", 404)
        return
    if command.disclosure_kind == "area":
        exists: Any | None = session.execute(
            select(WorkflowRecord.area_id).where(
                WorkflowRecord.context_id == command.context_id,
                WorkflowRecord.area_id == command.stable_subject_id,
            )
        ).first()
    elif command.disclosure_kind == "work_package":
        exists = session.execute(
            select(WorkflowRecord.id).where(
                WorkflowRecord.context_id == command.context_id,
                WorkflowRecord.work_package_id == command.stable_subject_id,
            )
        ).first()
    else:
        exists = session.execute(
            select(AchievementCardRecord.id).where(
                AchievementCardRecord.context_id == command.context_id,
                AchievementCardRecord.id == command.stable_subject_id,
            )
        ).first()
    if exists is None:
        raise AppError("OWNERSHIP_MISMATCH", "disclosure subject is not owned by the Context", 404)


def _disclosure_audit(
    command: DisclosurePreferenceUpsertCommand,
    record: ContextDisclosurePreferenceRecord,
    timestamp: datetime,
) -> OperationAuditEvent:
    identity = f"{command.local_user_key}:{command.context_id}:{command.disclosure_kind}:{command.stable_subject_id}"
    summary_json = {
        "disclosure_kind": command.disclosure_kind,
        "stable_subject_id": command.stable_subject_id,
        "is_expanded": command.requested_is_expanded,
        "row_version": record.row_version,
    }
    summary = json.dumps(summary_json, ensure_ascii=False, sort_keys=True)
    idempotency_key = f"disclosure:{identity}:{record.row_version}"
    request_id = hashlib.sha256(f"REQ:{idempotency_key}".encode()).hexdigest()[:32]
    operation_id = f"AUD-{hashlib.sha256(f'{idempotency_key}:{timestamp.isoformat()}'.encode()).hexdigest()[:24]}"
    digest_input = {
        "operation_id": operation_id,
        "context_id": command.context_id,
        "action": "context.disclosure-preference",
        "target_type": "context_disclosure_preference",
        "target_id": f"{command.context_id}:{command.disclosure_kind}:{command.stable_subject_id}",
        "result": "SUCCESS",
        "error_code": None,
        "summary": summary,
    }
    return OperationAuditEvent(
        operation_id=operation_id,
        request_id=request_id,
        idempotency_key=idempotency_key,
        context_id=command.context_id,
        actor=command.local_user_key,
        display_label=command.local_user_key,
        action="context.disclosure-preference",
        target_type="context_disclosure_preference",
        target_id=f"{command.context_id}:{command.disclosure_kind}:{command.stable_subject_id}",
        result="SUCCESS",
        error_code=None,
        summary=summary,
        summary_json=summary_json,
        schema_version=4,
        occurred_at=timestamp,
        content_digest=hashlib.sha256(
            json.dumps(digest_input, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
    )


def _context_record(context: ResearchContext) -> ContextRecord:
    return ContextRecord(
        id=context.id,
        type=context.type,
        name=context.name,
        problem=context.problem,
        goal=context.goal,
        owner=context.owner,
        created_at=context.created_at,
        row_version=context.row_version,
        lifecycle_state=context.lifecycle_state,
    )


def _context_from_record(record: ContextRecord) -> ResearchContext:
    return ResearchContext(
        id=record.id,
        type=record.type,
        name=record.name,
        problem=record.problem,
        goal=record.goal,
        owner=record.owner,
        created_at=record.created_at,
        row_version=record.row_version,
        lifecycle_state=record.lifecycle_state,
    )


def _workflow_record(workflow: ContextWorkflow) -> WorkflowRecord:
    return WorkflowRecord(
        id=workflow.id,
        context_id=workflow.context_id,
        work_package_id=workflow.work_package_id,
        status=workflow.status,
        created_at=workflow.created_at,
        is_completed=workflow.is_completed,
        completion_row_version=workflow.completion_row_version,
        completed_at=workflow.completed_at,
        completed_by=workflow.completed_by,
        area_id=workflow.area_id,
        template_id=workflow.template_id,
        skill_id=workflow.skill_id,
        selection_status=workflow.selection_status,
        selection_reason=workflow.selection_reason,
        author_confirmed=workflow.author_confirmed,
        mode=workflow.mode,
        row_version=workflow.row_version,
        archived=workflow.archived,
        inputs_json=workflow.inputs_json,
    )


def _workflow_from_record(record: WorkflowRecord) -> ContextWorkflow:
    return ContextWorkflow(
        id=record.id,
        context_id=record.context_id,
        work_package_id=record.work_package_id,
        status=record.status,
        created_at=record.created_at,
        is_completed=record.is_completed,
        completion_row_version=record.completion_row_version,
        completed_at=record.completed_at,
        completed_by=record.completed_by,
        area_id=record.area_id,
        template_id=record.template_id,
        skill_id=record.skill_id,
        selection_status=record.selection_status,
        selection_reason=record.selection_reason,
        author_confirmed=record.author_confirmed,
        mode=record.mode,
        row_version=record.row_version,
        archived=record.archived,
        inputs_json=record.inputs_json,
    )


def _canonical_digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _deletion_manifest(
    context_id: str,
    context_name: str,
    expected_version: int,
    session: Session,
) -> dict[str, Any]:
    workflows = session.scalars(
        select(WorkflowRecord).where(WorkflowRecord.context_id == context_id).order_by(WorkflowRecord.id)
    ).all()
    cards = session.scalars(
        select(AchievementCardRecord)
        .where(AchievementCardRecord.context_id == context_id)
        .order_by(AchievementCardRecord.id)
    ).all()
    card_ids = [card.id for card in cards]
    attachments = []
    if card_ids:
        records = session.scalars(
            select(AchievementAttachmentRecord)
            .where(AchievementAttachmentRecord.card_id.in_(card_ids))
            .order_by(AchievementAttachmentRecord.id)
        ).all()
        attachments = [
            {
                "id": record.id,
                "card_id": record.card_id,
                "original_name": record.original_name,
                "relative_path": record.relative_path,
                "size_bytes": record.size_bytes,
                "sha256": record.sha256,
            }
            for record in records
        ]
    workflow_ids = [workflow.id for workflow in workflows]
    counts: dict[str, int] = {
        "workflows": len(workflows),
        "achievement_cards": len(cards),
        "achievement_attachments": len(attachments),
        "workflow_events": int(
            session.execute(
                select(func.count())
                .select_from(WorkflowEventRecord)
                .where(WorkflowEventRecord.workflow_id.in_(workflow_ids or [""]))
            ).scalar_one()
        ),
        "workflow_completion_events": int(
            session.execute(
                select(func.count())
                .select_from(WorkflowCompletionEventRecord)
                .where(WorkflowCompletionEventRecord.context_id == context_id)
            ).scalar_one()
        ),
        "achievement_card_events": int(
            session.execute(
                select(func.count())
                .select_from(AchievementCardEventRecord)
                .where(AchievementCardEventRecord.context_id == context_id)
            ).scalar_one()
        ),
        "context_disclosure_preferences": int(
            session.execute(
                select(func.count())
                .select_from(ContextDisclosurePreferenceRecord)
                .where(ContextDisclosurePreferenceRecord.context_id == context_id)
            ).scalar_one()
        ),
        "artifacts": int(
            session.execute(
                select(func.count()).select_from(ArtifactRecord).where(ArtifactRecord.context_id == context_id)
            ).scalar_one()
        ),
    }
    return {
        "manifest_version": 1,
        "context_id": context_id,
        "context_name": context_name,
        "expected_version": expected_version,
        "entity_counts": counts,
        "attachments": attachments,
    }


def _saga_audit(
    *,
    context_id: str,
    actor: str,
    action: str,
    target_id: str,
    retain: bool,
    attachment_count: int,
    operation_id: str,
    timestamp: datetime,
) -> OperationAuditEvent:
    idempotency_key = f"context.delete:{operation_id}"
    summary_json = {"retain_files": retain, "attachment_count": attachment_count}
    summary = json.dumps(summary_json, ensure_ascii=False, sort_keys=True)
    content = json.dumps(
        {
            "request_id": f"REQ-{operation_id}",
            "idempotency_key": idempotency_key,
            "context_id": context_id,
            "actor": actor,
            "action": action,
            "target_type": "context",
            "target_id": target_id,
            "result": "SUCCESS",
            "summary": summary_json,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return OperationAuditEvent(
        operation_id=f"AUD-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]}",
        request_id=f"REQ-{operation_id}",
        idempotency_key=idempotency_key,
        context_id=context_id,
        actor=actor,
        display_label=actor,
        action=action,
        target_type="context",
        target_id=target_id,
        result="SUCCESS",
        error_code=None,
        summary=summary,
        summary_json=summary_json,
        schema_version=4,
        occurred_at=timestamp,
        content_digest=hashlib.sha256(content.encode()).hexdigest(),
    )


def _operation_audit_record(event: OperationAuditEvent) -> OperationAuditRecord:
    return OperationAuditRecord(
        operation_id=event.operation_id,
        request_id=event.request_id,
        idempotency_key=event.idempotency_key,
        context_id=event.context_id,
        actor=event.actor,
        display_label=event.display_label,
        action=event.action,
        target_type=event.target_type,
        target_id=event.target_id,
        result=event.result,
        error_code=event.error_code,
        summary=event.summary,
        summary_json=event.summary_json,
        schema_version=event.schema_version,
        occurred_at=event.occurred_at,
        content_digest=event.content_digest,
    )


def _card_record(card: AchievementCard) -> AchievementCardRecord:
    return AchievementCardRecord(
        id=card.id,
        context_id=card.context_id,
        workflow_id=card.workflow_id,
        work_package_id=card.work_package_id,
        event_date=card.event_date,
        event_name=card.event_name,
        description=card.description,
        status=card.status,
        row_version=card.row_version,
        created_at=card.created_at,
        updated_at=card.updated_at,
        week_item_id=card.week_item_id,
        is_important=card.is_important,
    )


def _card_event_record(event: AchievementCardEvent) -> AchievementCardEventRecord:
    return AchievementCardEventRecord(
        id=event.id,
        card_id=event.card_id,
        actor=event.actor,
        command=event.command,
        payload=event.payload,
        created_at=event.created_at,
        context_id=event.context_id,
        workflow_id=event.workflow_id,
        work_package_id=event.work_package_id,
        week_item_id=None,
        attachment_id=None,
        event_type=event.event_type,
    )


def _card_from_record(record: AchievementCardRecord, attachments: tuple[dict[str, Any], ...]) -> AchievementCard:
    return AchievementCard(
        id=record.id,
        context_id=record.context_id,
        workflow_id=record.workflow_id,
        work_package_id=record.work_package_id,
        week_item_id=record.week_item_id,
        event_date=record.event_date,
        event_name=record.event_name,
        description=record.description,
        status=record.status,
        is_important=record.is_important,
        row_version=record.row_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        attachments=attachments,
    )


def _attachments(session: Session, card_id: str) -> tuple[dict[str, Any], ...]:
    records = session.scalars(
        select(AchievementAttachmentRecord)
        .where(AchievementAttachmentRecord.card_id == card_id)
        .order_by(AchievementAttachmentRecord.created_at)
    ).all()
    return tuple(_attachment_value(record) for record in records)


def _attachment_value(record: AchievementAttachmentRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "card_id": record.card_id,
        "original_name": record.original_name,
        "storage_name": record.storage_name,
        "relative_path": record.relative_path,
        "mime_type": record.mime_type,
        "size_bytes": record.size_bytes,
        "sha256": record.sha256,
        "preview_state": record.preview_state,
        "created_at": _iso(record.created_at),
        "preview_error": record.preview_error,
        "settings_version": record.settings_version,
        "row_version": record.row_version,
        "path_schema_version": record.path_schema_version,
        "original_name_key": record.original_name_key,
        "area_name_snapshot": record.area_name_snapshot,
        "work_package_name_snapshot": record.work_package_name_snapshot,
        "event_folder_snapshot": record.event_folder_snapshot,
        "before_size_bytes": record.before_size_bytes,
        "before_sha256": record.before_sha256,
        "after_size_bytes": record.after_size_bytes,
        "after_sha256": record.after_sha256,
        "staging_path": record.staging_path,
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _workflow_event_record(event: WorkflowEvent) -> WorkflowEventRecord:
    return WorkflowEventRecord(
        id=event.id,
        workflow_id=event.workflow_id,
        command=event.command,
        payload=event.payload,
        created_at=event.created_at,
    )


def _workflow_completion_event_record(
    event: WorkflowCompletionEvent, authorization_expires_at: float
) -> WorkflowCompletionEventRecord:
    return WorkflowCompletionEventRecord(
        id=event.id,
        workflow_id=event.workflow_id,
        actor=event.actor,
        from_status=event.from_status,
        to_status=event.to_status,
        created_at=event.created_at,
        context_id=event.context_id,
        work_package_id=event.work_package_id,
        row_version=event.row_version,
        actor_kind=event.actor_kind,
        version_before=event.version_before,
        version_after=event.version_after,
        idempotency_key=event.idempotency_key,
        authorization_source=event.authorization_source,
        nonce_id=event.nonce_id,
        nonce_hash=event.nonce_hash,
        operation=event.operation,
        authorization_expires_at=authorization_expires_at,
        display_label=event.display_label,
    )


def _has_cards(session: Session, workflow_id: str) -> bool:
    return (
        session.execute(
            select(func.count())
            .select_from(AchievementCardRecord)
            .where(
                AchievementCardRecord.workflow_id == workflow_id,
                AchievementCardRecord.status == "Active",
            )
        ).scalar_one()
        > 0
    )


_DEFAULT_UPLOAD_SETTINGS = UploadSettings(
    max_file_bytes=104_857_600,
    max_attachments_per_card=20,
    allowed_extensions=(
        ".pptx",
        ".docx",
        ".pdf",
        ".md",
        ".markdown",
        ".ppt",
        ".doc",
        ".zip",
        ".7z",
        ".rar",
    ),
    version=1,
)


def _markdown_url(value: str) -> str | None:
    candidate = value.strip()
    if not candidate or any(character.isspace() for character in candidate):
        return None
    lowered = candidate.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:")):
        return None
    if lowered.startswith(("http://", "https://", "mailto:", "/", "#")):
        return candidate
    return None


def _inline_markdown(value: str) -> str:
    escaped = html.escape(value, quote=False)
    code_fragments: list[str] = []

    def capture_code(match: re.Match[str]) -> str:
        code_fragments.append(match.group(1))
        return f"\x00MDCODE{len(code_fragments) - 1}\x00"

    escaped = re.sub(r"`([^`]+)`", capture_code, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        url = _markdown_url(html.unescape(match.group(2)))
        if url is None:
            return match.group(0)
        safe_url = html.escape(url, quote=True)
        return f'<a href="{safe_url}" rel="noopener noreferrer">{label}</a>'

    escaped = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", replace_link, escaped)
    return re.sub(
        r"\x00MDCODE(\d+)\x00",
        lambda match: f"<code>{code_fragments[int(match.group(1))]}</code>",
        escaped,
    )


def _render_markdown(value: str) -> str:
    """Render a safe subset of Markdown without allowing raw HTML."""

    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            blocks.append("<pre><code>" + html.escape("\n".join(code), quote=False) + "</code></pre>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = min(len(heading.group(1)) + 1, 6)
            blocks.append(f"<h{level}>{_inline_markdown(heading.group(2))}</h{level}>")
            index += 1
            continue
        if re.fullmatch(r"(-{3,}|\*{3,})", stripped):
            blocks.append("<hr>")
            index += 1
            continue
        if stripped.startswith(">"):
            quote: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote.append(lines[index].strip().lstrip(">").strip())
                index += 1
            blocks.append(f"<blockquote><p>{_inline_markdown(' '.join(quote))}</p></blockquote>")
            continue
        if re.match(r"^[-*+]\s+", stripped):
            items: list[str] = []
            while index < len(lines) and re.match(r"^[-*+]\s+", lines[index].strip()):
                items.append(f"<li>{_inline_markdown(re.sub(r'^[-*+]\s+', '', lines[index].strip()))}</li>")
                index += 1
            blocks.append(f"<ul>{''.join(items)}</ul>")
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            items = []
            while index < len(lines) and re.match(r"^\d+[.)]\s+", lines[index].strip()):
                items.append(f"<li>{_inline_markdown(re.sub(r'^\d+[.)]\s+', '', lines[index].strip()))}</li>")
                index += 1
            blocks.append(f"<ol>{''.join(items)}</ol>")
            continue
        paragraph: list[str] = []
        while (
            index < len(lines)
            and lines[index].strip()
            and not re.match(r"^(#{1,6}\s|```|>|[-*+]\s|\d+[.)]\s)", lines[index].strip())
        ):
            paragraph.append(lines[index].strip())
            index += 1
        blocks.append(f"<p>{_inline_markdown(' '.join(paragraph))}</p>")
    return '<article class="markdown-body">' + "".join(blocks) + "</article>"


def _preview_document(filename: str, body: str) -> str:
    return (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<style>body{margin:0;background:#fff;color:#17212b;"
        'font:16px/1.7 "Segoe UI","Microsoft YaHei",system-ui,sans-serif}'
        ".markdown-body{box-sizing:border-box;max-width:960px;margin:0 auto;padding:28px;"
        "overflow-wrap:anywhere}.markdown-body h1,.markdown-body h2,.markdown-body h3{color:#173b57;"
        "line-height:1.25}.markdown-body pre{padding:14px;background:#f6f8fa;border-radius:8px;"
        "overflow:auto}.markdown-body code{background:#f6f8fa;padding:2px 5px;border-radius:4px}"
        ".markdown-body blockquote{margin:0;padding:10px 14px;border-left:4px solid #c9dfe8;"
        "background:#f8fbfd}</style>"
        f"<title>{html.escape(filename)}</title><body>{body}</body></html>"
    )


def _attachment_domain(record: AchievementAttachmentRecord) -> AchievementAttachment:
    return AchievementAttachment(
        id=record.id,
        card_id=record.card_id,
        original_name=record.original_name,
        storage_name=record.storage_name,
        relative_path=record.relative_path,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
        preview_state=record.preview_state,
        created_at=record.created_at,
        preview_error=record.preview_error,
        settings_version=record.settings_version,
        row_version=record.row_version,
        path_schema_version=record.path_schema_version,
        original_name_key=record.original_name_key,
        area_name_snapshot=record.area_name_snapshot,
        work_package_name_snapshot=record.work_package_name_snapshot,
        event_folder_snapshot=record.event_folder_snapshot,
        before_size_bytes=record.before_size_bytes,
        before_sha256=record.before_sha256,
        after_size_bytes=record.after_size_bytes,
        after_sha256=record.after_sha256,
        staging_path=record.staging_path,
    )


def _outbox_id(attachment_id: str) -> str:
    digest = hashlib.sha256(attachment_id.encode()).hexdigest()[:12]
    return f"OUT-{digest}"


def _unix_now() -> float:
    return datetime.now(UTC).timestamp()


__all__ = ["PostgresContextRepository"]
