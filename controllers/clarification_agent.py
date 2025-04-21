import json
from typing import Dict, Any, List, Optional

from llm.ollama_client import OllamaClient
from utils import prompts

class ClarificationAgent:
    """
    Handles ambiguous queries and generates appropriate clarification questions.
    """
    
    def __init__(self, llm_client: OllamaClient):
        """
        Initialize the clarification agent.
        
        Args:
            llm_client (OllamaClient): The LLM client to use
        """
        self.llm_client = llm_client
    
    async def process_clarification_request(self, query: str, clarification_context: Dict[str, Any], 
                                         conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a clarification request.
        
        Args:
            query (str): The user's query
            clarification_context (Dict[str, Any]): The context for the clarification
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the clarification
        """
        # Get the topic of the clarification
        topic = clarification_context.get("topic", "unknown")
        
        # Handle different clarification topics
        if topic == "origin location" or topic == "destination location" or topic == "waypoint location":
            return await self._handle_location_clarification(query, clarification_context, conversation_state)
        elif topic == "waypoint removal":
            return await self._handle_waypoint_removal_clarification(query, clarification_context, conversation_state)
        elif topic == "missing route":
            return await self._handle_missing_route_clarification(query, clarification_context, conversation_state)
        else:
            # Generate a generic clarification response
            return await self._generate_generic_clarification_response(query, clarification_context, conversation_state)
    
    async def generate_clarification_question(self, intent_data: Dict[str, Any], 
                                           conversation_state: Dict[str, Any]) -> str:
        """
        Generate a clarification question for ambiguous queries.
        
        Args:
            intent_data (Dict[str, Any]): The intent classification data
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            str: The clarification question
        """
        # Check if the intent data already has a clarification question
        if intent_data.get("requires_clarification") and intent_data.get("clarification_question"):
            return intent_data["clarification_question"]
        
        # Create a prompt for the LLM
        system_prompt = prompts.CLARIFICATION_AGENT_PROMPT
        
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
        
        # Prepare the user prompt
        user_prompt = f"""
I need to ask for clarification about a user query.

Intent: {intent_data.get('intent', 'UNKNOWN')}
Parameters: {json.dumps(intent_data.get('parameters', {}), indent=2)}
Confidence: {intent_data.get('confidence', 0.0)}

What's a good clarification question to ask the user?
"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            return response.get("message", {}).get("content", "Could you please provide more information?")
        except Exception as e:
            print(f"Error generating clarification question: {str(e)}")
            return "I need more information to help you. Could you please provide more details?"
    
    async def _handle_location_clarification(self, query: str, clarification_context: Dict[str, Any], 
                                          conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle clarification for location queries.
        
        Args:
            query (str): The user's query
            clarification_context (Dict[str, Any]): The context for the clarification
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the clarification
        """
        # Get the original value
        original_value = clarification_context.get("original_value", "")
        
        # Create a prompt for the LLM
        system_prompt = prompts.CLARIFICATION_AGENT_PROMPT
        
        user_prompt = f"""
The user is providing clarification about a location.

Original location: {original_value}
User's clarification: {query}

What location is the user referring to? Extract the location name from the user's response.
"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.2)
            content = response.get("message", {}).get("content", "")
            
            # Extract the location from the response
            # This is a simple extraction, in a real system you might want to use more sophisticated parsing
            location = content.strip()
            
            # Return the clarified location
            return {
                "success": True,
                "clarified_value": location,
                "message": f"Thank you for clarifying. I'll use '{location}' as the location."
            }
        except Exception as e:
            print(f"Error handling location clarification: {str(e)}")
            return {
                "success": False,
                "message": "I'm still having trouble understanding the location. Could you please try again with a different location name?"
            }
    
    async def _handle_waypoint_removal_clarification(self, query: str, clarification_context: Dict[str, Any], 
                                                  conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle clarification for waypoint removal queries.
        
        Args:
            query (str): The user's query
            clarification_context (Dict[str, Any]): The context for the clarification
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the clarification
        """
        # Get the available waypoints
        waypoints = clarification_context.get("waypoints", [])
        
        # Create a prompt for the LLM
        system_prompt = prompts.CLARIFICATION_AGENT_PROMPT
        
        user_prompt = f"""
The user is providing clarification about which waypoint to remove.

Available waypoints: {', '.join(waypoints)}
User's clarification: {query}

Which waypoint is the user referring to? Extract the waypoint name from the user's response.
"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.2)
            content = response.get("message", {}).get("content", "")
            
            # Extract the waypoint from the response
            waypoint = content.strip()
            
            # Check if the waypoint is in the list of available waypoints
            if waypoint in waypoints:
                # Return the clarified waypoint
                return {
                    "success": True,
                    "clarified_value": waypoint,
                    "message": f"Thank you for clarifying. I'll remove the waypoint '{waypoint}'."
                }
            else:
                # Try to find a partial match
                for wp in waypoints:
                    if waypoint.lower() in wp.lower() or wp.lower() in waypoint.lower():
                        return {
                            "success": True,
                            "clarified_value": wp,
                            "message": f"Thank you for clarifying. I'll remove the waypoint '{wp}'."
                        }
                
                # If no match found, ask for clarification again
                return {
                    "success": False,
                    "message": f"I couldn't find a waypoint matching '{waypoint}'. Available waypoints are: {', '.join(waypoints)}. Which one would you like to remove?"
                }
        except Exception as e:
            print(f"Error handling waypoint removal clarification: {str(e)}")
            return {
                "success": False,
                "message": "I'm still having trouble understanding which waypoint to remove. Could you please try again?"
            }
    
    async def _handle_missing_route_clarification(self, query: str, clarification_context: Dict[str, Any], 
                                               conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle clarification for missing route queries.
        
        Args:
            query (str): The user's query
            clarification_context (Dict[str, Any]): The context for the clarification
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the clarification
        """
        # Create a prompt for the LLM
        system_prompt = prompts.CLARIFICATION_AGENT_PROMPT
        
        user_prompt = f"""
The user needs to create a route before performing the requested action.

User's response: {query}

Does the user want to create a route? If so, extract the origin and destination from their response.
"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.2)
            content = response.get("message", {}).get("content", "")
            
            # Check if the response indicates the user wants to create a route
            if "yes" in content.lower() or "origin" in content.lower() or "destination" in content.lower():
                # Try to extract origin and destination
                origin = None
                destination = None
                
                if "origin" in content.lower() and "destination" in content.lower():
                    # Extract origin and destination using simple parsing
                    # In a real system, you might want to use more sophisticated parsing
                    origin_start = content.lower().find("origin") + 6
                    origin_end = content.lower().find("destination")
                    if origin_start > 6 and origin_end > origin_start:
                        origin = content[origin_start:origin_end].strip()
                    
                    destination_start = content.lower().find("destination") + 11
                    if destination_start > 11:
                        destination = content[destination_start:].strip()
                
                if origin and destination:
                    return {
                        "success": True,
                        "wants_route": True,
                        "origin": origin,
                        "destination": destination,
                        "message": f"I'll create a route from {origin} to {destination}."
                    }
                else:
                    return {
                        "success": True,
                        "wants_route": True,
                        "message": "I'd be happy to create a route for you. Could you please tell me the origin and destination?"
                    }
            else:
                return {
                    "success": True,
                    "wants_route": False,
                    "message": "No problem. Let me know if you'd like to create a route later."
                }
        except Exception as e:
            print(f"Error handling missing route clarification: {str(e)}")
            return {
                "success": False,
                "message": "I'm having trouble understanding your response. Would you like to create a route now?"
            }
    
    async def _generate_generic_clarification_response(self, query: str, clarification_context: Dict[str, Any], 
                                                    conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a generic clarification response.
        
        Args:
            query (str): The user's query
            clarification_context (Dict[str, Any]): The context for the clarification
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the clarification
        """
        # Create a prompt for the LLM
        system_prompt = prompts.CLARIFICATION_AGENT_PROMPT
        
        user_prompt = f"""
The user is providing clarification about: {clarification_context.get('topic', 'a query')}

Original context: {json.dumps(clarification_context, indent=2)}
User's clarification: {query}

How should I interpret the user's clarification? What's the key information they're providing?
"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            content = response.get("message", {}).get("content", "")
            
            # Return a generic response
            return {
                "success": True,
                "clarified_value": query,
                "interpretation": content,
                "message": "Thank you for the clarification. I'll use that information to help you."
            }
        except Exception as e:
            print(f"Error generating generic clarification response: {str(e)}")
            return {
                "success": False,
                "message": "I'm still having trouble understanding. Could you please try again with a clearer explanation?"
            }
