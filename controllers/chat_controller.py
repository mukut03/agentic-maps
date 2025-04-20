import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from ollama_client import OllamaClient
from conversation_manager import ConversationManager
from intent_classifier import IntentClassifier
from route_agent import RouteAgent
from places_features_agent import PlacesFeaturesAgent
from waypoint_agent import WaypointAgent
from clarification_agent import ClarificationAgent
import prompts

class ChatController:
    """
    Main controller for chat functionality.
    Handles HTTP requests from the frontend and manages the conversation flow.
    """
    
    def __init__(self, app_config: Dict[str, Any]):
        """
        Initialize the chat controller.
        
        Args:
            app_config (Dict[str, Any]): Application configuration
        """
        self.app_config = app_config
        self.llm_client = OllamaClient(model=app_config.get("llm_model", "llama3.2:7b"))
        self.conversation_manager = ConversationManager()
        
        # Initialize agents
        self.intent_classifier = IntentClassifier(self.llm_client)
        self.route_agent = RouteAgent(self.llm_client, app_config)
        self.places_features_agent = PlacesFeaturesAgent(self.llm_client, app_config)
        self.waypoint_agent = WaypointAgent(self.llm_client, app_config)
        self.clarification_agent = ClarificationAgent(self.llm_client)
    
    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process a user message.
        
        Args:
            message (str): The user's message
            
        Returns:
            Dict[str, Any]: The response
        """
        # Add the user message to the conversation history
        self.conversation_manager.add_user_message(message)
        
        # Get the conversation state
        conversation_state = self.conversation_manager.get_state()
        
        # Check if we're waiting for clarification
        if conversation_state.get("pending_clarification"):
            # Process the clarification
            clarification_context = conversation_state.get("clarification_context", {})
            clarification_result = await self.clarification_agent.process_clarification_request(
                message, clarification_context, conversation_state
            )
            
            # Clear the pending clarification
            self.conversation_manager.set_pending_clarification(False, None)
            
            # If the clarification was successful, update the state and continue processing
            if clarification_result.get("success", False):
                # Update the state with the clarified value
                if "clarified_value" in clarification_result:
                    topic = clarification_context.get("topic", "")
                    
                    if topic == "origin location":
                        # Set the clarified origin for a route query
                        conversation_state["clarified_origin"] = clarification_result["clarified_value"]
                    elif topic == "destination location":
                        # Set the clarified destination for a route query
                        conversation_state["clarified_destination"] = clarification_result["clarified_value"]
                    elif topic == "waypoint location":
                        # Set the clarified waypoint for an add waypoint query
                        conversation_state["clarified_waypoint"] = clarification_result["clarified_value"]
                    elif topic == "waypoint removal":
                        # Set the clarified waypoint for a remove waypoint query
                        conversation_state["clarified_waypoint_removal"] = clarification_result["clarified_value"]
                    elif topic == "missing route" and clarification_result.get("wants_route", False):
                        # Set the origin and destination for a new route
                        if "origin" in clarification_result and "destination" in clarification_result:
                            conversation_state["clarified_origin"] = clarification_result["origin"]
                            conversation_state["clarified_destination"] = clarification_result["destination"]
                
                # Add the assistant's response to the conversation history
                self.conversation_manager.add_assistant_message(clarification_result["message"])
                
                # Return the response
                return {
                    "message": clarification_result["message"],
                    "requires_ui_update": False
                }
            else:
                # If the clarification failed, ask for clarification again
                self.conversation_manager.set_pending_clarification(True, clarification_context)
                
                # Add the assistant's response to the conversation history
                self.conversation_manager.add_assistant_message(clarification_result["message"])
                
                # Return the response
                return {
                    "message": clarification_result["message"],
                    "requires_ui_update": False
                }
        
        # Classify the intent
        intent_data = await self.intent_classifier.classify(
            message, 
            self.conversation_manager.get_messages_for_llm(), 
            conversation_state
        )
        
        # Update the state with the intent
        conversation_state["last_query_type"] = intent_data.get("intent")
        
        # Check if we need clarification
        if intent_data.get("requires_clarification", False):
            # Generate a clarification question
            clarification_question = await self.clarification_agent.generate_clarification_question(
                intent_data, conversation_state
            )
            
            # Set the pending clarification
            self.conversation_manager.set_pending_clarification(
                True, 
                {
                    "topic": intent_data.get("intent"),
                    "parameters": intent_data.get("parameters", {})
                }
            )
            
            # Add the assistant's response to the conversation history
            self.conversation_manager.add_assistant_message(clarification_question)
            
            # Return the response
            return {
                "message": clarification_question,
                "requires_ui_update": False
            }
        
        # Always classify intent and process accordingly
        intent = intent_data.get("intent", "UNKNOWN")
        has_route = conversation_state.get("has_active_route")
        has_places = conversation_state.get("places_data") is not None
        has_features = conversation_state.get("features_data") is not None

        # If the user is asking for a new route, always process the route agent
        if intent == "ROUTE_QUERY":
            result = await self.route_agent.process_query(
                intent_data.get("original_query", ""), 
                {"intent": intent, "parameters": intent_data.get("parameters", {})}, 
                conversation_state
            )
            if result.get("success", False):
                self.conversation_manager.set_route_data(
                    result["origin"],
                    result["destination"],
                    result["waypoints"],
                    result["route_data"]
                )
                asyncio.create_task(
                    self.places_features_agent.proactive_load_data(conversation_state)
                )
                self.conversation_manager.add_assistant_message(result["message"])
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            # If failed, fall through to normal intent processing

        # If the user is asking for places, always process the places agent
        if intent == "PLACES_QUERY":
            result = await self.places_features_agent.process_places_query(
                intent_data.get("original_query", ""), 
                conversation_state
            )
            if result.get("success", False):
                self.conversation_manager.set_places_data(result["places_data"])
                self.conversation_manager.add_assistant_message(result["message"])
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            # If failed, fall through to normal intent processing

        # If the user is asking for features, always process the features agent
        if intent == "FEATURES_QUERY":
            result = await self.places_features_agent.process_features_query(
                intent_data.get("original_query", ""), 
                conversation_state
            )
            if result.get("success", False):
                self.conversation_manager.set_features_data(result["features_data"])
                self.conversation_manager.add_assistant_message(result["message"])
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            # If failed, fall through to normal intent processing

        # If all fields are present and the user is NOT asking for route/places/features, answer from context/history
        if has_route and has_places and has_features and intent not in ["ROUTE_QUERY", "PLACES_QUERY", "FEATURES_QUERY"]:
            response = await self._process_intent(intent_data, conversation_state)
            self.conversation_manager.add_assistant_message(response["message"])
            return response

        # Otherwise, process intent as normal (including if only some fields are present)
        response = await self._process_intent(intent_data, conversation_state)
        self.conversation_manager.add_assistant_message(response["message"])
        return response
    
    async def _process_intent(self, intent_data: Dict[str, Any], conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an intent.
        
        Args:
            intent_data (Dict[str, Any]): The intent classification data
            conversation_state (Dict[str, Any]): The current conversation state
            
        Returns:
            Dict[str, Any]: The response
        """
        intent = intent_data.get("intent", "UNKNOWN")
        parameters = intent_data.get("parameters", {})
        
        # Process different intents
        if intent == "ROUTE_QUERY":
            # Check if we have clarified values
            if conversation_state.get("clarified_origin"):
                parameters["origin"] = conversation_state.get("clarified_origin")
                conversation_state.pop("clarified_origin")
            
            if conversation_state.get("clarified_destination"):
                parameters["destination"] = conversation_state.get("clarified_destination")
                conversation_state.pop("clarified_destination")
            
            # Process the route query
            result = await self.route_agent.process_query(
                intent_data.get("original_query", ""), 
                {"intent": intent, "parameters": parameters}, 
                conversation_state
            )
            
            # If the query was successful, update the conversation state
            if result.get("success", False):
                self.conversation_manager.set_route_data(
                    result["origin"],
                    result["destination"],
                    result["waypoints"],
                    result["route_data"]
                )
                
                # Proactively load places and features data
                asyncio.create_task(
                    self.places_features_agent.proactive_load_data(conversation_state)
                )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            else:
                # If the query failed, check if we need clarification
                if result.get("requires_clarification", False):
                    self.conversation_manager.set_pending_clarification(
                        True, result.get("clarification_context", {})
                    )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": False
                }
        
        elif intent == "PLACES_QUERY":
            # Process the places query
            result = await self.places_features_agent.process_places_query(
                intent_data.get("original_query", ""), 
                conversation_state
            )
            
            # If the query was successful, update the conversation state
            if result.get("success", False):
                self.conversation_manager.set_places_data(result["places_data"])
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            else:
                # If the query failed, check if we need clarification
                if result.get("requires_clarification", False):
                    self.conversation_manager.set_pending_clarification(
                        True, result.get("clarification_context", {})
                    )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": False
                }
        
        elif intent == "FEATURES_QUERY":
            # Process the features query
            result = await self.places_features_agent.process_features_query(
                intent_data.get("original_query", ""), 
                conversation_state
            )
            
            # If the query was successful, update the conversation state
            if result.get("success", False):
                self.conversation_manager.set_features_data(result["features_data"])
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            else:
                # If the query failed, check if we need clarification
                if result.get("requires_clarification", False):
                    self.conversation_manager.set_pending_clarification(
                        True, result.get("clarification_context", {})
                    )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": False
                }
        
        elif intent == "ADD_WAYPOINT":
            # Check if we have a clarified waypoint
            if conversation_state.get("clarified_waypoint"):
                parameters["waypoint"] = conversation_state.get("clarified_waypoint")
                conversation_state.pop("clarified_waypoint")
            
            # Process the add waypoint query
            result = await self.waypoint_agent.process_add_waypoint(
                intent_data.get("original_query", ""), 
                {"intent": intent, "parameters": parameters}, 
                conversation_state
            )
            
            # If the query was successful, update the conversation state
            if result.get("success", False):
                self.conversation_manager.update_state(
                    waypoints=result["waypoints"],
                    route_data=result["route_data"]
                )
                
                # Proactively load places and features data
                asyncio.create_task(
                    self.places_features_agent.proactive_load_data(conversation_state)
                )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            else:
                # If the query failed, check if we need clarification
                if result.get("requires_clarification", False):
                    self.conversation_manager.set_pending_clarification(
                        True, result.get("clarification_context", {})
                    )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": False
                }
        
        elif intent == "REMOVE_WAYPOINT":
            # Check if we have a clarified waypoint removal
            if conversation_state.get("clarified_waypoint_removal"):
                parameters["waypoint"] = conversation_state.get("clarified_waypoint_removal")
                conversation_state.pop("clarified_waypoint_removal")
            
            # Process the remove waypoint query
            result = await self.waypoint_agent.process_remove_waypoint(
                intent_data.get("original_query", ""), 
                {"intent": intent, "parameters": parameters}, 
                conversation_state
            )
            
            # If the query was successful, update the conversation state
            if result.get("success", False):
                self.conversation_manager.update_state(
                    waypoints=result["waypoints"],
                    route_data=result["route_data"]
                )
                
                # Proactively load places and features data
                asyncio.create_task(
                    self.places_features_agent.proactive_load_data(conversation_state)
                )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": True
                }
            else:
                # If the query failed, check if we need clarification
                if result.get("requires_clarification", False):
                    self.conversation_manager.set_pending_clarification(
                        True, result.get("clarification_context", {})
                    )
                
                # Return the response
                return {
                    "message": result["message"],
                    "requires_ui_update": False
                }
        
        elif intent == "GENERAL_QUERY" or intent == "UNKNOWN":
            # Check if this is a query about the current route
            is_route_query = False
            query = intent_data.get("original_query", "").lower()
            route_keywords = ["route", "way", "journey", "trip", "path", "road", "current route", "this route"]
            
            if conversation_state.get("has_active_route"):
                # Check if the query contains route-related keywords
                for keyword in route_keywords:
                    if keyword in query:
                        is_route_query = True
                        break
            
            # Generate a response using the LLM
            system_prompt = prompts.generate_system_prompt_with_context(
                prompts.BASE_SYSTEM_PROMPT, conversation_state
            )
            
            # If this is a route query, add additional instructions to the system prompt
            if is_route_query:
                system_prompt += "\n\nThe user is asking about the current route. Please provide a detailed response that includes information about:\n"
                system_prompt += "1. The route details (origin, destination, distance, duration)\n"
                system_prompt += "2. Places along the route (cities, towns, villages)\n"
                system_prompt += "3. Natural features along the route (rivers, mountains, etc.)\n"
                system_prompt += "\nBe specific and mention actual place names and features from the context."
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add the conversation history
            messages.extend(self.conversation_manager.get_messages_for_llm())
            
            # Get the response from the LLM
            try:
                # Use a lower temperature for route queries to get more factual responses
                temp = 0.3 if is_route_query else 0.7
                response = await self.llm_client.async_chat(messages, temperature=temp)
                message = response.get("message", {}).get("content", "I'm not sure how to help with that.")
                
                # Return the response
                return {
                    "message": message,
                    "requires_ui_update": False
                }
            except Exception as e:
                print(f"Error generating response: {str(e)}")
                return {
                    "message": "I'm having trouble understanding your request. Could you please try again?",
                    "requires_ui_update": False
                }
        
        else:
            # Unknown intent
            return {
                "message": "I'm not sure how to help with that. Could you please try a different query?",
                "requires_ui_update": False
            }
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Returns:
            List[Dict[str, Any]]: The conversation history
        """
        return self.conversation_manager.get_history()
    
    def reset_conversation(self) -> None:
        """
        Reset the conversation.
        """
        self.conversation_manager.reset()
