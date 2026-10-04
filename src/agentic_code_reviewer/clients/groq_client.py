import os
from typing import Type

from pydantic import BaseModel
from groq import Groq

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key

class GroqClient(ClientInterface):
    def __init__(self, model_name: str = "openai/gpt-oss-120b"):
        get_or_prompt_api_key(__class__.__name__)

        api_key = os.getenv(__class__.__name__)
        if not api_key:
            raise ValueError(
                f"CRITICAL:{__class__.__name__} not found in system environment variables."
            )

        self.model_name = model_name
        self.client = Groq(api_key=api_key)

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

if __name__ == "__main__":
    client = GroqClient(model_name="openai/gpt-oss-120b")
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