from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ProjectType(str, Enum):
    LLM_APPLICATION = "llm_application"
    AI_AGENT        = "ai_agent"
    FINE_TUNING     = "fine_tuning"
    MODEL_SERVING   = "model_serving"
    DATA_PIPELINE   = "data_pipeline"
    COMPUTER_VISION = "computer_vision"
    MULTIMODAL      = "multimodal"
    CLASSICAL_ML    = "classical_ml"
    UNKNOWN         = "unknown"


class IssueSeverity(str, Enum):
    CRITICAL   = "critical"
    WARNING    = "warning"
    SUGGESTION = "suggestion"


class DetectedIssue(BaseModel):
    issue_id:     str                   # stable ID for frontend dedup
    severity:     IssueSeverity
    title:        str
    description:  str
    file:         Optional[str] = None
    line:         Optional[int] = None
    proposed_fix: str
    diff_preview: Optional[str] = None


class ScanResult(BaseModel):
    repo_url:                str
    project_type:            ProjectType
    confidence:              float                   # 0-1, blended L1+L2
    l1_confidence:           float                   # dep-parsing only
    ai_reasoning:            str                     # Claude's 1-2 sentence explanation
    detected_dependencies:   list[str]
    detected_characteristics: list[str]
    files_scanned:           int
    issues:                  list[DetectedIssue]


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id:            str
    text:          str
    context:       str
    options:       list[QuestionOption]
    allows_custom: bool = False


class FixApproval(BaseModel):
    issue_id: str
    approved: bool


class GenerateRequest(BaseModel):
    scan_result:            ScanResult
    approved_fixes:         list[FixApproval]
    questionnaire_answers:  dict[str, str]
    output_tier:            str = "docker_compose"


class GeneratedConfig(BaseModel):
    tier:             str
    files:            dict[str, str]
    deployment_guide: str
    cost_estimate:    Optional[str] = None
