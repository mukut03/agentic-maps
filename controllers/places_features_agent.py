import json
from typing import Dict, Any, List, Optional

import requests
from ollama_client import OllamaClient
import prompts

class PlacesFeaturesAgent:
    """
    Handles queries about places and natural features along routes.
    Manages proactive data loading and caching.
    """
    
    def __init__(self, llm_client: OllamaClient, app_config: Dict[str, Any]):
        """
        Initialize the places and features agent.
        
        Args:
            llm_client (OllamaClient): The LLM client to use
            app_config (Dict[str, Any]): Application configuration
        """
        self.llm_client = llm_client
        self.app_config = app_config
    
    async def process_places_query(self, query: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a query about places along a route.
        
        Args:
            query (str): The user's query
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the query
        """
        # Check if there's an active route
        if not conversation_state.get("has_active_route", False):
            return {
                "success": False,
                "message": "I don't have an active route to show places for. Would you like to create a route first?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "missing route",
                    "suggestion": "create a route"
                }
            }
        
        # Check if we already have places data
        places_data = conversation_state.get("places_data")
        
        # If we don't have places data, fetch it
        if not places_data:
            places_data = await self._fetch_places_data(conversation_state)
            
            if not places_data:
                return {
                    "success": False,
                    "message": "I couldn't fetch information about places along this route. Would you like to try again?",
                    "requires_clarification": True,
                    "clarification_context": {
                        "topic": "places data fetch failure"
                    }
                }
        
        # Generate a response using the LLM
        response_text = await self._generate_places_response(query, places_data, conversation_state)
        
        # Return the result
        return {
            "success": True,
            "message": response_text,
            "places_data": places_data,
            "requires_clarification": False
        }
    
    async def process_features_query(self, query: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a query about natural features along a route.
        
        Args:
            query (str): The user's query
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The result of processing the query
        """
        # Check if there's an active route
        if not conversation_state.get("has_active_route", False):
            return {
                "success": False,
                "message": "I don't have an active route to show natural features for. Would you like to create a route first?",
                "requires_clarification": True,
                "clarification_context": {
                    "topic": "missing route",
                    "suggestion": "create a route"
                }
            }
        
        # Check if we already have features data
        features_data = conversation_state.get("features_data")
        
        # If we don't have features data, fetch it
        if not features_data:
            features_data = await self._fetch_features_data(conversation_state)
            
            if not features_data:
                return {
                    "success": False,
                    "message": "I couldn't fetch information about natural features along this route. Would you like to try again?",
                    "requires_clarification": True,
                    "clarification_context": {
                        "topic": "features data fetch failure"
                    }
                }
        
        # Generate a response using the LLM
        response_text = await self._generate_features_response(query, features_data, conversation_state)
        
        # Return the result
        return {
            "success": True,
            "message": response_text,
            "features_data": features_data,
            "requires_clarification": False
        }
    
    async def proactive_load_data(self, conversation_state: Dict[str, Any]) -> None:
        """
        Proactively load places and features data for a route.
        
        Args:
            conversation_state (Dict[str, Any]): The current conversation state
        """
        # Check if there's an active route
        if not conversation_state.get("has_active_route", False):
            return
        
        # Check if we already have places data
        if not conversation_state.get("places_data"):
            # Fetch places data in the background
            places_data = await self._fetch_places_data(conversation_state)
            if places_data:
                conversation_state["places_data"] = places_data
        
        # Check if we already have features data
        if not conversation_state.get("features_data"):
            # Fetch features data in the background
            features_data = await self._fetch_features_data(conversation_state)
            if features_data:
                conversation_state["features_data"] = features_data
    
    async def _fetch_places_data(self, conversation_state: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch places data for a route.
        
        Args:
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Optional[List[Dict[str, Any]]]: The places data, or None if fetching failed
        """
        try:
            # Get the route data
            route_data = conversation_state.get("route_data", {}).get("data", {})
            
            # Check if we have polyline coordinates
            if not route_data.get("polyline_coords"):
                return None
            
            # Prepare the request data
            request_data = {
                "polyline_coords": route_data["polyline_coords"],
                "radius_m": 5000,  # 5 km radius as specified
                "method": "node"
            }
            
            # Use the existing places endpoint
            response = requests.post(
                f"{self.app_config.get('base_url', 'http://localhost:5000')}/places",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                places_data = response.json()
                return places_data.get("places", [])
            else:
                return None
                
        except Exception as e:
            print(f"Error fetching places data: {str(e)}")
            return None
    
    async def _fetch_features_data(self, conversation_state: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch natural features data for a route.
        
        Args:
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Optional[List[Dict[str, Any]]]: The features data, or None if fetching failed
        """
        try:
            # Get the route data
            route_data = conversation_state.get("route_data", {}).get("data", {})
            
            # Check if we have polyline coordinates
            if not route_data.get("polyline_coords"):
                return None
            
            # Prepare the request data
            request_data = {
                "polyline_coords": route_data["polyline_coords"],
                "radius_m": 1000,  # 1 km radius as specified
                "method": "way"
            }
            
            # Use the existing natural features endpoint
            response = requests.post(
                f"{self.app_config.get('base_url', 'http://localhost:5000')}/natural_features",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                features_data = response.json()
                return features_data.get("features", [])
            else:
                return None
                
        except Exception as e:
            print(f"Error fetching features data: {str(e)}")
            return None
    
    async def _generate_places_response(self, query: str, places_data: List[Dict[str, Any]], 
                                      conversation_state: Dict[str, Any]) -> str:
        """
        Generate a natural language response for a places query.
        
        Args:
            query (str): The user's query
            places_data (List[Dict[str, Any]]): The places data
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            str: The natural language response
        """
        # Create a prompt for the LLM
        system_prompt = prompts.PLACES_AGENT_PROMPT
        
        # Get route information
        origin = conversation_state.get("origin", {}).get("display_name", "Unknown origin")
        destination = conversation_state.get("destination", {}).get("display_name", "Unknown destination")
        
        # Count places by type
        place_counts = {"city": 0, "town": 0, "village": 0}
        for place in places_data:
            place_type = place.get("type")
            if place_type in place_counts:
                place_counts[place_type] += 1
        
        # Create a summary of places
        places_summary = f"Places along the route from {origin} to {destination}:\n"
        places_summary += f"- {place_counts['city']} cities\n"
        places_summary += f"- {place_counts['town']} towns\n"
        places_summary += f"- {place_counts['village']} villages\n\n"
        
        # Add notable places (up to 5 of each type)
        places_summary += "Notable places:\n"
        
        # Add cities
        cities = [p for p in places_data if p.get("type") == "city"][:5]
        if cities:
            places_summary += "Cities:\n"
            for city in cities:
                places_summary += f"- {city.get('name')}\n"
        
        # Add towns
        towns = [p for p in places_data if p.get("type") == "town"][:5]
        if towns:
            places_summary += "Towns:\n"
            for town in towns:
                places_summary += f"- {town.get('name')}\n"
        
        # Add villages
        villages = [p for p in places_data if p.get("type") == "village"][:5]
        if villages:
            places_summary += "Villages:\n"
            for village in villages:
                places_summary += f"- {village.get('name')}\n"
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}\n\n{places_summary}"}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            return response.get("message", {}).get("content", "Here are the places along your route.")
        except Exception as e:
            print(f"Error generating places response: {str(e)}")
            
            # Fallback response
            total_places = sum(place_counts.values())
            return f"Along your route from {origin} to {destination}, you'll pass through {total_places} places, including {place_counts['city']} cities, {place_counts['town']} towns, and {place_counts['village']} villages. Some notable places include {', '.join([p.get('name') for p in (cities + towns)[:3]])}."
    
    async def _generate_features_response(self, query: str, features_data: List[Dict[str, Any]], 
                                        conversation_state: Dict[str, Any]) -> str:
        """
        Generate a natural language response for a features query.
        
        Args:
            query (str): The user's query
            features_data (List[Dict[str, Any]]): The features data
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            str: The natural language response
        """
        # Create a prompt for the LLM
        system_prompt = prompts.FEATURES_AGENT_PROMPT
        
        # Get route information
        origin = conversation_state.get("origin", {}).get("display_name", "Unknown origin")
        destination = conversation_state.get("destination", {}).get("display_name", "Unknown destination")
        
        # Count features by type
        feature_counts = {}
        for feature in features_data:
            feature_type = feature.get("type")
            if feature_type not in feature_counts:
                feature_counts[feature_type] = 0
            feature_counts[feature_type] += 1
        
        # Create a summary of features
        features_summary = f"Natural features along the route from {origin} to {destination}:\n"
        
        for feature_type, count in feature_counts.items():
            features_summary += f"- {count} {feature_type}s\n"
        
        features_summary += "\nNotable features:\n"
        
        # Group features by type
        features_by_type = {}
        for feature in features_data:
            feature_type = feature.get("type")
            if feature_type not in features_by_type:
                features_by_type[feature_type] = []
            features_by_type[feature_type].append(feature)
        
        # Add up to 3 features of each type
        for feature_type, features in features_by_type.items():
            # Skip unnamed features
            named_features = [f for f in features if f.get("name") != "unnamed"]
            if named_features:
                features_summary += f"{feature_type.capitalize()}s:\n"
                for feature in named_features[:3]:
                    features_summary += f"- {feature.get('name')}\n"
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}\n\n{features_summary}"}
        ]
        
        # Get the response from the LLM
        try:
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            return response.get("message", {}).get("content", "Here are the natural features along your route.")
        except Exception as e:
            print(f"Error generating features response: {str(e)}")
            
            # Fallback response
            feature_types = list(feature_counts.keys())
            total_features = sum(feature_counts.values())
            
            if total_features == 0:
                return f"I couldn't find any significant natural features along your route from {origin} to {destination}."
            
            # Get a few named features for the fallback response
            named_features = []
            for features in features_by_type.values():
                for feature in features:
                    if feature.get("name") != "unnamed":
                        named_features.append(feature.get("name"))
                        if len(named_features) >= 3:
                            break
                if len(named_features) >= 3:
                    break
            
            if named_features:
                return f"Along your route from {origin} to {destination}, you'll encounter {total_features} natural features, including {', '.join(feature_types[:3])}. Some notable features include {', '.join(named_features)}."
            else:
                return f"Along your route from {origin} to {destination}, you'll encounter {total_features} natural features, including {', '.join(feature_types[:3])}."
