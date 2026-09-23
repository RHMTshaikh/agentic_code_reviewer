import time
from typing import Type
from pydantic import BaseModel
from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse, CriticResponse, ReviewFinding

class MockLLMClient(ClientInterface):
    """Simulates an LLM engine with deterministic outputs and latency."""
    def __init__(self, model_name: str = "mock-gemini-pro"):
        self.model_name = model_name

    def invoke_structured(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        schema: Type[BaseModel]
    ) -> ClientStructuredResponse:
        # Simulate ~120ms network & inference round-trip
        time.sleep(0.12)
        mock_tokens = len(system_prompt.split()) + len(user_prompt.split()) + 75

        # Rule-based synthetic generation based on critic persona
        if "Security" in system_prompt:
            findings = [
                ReviewFinding(
                    category="SECURITY",
                    severity="BLOCKER",
                    file_path="services/payment_service.py",
                    target_function="process_transaction",
                    line_number=42,
                    issue_summary="Hardcoded fallback auth secret detected in conditional block.",
                    grounding_proof="git_diff line 42: if not token: token = 'DEV_KEY_ADMIN'",
                    code_patch="- token = 'DEV_KEY_ADMIN'\n+ token = os.environ.get('PAYMENT_AUTH_TOKEN')",
                    confidence_score=0.96
                ),
                # Synthetic low-confidence finding (to test Arbitrator pruning)
                ReviewFinding(
                    category="SECURITY",
                    severity="NITPICK",
                    file_path="services/payment_service.py",
                    target_function="log_event",
                    line_number=12,
                    issue_summary="Theoretical timing attack on non-cryptographic hash.",
                    grounding_proof="unverified speculation",
                    code_patch=None,
                    confidence_score=0.45
                )
            ]
        elif "Architecture" in system_prompt:
            findings = [
                ReviewFinding(
                    category="ARCHITECTURE",
                    severity="WARNING",
                    file_path="services/payment_service.py",
                    target_function="process_transaction",
                    line_number=55,
                    issue_summary="Violates Single Responsibility Principle: Direct DB commit inside payment gateway handler.",
                    grounding_proof="SCIP call graph shows `process_transaction` directly invoking `db_session.execute()` instead of calling `RepositoryLayer`.",
                    code_patch="Delegate persistence to `PaymentRepository.record_transaction()`.",
                    confidence_score=0.88
                )
            ]
        elif "Logic" in system_prompt:
            findings = [
                ReviewFinding(
                    category="LOGIC",
                    severity="BLOCKER",
                    file_path="services/payment_service.py",
                    target_function="calculate_tax",
                    line_number=78,
                    issue_summary="ZeroDivisionError unhandled when `item_count` is 0.",
                    grounding_proof="git_diff line 78: unit_rate = total_tax / item_count",
                    code_patch="if item_count == 0: return Decimal('0.00')",
                    confidence_score=0.92
                )
            ]
        else:
            findings = []

        return ClientStructuredResponse(
            response=CriticResponse(findings=findings),
            total_tokens=mock_tokens,
            upload_tokens=0,
            download_tokens=0,
            model_name="mock_model"
        )