import os
from typing import Type

from pydantic import BaseModel
from cerebras.cloud.sdk import Cerebras

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key


class CerebrasClient(ClientInterface):
    def __init__(
        self,
        model_name: str = "gpt-oss-120b",
        ):
        get_or_prompt_api_key(__class__.__name__)

        api_key = os.getenv(__class__.__name__)

        if not api_key:
            raise ValueError(
                f"CRITICAL:{__class__.__name__} not found in system environment variables."
            )

        self.model_name = model_name
        self.client = Cerebras(api_key=api_key)

    def invoke_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[BaseModel],
        ) -> ClientStructuredResponse:

        # https://pypi.org/project/cerebras-cloud-sdk/
        response = self.openai_like_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )
        return response
    
if __name__ == "__main__":
    # Example usage of the CerebrasClient
    client = CerebrasClient(model_name="qwen-3.8-27b")
    system_prompt = "You are a helpful assistant."
    user_prompt = "Please summarize the following text: 'Cerebras Systems is a company that builds AI hardware and software.'"
    
    class SummarySchema(BaseModel):
        config = {"extra": "forbid"}
        summary: str

    response = client.invoke_structured(system_prompt, user_prompt, SummarySchema)
    print(response.response.summary)