"""
Configuration module for the MapChat application.
This module provides a centralized place for all configuration settings.
"""

import os
import json
from typing import Dict, Any, Optional

# Default configuration
DEFAULT_CONFIG = {
    "base_url": "http://localhost:5000",
    "llm_provider": "ollama",  # Options: "ollama", "openai"
    "llm_models": {
        "ollama": "llama3.2:latest",
        "openai": "gpt-4o"
    },
    "api_keys": {
        "openai": ""  # Will be loaded from environment variable if available
    },
    "ollama_base_url": "http://localhost:11434",
    "openai_base_url": "https://api.openai.com/v1",
    "temperature": 0.2,
    "max_tokens": 1000
}

# Path to the config file
CONFIG_FILE_PATH = "mapchat_config.json"

class Config:
    """
    Configuration manager for the MapChat application.
    Handles loading, saving, and accessing configuration settings.
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance of Config exists."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from file or create default if not exists."""
        try:
            if os.path.exists(CONFIG_FILE_PATH):
                with open(CONFIG_FILE_PATH, 'r') as f:
                    self._config = json.load(f)
                    print(f"Loaded configuration from {CONFIG_FILE_PATH}")
            else:
                self._config = DEFAULT_CONFIG.copy()
                self._load_from_env()
                self.save_config()
                print(f"Created default configuration at {CONFIG_FILE_PATH}")
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            self._config = DEFAULT_CONFIG.copy()
            self._load_from_env()
    
    def _load_from_env(self):
        """Load sensitive configuration from environment variables."""
        # Load OpenAI API key from environment variable if available
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            self._config["api_keys"]["openai"] = openai_api_key
            print("Loaded OpenAI API key from environment variable")
    
    def save_config(self):
        """Save the current configuration to file."""
        try:
            # Create a copy of the config without sensitive information
            safe_config = self._config.copy()
            # Remove API keys before saving to file
            safe_config["api_keys"] = {k: "" for k in safe_config["api_keys"]}
            
            with open(CONFIG_FILE_PATH, 'w') as f:
                json.dump(safe_config, f, indent=2)
            print(f"Saved configuration to {CONFIG_FILE_PATH}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key (str): The configuration key
            default (Any, optional): Default value if key not found
            
        Returns:
            Any: The configuration value
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key (str): The configuration key
            value (Any): The value to set
        """
        self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration settings.
        
        Returns:
            Dict[str, Any]: All configuration settings
        """
        return self._config.copy()
    
    def get_llm_model(self) -> str:
        """
        Get the current LLM model based on the selected provider.
        
        Returns:
            str: The current LLM model
        """
        provider = self._config.get("llm_provider", "ollama")
        return self._config.get("llm_models", {}).get(provider, "llama3.2:latest")
    
    def get_llm_provider(self) -> str:
        """
        Get the current LLM provider.
        
        Returns:
            str: The current LLM provider
        """
        return self._config.get("llm_provider", "ollama")
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get the API key for a provider.
        
        Args:
            provider (str): The provider name
            
        Returns:
            Optional[str]: The API key or None if not found
        """
        # Try to get from environment first
        env_var = f"{provider.upper()}_API_KEY"
        api_key = os.environ.get(env_var)
        
        # If not in environment, get from config
        if not api_key:
            api_key = self._config.get("api_keys", {}).get(provider, "")
        
        return api_key if api_key else None
    
    def set_llm_provider(self, provider: str) -> None:
        """
        Set the LLM provider.
        
        Args:
            provider (str): The provider name
        """
        if provider in ["ollama", "openai"]:
            self._config["llm_provider"] = provider
    
    def set_llm_model(self, provider: str, model: str) -> None:
        """
        Set the LLM model for a provider.
        
        Args:
            provider (str): The provider name
            model (str): The model name
        """
        if "llm_models" not in self._config:
            self._config["llm_models"] = {}
        self._config["llm_models"][provider] = model

# Create a global instance
config = Config()

# Function to get the config instance
def get_config() -> Config:
    """
    Get the global Config instance.
    
    Returns:
        Config: The global Config instance
    """
    return config
