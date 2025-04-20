"""
Simplified chat module that only handles sending route information to the LLM.
"""

import json
from typing import Dict, Any, List

from llm.llm_provider import LLMProvider

class SimpleChatController:
    """
    Simplified chat controller that only handles sending route information to the LLM.
    Assumes that the chat feature is only used when a route has already been manually set up.
    """
    
    def __init__(self, app_config: Dict[str, Any]):
        """
        Initialize the simple chat controller.
        
        Args:
            app_config (Dict[str, Any]): Application configuration
        """
        self.app_config = app_config
        # Use LLMProvider to get the appropriate client based on configuration
        self.llm_client = LLMProvider.get_client()
        self.conversation_history = []
        self.route_state = {
            "has_active_route": False,
            "origin": None,
            "destination": None,
            "waypoints": [],
            "route_data": None,
            "places_data": None,
            "features_data": None
        }
    
    def add_user_message(self, message: str) -> None:
        """
        Add a user message to the conversation history.
        
        Args:
            message (str): The user's message
        """
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
    
    def add_assistant_message(self, message: str) -> None:
        """
        Add an assistant message to the conversation history.
        
        Args:
            message (str): The assistant's message
        """
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Returns:
            List[Dict[str, Any]]: The conversation history
        """
        return self.conversation_history
    
    def reset_conversation(self) -> None:
        """
        Reset the conversation history.
        """
        print("Resetting conversation history only (preserving route state)")
        self.conversation_history = []
        
        # Debug: Print route state after reset to confirm it's preserved
        print(f"After reset: has_active_route={self.route_state['has_active_route']}")
        print(f"After reset: has_places_data={self.route_state['places_data'] is not None}")
        print(f"After reset: has_features_data={self.route_state['features_data'] is not None}")
    
    def update_route_state(self, origin: Dict[str, Any], destination: Dict[str, Any], 
                          waypoints: List[Dict[str, Any]], route_data: Dict[str, Any]) -> None:
        """
        Update the route state.
        
        Args:
            origin (Dict[str, Any]): Origin location data
            destination (Dict[str, Any]): Destination location data
            waypoints (List[Dict[str, Any]]): List of waypoint location data
            route_data (Dict[str, Any]): Route data from the API
        """
        self.route_state["has_active_route"] = True
        self.route_state["origin"] = origin
        self.route_state["destination"] = destination
        self.route_state["waypoints"] = waypoints
        self.route_state["route_data"] = route_data
    
    def update_places_data(self, places_data: List[Dict[str, Any]]) -> None:
        """
        Update the places data.
        
        Args:
            places_data (List[Dict[str, Any]]): Places data from the API
        """
        print(f"Updating places data with {len(places_data)} places")
        print(f"Places data before update: {self.route_state['places_data'] is not None}")
        
        # Store a deep copy of the places data to avoid reference issues
        import copy
        if places_data and len(places_data) > 0:
            self.route_state["places_data"] = copy.deepcopy(places_data)
        else:
            self.route_state["places_data"] = None
        
        print(f"Places data after update: {self.route_state['places_data'] is not None}")
        if self.route_state["places_data"] is not None:
            print(f"Places data count after update: {len(self.route_state['places_data'])}")
            if len(self.route_state["places_data"]) > 0:
                print(f"First place: {self.route_state['places_data'][0]}")
    
    def update_features_data(self, features_data: List[Dict[str, Any]]) -> None:
        """
        Update the features data.
        
        Args:
            features_data (List[Dict[str, Any]]): Features data from the API
        """
        print(f"Updating features data with {len(features_data)} features")
        print(f"Features data before update: {self.route_state['features_data'] is not None}")
        
        # Store a deep copy of the features data to avoid reference issues
        import copy
        if features_data and len(features_data) > 0:
            self.route_state["features_data"] = copy.deepcopy(features_data)
        else:
            self.route_state["features_data"] = None
        
        print(f"Features data after update: {self.route_state['features_data'] is not None}")
        if self.route_state["features_data"] is not None:
            print(f"Features data count after update: {len(self.route_state['features_data'])}")
            if len(self.route_state["features_data"]) > 0:
                print(f"First feature: {self.route_state['features_data'][0]}")
    
    def _generate_system_prompt(self) -> str:
        """
        Generate a system prompt with route information.
        
        Returns:
            str: The system prompt
        """
        system_prompt = """
You are MapChat, a friendly and helpful AI assistant who knows all about routes, places, and natural features.

I'm going to give you information about a route that the user has created. When they ask questions about this route, 
respond in a warm, conversational tone like a knowledgeable friend who's excited to share interesting details about their journey.

Here are some guidelines:
- Be enthusiastic and personable in your responses
- Use a casual, friendly tone (like you're chatting with a friend)
- Mention specific place names and features from the information I provide
- Feel free to add interesting observations or connections between places
- If they ask about what's on the route, tell them about both places AND natural features
- Make the journey sound interesting and engaging

Remember, you have all the information about their route below - use it to give them helpful, specific answers!
"""
        
        if self.route_state["has_active_route"]:
            origin = self.route_state["origin"]
            destination = self.route_state["destination"]
            waypoints = self.route_state["waypoints"]
            
            system_prompt += "\n\nCurrent route information:\n"
            system_prompt += f"- Origin: {origin.get('display_name', 'Unknown')}\n"
            system_prompt += f"- Destination: {destination.get('display_name', 'Unknown')}\n"
            
            if waypoints:
                system_prompt += "- Waypoints:\n"
                for i, wp in enumerate(waypoints):
                    system_prompt += f"  {i+1}. {wp.get('display_name', 'Unknown')}\n"
            
            route_data = self.route_state["route_data"]
            if route_data:
                system_prompt += f"- Distance: {route_data.get('distance_text', 'Unknown')}\n"
                system_prompt += f"- Duration: {route_data.get('duration_text', 'Unknown')}\n"
            
            # Add places data if available
            places_data = self.route_state["places_data"]
            if places_data:
                print(f"Including {len(places_data)} places in system prompt")
                
                # Count places by type
                place_counts = {"city": 0, "town": 0, "village": 0}
                for place in places_data:
                    place_type = place.get("type")
                    if place_type in place_counts:
                        place_counts[place_type] += 1
                
                system_prompt += "\nPlaces along the route:\n"
                system_prompt += f"- {place_counts['city']} cities\n"
                system_prompt += f"- {place_counts['town']} towns\n"
                system_prompt += f"- {place_counts['village']} villages\n"
                
                # Add notable places (up to 5 of each type)
                system_prompt += "\nNotable places:\n"
                
                # Add cities
                cities = [p for p in places_data if p.get("type") == "city"][:5]
                if cities:
                    system_prompt += "Cities:\n"
                    for city in cities:
                        system_prompt += f"- {city.get('name')}\n"
                
                # Add towns
                towns = [p for p in places_data if p.get("type") == "town"][:5]
                if towns:
                    system_prompt += "Towns:\n"
                    for town in towns:
                        system_prompt += f"- {town.get('name')}\n"
                
                # Add villages
                villages = [p for p in places_data if p.get("type") == "village"][:5]
                if villages:
                    system_prompt += "Villages:\n"
                    for village in villages:
                        system_prompt += f"- {village.get('name')}\n"
                
                # Add a list of all places for completeness
                system_prompt += "\nComplete list of places along the route:\n"
                for place in places_data:
                    system_prompt += f"- {place.get('name')} ({place.get('type')})\n"
            
            # Add features data if available
            features_data = self.route_state["features_data"]
            if features_data:
                print(f"Including {len(features_data)} features in system prompt")
                
                # Count features by type
                feature_counts = {}
                for feature in features_data:
                    feature_type = feature.get("type")
                    if feature_type not in feature_counts:
                        feature_counts[feature_type] = 0
                    feature_counts[feature_type] += 1
                
                system_prompt += "\nNatural features along the route:\n"
                for feature_type, count in feature_counts.items():
                    system_prompt += f"- {count} {feature_type}(s)\n"
                
                # Add notable features (up to 5 of each type)
                system_prompt += "\nNotable features:\n"
                
                # Group features by type
                features_by_type = {}
                for feature in features_data:
                    feature_type = feature.get("type")
                    if feature_type not in features_by_type:
                        features_by_type[feature_type] = []
                    features_by_type[feature_type].append(feature)
                
                # Add up to 5 features of each type
                for feature_type, features in features_by_type.items():
                    # Skip unnamed features
                    named_features = [f for f in features if f.get("name") != "unnamed"]
                    if named_features:
                        system_prompt += f"{feature_type.capitalize()}s:\n"
                        for feature in named_features[:5]:
                            system_prompt += f"- {feature.get('name')}\n"
                
                # Add a list of all named features for completeness
                system_prompt += "\nComplete list of natural features along the route:\n"
                named_features = [f for f in features_data if f.get("name") != "unnamed"]
                for feature in named_features:
                    system_prompt += f"- {feature.get('name')} ({feature.get('type')})\n"
        
        return system_prompt
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message.
        
        Args:
            message (str): The user's message
            
        Returns:
            Dict[str, Any]: The response
        """
        print(f"Processing message: {message}")
        
        # Add the user message to the conversation history
        self.add_user_message(message)
        
        # Dump the entire route_state for debugging
        print("==== ROUTE STATE DUMP ====")
        for key, value in self.route_state.items():
            if key in ["places_data", "features_data"]:
                if value is not None:
                    print(f"{key}: {len(value)} items")
                    if len(value) > 0:
                        print(f"First item: {value[0]}")
                else:
                    print(f"{key}: None")
            elif key == "route_data":
                if value is not None:
                    print(f"{key}: {value.keys()}")
                else:
                    print(f"{key}: None")
            else:
                print(f"{key}: {value}")
        print("==== END ROUTE STATE DUMP ====")
        
        # Check if we have route data
        has_route = self.route_state["has_active_route"]
        has_places = self.route_state["places_data"] is not None
        has_features = self.route_state["features_data"] is not None
        
        print(f"Route state: has_active_route={has_route}, has_places_data={has_places}, has_features_data={has_features}")
        
        if has_route:
            origin = self.route_state["origin"].get("display_name", "Unknown")
            destination = self.route_state["destination"].get("display_name", "Unknown")
            print(f"Current route: {origin} to {destination}")
            
            if has_places:
                places_count = len(self.route_state["places_data"])
                print(f"Places data available: {places_count} places")
                print(f"Places data types: {set(p.get('type') for p in self.route_state['places_data'])}")
            else:
                print("No places data available!")
            
            if has_features:
                features_count = len(self.route_state["features_data"])
                print(f"Features data available: {features_count} features")
                print(f"Features data types: {set(f.get('type') for f in self.route_state['features_data'])}")
            else:
                print("No features data available!")
        
        # Generate a system prompt with route information
        system_prompt = self._generate_system_prompt()
        print(f"Generated system prompt with {len(system_prompt)} characters")
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add the conversation history (last 5 messages)
        history_limit = 5
        if len(self.conversation_history) > history_limit:
            messages.extend(self.conversation_history[-history_limit:])
        else:
            messages.extend(self.conversation_history)
        
        print(f"Sending {len(messages)} messages to LLM")
        
        # Get the response from the LLM
        try:
            # Use a higher temperature for more conversational responses
            response = await self.llm_client.async_chat(messages, temperature=0.7)
            message_content = response.get("message", {}).get("content", "I'm not sure how to help with that.")
            
            print(f"Received response from LLM: {len(message_content)} characters")
            
            # Add the assistant's response to the conversation history
            self.add_assistant_message(message_content)
            
            # Return the response (no UI update logic here anymore)
            return {
                "message": message_content
            }
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            print(error_message)
            
            # Add the error message to the conversation history
            self.add_assistant_message("I'm having trouble understanding your request. Could you please try again?")
            
            # Return the error message
            return {
                "message": "I'm having trouble understanding your request. Could you please try again?",
                "requires_ui_update": False
            }
    
    async def process_message_stream(self, message: str):
        """
        Process a user message and stream the response.
        
        Args:
            message (str): The user's message
            
        Yields:
            str: Chunks of the generated response
        """
        print(f"Processing message (streaming): {message}")
        
        # Add the user message to the conversation history
        self.add_user_message(message)
        
        # Check if we have route data
        has_route = self.route_state["has_active_route"]
        has_places = self.route_state["places_data"] is not None
        has_features = self.route_state["features_data"] is not None
        
        print(f"Route state (streaming): has_active_route={has_route}, has_places_data={has_places}, has_features_data={has_features}")
        
        # Generate a system prompt with route information
        system_prompt = self._generate_system_prompt()
        print(f"Generated system prompt with {len(system_prompt)} characters for streaming")
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add the conversation history (last 5 messages)
        history_limit = 5
        if len(self.conversation_history) > history_limit:
            messages.extend(self.conversation_history[-history_limit:])
        else:
            messages.extend(self.conversation_history)
        
        print(f"Sending {len(messages)} messages to LLM for streaming")
        
        # Variables to accumulate the full response
        full_response = ""
        
        # Stream the response from the LLM
        try:
            # Use a higher temperature for more conversational responses
            async for chunk in self.llm_client.async_stream_chat(messages, temperature=0.7):
                # Accumulate the full response
                full_response += chunk
                
                # Yield the chunk for streaming to the client
                yield chunk
            
            print(f"Completed streaming response: {len(full_response)} characters")
            
            # Add the complete response to the conversation history
            self.add_assistant_message(full_response)
            
            # No route generation or UI update logic here anymore
            
        except Exception as e:
            error_message = f"Error streaming response: {str(e)}"
            print(error_message)
            
            # Add the error message to the conversation history
            error_response = "I'm having trouble understanding your request. Could you please try again?"
            self.add_assistant_message(error_response)
            
            # Yield the error message
            yield error_response
