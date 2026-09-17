from __future__ import annotations

from enum import StrEnum


class RunState(StrEnum):
    DRAFT = "Draft"
    PLANNED = "Planned"
    AWAITING_APPROVAL = "AwaitingApproval"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    PARTIAL = "Partial"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    INTERRUPTED = "Interrupted"


class CompletionGate(StrEnum):
    TARGET = "target"
    STANDARD = "standard"
    DELIVERABLE = "deliverable"
    EVIDENCE = "evidence"
    BOUNDARY = "boundary"
    NEXT_STEP = "next_step"
