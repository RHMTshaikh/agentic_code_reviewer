import os
from typing import Type
from pydantic import BaseModel
from google import genai
from google.genai import types
from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.schemas.state import ClientStructuredResponse
from agentic_code_reviewer.environment_manager import get_or_prompt_api_key

class GeminiClient(ClientInterface):
    """Production client for interacting with Gemini via Structured Outputs."""
    
    def __init__(self, model_name: str = "gemini-3.7-flash"):
        get_or_prompt_api_key(self.__class__.__name__)  

        api_key = os.getenv(self.__class__.__name__)
        if not api_key:
            raise ValueError(f"{self.__class__.__name__} API key is not set.")

        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    def invoke_structured(self, 
            system_prompt: str, 
            user_prompt: str, 
            schema: Type[BaseModel],
            print_trace: bool = False
        ) -> ClientStructuredResponse:
        
        response = self.google_like_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            print_trace=print_trace
        )
        return response
    
    def list_available_models(self):
        """List available models for the client."""

        if not hasattr(self, 'client'):
            raise ValueError("Client is not initialized.")

        api_key = os.getenv(self.__class__.__name__)
        if not api_key:
            raise ValueError(
                f"CRITICAL:{self.__class__.__name__} API key not found in system environment variables."
            )

        try:
            # 1. client.models.list() returns a Pager iterator
            pager = self.client.models.list()
            
            # 2. Iterate directly over the pager and extract the 'name' attribute
            return [model.name for model in pager] 

        except Exception as e:
            print(f"\n🛑 [ERROR] Failed to list models for client {self.__class__.__name__}.")
            print(f"Details: {str(e)}\n")
            return []
    
    def ping(self) -> bool:
        """Check if the Gemini API is reachable and the model is available."""
        # check if the model is available by trying make network call to the model
        try:
            # FIX: Pass model_name as a keyword argument ('model=')
            self.client.models.get(model=self.model_name)
            return True
        except Exception as e:
            print(f"\n⚠️ [PING ERROR] Failed to ping Gemini API or list models.")
            print(f"Details: {str(e)}\n")
            return False
            
    # You generally do not need to explicitly close the Gemini client. Google's libraries rely on Python's garbage collector to clean up the underlying gRPC channels once the client object goes out of scope.
    def close(self):
        """Close the client connection if applicable."""
        if hasattr(self.client, 'close'):
            pass
        else:
            raise ValueError("Client is not initialized.")
        
if __name__ == "__main__":
    # Example usage
    client = GeminiClient("gemini-3.8-flash")
    
    modles = client.show_models()
    
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "Please summarize the following text: 'Cerebras Systems is a company that builds AI hardware and software.'"
    
    class SummarySchema(BaseModel):
        model_config = {"extra": "forbid"}
        summary: str

    for model in modles:
        client.model_name = model
        print(f"✅ MODEL {model}. ","="*50)
        response = client.invoke_structured(system_prompt, user_prompt, SummarySchema)
        print(response)

    # response = client.invoke_structured(system_prompt, user_prompt, SummarySchema)
    # print(response)
    