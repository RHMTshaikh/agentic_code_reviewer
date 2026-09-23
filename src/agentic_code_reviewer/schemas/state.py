import operator
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from typing import Annotated, List, Optional

class ReviewFinding(BaseModel):
    model_config = {"extra": "forbid"}
    category: str = Field(description="Category: SECURITY, ARCHITECTURE, or LOGIC")
    severity: str = Field(description="Severity: BLOCKER, WARNING, or NITPICK")
    file_path: str
    target_function: str
    line_number: Optional[int]
    issue_summary: str
    grounding_proof: str = Field(description="Evidence referencing actual code lines.")
    suggestion_to_fix: str = Field(description="Clear, actionable steps to remediate the issue.")
    code_patch: Optional[str] = Field(description="Optional code patch suggestion(only code patch with + or - as preffix and warp inside ```diff...``` or ```python...``` blocks).")
    confidence_score: float = Field(ge=0.0, le=1.0)

class CriticResponse(BaseModel):
    model_config = {"extra": "forbid"}
    findings: List[ReviewFinding]
    
class ErrorResponse(BaseModel):
    model_config = {"extra": "forbid"}
    error_message: str

class EvaluationScores(BaseModel):
    """Nested schema for the detailed evaluation scores."""
    model_config = {"extra": "forbid"}
    
    recall: int = Field(description="Score from 0 to 4 based on the number of ground truth issues successfully found.")
    root_cause: int = Field(description="Score from 0 to 3 evaluating if the systemic impact was correctly explained according to the repository context.")
    false_positive_penalty: int = Field(description="Penalty from -3 to 0 for falsely flagging benign code changes as critical bugs.")
    hallucination_penalty: int = Field(description="Penalty from -2 to 0 for inventing code not present in the diff or asserting fake bugs.")
    actionability: int = Field(description="Score from 0 to 2 evaluating if the remediation steps are clear, correct, and safe to apply.")
    discovery_bonus: int = Field(description="Bonus from 0 to 2 for identifying legitimate, severe flaws that were not listed in the Ground Truth.")

class FindingEvaluation(BaseModel):
    model_config = {"extra": "forbid"}

    original_review_finding_identifier: str = Field(description="Unique identifier description of the issue found by the review agent.")
    issue_id: Optional[int] = Field(description="Issue ID of the corresponding ground truth issue if it was successfully matched. None if not detected.")
    severity_correct: Optional[bool] = Field(description="Whether the severity level was correctly assessed. None if not detected.")
    category_correct: Optional[bool] = Field(description="Whether the category was correctly assessed. None if not detected.")
    description_correct: Optional[bool] = Field(description="Whether the description of issue correctly represents the problem described in the ground truth.")
    remediation_quality: Optional[str] = Field(description="Assessment of the suggested remediation steps. None if not detected.")
    false_positive_flagged: bool = Field(description="Whether the agent incorrectly flagged a safe, benign change as a bug.")

class EvaluatorResponse(BaseModel):
    """The strict JSON schema the LLM must follow when evaluating the agent."""
    model_config = {"extra": "forbid"}
    
    finding_evaluations: list[FindingEvaluation]
    missed_ground_truths_ids: list[int] = Field(description="List of issue IDs of the ground truth issues that the agent failed to identify.")
    reasoning: str = Field(description="Step-by-step logical breakdown of the comparison before scoring.")
    scores: EvaluationScores = Field(description="The detailed scoring breakdown across all evaluated metrics.")

class ClientStructuredResponse(BaseModel):
    model_config = {"extra": "forbid"}
    response: BaseModel   # CriticResponse | EvaluatorResponse | ErrorResponse
    total_tokens: int
    upload_tokens: int
    download_tokens: int
    model_name: str

class NodeAuditEntry(BaseModel):
    model_config = {"extra": "forbid"}
    node_name: str
    model_name: Optional[str] = None
    latency_ms: float
    total_tokens: int
    upload_tokens: int
    download_tokens: int

class ReviewNodeAuditEntry(NodeAuditEntry):
    findings_generated: int

class AgentState(TypedDict):
    # Immutable Inputs
    time_stamp: str
    modified_code: str
    affected_code: dict
    linter_annotations: list
    repository_context: Optional[str]
    senior_custom_instructions: Optional[str]

    # Parallel Fan-In Reducers (operator.add concatenates outputs safely)
    raw_findings: Annotated[List[ReviewFinding], operator.add]
    node_audit_trail: Annotated[List[ReviewNodeAuditEntry], operator.add]
    errors: Annotated[List[ErrorResponse], operator.add]

    # Arbitrated Final Outputs
    validated_findings: List[ReviewFinding]
    dropped_findings: List[dict]
    final_markdown_report: str
    

if __name__ == "__main__":
    schema = CriticResponse.model_json_schema()
    import json
    print(json.dumps(schema, indent=2))
    with open("critic_response_schema.json", "w") as f:
        json.dump(schema, f, indent=4)