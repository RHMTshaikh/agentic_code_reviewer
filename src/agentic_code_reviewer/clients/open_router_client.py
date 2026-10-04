import os
from typing import Type

from pydantic import BaseModel
from openai import OpenAI

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key

class OpenRouterClient(ClientInterface):
    def __init__(
        self,
        model_name: str = "z-ai/glm-5.2",
        ):
        get_or_prompt_api_key(__class__.__name__)

        api_key = os.getenv(__class__.__name__)
        if not api_key:
            raise ValueError(
                f"CRITICAL:{__class__.__name__} not found in system environment variables."
            )

        self.model_name = model_name

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

    def invoke_structured(self,
            system_prompt: str,
            user_prompt: str,
            schema: Type[BaseModel],
            print_trace: bool = False
        ) -> ClientStructuredResponse:

        max_tokens = 8000  # Set a default max token limit; adjust as needed
        response = self.openai_like_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            max_tokens=max_tokens,
            print_trace=print_trace
        )
        return response

if __name__ == "__main__":
    client = OpenRouterClient("qwen/qwen3.8-27b:free")
    models = client.list_available_models()
    for model in models:
        client.add_model(model)
    system_prompt = "You are a helpful assistant."
    user_prompt = "Please summarize the following text: 'Cerebras Systems is a company that builds AI hardware and software.'"
    
    class SummarySchema(BaseModel):
        model_config = {"extra": "forbid"}
        summary: str
        
    response = client.invoke_structured(system_prompt, user_prompt, SummarySchema)
    print(response)

