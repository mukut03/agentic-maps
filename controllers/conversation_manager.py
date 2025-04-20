import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class ConversationManager:
    """
    Manages conversation history and context for the chat interface.
    Tracks the current state (active route, waypoints, etc.) and provides
    context to the LLM for each query.
    """
    
    def __init__(self):
        """Initialize a new conversation manager with empty history and state."""
        self.history: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {
            "has_active_route": False,
            "origin": None,
            "destination": None,
            "waypoints": [],
            "route_data": None,
            "places_data": None,
            "features_data": None,
            "last_query_type": None,
            "pending_clarification": False,
            "clarification_context": None
        }
    
    def add_user_message(self, message: str) -> None:
        """
        Add a user message to the conversation history.
        
        Args:
            message (str): The user's message
        """
        self.history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_assistant_message(self, message: str) -> None:
        """
        Add an assistant message to the conversation history.
        
        Args:
            message (str): The assistant's message
        """
        self.history.append({
            "role": "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Returns:
            List[Dict[str, Any]]: The conversation history
        """
        return self.history
    
    def get_messages_for_llm(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """
        Get the conversation history formatted for the LLM.
        
        Args:
            max_messages (int): Maximum number of messages to include
            
        Returns:
            List[Dict[str, str]]: The conversation history formatted for the LLM
        """
        # Get the most recent messages, limited by max_messages
        recent_messages = self.history[-max_messages:] if len(self.history) > max_messages else self.history
        
        # Format messages for the LLM (only include role and content)
        return [{"role": msg["role"], "content": msg["content"]} for msg in recent_messages]
    
    def update_state(self, **kwargs) -> None:
        """
        Update the conversation state.
        
        Args:
            **kwargs: Key-value pairs to update in the state
        """
        self.state.update(kwargs)
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current conversation state.
        
        Returns:
            Dict[str, Any]: The current state
        """
        return self.state
    
    def reset(self) -> None:
        """Reset the conversation history and state."""
        self.history = []
        self.state = {
            "has_active_route": False,
            "origin": None,
            "destination": None,
            "waypoints": [],
            "route_data": None,
            "places_data": None,
            "features_data": None,
            "last_query_type": None,
            "pending_clarification": False,
            "clarification_context": None
        }
    
    def set_route_data(self, origin: Dict[str, Any], destination: Dict[str, Any], 
                      waypoints: List[Dict[str, Any]], route_data: Dict[str, Any]) -> None:
        """
        Set the current route data in the state.
        
        Args:
            origin (Dict[str, Any]): Origin location data
            destination (Dict[str, Any]): Destination location data
            waypoints (List[Dict[str, Any]]): List of waypoint location data
            route_data (Dict[str, Any]): Route data from the API
        """
        self.state["has_active_route"] = True
        self.state["origin"] = origin
        self.state["destination"] = destination
        self.state["waypoints"] = waypoints
        self.state["route_data"] = route_data
    
    def set_places_data(self, places_data: List[Dict[str, Any]]) -> None:
        """
        Set the places data for the current route.
        
        Args:
            places_data (List[Dict[str, Any]]): Places data from the API
        """
        self.state["places_data"] = places_data
    
    def set_features_data(self, features_data: List[Dict[str, Any]]) -> None:
        """
        Set the natural features data for the current route.
        
        Args:
            features_data (List[Dict[str, Any]]): Features data from the API
        """
        self.state["features_data"] = features_data
    
    def has_active_route(self) -> bool:
        """
        Check if there is an active route.
        
        Returns:
            bool: True if there is an active route, False otherwise
        """
        return self.state["has_active_route"]
    
    def set_pending_clarification(self, is_pending: bool, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Set whether a clarification is pending from the user.
        
        Args:
            is_pending (bool): Whether a clarification is pending
            context (Optional[Dict[str, Any]]): Context for the clarification
        """
        self.state["pending_clarification"] = is_pending
        self.state["clarification_context"] = context
    
    def is_pending_clarification(self) -> bool:
        """
        Check if a clarification is pending from the user.
        
        Returns:
            bool: True if a clarification is pending, False otherwise
        """
        return self.state["pending_clarification"]
    
    def get_clarification_context(self) -> Optional[Dict[str, Any]]:
        """
        Get the context for the pending clarification.
        
        Returns:
            Optional[Dict[str, Any]]: The clarification context, or None if no clarification is pending
        """
        return self.state["clarification_context"]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the conversation manager to a dictionary for serialization.
        
        Returns:
            Dict[str, Any]: The serialized conversation manager
        """
        return {
            "history": self.history,
            "state": self.state
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationManager':
        """
        Create a conversation manager from a serialized dictionary.
        
        Args:
            data (Dict[str, Any]): The serialized conversation manager
            
        Returns:
            ConversationManager: The deserialized conversation manager
        """
        manager = cls()
        manager.history = data.get("history", [])
        manager.state = data.get("state", {})
        return manager
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save the conversation to a file.
        
        Args:
            filepath (str): The path to save the file to
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'ConversationManager':
        """
        Load a conversation from a file.
        
        Args:
            filepath (str): The path to load the file from
            
        Returns:
            ConversationManager: The loaded conversation manager
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
