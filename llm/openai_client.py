"""
A client for interacting with the OpenAI API.
This allows querying OpenAI models like GPT-4o without using frameworks like LangChain.
"""

import json
import time
import aiohttp
import asyncio
import requests
from typing import Dict, List, Any, Optional, AsyncGenerator, Generator

from config import get_config

class OpenAIClient:
    """
    A client for interacting with the OpenAI API.
    This allows querying OpenAI models like GPT-4o without using frameworks like LangChain.
    """
    
    def __init__(self, base_url=None, model=None, api_key=None):
        """
        Initialize the OpenAI client.
        
        Args:
            base_url (str, optional): The base URL of the OpenAI API
            model (str, optional): The default model to use for queries
            api_key (str, optional): The OpenAI API key
        """
        config = get_config()
        
        self.base_url = base_url or config.get("openai_base_url", "https://api.openai.com/v1")
        self.model = model or config.get_llm_model() or "gpt-4o"
        self.api_key = api_key or config.get_api_key("openai")
        
        # API endpoints
        self.api_chat = f"{self.base_url}/chat/completions"
        self.api_completions = f"{self.base_url}/completions"
        
        # Check if API key is available
        if not self.api_key:
            print("Warning: No OpenAI API key provided. Set the OPENAI_API_KEY environment variable or configure it in the config file.")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get the headers for API requests.
        
        Returns:
            Dict[str, str]: The headers
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def query(self, prompt: str, model=None, system_prompt=None, temperature=0.7, stream=False) -> Dict[str, Any]:
        """
        Send a query to the OpenAI API and get a response.
        
        Args:
            prompt (str): The prompt to send to the model
            model (str, optional): The model to use. Defaults to the instance's model.
            system_prompt (str, optional): A system prompt to provide context
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            
        Returns:
            dict: The response from the API
        """
        model = model or self.model
        
        # For OpenAI, we use the chat completions endpoint with a formatted message
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Prepare the payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            response = requests.post(
                self.api_chat,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            # Process the response
            response_data = response.json()
            
            # Convert to a format similar to Ollama's response
            return {
                "model": model,
                "response": response_data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "done": True
            }
        except requests.exceptions.RequestException as e:
            print(f"Error querying OpenAI API: {e}")
            return {"error": f"OpenAI API request failed: {e}"}
    
    def chat(self, messages: List[Dict[str, str]], model=None, temperature=0.7, stream=False) -> Dict[str, Any]:
        """
        Send a chat request to the OpenAI API (synchronous version).
        
        Args:
            messages (list): List of message objects with 'role' and 'content'
            model (str, optional): The model to use. Defaults to the instance's model.
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            
        Returns:
            dict: The response from the API
        """
        model = model or self.model
        
        # Prepare the payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            response = requests.post(
                self.api_chat,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            # Process the response
            response_data = response.json()
            
            # Convert to a format similar to Ollama's response
            return {
                "model": model,
                "message": {
                    "role": "assistant",
                    "content": response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                },
                "done": True
            }
        except requests.exceptions.RequestException as e:
            print(f"Error in chat with OpenAI API: {e}")
            return {"error": f"OpenAI API chat request failed: {e}"}
    
    async def async_chat(self, messages: List[Dict[str, str]], model=None, temperature=0.7, stream=False) -> Dict[str, Any]:
        """
        Send a chat request to the OpenAI API (async version).
        
        Args:
            messages (list): List of message objects with 'role' and 'content'
            model (str, optional): The model to use. Defaults to the instance's model.
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            
        Returns:
            dict: The response from the API
        """
        model = model or self.model
        
        # Prepare the payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_chat,
                    headers=self._get_headers(),
                    json=payload
                ) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    
                    # Convert to a format similar to Ollama's response
                    return {
                        "model": model,
                        "message": {
                            "role": "assistant",
                            "content": response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        },
                        "done": True
                    }
        except aiohttp.ClientError as e:
            print(f"Error in async chat with OpenAI API: {e}")
            return {"error": f"OpenAI API async chat request failed: {e}"}
    
    async def async_stream_chat(self, messages: List[Dict[str, str]], model=None, temperature=0.7) -> AsyncGenerator[str, None]:
        """
        Stream a chat response from the OpenAI API (async version).
        
        Args:
            messages (list): List of message objects with 'role' and 'content'
            model (str, optional): The model to use. Defaults to the instance's model.
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            
        Yields:
            str: Chunks of the generated response
        """
        model = model or self.model
        
        # Prepare the payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_chat,
                    headers=self._get_headers(),
                    json=payload
                ) as response:
                    response.raise_for_status()
                    
                    # Process the streaming response
                    async for line in response.content:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Handle data: prefix in SSE
                        if line.startswith(b'data: '):
                            line = line[6:]  # Remove 'data: ' prefix
                        
                        # Skip [DONE] message
                        if line == b'[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except aiohttp.ClientError as e:
            print(f"Error streaming from OpenAI API: {e}")
            yield f"Error: OpenAI API streaming failed: {e}"
    
    def stream_query(self, prompt: str, model=None, system_prompt=None, temperature=0.7) -> Generator[str, None, None]:
        """
        Stream a response from the OpenAI API.
        
        Args:
            prompt (str): The prompt to send to the model
            model (str, optional): The model to use. Defaults to the instance's model.
            system_prompt (str, optional): A system prompt to provide context
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            
        Yields:
            str: Chunks of the generated response
        """
        model = model or self.model
        
        # For OpenAI, we use the chat completions endpoint with a formatted message
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Prepare the payload
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        try:
            response = requests.post(
                self.api_chat,
                headers=self._get_headers(),
                json=payload,
                stream=True
            )
            response.raise_for_status()
            
            # Process the streaming response
            for line in response.iter_lines():
                if not line:
                    continue
                
                # Handle data: prefix in SSE
                if line.startswith(b'data: '):
                    line = line[6:]  # Remove 'data: ' prefix
                
                # Skip [DONE] message
                if line == b'[DONE]':
                    break
                
                try:
                    chunk = json.loads(line)
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
                    
        except requests.exceptions.RequestException as e:
            print(f"Error streaming from OpenAI API: {e}")
            yield f"Error: OpenAI API streaming failed: {e}"
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from the OpenAI API.
        
        Returns:
            list: A list of available models
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            # Process the response
            response_data = response.json()
            
            # Extract model information
            models = []
            for model_data in response_data.get("data", []):
                models.append({
                    "name": model_data.get("id"),
                    "id": model_data.get("id"),
                    "created": model_data.get("created")
                })
            
            return models
        except requests.exceptions.RequestException as e:
            print(f"Error listing models from OpenAI API: {e}")
            return []
    
    def is_available(self) -> bool:
        """
        Check if the OpenAI API is available.
        
        Returns:
            bool: True if available, False otherwise
        """
        if not self.api_key:
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except:
            return False


# Example usage
if __name__ == "__main__":
    client = OpenAIClient()
    
    # Check if OpenAI API is available
    if not client.is_available():
        print("OpenAI API is not available. Please check your API key and try again.")
        exit(1)
    
    # List available models
    print("Available models:")
    models = client.list_models()
    for model in models:
        print(f" - {model.get('name')}")
    
    # Simple query example
    print("\nSending a query to the model...")
    response = client.query("Explain what an LLM agent is in simple terms.")
    print(f"\nResponse: {response.get('response')}")
    
    # Chat example
    print("\nStarting a chat conversation...")
    chat_response = client.chat([
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What can I do with OpenAI's GPT models?"}
    ])
    print(f"\nChat response: {chat_response.get('message', {}).get('content')}")
    
    # Streaming example
    print("\nStreaming a response...")
    print("Response: ", end="", flush=True)
    for chunk in client.stream_query("Give me 3 ideas for building agentic behavior with LLMs."):
        print(chunk, end="", flush=True)
        time.sleep(0.01)  # Small delay to simulate real-time streaming
    print()
