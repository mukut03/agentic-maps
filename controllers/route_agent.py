import json
from typing import Dict, Any, List, Tuple, Optional

import requests
from ollama_client import OllamaClient
import prompts

class RouteAgent:
    """
    Handles route generation queries and interfaces with the existing route generation code.
    """
    
    def __init__(self, llm_client: OllamaClient, app_config: Dict[str, Any]):
        """
        Initialize the route agent.
        
        Args:
            llm_client (OllamaClient): The LLM client to use
            app_config (Dict[str, Any]): Application configuration
        """
        self.llm_client = llm_client
        self.app_config = app_config
    
    async def process_query(self, query: str, intent_data: Dict[str, Any], conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a route query.
        
        Args:
            query (str): The user's query
            intent_data (Dict[str, Any]): The intent classification data
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the query
        """
        parameters = intent_data.get("parameters", {})
        
        # Extract origin and destination from the parameters
        origin_text = parameters.get("origin")
        destination_text = parameters.get("destination")
        waypoints_text = parameters.get("waypoints", [])
        
        # Geocode the origin
        origin_data = await self._geocode_location(origin_text)
        if not origin_data:
            return {
                "success": False,
                "message": f"I couldn't find the location '{origin_text}'. Could you please provide a more specific origin?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "origin location",
                    "original_value": origin_text
                }
            }
        
        # Geocode the destination
        destination_data = await self._geocode_location(destination_text)
        if not destination_data:
            return {
                "success": False,
                "message": f"I couldn't find the location '{destination_text}'. Could you please provide a more specific destination?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "destination location",
                    "original_value": destination_text
                }
            }
        
        # Geocode any waypoints
        waypoints_data = []
        for waypoint_text in waypoints_text:
            waypoint_data = await self._geocode_location(waypoint_text)
            if waypoint_data:
                waypoints_data.append(waypoint_data)
            else:
                return {
                    "success": False,
                    "message": f"I couldn't find the waypoint location '{waypoint_text}'. Could you please provide a more specific waypoint?",
                    "requires_clarification": True,
                    "clarification_context": {
                        "topic": "waypoint location",
                        "original_value": waypoint_text
                    }
                }
        
        # Generate the route
        route_data = await self._generate_route(origin_data, destination_data, waypoints_data)
        if not route_data.get("success", False):
            return {
                "success": False,
                "message": f"I couldn't generate a route between {origin_text} and {destination_text}. {route_data.get('error', 'Please try again with different locations.')}",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "route generation",
                    "original_origin": origin_text,
                    "original_destination": destination_text
                }
            }
        
        # Generate a response using the LLM
        response_text = await self._generate_response(query, origin_data, destination_data, waypoints_data, route_data)
        
        # Return the result
        return {
            "success": True,
            "message": response_text,
            "route_data": route_data,
            "origin": origin_data,
            "destination": destination_data,
            "waypoints": waypoints_data,
            "requires_clarification": False
        }
    
    async def _geocode_location(self, location_text: str) -> Optional[Dict[str, Any]]:
        """
        Geocode a location using the existing geocoding endpoint.
        
        Args:
            location_text (str): The location text to geocode
            
        Returns:
            Optional[Dict[str, Any]]: The geocoded location data, or None if geocoding failed
        """
        if not location_text:
            return None
        
        try:
            # Use the existing geocoding endpoint
            response = requests.post(
                f"{self.app_config.get('base_url', 'http://localhost:5000')}/geocode",
                json={"address": location_text},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"Error geocoding location '{location_text}': {str(e)}")
            return None
    
    async def _generate_route(self, origin: Dict[str, Any], destination: Dict[str, Any], 
                             waypoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a route using the existing route endpoint.
        
        Args:
            origin (Dict[str, Any]): The origin location data
            destination (Dict[str, Any]): The destination location data
            waypoints (List[Dict[str, Any]]): The waypoint location data
            
        Returns:
            Dict[str, Any]: The route data
        """
        try:
            # Prepare the request data
            request_data = {
                "origin": {"lat": origin["lat"], "lng": origin["lng"]},
                "destination": {"lat": destination["lat"], "lng": destination["lng"]},
                "waypoints": [{"lat": wp["lat"], "lng": wp["lng"]} for wp in waypoints]
            }
            
            # Use the existing route endpoint
            response = requests.post(
                f"{self.app_config.get('base_url', 'http://localhost:5000')}/route",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                route_data = response.json()
                return {"success": True, "data": route_data}
            else:
                error_data = response.json()
                return {"success": False, "error": error_data.get("error", "Unknown error")}
                
        except Exception as e:
            print(f"Error generating route: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _generate_response(self, query: str, origin: Dict[str, Any], destination: Dict[str, Any],
                               waypoints: List[Dict[str, Any]], route_data: Dict[str, Any]) -> str:
        """
        Generate a natural language response for the route query.
        
        Args:
            query (str): The user's query
            origin (Dict[str, Any]): The origin location data
            destination (Dict[str, Any]): The destination location data
            waypoints (List[Dict[str, Any]]): The waypoint location data
            route_data (Dict[str, Any]): The route data
            
        Returns:
            str: The natural language response
        """
        # Create a prompt for the LLM
        system_prompt = prompts.ROUTE_AGENT_PROMPT
        
        # Add route information to the prompt
        route_info = route_data.get("data", {})
        distance_text = route_info.get("distance_text", "Unknown distance")
        duration_text = route_info.get("duration_text", "Unknown duration")
        
        user_prompt = f"""
Generate a response for a route from {origin.get('display_name')} to {destination.get('display_name')}.

Route details:
- Distance: {distance_text}
- Duration: {duration_text}
"""

        if waypoints:
            user_prompt += "- Waypoints:\n"
            for i, wp in enumerate(waypoints):
                user_prompt += f"  {i+1}. {wp.get('display_name')}\n"
        
        user_prompt += "\nOriginal query: " + query
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            return response.get("message", {}).get("content", "I've found a route for you.")
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return f"I've found a route from {origin.get('display_name')} to {destination.get('display_name')}. The journey is {distance_text} and will take approximately {duration_text}. Would you like to see places or natural features along this route?"
