#!/usr/bin/env python3
"""
Command-line utility for managing MapChat configuration.
This allows users to easily switch between Ollama and OpenAI, set API keys, and configure other settings.
"""

import os
import sys
import argparse
from typing import Dict, Any, Optional

from config import get_config, Config
from llm_provider import LLMProvider

def print_current_config():
    """Print the current configuration."""
    config = get_config()
    all_config = config.get_all()
    
    print("\n=== Current Configuration ===")
    print(f"LLM Provider: {config.get_llm_provider()}")
    print(f"LLM Model: {config.get_llm_model()}")
    
    # Print provider-specific settings
    if config.get_llm_provider() == "ollama":
        print(f"Ollama Base URL: {all_config.get('ollama_base_url', 'http://localhost:11434')}")
    elif config.get_llm_provider() == "openai":
        print(f"OpenAI Base URL: {all_config.get('openai_base_url', 'https://api.openai.com/v1')}")
        # Don't print the actual API key for security reasons
        api_key = config.get_api_key("openai")
        if api_key:
            print("OpenAI API Key: [Set]")
        else:
            print("OpenAI API Key: [Not Set]")
    
    print(f"Temperature: {all_config.get('temperature', 0.7)}")
    print(f"Max Tokens: {all_config.get('max_tokens', 1000)}")
    print(f"Base URL: {all_config.get('base_url', 'http://localhost:5000')}")
    print()

def set_provider(provider: str):
    """
    Set the LLM provider.
    
    Args:
        provider (str): The provider name
    """
    if provider not in ["ollama", "openai"]:
        print(f"Error: Unsupported provider '{provider}'. Supported providers are 'ollama' and 'openai'.")
        return
    
    config = get_config()
    config.set_llm_provider(provider)
    config.save_config()
    
    print(f"LLM provider set to '{provider}'.")
    
    # Check if the provider is available
    if LLMProvider.is_provider_available(provider):
        print(f"Provider '{provider}' is available and ready to use.")
    else:
        if provider == "ollama":
            print(f"Warning: Provider '{provider}' is not available. Make sure Ollama is running.")
        elif provider == "openai":
            print(f"Warning: Provider '{provider}' is not available. Make sure you have set a valid API key.")

def set_model(provider: str, model: str):
    """
    Set the LLM model for a provider.
    
    Args:
        provider (str): The provider name
        model (str): The model name
    """
    if provider not in ["ollama", "openai"]:
        print(f"Error: Unsupported provider '{provider}'. Supported providers are 'ollama' and 'openai'.")
        return
    
    config = get_config()
    config.set_llm_model(provider, model)
    config.save_config()
    
    print(f"LLM model for '{provider}' set to '{model}'.")

def set_api_key(provider: str, api_key: str):
    """
    Set the API key for a provider.
    
    Args:
        provider (str): The provider name
        api_key (str): The API key
    """
    if provider not in ["openai"]:
        print(f"Error: API key not required for provider '{provider}'.")
        return
    
    # Set the API key in the environment variable
    os.environ[f"{provider.upper()}_API_KEY"] = api_key
    print(f"API key for '{provider}' set in environment variable.")
    
    # Also store it in the config (though it won't be saved to file)
    config = get_config()
    all_config = config.get_all()
    if "api_keys" not in all_config:
        all_config["api_keys"] = {}
    all_config["api_keys"][provider] = api_key
    
    # Check if the provider is available with the new API key
    if LLMProvider.is_provider_available(provider):
        print(f"Provider '{provider}' is available and ready to use with the new API key.")
    else:
        print(f"Warning: Provider '{provider}' is still not available. The API key may be invalid.")

def set_base_url(provider: str, base_url: str):
    """
    Set the base URL for a provider.
    
    Args:
        provider (str): The provider name
        base_url (str): The base URL
    """
    if provider not in ["ollama", "openai"]:
        print(f"Error: Unsupported provider '{provider}'. Supported providers are 'ollama' and 'openai'.")
        return
    
    config = get_config()
    all_config = config.get_all()
    
    if provider == "ollama":
        all_config["ollama_base_url"] = base_url
    elif provider == "openai":
        all_config["openai_base_url"] = base_url
    
    config.save_config()
    print(f"Base URL for '{provider}' set to '{base_url}'.")

def set_temperature(temperature: float):
    """
    Set the temperature for LLM generation.
    
    Args:
        temperature (float): The temperature value
    """
    if temperature < 0.0 or temperature > 2.0:
        print("Warning: Temperature should typically be between 0.0 and 2.0.")
    
    config = get_config()
    all_config = config.get_all()
    all_config["temperature"] = temperature
    config.save_config()
    
    print(f"Temperature set to {temperature}.")

def set_max_tokens(max_tokens: int):
    """
    Set the maximum number of tokens for LLM generation.
    
    Args:
        max_tokens (int): The maximum number of tokens
    """
    if max_tokens < 1:
        print("Error: Max tokens must be at least 1.")
        return
    
    config = get_config()
    all_config = config.get_all()
    all_config["max_tokens"] = max_tokens
    config.save_config()
    
    print(f"Max tokens set to {max_tokens}.")

def check_providers():
    """Check which providers are available."""
    print("\n=== Provider Availability ===")
    
    providers = LLMProvider.get_available_providers()
    for provider, available in providers.items():
        status = "Available" if available else "Not Available"
        print(f"{provider}: {status}")
    
    print()

def list_models(provider: str):
    """
    List available models for a provider.
    
    Args:
        provider (str): The provider name
    """
    if provider not in ["ollama", "openai"]:
        print(f"Error: Unsupported provider '{provider}'. Supported providers are 'ollama' and 'openai'.")
        return
    
    try:
        client = LLMProvider.get_client(provider)
        models = client.list_models()
        
        print(f"\n=== Available Models for {provider} ===")
        if not models:
            print(f"No models found for {provider}.")
        else:
            for model in models:
                print(f"- {model.get('name')}")
        print()
    except Exception as e:
        print(f"Error listing models for {provider}: {str(e)}")

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="MapChat Configuration CLI")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show current configuration")
    
    # Provider command
    provider_parser = subparsers.add_parser("provider", help="Set the LLM provider")
    provider_parser.add_argument("name", choices=["ollama", "openai"], help="Provider name")
    
    # Model command
    model_parser = subparsers.add_parser("model", help="Set the LLM model for a provider")
    model_parser.add_argument("provider", choices=["ollama", "openai"], help="Provider name")
    model_parser.add_argument("name", help="Model name")
    
    # API key command
    api_key_parser = subparsers.add_parser("api-key", help="Set the API key for a provider")
    api_key_parser.add_argument("provider", choices=["openai"], help="Provider name")
    api_key_parser.add_argument("key", help="API key")
    
    # Base URL command
    base_url_parser = subparsers.add_parser("base-url", help="Set the base URL for a provider")
    base_url_parser.add_argument("provider", choices=["ollama", "openai"], help="Provider name")
    base_url_parser.add_argument("url", help="Base URL")
    
    # Temperature command
    temperature_parser = subparsers.add_parser("temperature", help="Set the temperature for LLM generation")
    temperature_parser.add_argument("value", type=float, help="Temperature value")
    
    # Max tokens command
    max_tokens_parser = subparsers.add_parser("max-tokens", help="Set the maximum number of tokens for LLM generation")
    max_tokens_parser.add_argument("value", type=int, help="Maximum number of tokens")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check which providers are available")
    
    # List models command
    list_models_parser = subparsers.add_parser("list-models", help="List available models for a provider")
    list_models_parser.add_argument("provider", choices=["ollama", "openai"], help="Provider name")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "show" or args.command is None:
        print_current_config()
    elif args.command == "provider":
        set_provider(args.name)
    elif args.command == "model":
        set_model(args.provider, args.name)
    elif args.command == "api-key":
        set_api_key(args.provider, args.key)
    elif args.command == "base-url":
        set_base_url(args.provider, args.url)
    elif args.command == "temperature":
        set_temperature(args.value)
    elif args.command == "max-tokens":
        set_max_tokens(args.value)
    elif args.command == "check":
        check_providers()
    elif args.command == "list-models":
        list_models(args.provider)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
