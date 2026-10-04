import os
from typing import Type
from langsmith import APIError
from pydantic import BaseModel

import openai

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key

class AionClient(ClientInterface):
    def __init__(self, model_name: str = "openai/gpt-6.1-sol"):
        get_or_prompt_api_key(__class__.__name__)  # Ensure the API key is set in the environment
        
        api_key = os.getenv(__class__.__name__)
        if not api_key:
            raise ValueError(f"CRITICAL:{__class__.__name__} not found in system environment variables.")
        
        self.model_name = model_name
        # Initialize the official OpenAI synchronous client
        self.client = openai.OpenAI(
            base_url="https://api.aionlabs.ai/v1",
            api_key=api_key
        )

    def invoke_structured(self, 
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
    # Example usage of the AionClient
    client = AionClient(model_name="aion-labs/aion-rp-llama-3.1-8b")

    system_prompt = "You are a helpful assistant."
    user_prompt = "Please summarize the following text: 'Orca is a company that provides AI services.'"
    
    class SummarySchema(BaseModel):
        model_config = {"extra": "forbid"}
        summary: str

    response = client.invoke_structured(system_prompt, user_prompt, SummarySchema)