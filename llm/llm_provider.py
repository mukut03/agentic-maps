"""
LLM Provider module for the MapChat application.
This module provides a factory for creating LLM clients based on configuration.
"""

from typing import Dict, Any, Optional, Union

from config import get_config
from llm.ollama_client import OllamaClient
from llm.openai_client import OpenAIClient

class LLMProvider:
    """
    Factory class for creating LLM clients based on configuration.
    """
    
    @staticmethod
    def get_client(provider: Optional[str] = None, model: Optional[str] = None) -> Union[OllamaClient, OpenAIClient]:
        """
        Get an LLM client based on the specified provider or configuration.
        
        Args:
            provider (str, optional): The provider to use. If not specified, uses the configured provider.
            model (str, optional): The model to use. If not specified, uses the configured model.
            
        Returns:
            Union[OllamaClient, OpenAIClient]: The LLM client
            
        Raises:
            ValueError: If the provider is not supported
        """
        config = get_config()
        
        # Use the specified provider or get from config
        provider = provider or config.get_llm_provider()
        
        # Get the model for the provider
        if model is None:
            if provider == "ollama":
                model = config.get("llm_models", {}).get("ollama", "llama3.2:latest")
            elif provider == "openai":
                model = config.get("llm_models", {}).get("openai", "gpt-4o")
        
        # Create the client based on the provider
        if provider == "ollama":
            base_url = config.get("ollama_base_url", "http://localhost:11434")
            return OllamaClient(base_url=base_url, model=model)
        elif provider == "openai":
            base_url = config.get("openai_base_url", "https://api.openai.com/v1")
            api_key = config.get_api_key("openai")
            return OpenAIClient(base_url=base_url, model=model, api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def is_provider_available(provider: str) -> bool:
        """
        Check if a provider is available.
        
        Args:
            provider (str): The provider to check
            
        Returns:
            bool: True if the provider is available, False otherwise
        """
        try:
            client = LLMProvider.get_client(provider)
            return client.is_available()
        except Exception as e:
            print(f"Error checking provider availability: {e}")
            return False
    
    @staticmethod
    def get_available_providers() -> Dict[str, bool]:
        """
        Get a dictionary of available providers.
        
        Returns:
            Dict[str, bool]: A dictionary mapping provider names to availability
        """
        providers = {
            "ollama": False,
            "openai": False
        }
        
        # Check each provider
        for provider in providers.keys():
            providers[provider] = LLMProvider.is_provider_available(provider)
        
        return providers


# Example usage
if __name__ == "__main__":
    # Check available providers
    available_providers = LLMProvider.get_available_providers()
    print("Available providers:")
    for provider, available in available_providers.items():
        status = "Available" if available else "Not available"
        print(f" - {provider}: {status}")
    
    # Get the default client
    config = get_config()
    default_provider = config.get_llm_provider()
    print(f"\nDefault provider: {default_provider}")
    
    # Try to get a client for the default provider
    try:
        client = LLMProvider.get_client()
        print(f"Created client for {default_provider}")
        
        # Check if the client is available
        if client.is_available():
            print(f"{default_provider} is available")
            
            # List models
            models = client.list_models()
            print(f"Available models for {default_provider}:")
            for model in models[:5]:  # Show only the first 5 models
                print(f" - {model.get('name')}")
        else:
            print(f"{default_provider} is not available")
    except Exception as e:
        print(f"Error creating client for {default_provider}: {e}")
