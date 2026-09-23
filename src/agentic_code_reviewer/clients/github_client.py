import os
from typing import Type
from pydantic import BaseModel

from openai import OpenAI 

from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key

class GithubClient(ClientInterface):
    def __init__(self, model_name: str = "gpt-4o"):
        get_or_prompt_api_key(__class__.__name__)  # Ensure the API key is set in the environment
        
        api_key = os.getenv(__class__.__name__)
        if not api_key:
            raise ValueError(f"CRITICAL:{__class__.__name__} not found in system environment variables.")
        
        self.model_name = model_name
        # Initialize the official OpenAI synchronous client
        self.client = OpenAI(
            base_url="https://models.github.ai/inference",
            api_key=api_key,
        )

    def invoke_structured(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        schema: Type[BaseModel]
    ) -> ClientStructuredResponse:
        
        response = self.openai_like_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
        )
        return response
    


if __name__ == "__main__":
    client = GithubClient(model_name="openai/gpt-4o")
    system_prompt = "You are a helpful assistant."
    user_prompt = "Please summarize the following text: 'Cerebras Systems is a company that builds AI hardware and software.'"
    
    class SummarySchema(BaseModel):
        model_config = {"extra": "forbid"}
        summary: str
    try:
        response = client.invoke_structured(system_prompt, user_prompt, SummarySchema)
        print(response.response.summary)
    except Exception as e:
        raise e