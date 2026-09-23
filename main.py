from pathlib import Path
import sys

from agentic_code_reviewer import run_code_review
from agentic_code_reviewer.agents import AgentFactory
from agentic_code_reviewer.clients.client_interface import ClientInterface
from agentic_code_reviewer.clients import (
    OpenAIClient,
    GeminiClient,
    GroqClient,
    MistralClient,
    CerebrasClient,
    OpenRouterClient
)
from agentic_code_reviewer.my_langgraph import create_code_review_agent, default_code_review_agent
from codebase_map.gui.streamlit import launch_gui


if __name__ == "__main__":
    project_path = r'../document_align'
    project_path = r'../huggingface_transformer_clone/transformers/src/transformers/generation'
    absolute_path = Path(project_path).resolve()
    
    # launch_gui(absolute_path)
    # sys.exit(0)  # Exit after launching the GUI to prevent further execution

    # ClientClasses: list[ClientInterface] = [
    #     OpenAIClient,
    #     GeminiClient,
    #     GroqClient,
    #     MistralClient,
    #     CerebrasClient,
    #     OpenRouterClient
    # ]
    
    # for ClientClass in ClientClasses:
    #     client_instance = ClientClass()
    #     client_instance.add_model("dummy-model-for-testing")  # Add a dummy model for testing
        # for model in client_instance.list_available_models()[:5]:
        #     print(f"   - {model}")
    
    # free_openrouter_models = [
    #     "inclusionai/ling-3.0-flash-fin:free",
    #     "dots-studio/dots-3-note-preview:free",
    #     "liquid/lfm-2.5-2.6b:free",
    #     "nvidia/nemotron-3.5-lightning:free",
    #     "thinkingmachines/inkling-small:free",
    #     "poolside/laguna-s-2.1:free",
    #     "thinkingmachines/inkling:free",
    #     "poolside/laguna-xs-2.1:free",
    #     "cohere/north-mini-code:free",
    #     "z-ai/glm-5.2:free",
    #     "nvidia/nemotron-3.5-content-safety:free",
    #     "nvidia/nemotron-3-ultra-550b-a55b:free",
    #     "minimax/minimax-m3:free",
    #     "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    #     "google/gemma-4-26b-a4b-it:free",
    #     "google/gemma-4-31b-it:free",
    #     "minimax/minimax-m2.7:free",
    #     "nvidia/nemotron-3-super-120b-a12b:free",
    # ]
    
    # free_gemini_models = [
    #     "gemini-2.5-flash",
    #     "gemini-flash-latest",
    #     "gemini-flash-lite-latest",
    #     "gemini-2.5-flash-lite",
    #     "gemini-3.5-flash",
    #     "gemini-3.5-flash-lite",
    #     "gemini-3.6-flash",
    #     "gemini-3.7-flash",
    #     "gemini-3.1-flash-lite",
    #     "gemini-3.1-flash-live-preview",
    #     "gemini-2.5-flash-native-audio-latest",
    #     "gemini-2.5-flash-native-audio-preview-09-2025",
    #     "gemini-2.5-flash-native-audio-preview-12-2025",
    #     "gemini-2.5-flash-preview-tts",
    #     "gemini-3.1-flash-tts-preview",
    # ]

    # free_groq_models = [
    #     "openai/gpt-oss-120b",
    #     "openai/gpt-oss-20b",
    #     "openai/gpt-oss-safeguard-20b",
    #     "qwen/qwen3.6-27b",
    #     "qwen/qwen3.8-27b",
    #     "groq/compound",
    #     "groq/compound-mini",
    #     "meta-llama/llama-prompt-guard-2-86m",
    #     "meta-llama/llama-prompt-guard-2-22m",
    #     "whisper-large-v3",
    #     "whisper-large-v3-turbo",
    #     "canopylabs/orpheus-v1-english",
    #     "canopylabs/orpheus-arabic-saudi",
    #     "allam-2-7b",
    # ]

    # free_cerebras_models = [
    #     "gpt-oss-120b",
    #     "qwen-3.8-27b",
    #     "gemma-4-31b"
    # ]

    # free_mistral_models = [
    #     "mistral-small-latest",
    #     "ministral-3b-latest",
    #     "ministral-8b-latest",
    #     "ministral-14b-latest",
    #     "voxtral-small-latest",
    #     "voxtral-mini-latest",
    #     "devstral-latest",
    #     "devstral-medium-latest",
    #     "codestral-latest",
    #     "magistral-small-latest",
    #     "mistral-embed",
    #     "mistral-ocr-latest",
    # ]
    
    # client_models_tuples: list[tuple[ClientInterface, list[str]]] = [
    #     (OpenRouterClient(), free_openrouter_models),
    #     (GeminiClient(), free_gemini_models),
    #     (GroqClient(), free_groq_models),
    #     (MistralClient(), free_mistral_models),
    #     (CerebrasClient(), free_cerebras_models),
    # ]
    
    # for client, free_models in client_models_tuples:
        # for model in free_models:
        #     client.add_model(model)
            
    # ClientInterface.show_all_models()
    
    
        
    # client = OpenAIClient()
    # client = GeminiClient()
    # client = GroqClient()
    # client = MistralClient()
    # client = CerebrasClient()
    # client = OpenRouterClient()
    
    # models = client.list_available_models()
    # for model in models[:]:  # Display only the first 5 models for brevity
    #     print(f"   - {model}")
    

    # logic_critic_factory = AgentFactory(
    #     agent_name="logic_critic",
    #     agent_category="LOGIC",
    #     system_prompt = (
    #         "You are a Senior Logic & Edge-Case Reviewer."
    #         "Find unhandled exceptions, null dereferences, and boundary bugs."
    #         "Only output findings if you are highly confident."
    #     ),
    #     client=client
    # )
    # architecture_critic_factory = AgentFactory(
    #     agent_name="architecture_critic",
    #     agent_category="ARCHITECTURE",
    #     system_prompt = (
    #         "You are a Senior Architecture Reviewer."
    #         "Analyze the code for architectural issues, design flaws, and maintainability concerns."
    #         "Only output findings if you are highly confident."
    #     ),
    #     client=client
    # )
    # security_critic_factory = AgentFactory(
    #     agent_name="security_critic",
    #     agent_category="SECURITY",
    #     system_prompt = (
    #         "You are an elite Security Operations Reviewer. "
    #         "Hunt for injection, auth bypasses, and credential leaks. "
    #         "Only output findings if you are highly confident."
    #     ),
    #     client=client
    # )
    
    # agent = create_code_review_agent(
    #     agent_factories=[
    #         logic_critic_factory,
    #         architecture_critic_factory,
    #         security_critic_factory
    #     ]
    # )
    
    # agent = default_code_review_agent(client=client)
    
    # run_review(
    #     agent=agent,
    #     absolute_project_path=absolute_path,
    #     report_dir=Path.cwd() / f"{client.__class__.__name__}_reports"
    # )