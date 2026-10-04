from agentic_code_reviewer.logging import log
import time
from typing import Dict, Any, List
from agentic_code_reviewer.schemas.state import AgentState, CriticResponse, CriticResponse, ErrorResponse, ReviewNodeAuditEntry, ReviewFinding
from agentic_code_reviewer.paths import LOGS_DIR_PATH

def arbitrator_node(state: AgentState) -> Dict[str, Any]:
    start_time = time.perf_counter()
    raw_findings: List[ReviewFinding] = state.get("raw_findings", [])
    errors: List[ErrorResponse] = state.get("errors", [])
    custom_instruction = state.get("senior_custom_instructions")

    unique_findings_map: Dict[str, ReviewFinding] = {}
    dropped: List[dict] = []
    validated: List[ReviewFinding] = []

    # ---------------------------------------------------------
    # PASS 1: The Deduplication Hash
    # ---------------------------------------------------------
    for finding in raw_findings:
        # Create a unique signature: function + line + category
        signature = f"{finding.target_function}:{finding.line_number}:{finding.category}"
        
        if signature in unique_findings_map:
            # We found a duplicate! Keep the one with higher confidence.
            existing_finding = unique_findings_map[signature]
            if finding.confidence_score > existing_finding.confidence_score:
                dropped.append({
                    "target_function": finding.target_function,
                    "reason": f"Pruned: Duplicate overridden by higher confidence ({finding.confidence_score})"
                })
                unique_findings_map[signature] = finding
            else:
                dropped.append({
                    "target_function": finding.target_function,
                    "reason": f"Pruned: Duplicate dropped due to lower confidence ({finding.confidence_score})"
                })
        else:
            unique_findings_map[signature] = finding

    # ---------------------------------------------------------
    # PASS 2: Validation & False-Positive Filter
    # ---------------------------------------------------------
    for finding in unique_findings_map.values():
        if finding.confidence_score < 0.70 or len(finding.grounding_proof.strip()) < 15:
            dropped.append({
                "target_function": finding.target_function,
                "reason": f"Pruned: Low confidence ({finding.confidence_score}) or weak grounding proof."
            })
        else:
            validated.append(finding)

    # 3. Sort by severity: BLOCKER > WARNING > NITPICK
    severity_order = {"BLOCKER": 0, "WARNING": 1, "NITPICK": 2}
    validated.sort(key=lambda x: severity_order.get(x.severity, 99))

    # 3. Format Enterprise Markdown Report
    lines = [
        f"# TIMESTAMP: {state.get('time_stamp')}",
        f"## Senior Engineer Code Review Report",
        f"  **Current Branch:** {state.get('current_branch')}",
        "### Executive Summary",
        f"- **Total Raw Findings:** {len(raw_findings)}",
        f"- **Actionable Findings (Validated):** {len(validated)}",
        f"- **Hallucinations / Noise Filtered:** {len(dropped)}\n"
    ]
    
    lines.append("### Detailed Logs\n")
    for log_entry in state.get("logs", []):
        lines.append(f"- {log_entry}\n")

    if custom_instruction:
        lines.append(f"> **Senior Directive Applied:** *\"{custom_instruction}\"*\n")

    lines.append("## Findings & Required Actions\n")

    for f in validated:
        badge = "🛑 BLOCKER" if f.severity == "BLOCKER" else ("⚠️ WARNING" if f.severity == "WARNING" else "💡 NITPICK")
        lines.append(f"### {badge} — `{f.category}` in `{f.file_path}` (`{f.target_function}`)")
        if f.line_number:
            lines.append(f"**Line:** `{f.line_number}` | **Confidence:** `{f.confidence_score * 100:.0f}%`")
        lines.append(f"\n**Problem:** {f.issue_summary}\n")
        lines.append(f"**Grounding Reference:**\n> {f.grounding_proof}\n")
        lines.append(f"**Suggested Remediation:**\n> {f.suggestion_to_fix}\n")
        if f.code_patch:
            lines.append(f"**Suggested Fix:**\n")
            lines.append(f"\n{f.code_patch}\n")
        lines.append("\n")
        
    for error in errors:
        lines.append(f"### ⚠️ ERROR\n")
        lines.append(f"```\n")
        lines.append(f"{error.error_message}\n")
        lines.append(f"```\n")

    lines.append("---")
    lines.append(f"<br><br><br>\n\n")

    latency = (time.perf_counter() - start_time) * 1000
    total_tokens = 0  # Arbitrator does not consume tokens, but we include this for consistency
    upload_tokens = 0
    download_tokens = 0

    audit = ReviewNodeAuditEntry(
        node_name="arbitrator",
        latency_ms=round(latency, 2),
        findings_generated=len(validated),
        total_tokens=total_tokens,
        upload_tokens=upload_tokens,
        download_tokens=download_tokens
    )
    
    log(
        time_stamp=state.get("time_stamp"),
        system_prompt="--- NOT USING LLM ---",
        user_prompt=f"",
        response= CriticResponse(findings=validated),
        audit_trail=audit,
        log_path=LOGS_DIR_PATH / "arbitrator.log"
    )

    return {
        "validated_findings": validated,
        "dropped_findings": dropped,
        "final_markdown_report": "\n".join(lines),
        "node_audit_trail": [audit]
    }