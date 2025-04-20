import json
import time
import aiohttp
import asyncio
import requests  # Keep for synchronous methods

class OllamaClient:
    """
    A simple client for interacting with Ollama API.
    This allows querying locally hosted LLMs without using frameworks like LangChain.
    """
    
    def __init__(self, base_url="http://localhost:11434", model="llama3.2:latest"):
        """
        Initialize the Ollama client.
        
        Args:
            base_url (str): The base URL of the Ollama API
            model (str): The default model to use for queries
        """
        self.base_url = base_url
        self.model = model
        # API endpoints
        self.api_generate = f"{base_url}/api/generate"  # Legacy endpoint
        self.api_chat = f"{base_url}/api/chat"
        self.api_completions = f"{base_url}/v1/completions"  # New endpoint for completions
        
    def query(self, prompt, model=None, system_prompt=None, temperature=0.2, stream=False):
        """
        Send a query to the Ollama API and get a response.
        
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
        
        # Try the legacy generate endpoint first
        payload_generate = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": stream
        }
        
        if system_prompt:
            payload_generate["system"] = system_prompt
            
        try:
            response = requests.post(self.api_generate, json=payload_generate)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error using generate endpoint: {e}")
            print("Trying completions endpoint instead...")
            
            # If generate fails, try the completions endpoint
            try:
                # Format for completions endpoint
                payload_completions = {
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": stream
                }
                
                if system_prompt:
                    # For completions, we prepend the system prompt to the user prompt
                    payload_completions["prompt"] = f"{system_prompt}\n\n{prompt}"
                
                response = requests.post(self.api_completions, json=payload_completions)
                response.raise_for_status()
                completion_response = response.json()
                
                # Convert completions response format to generate response format
                return {
                    "model": model,
                    "response": completion_response.get("choices", [{}])[0].get("text", ""),
                    "done": True
                }
            except requests.exceptions.RequestException as e2:
                print(f"Error using completions endpoint: {e2}")
                return {"error": f"Both generate and completions endpoints failed: {e}, {e2}"}
    
    def chat(self, messages, model=None, temperature=0.7, stream=False):
        """
        Send a chat request to the Ollama API (synchronous version).
        
        Args:
            messages (list): List of message objects with 'role' and 'content'
            model (str, optional): The model to use. Defaults to the instance's model.
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            
        Returns:
            dict: The response from the API
        """
        model = model or self.model
        
        # Try the legacy chat endpoint first
        payload_chat = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            response = requests.post(self.api_chat, json=payload_chat)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error using chat endpoint: {e}")
            print("Trying OpenAI-compatible chat endpoint instead...")
            
            # If chat fails, try the OpenAI-compatible chat endpoint
            try:
                # OpenAI-compatible chat endpoint
                api_openai_chat = f"{self.base_url}/v1/chat/completions"
                
                # Format for OpenAI-compatible chat endpoint
                payload_openai = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": stream
                }
                
                response = requests.post(api_openai_chat, json=payload_openai)
                response.raise_for_status()
                openai_response = response.json()
                
                # Convert OpenAI response format to Ollama chat response format
                return {
                    "model": model,
                    "message": {
                        "role": "assistant",
                        "content": openai_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    },
                    "done": True
                }
            except requests.exceptions.RequestException as e2:
                print(f"Error using OpenAI-compatible chat endpoint: {e2}")
                return {"error": f"Both chat endpoints failed: {e}, {e2}"}
    
    async def async_chat(self, messages, model=None, temperature=0.7, stream=False):
        """
        Send a chat request to the Ollama API (async version).
        
        Args:
            messages (list): List of message objects with 'role' and 'content'
            model (str, optional): The model to use. Defaults to the instance's model.
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            
        Returns:
            dict: The response from the API
        """
        model = model or self.model
        
        # Try the legacy chat endpoint first
        payload_chat = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_chat, json=payload_chat) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            print(f"Error using chat endpoint: {e}")
            print("Trying OpenAI-compatible chat endpoint instead...")
            
            # If chat fails, try the OpenAI-compatible chat endpoint
            try:
                # OpenAI-compatible chat endpoint
                api_openai_chat = f"{self.base_url}/v1/chat/completions"
                
                # Format for OpenAI-compatible chat endpoint
                payload_openai = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": stream
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_openai_chat, json=payload_openai) as response:
                        response.raise_for_status()
                        openai_response = await response.json()
                
                # Convert OpenAI response format to Ollama chat response format
                return {
                    "model": model,
                    "message": {
                        "role": "assistant",
                        "content": openai_response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    },
                    "done": True
                }
            except aiohttp.ClientError as e2:
                print(f"Error using OpenAI-compatible chat endpoint: {e2}")
                return {"error": f"Both chat endpoints failed: {e}, {e2}"}
    
    async def async_stream_chat(self, messages, model=None, temperature=0.7):
        """
        Stream a chat response from the Ollama API (async version).
        
        Args:
            messages (list): List of message objects with 'role' and 'content'
            model (str, optional): The model to use. Defaults to the instance's model.
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            
        Yields:
            str: Chunks of the generated response
        """
        model = model or self.model
        
        # Try the legacy chat endpoint first with streaming enabled
        payload_chat = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_chat, json=payload_chat) as response:
                    response.raise_for_status()
                    
                    # Process the streaming response
                    async for line in response.content:
                        line = line.strip()
                        if line:
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield content
                                
                                # If we've reached the end of the response, break
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
                                
        except aiohttp.ClientError as e:
            print(f"Error streaming from chat endpoint: {e}")
            print("Trying OpenAI-compatible chat endpoint instead...")
            
            # If chat fails, try the OpenAI-compatible chat endpoint
            try:
                # OpenAI-compatible chat endpoint
                api_openai_chat = f"{self.base_url}/v1/chat/completions"
                
                # Format for OpenAI-compatible chat endpoint
                payload_openai = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_openai_chat, json=payload_openai) as response:
                        response.raise_for_status()
                        
                        # Process the streaming response from OpenAI-compatible chat endpoint
                        async for line in response.content:
                            line = line.strip()
                            if line:
                                try:
                                    # Skip empty lines
                                    if not line:
                                        continue
                                        
                                    # Handle data: prefix in SSE
                                    if line.startswith(b'data: '):
                                        line = line[6:]  # Remove 'data: ' prefix
                                        
                                    # Skip [DONE] message
                                    if line == b'[DONE]':
                                        break
                                        
                                    chunk = json.loads(line)
                                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                                except json.JSONDecodeError:
                                    continue
                
            except aiohttp.ClientError as e2:
                print(f"Error streaming from OpenAI-compatible chat endpoint: {e2}")
                yield f"Error: Both streaming endpoints failed: {e}, {e2}"
    
    def stream_query(self, prompt, model=None, system_prompt=None, temperature=0.7):
        """
        Stream a response from the Ollama API.
        
        Args:
            prompt (str): The prompt to send to the model
            model (str, optional): The model to use. Defaults to the instance's model.
            system_prompt (str, optional): A system prompt to provide context
            temperature (float, optional): Controls randomness. Defaults to 0.7.
            
        Yields:
            str: Chunks of the generated response
        """
        model = model or self.model
        
        # Try the legacy generate endpoint first
        payload_generate = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": True
        }
        
        if system_prompt:
            payload_generate["system"] = system_prompt
            
        try:
            response = requests.post(self.api_generate, json=payload_generate, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    yield chunk.get("response", "")
                    
                    # If we've reached the end of the response, break
                    if chunk.get("done", False):
                        break
                        
        except requests.exceptions.RequestException as e:
            print(f"Error streaming from generate endpoint: {e}")
            print("Trying OpenAI-compatible completions endpoint instead...")
            
            # If generate fails, try the OpenAI-compatible completions endpoint
            try:
                # OpenAI-compatible completions endpoint
                api_openai_completions = f"{self.base_url}/v1/completions"
                
                # Format for OpenAI-compatible completions endpoint
                payload_openai = {
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": True
                }
                
                if system_prompt:
                    # For completions, we prepend the system prompt to the user prompt
                    payload_openai["prompt"] = f"{system_prompt}\n\n{prompt}"
                
                response = requests.post(api_openai_completions, json=payload_openai, stream=True)
                response.raise_for_status()
                
                # Process the streaming response from OpenAI-compatible completions endpoint
                for line in response.iter_lines():
                    if line:
                        try:
                            # Skip empty lines
                            if line.strip() == b'':
                                continue
                                
                            # Handle data: prefix in SSE
                            if line.startswith(b'data: '):
                                line = line[6:]  # Remove 'data: ' prefix
                                
                            # Skip [DONE] message
                            if line.strip() == b'[DONE]':
                                break
                                
                            chunk = json.loads(line)
                            text = chunk.get("choices", [{}])[0].get("text", "")
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            continue
                
            except requests.exceptions.RequestException as e2:
                print(f"Error streaming from OpenAI-compatible completions endpoint: {e2}")
                
                # Try OpenAI-compatible chat completions endpoint as a last resort
                try:
                    # OpenAI-compatible chat completions endpoint
                    api_openai_chat = f"{self.base_url}/v1/chat/completions"
                    
                    # Format for OpenAI-compatible chat completions endpoint
                    payload_chat = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt} if system_prompt else {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "stream": True
                    }
                    
                    response = requests.post(api_openai_chat, json=payload_chat, stream=True)
                    response.raise_for_status()
                    
                    # Process the streaming response from OpenAI-compatible chat completions endpoint
                    for line in response.iter_lines():
                        if line:
                            try:
                                # Skip empty lines
                                if line.strip() == b'':
                                    continue
                                    
                                # Handle data: prefix in SSE
                                if line.startswith(b'data: '):
                                    line = line[6:]  # Remove 'data: ' prefix
                                    
                                # Skip [DONE] message
                                if line.strip() == b'[DONE]':
                                    break
                                    
                                chunk = json.loads(line)
                                text = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if text:
                                    yield text
                            except json.JSONDecodeError:
                                continue
                    
                except requests.exceptions.RequestException as e3:
                    print(f"Error streaming from OpenAI-compatible chat completions endpoint: {e3}")
                    yield f"Error: All streaming endpoints failed: {e}, {e2}, {e3}"
    
    def list_models(self):
        """
        List all available models in the Ollama instance.
        
        Returns:
            list: A list of available models
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except requests.exceptions.RequestException as e:
            print(f"Error listing models: {e}")
            return []
            
    def is_available(self):
        """
        Check if the Ollama API is available.
        
        Returns:
            bool: True if available, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/version")
            return response.status_code == 200
        except:
            return False


# Example usage
if __name__ == "__main__":
    client = OllamaClient()
    
    # Check if Ollama is running
    if not client.is_available():
        print("Ollama is not running. Please start Ollama and try again.")
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
        {"role": "user", "content": "What can I do with Ollama?"}
    ])
    print(f"\nChat response: {chat_response.get('message', {}).get('content')}")
    
    # Streaming example
    print("\nStreaming a response...")
    print("Response: ", end="", flush=True)
    for chunk in client.stream_query("Give me 3 ideas for building agentic behavior with LLMs."):
        print(chunk, end="", flush=True)
        time.sleep(0.01)  # Small delay to simulate real-time streaming
    print()
