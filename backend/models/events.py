from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum

class EventType(str, Enum):
    RETURN_API_FAILURE = "return_api.failure"
    SCHEMA_MISMATCH = "schema.mismatch"
    RCA_READY = "rca.ready"
    MORPH_APPLY_REQUESTED = "morph.apply.requested"
    MORPH_APPLY_SUCCEEDED = "morph.apply.succeeded"
    MORPH_APPLY_FAILED = "morph.apply.failed"
    PATCH_LOG = "patch.log"
    RELOAD_DONE = "reload.done"
    VERIFY_REPLAY_PASS = "verify.replay.pass"
    VERIFY_REPLAY_FAIL = "verify.replay.fail"
    HEAL_COMPLETED = "heal.completed"
    TRACE_START = "trace.start"

class Event(BaseModel):
    type: EventType
    key: str
    payload: Dict[str, Any]
    ts: datetime
    trace_id: Optional[str] = None
    ui_hint: Optional[str] = None

class FailureDetail(BaseModel):
    type: str
    field: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    message: str

class TraceStep(BaseModel):
    trace_id: str
    step: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    schema_ok: bool
    failure: Optional[FailureDetail] = None
    latency_ms: int
    timestamp: datetime

class RCAPlan(BaseModel):
    playbook: str
    cause: str
    patch_spec: Dict[str, Any]
    risk_score: float
    confidence: float

class MachineDiff(BaseModel):
    file: str
    original_content: str
    updated_content: str
    diff_lines: List[str]
    loc_changed: int

class HealOutcome(BaseModel):
    trace_id: str
    status: str  # "pass" | "fail"
    replay_ms: int
    before: Dict[str, Any]
    after: Dict[str, Any]
    commit_sha: Optional[str] = None

class GuardrailCheck(BaseModel):
    rule: str
    passed: bool
    message: str
    risk_score: float 