import os
from typing import Type
from langsmith import APIError
from pydantic import BaseModel

import openai

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key

class OpenAIClient(ClientInterface):
    def __init__(self, model_name: str = "gpt-4o"):
        get_or_prompt_api_key(__class__.__name__)  # Ensure the API key is set in the environment
        
        api_key = os.getenv(__class__.__name__)
        if not api_key:
            raise ValueError(f"CRITICAL:{__class__.__name__} not found in system environment variables.")
        
        self.model_name = model_name
        # Initialize the official OpenAI synchronous client
        self.client = openai.OpenAI(api_key=api_key)

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
    