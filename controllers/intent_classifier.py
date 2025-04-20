import json
from typing import Dict, Any, Optional, Tuple, Union

from llm.ollama_client import OllamaClient
from llm.openai_client import OpenAIClient
from utils import prompts

class IntentClassifier:
    """
    Uses the LLM to classify user queries into intents and extract relevant parameters.
    """
    
    def __init__(self, llm_client: Union[OllamaClient, OpenAIClient]):
        """
        Initialize the intent classifier.
        
        Args:
            llm_client (Union[OllamaClient, OpenAIClient]): The LLM client to use for classification
        """
        self.llm_client = llm_client
    
    async def classify(self, query: str, conversation_history: list, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the user's query into an intent and extract relevant parameters.
        
        Args:
            query (str): The user's query
            conversation_history (list): The conversation history
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The classification result
        """
        # Create a prompt for the LLM
        system_prompt = prompts.INTENT_CLASSIFIER_PROMPT
        
        # Add context about the current route if available
        if conversation_state.get("has_active_route"):
            origin = conversation_state.get("origin", {})
            destination = conversation_state.get("destination", {})
            waypoints = conversation_state.get("waypoints", [])
            
            context = "\nCurrent route information:\n"
            context += f"- Origin: {origin.get('display_name', 'Unknown')}\n"
            context += f"- Destination: {destination.get('display_name', 'Unknown')}\n"
            
            if waypoints:
                context += "- Waypoints:\n"
                for i, wp in enumerate(waypoints):
                    context += f"  {i+1}. {wp.get('display_name', 'Unknown')}\n"
            
            system_prompt += context
        
        # Add context about pending clarification if applicable
        if conversation_state.get("pending_clarification"):
            clarification_context = conversation_state.get("clarification_context", {})
            system_prompt += "\nThe user is responding to a clarification request about: "
            system_prompt += clarification_context.get("topic", "a previous query")
            system_prompt += "\n"
        
        # Prepare messages for the LLM - only use the current query for intent classification
        # Do not include conversation history as it can confuse the intent classifier
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
            # Get the classification from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.2)
            content = response.get("message", {}).get("content", "")
            
            # Extract the JSON from the response
            try:
                # Find JSON in the response (it might be surrounded by markdown code blocks or other text)
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    classification = json.loads(json_str)
                else:
                    # If no JSON found, create a default classification
                    classification = {
                        "intent": "UNKNOWN",
                        "parameters": {},
                        "confidence": 0.0,
                        "requires_clarification": True,
                        "clarification_question": "I'm not sure what you're asking. Could you please rephrase your question?"
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, create a default classification
                classification = {
                    "intent": "UNKNOWN",
                    "parameters": {},
                    "confidence": 0.0,
                    "requires_clarification": True,
                    "clarification_question": "I'm having trouble understanding your request. Could you please rephrase it?"
                }
            
            # Add the original query to the classification
            classification["original_query"] = query
            
            return classification
            
        except Exception as e:
            # If the LLM call fails, return a default classification
            return {
                "intent": "UNKNOWN",
                "parameters": {},
                "confidence": 0.0,
                "requires_clarification": True,
                "clarification_question": f"I encountered an error processing your request. Could you please try again? Error: {str(e)}"
            }
    
    def validate_parameters(self, intent: str, parameters: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate the parameters for a given intent.
        
        Args:
            intent (str): The intent
            parameters (Dict[str, Any]): The parameters
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple of (is_valid, error_message)
        """
        if intent == "ROUTE_QUERY":
            # Check if origin and destination are present
            if not parameters.get("origin"):
                return False, "Please specify an origin location."
            if not parameters.get("destination"):
                return False, "Please specify a destination location."
            return True, None
            
        elif intent == "ADD_WAYPOINT":
            # Check if waypoint is present
            if not parameters.get("waypoint"):
                return False, "Please specify a location to add as a waypoint."
            return True, None
            
        elif intent == "REMOVE_WAYPOINT":
            # Check if waypoint is present
            if not parameters.get("waypoint"):
                return False, "Please specify which waypoint to remove."
            return True, None
            
        elif intent in ["PLACES_QUERY", "FEATURES_QUERY"]:
            # Check if there's an active route
            # This is handled by the agent, not here
            return True, None
            
        elif intent in ["GENERAL_QUERY", "CLARIFICATION", "UNKNOWN"]:
            # No specific parameters to validate
            return True, None
            
        else:
            # Unknown intent
            return False, f"Unknown intent: {intent}"
