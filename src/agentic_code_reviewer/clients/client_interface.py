from abc import ABC, abstractmethod
from typing import Type
import os
import json

from pydantic import BaseModel

from agentic_code_reviewer.schemas.state import ClientStructuredResponse, ErrorResponse
from agentic_code_reviewer.paths import MODELS_REGISTRY_FILE_PATH

class ClientInterface(ABC):
    MODELS_REGISTRY = {}
    MODELS_REGISTRY_FILE_PATH = MODELS_REGISTRY_FILE_PATH
    
    @abstractmethod
    def invoke_structured(self,             
            system_prompt: str,
            user_prompt: str, 
            schema: Type[BaseModel],
            print_trace: bool = False
        ) -> ClientStructuredResponse:
        """Invoke the model with structured output based on the provided schema.
        Args:
            system_prompt (str): The system prompt to guide the model's behavior.
            user_prompt (str): The user prompt containing the input data.
            schema (Type[BaseModel]): The Pydantic schema to validate the model's output.
        Returns:
            ClientStructuredResponse: A structured response containing the model's output and metadata.
        """
        pass
    
    def openai_like_api(self, 
            system_prompt: str,
            user_prompt: str, 
            schema: Type[BaseModel],
            max_tokens: int = None,
            print_trace: bool = False
        ) -> ClientStructuredResponse:
        try:
            messages = [
                {"role": "system", "content": system_prompt,},
                {"role": "user", "content": user_prompt,},
            ]

            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            }

            # Detect whether self.client is the OpenAI SDK or the native Mistral SDK
            if hasattr(self.client.chat, "completions"):
                # OpenAI SDK, OpenRouter, Cerebras
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    response_format=response_format,
                    temperature=0.1,
                    max_tokens=max_tokens,
                )
            else:
                # Native Mistral SDK (client.chat.complete)
                response = self.client.chat.complete(
                    model=self.model_name,
                    messages=messages,
                    response_format=response_format,
                    temperature=0.1,
                    max_tokens=max_tokens,
                )

            content = response.choices[0].message.content or "{}"
            parsed_response = schema.model_validate_json(content)

            usage = response.usage
            upload_tokens = usage.prompt_tokens if usage else 0
            download_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            return ClientStructuredResponse(
                response=parsed_response,
                total_tokens=total_tokens,
                upload_tokens=upload_tokens,
                download_tokens=download_tokens,
                model_name=self.model_name,
            )
        except Exception as e:
            return self._handel_api_error(e, model_name=self.model_name, print_trace=print_trace)

    def google_like_api(self, 
            system_prompt: str,
            user_prompt: str, 
            schema: Type[BaseModel],
            print_trace: bool = False
        ) -> ClientStructuredResponse:
        
        full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PAYLOAD:\n{user_prompt}"

        # 1. Define the cleaner function internally
        def _clean_schema_for_gemini(schema_obj):
            if isinstance(schema_obj, dict):
                schema_obj.pop("additionalProperties", None)
                schema_obj.pop("additional_properties", None)
                schema_obj.pop("title", None) 
                schema_obj.pop("default", None)
                for key, value in list(schema_obj.items()):
                    _clean_schema_for_gemini(value)
            elif isinstance(schema_obj, list):
                for item in schema_obj:
                    _clean_schema_for_gemini(item)
            return schema_obj

        # 2. Extract and clean the dictionary payload
        raw_schema = schema.model_json_schema()
        gemini_safe_schema = _clean_schema_for_gemini(raw_schema)

        from google.genai import types
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=gemini_safe_schema,  # Pass the cleaned dict here!
            temperature=0.1
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=config
            )
            
            tokens_used = response.usage_metadata.total_token_count if response.usage_metadata else 0
            upload_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
            download_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            
            # 3. Because 'schema' is still the Pydantic class, this will work perfectly
            parsed_response = schema.model_validate_json(response.text)
            
            return ClientStructuredResponse(
                response=parsed_response,
                total_tokens=tokens_used,
                upload_tokens=upload_tokens,
                download_tokens=download_tokens,
                model_name=self.model_name
            )
        except Exception as e:
            return self._handel_api_error(e, model_name=self.model_name, print_trace=print_trace)
        
    @classmethod
    def _handel_api_error(cls, e: Exception, model_name: str = None, print_trace: bool = False) -> ClientStructuredResponse:
        print(f"[ERROR] Provider: {cls.__name__}, Model: {model_name}")
        print(f"Details:\n{str(e)}\n")
        
        if print_trace:
            import traceback
            traceback.print_exc()
            
        return ClientStructuredResponse(
            response=ErrorResponse(error_message=f"Provider: {cls.__name__}, Model: {model_name}\nError: {str(e)}"),
            total_tokens=0,
            upload_tokens=0,
            download_tokens=0,
            model_name=model_name
        )
    
    @classmethod
    def is_error_response(cls, response: BaseModel) -> bool:
        return isinstance(response, ErrorResponse)
    
    def ping(self) -> bool:
        """Check if the OpenAI-like/Mistral model is actively generating text."""
        try:
            # Standard OpenAI/Mistral chat completion syntax
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return True if response.choices else False
        except Exception as e:
            print(f"\n⚠️ [PING ERROR] Failed to ping {self.__class__.__name__} for model {self.model_name}.")
            print(f"Details:\n{str(e)}\n")
            return False
        
    # NOTE: Gemini has a different way of closing the client, so we will override this method in GeminiClient
    def close(self):
        """Close the client connection if applicable."""
        if hasattr(self.client, 'close'):
            self.client.close()
        else:
            raise ValueError("Client is not initialized.")
    
    # NOTE: Gemini has a different way of listing models, so we will override this method in GeminiClient
    def list_available_models(self):
        # NOTE: Gemini has a diffesetrent way of listing models, so we will override th
        """List available models for the client."""

        if not hasattr(self, 'client'):
            raise ValueError("Client is not initialized.")

        api_key = os.getenv(self.__class__.__name__)
        if not api_key:
            raise ValueError(
                f"CRITICAL:{self.__class__.__name__} API key not found in system environment variables."
            )

        try:
            models = self.client.models.list()
            return [model.id for model in models.data] 

        except Exception as e:
            print(f"\n🛑 [ERROR] Failed to list models for client {self.__class__.__name__}.")
            print(f"Details: {str(e)}\n")
            return []
    
    @classmethod
    def _populate_models_registry(cls):
        """Load free models from a JSON file."""

        if not cls.MODELS_REGISTRY_FILE_PATH.exists():
            print(f"⚠️ [WARNING] Free models JSON file not found at {cls.MODELS_REGISTRY_FILE_PATH}. Skipping initialization.")
            return

        try:
            with open(cls.MODELS_REGISTRY_FILE_PATH, "r", encoding="utf-8") as file:
                print(cls.MODELS_REGISTRY_FILE_PATH)
                cls.MODELS_REGISTRY = json.load(file)
                print(f"✅ Loaded free models:")
                print("To see all available models, use ClientInterface.show_all_models() method.")
                print("from agentic_code_reviewer.clients.llm_client_interface import ClientInterface ")
        except Exception as e:
            print(f"⚠️ [ERROR] Failed to load free models from {cls.MODELS_REGISTRY_FILE_PATH}. Details: {str(e)}")


    @classmethod
    def add_model(cls, model: str):
        provider = cls.__name__
        # 1. Read the JSON file
        with open(cls.MODELS_REGISTRY_FILE_PATH, "r", encoding="utf-8") as file:
            cls.MODELS_REGISTRY = json.load(file)

        # 2. Modify the data (works exactly like a normal Python dictionary)
        if provider not in cls.MODELS_REGISTRY:
            cls.MODELS_REGISTRY[provider] = []
        models = cls.MODELS_REGISTRY[provider]
        models.append(model)
        
        cls.MODELS_REGISTRY[provider] = list(set(models))  # Remove duplicates if any
        
        # 3. Save the modified data back to the same file
        with open(cls.MODELS_REGISTRY_FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(cls.MODELS_REGISTRY, file, indent=4)
    
    @classmethod
    def remove_model(cls, model: str):
        provider = cls.__name__
        # 1. Read the JSON file
        with open(cls.MODELS_REGISTRY_FILE_PATH, "r", encoding="utf-8") as file:
            cls.MODELS_REGISTRY = json.load(file)

        # 2. Modify the data (works exactly like a normal Python dictionary)
        if provider in cls.MODELS_REGISTRY and model in cls.MODELS_REGISTRY[provider]:
            cls.MODELS_REGISTRY[provider].remove(model)
        
        # 3. Save the modified data back to the same file
        with open(cls.MODELS_REGISTRY_FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(cls.MODELS_REGISTRY, file, indent=4)

    @classmethod
    def show_all_models(cls):
        for provider, models in cls.MODELS_REGISTRY.items():
            print(f"Current MODELS_REGISTRY for {provider}:")
            for model in models:
                print(f"  - {model}")

    @classmethod
    def show_models(cls) -> list[str]:
        provider = cls.__name__
        print(f"Current MODELS_REGISTRY for {provider}:")
        models = cls.MODELS_REGISTRY.get(provider, [])
        for i, model in enumerate(models):
            print(f"  - {i}: {model}")
        return models
    
