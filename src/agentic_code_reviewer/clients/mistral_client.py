import os
from typing import Type

from pydantic import BaseModel
from mistralai.client import Mistral

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key

class MistralClient(ClientInterface):
    def __init__(
        self,
        model_name: str = "codestral-latest",
        ):
        get_or_prompt_api_key(__class__.__name__)

        api_key = os.getenv(__class__.__name__)
        if not api_key:
            raise ValueError(
                f"CRITICAL:{__class__.__name__} not found in system environment variables."
            )

        self.model_name = model_name
        self.client = Mistral(api_key=api_key)

    def invoke_structured(
            self,
            system_prompt: str,
            user_prompt: str,
            schema: Type[BaseModel],
            print_trace: bool = False
        ) -> ClientStructuredResponse:

            response = self.openai_like_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                print_trace=print_trace
            )
            return response

    def ping(self) -> bool:
        """Check if the Mistral model is actively generating text."""
        try:
            response = self.client.chat.complete(
                model=self.model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return True if response.choices else False
        except Exception as e:
            print(f"\n⚠️ [INFERENCE ERROR] Failed to generate content.")
            print(f"Details: {str(e)}\n")
            return False
        
if __name__ == "__main__":
    client = MistralClient(model_name="ministral-3b-latest")
    system_prompt = "You are a helpful assistant."
    user_prompt = "Please summarize the following text: 'Cerebras Systems is a company that builds AI hardware and software.'"
    
    class SummarySchema(BaseModel):
        model_config = {"extra": "forbid"}
        summary: str
        
    response = client.invoke_structured(system_prompt, user_prompt, SummarySchema)
    print(response)