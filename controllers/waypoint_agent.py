import json
from typing import Dict, Any, List, Optional

import requests
from ollama_client import OllamaClient
import prompts

class WaypointAgent:
    """
    Handles adding, removing, and modifying waypoints on routes.
    """
    
    def __init__(self, llm_client: OllamaClient, app_config: Dict[str, Any]):
        """
        Initialize the waypoint agent.
        
        Args:
            llm_client (OllamaClient): The LLM client to use
            app_config (Dict[str, Any]): Application configuration
        """
        self.llm_client = llm_client
        self.app_config = app_config
    
    async def process_add_waypoint(self, query: str, intent_data: Dict[str, Any], 
                                 conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request to add a waypoint to a route.
        
        Args:
            query (str): The user's query
            intent_data (Dict[str, Any]): The intent classification data
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the query
        """
        # Check if there's an active route
        if not conversation_state.get("has_active_route", False):
            return {
                "success": False,
                "message": "I don't have an active route to add a waypoint to. Would you like to create a route first?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "missing route",
                    "suggestion": "create a route"
                }
            }
        
        # Extract the waypoint from the parameters
        parameters = intent_data.get("parameters", {})
        waypoint_text = parameters.get("waypoint")
        
        if not waypoint_text:
            return {
                "success": False,
                "message": "I couldn't determine which location you want to add as a waypoint. Could you please specify the location?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "waypoint location",
                    "suggestion": "specify location"
                }
            }
        
        # Geocode the waypoint
        waypoint_data = await self._geocode_location(waypoint_text)
        if not waypoint_data:
            return {
                "success": False,
                "message": f"I couldn't find the location '{waypoint_text}'. Could you please provide a more specific waypoint?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "waypoint location",
                    "original_value": waypoint_text
                }
            }
        
        # Get the current waypoints
        current_waypoints = conversation_state.get("waypoints", [])
        
        # Add the new waypoint
        current_waypoints.append(waypoint_data)
        
        # Update the route with the new waypoint
        origin = conversation_state.get("origin")
        destination = conversation_state.get("destination")
        
        if not origin or not destination:
            return {
                "success": False,
                "message": "I couldn't update the route because the origin or destination is missing.",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "missing route information"
                }
            }
        
        # Generate the updated route
        route_data = await self._generate_route(origin, destination, current_waypoints)
        if not route_data.get("success", False):
            return {
                "success": False,
                "message": f"I couldn't update the route with the new waypoint. {route_data.get('error', 'Please try again with a different waypoint.')}",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "route update failure",
                    "waypoint": waypoint_text
                }
            }
        
        # Generate a response using the LLM
        response_text = await self._generate_add_waypoint_response(query, waypoint_data, current_waypoints, route_data)
        
        # Return the result
        return {
            "success": True,
            "message": response_text,
            "route_data": route_data,
            "waypoints": current_waypoints,
            "requires_clarification": False
        }
    
    async def process_remove_waypoint(self, query: str, intent_data: Dict[str, Any], 
                                    conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request to remove a waypoint from a route.
        
        Args:
            query (str): The user's query
            intent_data (Dict[str, Any]): The intent classification data
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the query
        """
        # Check if there's an active route
        if not conversation_state.get("has_active_route", False):
            return {
                "success": False,
                "message": "I don't have an active route to remove a waypoint from.",
                "requires_clarification": False
            }
        
        # Get the current waypoints
        current_waypoints = conversation_state.get("waypoints", [])
        
        # Check if there are any waypoints to remove
        if not current_waypoints:
            return {
                "success": False,
                "message": "There are no waypoints on the current route to remove.",
                "requires_clarification": False
            }
        
        # Extract the waypoint from the parameters
        parameters = intent_data.get("parameters", {})
        waypoint_text = parameters.get("waypoint")
        
        if not waypoint_text:
            # If no specific waypoint was mentioned, ask for clarification
            waypoint_names = [wp.get("display_name", "Unknown") for wp in current_waypoints]
            
            return {
                "success": False,
                "message": f"Which waypoint would you like to remove? Current waypoints: {', '.join(waypoint_names)}",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "waypoint removal",
                    "waypoints": waypoint_names
                }
            }
        
        # Try to find the waypoint to remove
        removed_waypoint = None
        new_waypoints = []
        
        for wp in current_waypoints:
            wp_name = wp.get("display_name", "").lower()
            if waypoint_text.lower() in wp_name:
                removed_waypoint = wp
            else:
                new_waypoints.append(wp)
        
        # If we couldn't find the waypoint, ask for clarification
        if not removed_waypoint:
            waypoint_names = [wp.get("display_name", "Unknown") for wp in current_waypoints]
            
            return {
                "success": False,
                "message": f"I couldn't find a waypoint matching '{waypoint_text}'. Current waypoints: {', '.join(waypoint_names)}. Which one would you like to remove?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "waypoint removal",
                    "waypoints": waypoint_names,
                    "original_value": waypoint_text
                }
            }
        
        # Update the route with the new waypoints
        origin = conversation_state.get("origin")
        destination = conversation_state.get("destination")
        
        if not origin or not destination:
            return {
                "success": False,
                "message": "I couldn't update the route because the origin or destination is missing.",
                "requires_clarification": False
            }
        
        # Generate the updated route
        route_data = await self._generate_route(origin, destination, new_waypoints)
        if not route_data.get("success", False):
            return {
                "success": False,
                "message": f"I couldn't update the route after removing the waypoint. {route_data.get('error', 'Please try again.')}",
                "requires_clarification": False
            }
        
        # Generate a response using the LLM
        response_text = await self._generate_remove_waypoint_response(query, removed_waypoint, new_waypoints, route_data)
        
        # Return the result
        return {
            "success": True,
            "message": response_text,
            "route_data": route_data,
            "waypoints": new_waypoints,
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
    
    async def _generate_add_waypoint_response(self, query: str, waypoint: Dict[str, Any], 
                                           all_waypoints: List[Dict[str, Any]], 
                                           route_data: Dict[str, Any]) -> str:
        """
        Generate a natural language response for adding a waypoint.
        
        Args:
            query (str): The user's query
            waypoint (Dict[str, Any]): The waypoint that was added
            all_waypoints (List[Dict[str, Any]]): All waypoints on the route
            route_data (Dict[str, Any]): The updated route data
            
        Returns:
            str: The natural language response
        """
        # Create a prompt for the LLM
        system_prompt = prompts.WAYPOINT_AGENT_PROMPT
        
        # Get route information
        route_info = route_data.get("data", {})
        distance_text = route_info.get("distance_text", "Unknown distance")
        duration_text = route_info.get("duration_text", "Unknown duration")
        
        user_prompt = f"""
Generate a response for adding the waypoint '{waypoint.get('display_name')}' to the route.

Route details:
- Distance: {distance_text}
- Duration: {duration_text}
- Total waypoints: {len(all_waypoints)}

Original query: {query}
"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            return response.get("message", {}).get("content", f"I've added {waypoint.get('display_name')} as a waypoint to your route.")
        except Exception as e:
            print(f"Error generating add waypoint response: {str(e)}")
            return f"I've added {waypoint.get('display_name')} as a waypoint to your route. The updated journey is {distance_text} and will take approximately {duration_text}."
    
    async def _generate_remove_waypoint_response(self, query: str, removed_waypoint: Dict[str, Any], 
                                              remaining_waypoints: List[Dict[str, Any]], 
                                              route_data: Dict[str, Any]) -> str:
        """
        Generate a natural language response for removing a waypoint.
        
        Args:
            query (str): The user's query
            removed_waypoint (Dict[str, Any]): The waypoint that was removed
            remaining_waypoints (List[Dict[str, Any]]): The remaining waypoints on the route
            route_data (Dict[str, Any]): The updated route data
            
        Returns:
            str: The natural language response
        """
        # Create a prompt for the LLM
        system_prompt = prompts.WAYPOINT_AGENT_PROMPT
        
        # Get route information
        route_info = route_data.get("data", {})
        distance_text = route_info.get("distance_text", "Unknown distance")
        duration_text = route_info.get("duration_text", "Unknown duration")
        
        user_prompt = f"""
Generate a response for removing the waypoint '{removed_waypoint.get('display_name')}' from the route.

Route details:
- Distance: {distance_text}
- Duration: {duration_text}
- Remaining waypoints: {len(remaining_waypoints)}

Original query: {query}
"""
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            return response.get("message", {}).get("content", f"I've removed {removed_waypoint.get('display_name')} from your route.")
        except Exception as e:
            print(f"Error generating remove waypoint response: {str(e)}")
            return f"I've removed {removed_waypoint.get('display_name')} from your route. The updated journey is {distance_text} and will take approximately {duration_text}."
