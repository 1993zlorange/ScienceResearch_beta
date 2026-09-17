"""Target v1 context, workflow, and achievement card routes."""

from __future__ import annotations

from io import BytesIO
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import JsonValue
from werkzeug.formparser import parse_form_data

from ...application.context import ContextUseCase
from ...domain.context import (
    AchievementAttachment,
    AchievementCard,
    AchievementCardCreateCommand,
    AchievementCardDeleteCommand,
    AchievementCardImportanceCommand,
    AchievementCardUpdateCommand,
    AttachmentUploadCommand,
    CompletionAuthorizationCommand,
    ContextCreateCommand,
    ContextDeletionCommitCommand,
    ContextDeletionPrepareCommand,
    ContextWorkflow,
    DisclosurePreferenceUpsertCommand,
    UiSessionIssueCommand,
    WorkflowCompletionCommand,
    WorkflowSelectionCommand,
)
from ...domain.errors import AppError
from ..dto.context import (
    AchievementAttachmentDTO,
    AchievementAttachmentMetadataDTO,
    AchievementCardCreateDTO,
    AchievementCardDeleteDTO,
    AchievementCardDTO,
    AchievementCardImportanceDTO,
    AchievementCardUpdateDTO,
    CardDeleteResultDTO,
    CardImportanceResultDTO,
    CompletionAuthorizationDTO,
    CompletionAuthorizationResultDTO,
    ContextCreateDTO,
    ContextDeletionCommitDTO,
    ContextDeletionCommitResultDTO,
    ContextDeletionPrepareDTO,
    ContextDeletionPrepareResultDTO,
    ContextDTO,
    ContextListDTO,
    CreatedContextDTO,
    DisclosurePreferenceDTO,
    DisclosurePreferenceListDTO,
    DisclosurePreferenceUpsertDTO,
    ProgressDTO,
    UiSessionIssueDTO,
    UiSessionIssueResultDTO,
    WorkflowCompletionDTO,
    WorkflowCompletionResultDTO,
    WorkflowDTO,
    WorkflowListDTO,
    WorkflowRecordDTO,
    WorkflowSelectionDTO,
)

router = APIRouter(tags=["contexts", "workflows", "achievement cards"])


def error_response(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {"application/problem+json": {"schema": {"$ref": "#/components/schemas/APIErrorDTO"}}},
    }


CONTEXT_LIST_ERRORS: dict[int | str, dict[str, Any]] = {
    503: error_response("Context database dependency is unavailable")
}
CONTEXT_DETAIL_ERRORS: dict[int | str, dict[str, Any]] = {
    404: error_response("Context does not exist"),
    503: error_response("Context database dependency is unavailable"),
}
CONTEXT_CREATE_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    422: error_response("Context input is invalid"),
    503: error_response("Context database dependency is unavailable"),
}
DISCLOSURE_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    404: error_response("Context or disclosure subject does not exist"),
    409: error_response("Disclosure preference version changed"),
    422: error_response("Disclosure input is invalid"),
    503: error_response("Disclosure database dependency is unavailable"),
}
UI_SESSION_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    422: error_response("UI session input is invalid"),
    503: error_response("UI session database dependency is unavailable"),
}
COMPLETION_AUTHORIZATION_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    403: error_response("UI session is invalid"),
    404: error_response("Workflow does not exist"),
    409: error_response("Workflow version changed"),
    422: error_response("Completion authorization input is invalid"),
    503: error_response("Workflow authorization database dependency is unavailable"),
}
WORKFLOW_LIST_ERRORS: dict[int | str, dict[str, Any]] = {
    404: error_response("Context does not exist"),
    503: error_response("Workflow database dependency is unavailable"),
}
CARD_CREATE_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    404: error_response("Workflow does not exist"),
    409: error_response("Workflow ownership or week item binding conflicts"),
    422: error_response("Achievement card input is invalid"),
    503: error_response("Achievement card database dependency is unavailable"),
}

CARD_UPDATE_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    404: error_response("Achievement card does not exist"),
    409: error_response("Achievement card version changed"),
    422: error_response("Achievement card input is invalid"),
    503: error_response("Achievement card database dependency is unavailable"),
}
CARD_IMPORTANCE_ERRORS: dict[int | str, dict[str, Any]] = {
    404: error_response("Card or owning context and workflow does not exist"),
    409: error_response("Achievement card version changed"),
    422: error_response("Importance input is invalid"),
    503: error_response("Achievement card database dependency is unavailable"),
}
CARD_DELETE_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    404: error_response("Achievement card does not exist"),
    409: error_response("Delete confirmation or card version conflicts"),
    422: error_response("Delete input is invalid"),
    503: error_response("Achievement card database dependency is unavailable"),
}
WORKFLOW_SELECTION_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    404: error_response("Work package or workflow does not exist"),
    409: error_response("Workflow version changed"),
    422: error_response("Selection status or author confirmation is invalid"),
    503: error_response("Workflow database dependency is unavailable"),
}
ATTACHMENT_UPLOAD_ERRORS: dict[int | str, dict[str, Any]] = {
    404: error_response("Achievement card does not exist"),
    409: error_response("Attachment filename or deleted-card state conflicts"),
    422: error_response("Attachment file exceeds limits or fails validation"),
    503: error_response("Attachment database dependency is unavailable"),
}
ATTACHMENT_DETAIL_ERRORS: dict[int | str, dict[str, Any]] = {
    404: error_response("Attachment or artifact file does not exist"),
    409: error_response("Attachment integrity verification failed"),
    503: error_response("Attachment database dependency is unavailable"),
}
ATTACHMENT_PREVIEW_ERRORS: dict[int | str, dict[str, Any]] = {
    404: error_response("Attachment or preview artifact does not exist"),
    409: error_response("Attachment integrity verification failed"),
    422: error_response("Attachment preview is unavailable"),
    503: error_response("Attachment database dependency is unavailable"),
}
CONTEXT_DELETION_PREPARE_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    404: error_response("Context does not exist"),
    409: error_response("Context version changed or a deletion is already active"),
    422: error_response("Deletion preparation input is invalid"),
    503: error_response("Deletion database dependency is unavailable"),
}
CONTEXT_DELETION_COMMIT_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    403: error_response("Deletion ticket is invalid or bound to another session"),
    404: error_response("Context or deletion operation does not exist"),
    409: error_response("Deletion ticket expired, was replayed, or conflict requires preparation again"),
    503: error_response("Deletion database or artifact dependency is unavailable"),
}
WORKFLOW_COMPLETION_ERRORS: dict[int | str, dict[str, Any]] = {
    400: error_response("Request body is not a JSON object"),
    403: error_response("UI session or completion nonce is invalid"),
    404: error_response("Workflow does not exist"),
    409: error_response("Workflow version changed"),
    422: error_response("Completion input is invalid"),
    503: error_response("Workflow database dependency is unavailable"),
}


def context_use_case(request: Request) -> ContextUseCase:
    use_case: ContextUseCase | None = getattr(request.app.state, "context_use_case", None)
    if use_case is None:
        raise AppError("SERVICE_UNAVAILABLE", "native context API is not configured", 503)
    return use_case


ContextUseCaseDependency = Annotated[ContextUseCase, Depends(context_use_case)]


async def json_object(request: Request) -> dict[str, JsonValue]:
    """Mirror the legacy silent-JSON behavior for malformed request bodies."""
    try:
        payload = await request.json()
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError("INVALID_INPUT", "JSON object is required", 400) from exc
    if not isinstance(payload, dict):
        raise AppError("INVALID_INPUT", "JSON object is required", 400)
    return payload


def text(value: JsonValue) -> str:
    """Preserve legacy ``str(payload.get(...))`` coercion behavior."""
    return str(value)


def boolean(value: JsonValue) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "on"})


def integer(value: JsonValue, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise AppError("INVALID_INPUT", f"{field} must be a positive integer")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise AppError("INVALID_INPUT", f"{field} must be a positive integer") from exc
    return parsed


def request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) and value else ""


def attachment_dto(attachment: AchievementAttachment) -> AchievementAttachmentDTO:
    return AchievementAttachmentDTO.model_validate(attachment, from_attributes=True)


def file_response(content: bytes, media_type: str, filename: str, disposition: str) -> Response:
    fallback = "attachment" if disposition == "attachment" else "preview"
    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{fallback}\"; filename*=utf-8''{quote(filename)}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/api/v1/achievement-cards/{card_id}/attachments",
    status_code=status.HTTP_201_CREATED,
    response_model=AchievementAttachmentDTO,
    responses=ATTACHMENT_UPLOAD_ERRORS,
)
async def upload_achievement_attachment(
    card_id: str,
    request: Request,
    use_case: ContextUseCaseDependency,
) -> AchievementAttachmentDTO:
    body = await request.body()
    environ = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": request.headers.get("content-type", ""),
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
        "wsgi.errors": BytesIO(),
    }
    try:
        _, form, files = parse_form_data(environ, max_form_memory_size=128 * 1024 * 1024)
    except (ValueError, OSError) as exc:
        raise AppError("INVALID_ATTACHMENT_UPLOAD", "multipart attachment upload is invalid", 422) from exc
    upload = files.get("file")
    if upload is None:
        raise AppError("ATTACHMENT_FILE_REQUIRED", "multipart file field is required", 422)
    attachment = use_case.upload_achievement_attachment(
        AttachmentUploadCommand(
            card_id=card_id,
            original_name=upload.filename or "",
            mime_type=upload.mimetype,
            content=upload.read(),
            actor=(form.get("actor") or "author").strip() or "author",
            request_id=(form.get("request_id") or "").strip() or None,
            idempotency_key=(form.get("idempotency_key") or "").strip() or None,
        )
    )
    return attachment_dto(attachment)


@router.get(
    "/api/v1/achievement-attachments/{attachment_id}",
    response_model=AchievementAttachmentDTO,
    responses=ATTACHMENT_DETAIL_ERRORS,
)
def achievement_attachment_detail(
    attachment_id: str,
    use_case: ContextUseCaseDependency,
) -> AchievementAttachmentDTO:
    return attachment_dto(use_case.achievement_attachment(attachment_id))


@router.get(
    "/api/v1/achievement-attachments/{attachment_id}/download",
    responses=ATTACHMENT_DETAIL_ERRORS,
)
def download_achievement_attachment(
    attachment_id: str,
    use_case: ContextUseCaseDependency,
) -> Response:
    content = use_case.download_achievement_attachment(attachment_id)
    return file_response(content.data, content.media_type, content.filename, content.disposition)


@router.get(
    "/api/v1/achievement-attachments/{attachment_id}/preview",
    responses=ATTACHMENT_PREVIEW_ERRORS,
)
def preview_achievement_attachment(
    attachment_id: str,
    use_case: ContextUseCaseDependency,
    representation: Annotated[str, Query()] = "document",
) -> Response:
    result = use_case.preview_achievement_attachment(attachment_id, representation)
    if representation == "metadata":
        payload = AchievementAttachmentMetadataDTO(
            attachment=attachment_dto(result.attachment),
            representation=result.representation,
            preview_url=f"/api/v1/achievement-attachments/{quote(attachment_id, safe='')}/preview",
            download_url=f"/api/v1/achievement-attachments/{quote(attachment_id, safe='')}/download",
        )
        return JSONResponse(payload.model_dump(mode="json"), headers={"X-Content-Type-Options": "nosniff"})
    return file_response(
        result.content.data,
        result.content.media_type,
        result.content.filename,
        result.content.disposition,
    )


@router.get(
    "/api/v1/achievement-attachments/{attachment_id}/images/{index}",
    responses=ATTACHMENT_PREVIEW_ERRORS,
)
def achievement_attachment_image(
    attachment_id: str,
    index: int,
    use_case: ContextUseCaseDependency,
) -> Response:
    content = use_case.preview_achievement_attachment_image(attachment_id, index)
    return file_response(content.data, content.media_type, content.filename, content.disposition)


@router.post(
    "/api/v1/contexts/{context_id}/deletion/prepare",
    response_model=ContextDeletionPrepareResultDTO,
    responses=CONTEXT_DELETION_PREPARE_ERRORS,
)
def prepare_context_deletion(
    context_id: str,
    dto: ContextDeletionPrepareDTO,
    use_case: ContextUseCaseDependency,
) -> ContextDeletionPrepareResultDTO:
    result = use_case.prepare_context_deletion(
        ContextDeletionPrepareCommand(
            context_id=context_id,
            session_id=text(dto.session_id),
            retain_files=boolean(dto.retain_files),
            expected_version=integer(dto.expected_version, "expected_version"),
        )
    )
    return ContextDeletionPrepareResultDTO.model_validate(result, from_attributes=True)


@router.post(
    "/api/v1/contexts/{context_id}/deletion/commit",
    response_model=ContextDeletionCommitResultDTO,
    responses=CONTEXT_DELETION_COMMIT_ERRORS,
)
def commit_context_deletion(
    context_id: str,
    dto: ContextDeletionCommitDTO,
    use_case: ContextUseCaseDependency,
) -> ContextDeletionCommitResultDTO:
    result = use_case.commit_context_deletion(
        ContextDeletionCommitCommand(
            context_id=context_id,
            operation_id=text(dto.operation_id),
            confirmation=text(dto.confirmation),
            session_id=text(dto.session_id),
        )
    )
    return ContextDeletionCommitResultDTO.model_validate(result, from_attributes=True)


@router.get("/api/v1/contexts", response_model=ContextListDTO, responses=CONTEXT_LIST_ERRORS)
def list_contexts(use_case: ContextUseCaseDependency) -> ContextListDTO:
    return ContextListDTO(
        contexts=[ContextDTO.model_validate(context, from_attributes=True) for context in use_case.list_contexts()]
    )


@router.get("/api/v1/contexts/{context_id}", response_model=ContextDTO, responses=CONTEXT_DETAIL_ERRORS)
def context_detail(
    context_id: str,
    use_case: ContextUseCaseDependency,
) -> ContextDTO:
    return ContextDTO.model_validate(use_case.context(context_id), from_attributes=True)


@router.post(
    "/api/v1/contexts",
    response_model=CreatedContextDTO,
    status_code=status.HTTP_201_CREATED,
    responses=CONTEXT_CREATE_ERRORS,
)
async def create_context(
    request: Request,
    use_case: ContextUseCaseDependency,
) -> CreatedContextDTO:
    payload = await json_object(request)
    dto = ContextCreateDTO.model_validate(payload)
    context = use_case.create_context(
        ContextCreateCommand(
            type=text(dto.type),
            name=text(dto.name),
            problem=text(dto.problem),
            goal=text(dto.goal),
            owner=text(dto.owner),
        )
    )
    return CreatedContextDTO.model_validate(context, from_attributes=True)


@router.get(
    "/api/v1/contexts/{context_id}/disclosure-preferences",
    response_model=DisclosurePreferenceListDTO,
    responses=DISCLOSURE_ERRORS,
)
def get_disclosure_preferences(
    context_id: str,
    use_case: ContextUseCaseDependency,
) -> DisclosurePreferenceListDTO:
    local_user_key = "_local_author_v1"
    preferences = use_case.disclosure_preferences(context_id, local_user_key)
    return DisclosurePreferenceListDTO(
        context_id=context_id,
        local_user_key=local_user_key,
        preferences=[
            DisclosurePreferenceDTO.model_validate(preference, from_attributes=True) for preference in preferences
        ],
    )


@router.post(
    "/api/v1/contexts/{context_id}/disclosure-preferences",
    response_model=DisclosurePreferenceDTO,
    responses=DISCLOSURE_ERRORS,
)
async def upsert_disclosure_preference(
    request: Request,
    context_id: str,
    use_case: ContextUseCaseDependency,
) -> DisclosurePreferenceDTO:
    payload = await json_object(request)
    dto = DisclosurePreferenceUpsertDTO.model_validate(payload)
    preference = use_case.upsert_disclosure_preference(
        DisclosurePreferenceUpsertCommand(
            context_id=context_id,
            local_user_key=text(dto.local_user_key),
            disclosure_kind=text(dto.disclosure_kind),
            stable_subject_id=text(dto.stable_subject_id),
            requested_is_expanded=boolean(dto.requested_is_expanded),
            expected_version=integer(dto.expected_version, "expected_version"),
        )
    )
    return DisclosurePreferenceDTO.model_validate(preference, from_attributes=True)


@router.post(
    "/api/v1/ui/session",
    response_model=UiSessionIssueResultDTO,
    status_code=status.HTTP_201_CREATED,
    responses=UI_SESSION_ERRORS,
)
async def create_ui_session(
    request: Request,
    use_case: ContextUseCaseDependency,
) -> UiSessionIssueResultDTO:
    payload = await json_object(request)
    dto = UiSessionIssueDTO.model_validate(payload)
    result = use_case.create_ui_session(
        UiSessionIssueCommand(
            actor=text(dto.actor),
            display_label=None if dto.display_label is None else text(dto.display_label),
        )
    )
    return UiSessionIssueResultDTO.model_validate(result, from_attributes=True)


@router.post(
    "/api/v1/workflows/{workflow_id}/completion-authorization",
    response_model=CompletionAuthorizationResultDTO,
    status_code=status.HTTP_201_CREATED,
    responses=COMPLETION_AUTHORIZATION_ERRORS,
)
async def create_completion_authorization(
    request: Request,
    workflow_id: str,
    use_case: ContextUseCaseDependency,
) -> CompletionAuthorizationResultDTO:
    payload = await json_object(request)
    dto = CompletionAuthorizationDTO.model_validate(payload)
    result = use_case.issue_completion_authorization(
        CompletionAuthorizationCommand(
            workflow_id=workflow_id,
            expected_version=integer(dto.expected_version, "expected_version"),
            operation=text(dto.operation),
            session_id=text(dto.session_id),
        )
    )
    return CompletionAuthorizationResultDTO.model_validate(result, from_attributes=True)


@router.get("/api/v1/contexts/{context_id}/workflows", response_model=WorkflowListDTO, responses=WORKFLOW_LIST_ERRORS)
def context_workflows(
    context_id: str,
    use_case: ContextUseCaseDependency,
) -> WorkflowListDTO:
    result = use_case.workflows(context_id)
    workflows = [
        WorkflowDTO.model_validate(
            {
                **vars_without_cards(workflow),
                "achievement_cards": [card_value(card) for card in cards],
            }
        )
        for workflow, cards in result.workflows
    ]
    return WorkflowListDTO(
        workflows=workflows,
        progress=ProgressDTO.model_validate(result.progress),
    )


async def create_achievement_card_value(
    request: Request,
    use_case: ContextUseCaseDependency,
) -> AchievementCardDTO:
    payload = await json_object(request)
    dto = AchievementCardCreateDTO.model_validate(payload)
    card = use_case.create_achievement_card(
        AchievementCardCreateCommand(
            context_id=text(dto.context_id),
            workflow_id=text(dto.workflow_id),
            event_date=text(dto.event_date),
            event_name=text(dto.event_name),
            description=text(dto.description),
            actor=text(dto.actor),
            week_item_id=None if dto.week_item_id is None else text(dto.week_item_id),
            is_important=boolean(dto.important),
        )
    )
    return AchievementCardDTO.model_validate(card_value(card))


@router.post(
    "/api/v1/achievement-cards",
    response_model=AchievementCardDTO,
    status_code=status.HTTP_201_CREATED,
    responses=CARD_CREATE_ERRORS,
)
async def create_achievement_card(
    request: Request,
    use_case: ContextUseCaseDependency,
) -> AchievementCardDTO:
    return await create_achievement_card_value(request, use_case)


@router.post(
    "/api/achievement-cards",
    response_model=AchievementCardDTO,
    status_code=status.HTTP_201_CREATED,
    responses=CARD_CREATE_ERRORS,
)
async def create_achievement_card_compat(
    request: Request,
    use_case: ContextUseCaseDependency,
) -> AchievementCardDTO:
    return await create_achievement_card_value(request, use_case)


@router.put(
    "/api/v1/achievement-cards/{card_id}",
    response_model=AchievementCardDTO,
    responses=CARD_UPDATE_ERRORS,
)
async def update_achievement_card(
    dto: AchievementCardUpdateDTO,
    card_id: str,
    use_case: ContextUseCaseDependency,
) -> AchievementCardDTO:
    card = use_case.update_achievement_card(
        AchievementCardUpdateCommand(
            card_id=card_id,
            event_date=text(dto.event_date),
            event_name=text(dto.event_name),
            description=text(dto.description),
            expected_version=integer(dto.expected_version, "expected_version"),
            actor=text(dto.actor),
        )
    )
    return AchievementCardDTO.model_validate(card_value(card))


@router.patch(
    "/api/v1/contexts/{context_id}/workflows/{workflow_id}/achievement-cards/{card_id}/importance",
    response_model=CardImportanceResultDTO,
    responses=CARD_IMPORTANCE_ERRORS,
)
async def set_achievement_card_importance(
    request: Request,
    dto: AchievementCardImportanceDTO,
    context_id: str,
    workflow_id: str,
    card_id: str,
    use_case: ContextUseCaseDependency,
) -> CardImportanceResultDTO:
    result = use_case.set_achievement_card_importance(
        AchievementCardImportanceCommand(
            context_id=context_id,
            workflow_id=workflow_id,
            card_id=card_id,
            is_important=boolean(dto.is_important),
            expected_version=integer(dto.expected_version, "expected_version"),
            actor=text(dto.actor),
            idempotency_key=None if dto.idempotency_key is None else text(dto.idempotency_key),
            request_id=request_id(request),
            display_label=text(dto.actor),
        )
    )
    return CardImportanceResultDTO.model_validate(result, from_attributes=True)


@router.delete(
    "/api/v1/achievement-cards/{card_id}",
    response_model=CardDeleteResultDTO,
    responses=CARD_DELETE_ERRORS,
)
async def delete_achievement_card(
    dto: AchievementCardDeleteDTO,
    card_id: str,
    use_case: ContextUseCaseDependency,
) -> CardDeleteResultDTO:
    result = use_case.delete_achievement_card(
        AchievementCardDeleteCommand(
            card_id=card_id,
            actor=text(dto.actor),
            confirmation_token=None if dto.confirmation_token is None else text(dto.confirmation_token),
            expected_version=integer(dto.expected_version, "expected_version"),
        )
    )
    return CardDeleteResultDTO.model_validate(result, from_attributes=True)


@router.post(
    "/api/v1/contexts/{context_id}/workflow-selection",
    response_model=WorkflowRecordDTO,
    responses=WORKFLOW_SELECTION_ERRORS,
)
async def set_workflow_selection(
    dto: WorkflowSelectionDTO,
    context_id: str,
    use_case: ContextUseCaseDependency,
) -> WorkflowRecordDTO:
    workflow = use_case.set_workflow_selection(
        WorkflowSelectionCommand(
            context_id=context_id,
            work_package_id=text(dto.wp_id),
            selection_status=text(dto.selection_status),
            reason=None if dto.reason is None else text(dto.reason),
            author_confirmed=boolean(dto.author_confirmed),
            expected_version=integer(dto.expected_version, "expected_version"),
        )
    )
    return WorkflowRecordDTO.model_validate(vars_without_cards(workflow))


@router.post(
    "/api/v1/workflows/{workflow_id}/completion",
    response_model=WorkflowCompletionResultDTO,
    responses=WORKFLOW_COMPLETION_ERRORS,
)
async def set_workflow_completion(
    workflow_id: str,
    dto: WorkflowCompletionDTO,
    use_case: ContextUseCaseDependency,
) -> WorkflowCompletionResultDTO:
    result = use_case.set_workflow_completion(
        WorkflowCompletionCommand(
            workflow_id=workflow_id,
            completed=boolean(dto.completed),
            expected_version=integer(dto.expected_version, "expected_version"),
            session_id=text(dto.session_id),
            nonce_id=text(dto.nonce_id),
            nonce_hash=text(dto.nonce_hash),
            actor="author",
            idempotency_key=None if dto.idempotency_key is None else text(dto.idempotency_key),
        )
    )
    return WorkflowCompletionResultDTO.model_validate(
        {
            **vars_without_cards(result.workflow),
            "idempotent": result.idempotent,
            "has_achievement_cards": result.has_achievement_cards,
        }
    )


def vars_without_cards(workflow: ContextWorkflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "context_id": workflow.context_id,
        "work_package_id": workflow.work_package_id,
        "status": workflow.status,
        "created_at": workflow.created_at,
        "is_completed": workflow.is_completed,
        "completion_row_version": workflow.completion_row_version,
        "completed_at": workflow.completed_at,
        "completed_by": workflow.completed_by,
        "area_id": workflow.area_id,
        "template_id": workflow.template_id,
        "skill_id": workflow.skill_id,
        "selection_status": workflow.selection_status,
        "selection_reason": workflow.selection_reason,
        "author_confirmed": workflow.author_confirmed,
        "mode": workflow.mode,
        "row_version": workflow.row_version,
        "archived": workflow.archived,
        "inputs_json": workflow.inputs_json,
    }


def card_value(card: AchievementCard) -> dict[str, Any]:
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
        "attachments": [dict(attachment) for attachment in card.attachments],
    }
