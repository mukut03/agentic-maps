import os
import json
import asyncio
import requests
import polyline
from flask import Flask, render_template, request, jsonify, g
from utils import routechat
from config import get_config
from llm.llm_provider import LLMProvider
from controllers.simple_chat import SimpleChatController
from controllers.intent_classifier import IntentClassifier

# Get global configuration
config = get_config()

# Create a global chat controller that persists across requests
global_chat_controller = None

def get_chat_controller():
    """Get or create the chat controller"""
    global global_chat_controller
    if global_chat_controller is None:
        print("Creating new chat controller")
        # Pass the config dictionary to the chat controller
        global_chat_controller = SimpleChatController(config.get_all())
    return global_chat_controller

app = Flask(__name__)

# Initialize the chat controller and intent classifier
chat_controller = get_chat_controller()
# Get the LLM client using the provider
llm_client = LLMProvider.get_client()
intent_classifier = IntentClassifier(llm_client) # Instantiate classifier

# Custom geocoding function that disables SSL verification
def geocode_address_custom(address):
    """
    Convert an address to coordinates using Nominatim API directly with SSL verification disabled.
    """
    url = f"https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "mapchat-app"
    }
    
    # Disable SSL verification
    response = requests.get(url, params=params, headers=headers, verify=False)
    
    if response.status_code == 200:
        results = response.json()
        if results:
            location = results[0]
            return {
                "lat": float(location["lat"]),
                "lng": float(location["lon"]),
                "display_name": location["display_name"]
            }
    
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/geocode', methods=['POST'])
def geocode_address():
    """Convert an address to coordinates"""
    data = request.json
    address = data.get('address')
    
    if not address:
        return jsonify({"error": "No address provided"}), 400
    
    try:
        # Suppress the InsecureRequestWarning that comes from using verify=False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        
        location = geocode_address_custom(address)
        if location:
            return jsonify(location)
        else:
            return jsonify({"error": "Location not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/route', methods=['POST'])
def get_route():
    """Get a route between origin and destination with optional waypoints"""
    data = request.json
    
    try:
        origin = (data['origin']['lat'], data['origin']['lng'])
        destination = (data['destination']['lat'], data['destination']['lng'])
        
        print(f"Generating route from {origin} to {destination}")
        
        waypoints = []
        if 'waypoints' in data and data['waypoints']:
            waypoints = [(wp['lat'], wp['lng']) for wp in data['waypoints']]
            print(f"With waypoints: {waypoints}")
        
        try:
            # Try to get the route using the function's documented return structure
            route_data = routechat.get_google_route(origin, destination, waypoints)
            print(f"Route data received: {route_data.keys()}")
            
            # Check if we have the expected keys
            if 'polyline' not in route_data:
                # If not, the function might be returning a different structure
                # Let's try to adapt to what the main() function expects
                if 'routes' in route_data and len(route_data['routes']) > 0:
                    route = route_data['routes'][0]
                    encoded_polyline = route['polyline']['encodedPolyline']
                    decoded_coords = polyline.decode(encoded_polyline)
                    distance_meters = route.get('distanceMeters', 0)
                    duration_seconds = route.get('duration', {}).get('seconds', 0)
                    
                    # Create a standardized response
                    route_data = { # TODO: need to add navigation instructions
                        "polyline": encoded_polyline,
                        "polyline_coords": decoded_coords,
                        "distance_text": f"{distance_meters/1000:.1f} km",
                        "duration_text": f"{duration_seconds/60:.0f} minutes"
                    }
                    print(f"Adapted route data: {route_data.keys()}")
            
            # Sample the polyline if requested
            if 'sample' in data and data['sample']:
                method = data.get('sample_method', 'interval')
                if method == 'interval':
                    interval_km = float(data.get('interval_km', 5.0))
                    sampled_points = routechat.sample_polyline(
                        route_data['polyline'], 
                        method="interval", 
                        interval_km=interval_km
                    )
                else:
                    every_nth = int(data.get('every_nth', 10))
                    sampled_points = routechat.sample_polyline(
                        route_data['polyline'], 
                        method="nth", 
                        every_nth=every_nth
                    )
                route_data['sampled_points'] = sampled_points
            
            return jsonify(route_data)
        except Exception as e:
            print(f"Error processing route: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/places', methods=['POST'])
def get_places():
    """Get places along a route"""
    data = request.json
    
    try:
        polyline_coords = data['polyline_coords']
        radius_m = int(data.get('radius_m', 10000))
        method = data.get('method', 'node')
        
        print(f"Getting places along route with {len(polyline_coords)} coordinates")
        print(f"First few coordinates: {polyline_coords[:3]}")
        print(f"Using radius: {radius_m}m and method: {method}")
        
        # Sample the coordinates if there are too many
        if len(polyline_coords) > 100:
            # Sample every 10th point
            sampled_coords = polyline_coords[::10]
            print(f"Sampled down to {len(sampled_coords)} coordinates for places query")
        else:
            sampled_coords = polyline_coords
        
        places = routechat.get_places_along_polyline(
            sampled_coords, 
            radius_m=radius_m, 
            method=method
        )
        
        print(f"Found {len(places)} places along the route")
        if places:
            print(f"First few places: {places[:3]}")
        else:
            print("No places found along the route")
        
        # Remove duplicates
        seen_places = set()
        unique_places = []
        for place in places:
            place_key = f"{place['name']}|{place['type']}"
            if place_key not in seen_places:
                unique_places.append(place)
                seen_places.add(place_key)
        
        print(f"After removing duplicates, returning {len(unique_places)} unique places")
        
        return jsonify({
            "places": unique_places
        })
    
    except Exception as e:
        print(f"Error getting places: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/natural_features', methods=['POST'])
def get_natural_features():
    """Get natural features along a route"""
    data = request.json
    
    try:
        polyline_coords = data['polyline_coords']
        radius_m = int(data.get('radius_m', 2000))
        method = data.get('method', 'way')
        
        print(f"Getting natural features along route with {len(polyline_coords)} coordinates")
        print(f"First few coordinates: {polyline_coords[:3]}")
        print(f"Using radius: {radius_m}m and method: {method}")
        
        # Sample the coordinates if there are too many
        if len(polyline_coords) > 100:
            # Sample every 10th point
            sampled_coords = polyline_coords[::10]
            print(f"Sampled down to {len(sampled_coords)} coordinates for natural features query")
        else:
            sampled_coords = polyline_coords
        
        features = routechat.get_natural_features_along_polyline(
            sampled_coords, 
            radius_m=radius_m, 
            method=method
        )
        
        print(f"Found {len(features)} natural features along the route")
        if features:
            print(f"First few features: {features[:3]}")
        else:
            print("No natural features found along the route")
        
        # Filter out unnamed features and remove duplicates
        seen_features = set()
        unique_features = []
        for feature in features:
            # Skip unnamed features
            if feature['name'] == 'unnamed':
                continue
                
            feature_key = f"{feature['name']}|{feature['type']}"
            if feature_key not in seen_features:
                unique_features.append(feature)
                seen_features.add(feature_key)
        
        print(f"After filtering unnamed features and removing duplicates, returning {len(unique_features)} unique features")
        
        return jsonify({
            "features": unique_features
        })
    
    except Exception as e:
        print(f"Error getting natural features: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def process_chat_message():
    """Process a chat message"""
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        print(f"Processing chat message: {message}")
        print(f"Chat controller has route data: {chat_controller.route_state['has_active_route']}")
        print(f"Chat controller has places data: {chat_controller.route_state['places_data'] is not None}")
        print(f"Chat controller has features data: {chat_controller.route_state['features_data'] is not None}")

        # Initialize asyncio loop for potential async calls
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Always check intent regardless of route status
            print("Checking intent...")
            classification = loop.run_until_complete(
                intent_classifier.classify(
                    message, 
                    chat_controller.get_conversation_history(), 
                    chat_controller.route_state
                )
            )
            
            intent = classification.get("intent")
            parameters = classification.get("parameters", {})
            print(f"Intent classification: {intent}, Parameters: {parameters}")

            # Get current state
            has_route = chat_controller.route_state['has_active_route']
            has_places = chat_controller.route_state['places_data'] is not None
            has_features = chat_controller.route_state['features_data'] is not None
            
            # If all data is already fetched, skip intent processing and just answer from context
            if has_route and has_places and has_features:
                print("All data (route, places, features) already fetched. Proceeding with normal chat.")
                response = loop.run_until_complete(chat_controller.process_message(message))
                return jsonify({
                    "message": response.get("message", ""),
                    "requires_ui_update": False
                })
            
            # Process based on intent
            is_valid, error_msg = intent_classifier.validate_parameters(intent, parameters)
            
            # ROUTE_QUERY: Generate a new route
            if intent == "ROUTE_QUERY" and is_valid:
                print("Intent is ROUTE_QUERY. Attempting to generate route...")
                origin_text = parameters.get("origin")
                destination_text = parameters.get("destination")
                # TODO: Handle waypoints if extracted

                # 1. Geocode Origin & Destination
                origin_data = geocode_address_custom(origin_text)
                if not origin_data:
                    raise ValueError(f"Could not geocode origin: {origin_text}")
                destination_data = geocode_address_custom(destination_text)
                if not destination_data:
                    raise ValueError(f"Could not geocode destination: {destination_text}")
                
                print(f"Geocoded Origin: {origin_data['display_name']}")
                print(f"Geocoded Destination: {destination_data['display_name']}")

                # 2. Get Route
                route_info = routechat.get_google_route(
                    (origin_data['lat'], origin_data['lng']),
                    (destination_data['lat'], destination_data['lng']),
                    [] # TODO: Add waypoints if implemented
                )
                # Adapt route data structure if necessary
                if 'polyline' not in route_info and 'routes' in route_info and len(route_info['routes']) > 0:
                     route = route_info['routes'][0]
                     encoded_polyline = route['polyline']['encodedPolyline']
                     decoded_coords = polyline.decode(encoded_polyline)
                     distance_meters = route.get('distanceMeters', 0)
                     duration_seconds = route.get('duration', {}).get('seconds', 0)
                     route_info = {
                         "polyline": encoded_polyline,
                         "polyline_coords": decoded_coords,
                         "distance_text": f"{distance_meters/1000:.1f} km",
                         "duration_text": f"{duration_seconds/60:.0f} minutes"
                     }
                
                if not route_info or 'polyline_coords' not in route_info:
                     raise ValueError("Failed to generate route details.")
                print(f"Route generated: {route_info.get('distance_text', 'N/A')}, {route_info.get('duration_text', 'N/A')}")

                # 3. Update Chat Controller State (Route Only)
                chat_controller.update_route_state(origin_data, destination_data, [], route_info)
                # Clear any stale places/features data from previous routes
                chat_controller.update_places_data([]) 
                chat_controller.update_features_data([])
                print("Chat controller state updated with new route (places/features cleared).")

                # 4. Return specific response
                response_message = f"OK, I've planned a route from {origin_data['display_name']} to {destination_data['display_name']}. Check the map and form!"
                chat_controller.add_user_message(message)
                chat_controller.add_assistant_message(response_message)
                
                return jsonify({
                    "status": "route_generated",
                    "message": response_message,
                    "requires_ui_update": True
                })
            
            # PLACES_QUERY: Get places along the route
            elif intent == "PLACES_QUERY" and has_route:
                print("Intent is PLACES_QUERY. Fetching places data...")
                
                # Get route data
                route_data = chat_controller.route_state.get("route_data", {})
                if not route_data or not route_data.get("polyline_coords"):
                    print("No valid route data for places query")
                    response = loop.run_until_complete(chat_controller.process_message(message))
                    return jsonify({
                        "message": response.get("message", ""),
                        "requires_ui_update": False
                    })
                
                # Prepare request data
                request_data = {
                    "polyline_coords": route_data["polyline_coords"],
                    "radius_m": 5000,  # 5 km radius
                    "method": "node"
                }
                
                # Fetch places data
                try:
                    places_response = requests.post(
                        f"{config.get('base_url', 'http://localhost:5000')}/places",
                        json=request_data,
                        timeout=30
                    )
                    
                    if places_response.status_code == 200:
                        places_data = places_response.json().get("places", [])
                        print(f"Fetched {len(places_data)} places along the route")
                        
                        # Update chat controller with places data
                        chat_controller.update_places_data(places_data)
                        
                        # Process the message with the updated data
                        response = loop.run_until_complete(chat_controller.process_message(message))
                        return jsonify({
                            "message": response.get("message", ""),
                            "requires_ui_update": True
                        })
                    else:
                        print(f"Failed to fetch places data: {places_response.status_code}")
                except Exception as e:
                    print(f"Error fetching places data: {str(e)}")
                
                # Fallback to normal processing if places fetch fails
                response = loop.run_until_complete(chat_controller.process_message(message))
                return jsonify({
                    "message": response.get("message", ""),
                    "requires_ui_update": False
                })
            
            # FEATURES_QUERY: Get features along the route
            elif intent == "FEATURES_QUERY" and has_route:
                print("Intent is FEATURES_QUERY. Fetching features data...")
                
                # Get route data
                route_data = chat_controller.route_state.get("route_data", {})
                if not route_data or not route_data.get("polyline_coords"):
                    print("No valid route data for features query")
                    response = loop.run_until_complete(chat_controller.process_message(message))
                    return jsonify({
                        "message": response.get("message", ""),
                        "requires_ui_update": False
                    })
                
                # Prepare request data
                request_data = {
                    "polyline_coords": route_data["polyline_coords"],
                    "radius_m": 1000,  # 1 km radius
                    "method": "way"
                }
                
                # Fetch features data
                try:
                    features_response = requests.post(
                        f"{config.get('base_url', 'http://localhost:5000')}/natural_features",
                        json=request_data,
                        timeout=30
                    )
                    
                    if features_response.status_code == 200:
                        features_data = features_response.json().get("features", [])
                        print(f"Fetched {len(features_data)} features along the route")
                        
                        # Update chat controller with features data
                        chat_controller.update_features_data(features_data)
                        
                        # Process the message with the updated data
                        response = loop.run_until_complete(chat_controller.process_message(message))
                        return jsonify({
                            "message": response.get("message", ""),
                            "requires_ui_update": True
                        })
                    else:
                        print(f"Failed to fetch features data: {features_response.status_code}")
                except Exception as e:
                    print(f"Error fetching features data: {str(e)}")
                
                # Fallback to normal processing if features fetch fails
                response = loop.run_until_complete(chat_controller.process_message(message))
                return jsonify({
                    "message": response.get("message", ""),
                    "requires_ui_update": False
                })
            
            # For any other intent or if parameters are invalid, proceed with normal chat
            else:
                print(f"Processing with normal chat (intent: {intent})")
                response = loop.run_until_complete(chat_controller.process_message(message))
                return jsonify({
                    "message": response.get("message", ""),
                    "requires_ui_update": False
                })
                
        finally:
            # Close the loop
            loop.close()
            
    except Exception as e:
        print(f"Error processing chat message: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/chat/stream', methods=['POST'])
def stream_chat_message():
    """Process a chat message and stream the response"""
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    def generate():
        loop = None # Initialize loop variable
        try:
            print(f"Processing chat message (streaming): {message}")
            print(f"Chat controller has route data: {chat_controller.route_state['has_active_route']}")
            print(f"Chat controller has places data: {chat_controller.route_state['places_data'] is not None}")
            print(f"Chat controller has features data: {chat_controller.route_state['features_data'] is not None}")

            # Initialize asyncio loop
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Always check intent regardless of route status
            print("Checking intent (streaming)...")
            classification = loop.run_until_complete(
                intent_classifier.classify(
                    message, 
                    chat_controller.get_conversation_history(), 
                    chat_controller.route_state
                )
            )
            intent = classification.get("intent")
            parameters = classification.get("parameters", {})
            print(f"Intent classification (streaming): {intent}, Parameters: {parameters}")

            # Get current state
            has_route = chat_controller.route_state['has_active_route']
            has_places = chat_controller.route_state['places_data'] is not None
            has_features = chat_controller.route_state['features_data'] is not None
            
            # If all data is already fetched, skip intent processing and just answer from context
            if has_route and has_places and has_features:
                print("All data (route, places, features) already fetched. Proceeding with normal chat streaming.")
                # Continue to normal streaming chat below
            # Process based on intent
            is_valid, error_msg = intent_classifier.validate_parameters(intent, parameters)
            
            # ROUTE_QUERY: Generate a new route
            if intent == "ROUTE_QUERY" and is_valid:
                print("Intent is ROUTE_QUERY. Attempting to generate route (streaming)...")
                try:
                    origin_text = parameters.get("origin")
                    destination_text = parameters.get("destination")
                    # TODO: Handle waypoints

                    # 1. Geocode
                    origin_data = geocode_address_custom(origin_text)
                    if not origin_data: raise ValueError(f"Could not geocode origin: {origin_text}")
                    destination_data = geocode_address_custom(destination_text)
                    if not destination_data: raise ValueError(f"Could not geocode destination: {destination_text}")
                    print(f"Geocoded Origin (streaming): {origin_data['display_name']}")
                    print(f"Geocoded Destination (streaming): {destination_data['display_name']}")

                    # 2. Route
                    route_info = routechat.get_google_route(
                        (origin_data['lat'], origin_data['lng']),
                        (destination_data['lat'], destination_data['lng']),
                        [] # TODO: Waypoints
                    )
                    # Adapt structure if needed
                    if 'polyline' not in route_info and 'routes' in route_info and len(route_info['routes']) > 0:
                         route = route_info['routes'][0]
                         encoded_polyline = route['polyline']['encodedPolyline']
                         decoded_coords = polyline.decode(encoded_polyline)
                         distance_meters = route.get('distanceMeters', 0)
                         duration_seconds = route.get('duration', {}).get('seconds', 0)
                         route_info = {
                             "polyline": encoded_polyline,
                             "polyline_coords": decoded_coords,
                             "distance_text": f"{distance_meters/1000:.1f} km",
                             "duration_text": f"{duration_seconds/60:.0f} minutes"
                         }
                    if not route_info or 'polyline_coords' not in route_info:
                         raise ValueError("Failed to generate route details.")
                    print(f"Route generated (streaming): {route_info.get('distance_text', 'N/A')}, {route_info.get('duration_text', 'N/A')}")
                    # polyline_coords = route_info['polyline_coords'] # Keep for potential future use

                    # --- Removed automatic fetching of places and features ---
                    # Places/features will be fetched on demand later

                    # 3. Update State (Route Only)
                    chat_controller.update_route_state(origin_data, destination_data, [], route_info) # TODO: Waypoints
                    # Clear any stale places/features data
                    chat_controller.update_places_data([])
                    chat_controller.update_features_data([])
                    print("Chat controller state updated with new route (streaming, places/features cleared).")

                    # 4. Yield specific SSE event and stop
                    response_message = f"OK, I've planned a route from {origin_data['display_name']} to {destination_data['display_name']}. Check the map and form!"
                    # Add to history
                    chat_controller.add_user_message(message)
                    chat_controller.add_assistant_message(response_message)
                    
                    yield f"data: {json.dumps({'status': 'route_generated', 'message': response_message, 'requires_ui_update': True})}\n\n"
                    return # Stop the generator here

                except Exception as route_gen_error:
                    print(f"Error during route generation (streaming): {str(route_gen_error)}")
                    # Yield an error message and stop
                    yield f"data: {json.dumps({'error': f'Failed to generate route: {str(route_gen_error)}'})}\n\n"
                    return # Stop the generator
            
            # PLACES_QUERY: Get places along the route
            elif intent == "PLACES_QUERY" and has_route:
                print("Intent is PLACES_QUERY. Handling places request (streaming)...")
                
                # Get route data
                route_data = chat_controller.route_state.get("route_data", {})
                if not route_data or not route_data.get("polyline_coords"):
                    print("No valid route data for places query (streaming)")
                    # Continue to normal streaming chat below
                else:
                    # Instead of fetching places directly, we'll return a response that will
                    # trigger the frontend to check the "show_places" checkbox and click the
                    # "generate_route" button
                    
                    # Get origin and destination for the response message
                    origin_name = chat_controller.route_state.get("origin", {}).get("display_name", "your origin")
                    destination_name = chat_controller.route_state.get("destination", {}).get("display_name", "your destination")
                    
                    # Create a response message
                    response_message = f"I'll show you places along your route from {origin_name} to {destination_name}. Check the map!"
                    
                    # Add to history
                    chat_controller.add_user_message(message)
                    chat_controller.add_assistant_message(response_message)
                    
                    # Return a special event that will trigger the UI update
                    # The frontend will handle checking the "show_places" checkbox and clicking "generate_route"
                    yield f"data: {json.dumps({'status': 'places_requested', 'message': response_message, 'requires_ui_update': True, 'show_places': True})}\n\n"
                    return # Stop the generator here
            
            # FEATURES_QUERY: Get features along the route
            elif intent == "FEATURES_QUERY" and has_route:
                print("Intent is FEATURES_QUERY. Handling features request (streaming)...")
                
                # Get route data
                route_data = chat_controller.route_state.get("route_data", {})
                if not route_data or not route_data.get("polyline_coords"):
                    print("No valid route data for features query (streaming)")
                    # Continue to normal streaming chat below
                else:
                    # Instead of fetching features directly, we'll return a response that will
                    # trigger the frontend to check the "show_features" checkbox and click the
                    # "generate_route" button
                    
                    # Get origin and destination for the response message
                    origin_name = chat_controller.route_state.get("origin", {}).get("display_name", "your origin")
                    destination_name = chat_controller.route_state.get("destination", {}).get("display_name", "your destination")
                    
                    # Create a response message
                    response_message = f"I'll show you natural features along your route from {origin_name} to {destination_name}. Check the map!"
                    
                    # Add to history
                    chat_controller.add_user_message(message)
                    chat_controller.add_assistant_message(response_message)
                    
                    # Return a special event that will trigger the UI update
                    # The frontend will handle checking the "show_features" checkbox and clicking "generate_route"
                    yield f"data: {json.dumps({'status': 'features_requested', 'message': response_message, 'requires_ui_update': True, 'show_features': True})}\n\n"
                    return # Stop the generator here
            
            # ADD_WAYPOINT: Add a waypoint to the current route
            elif intent == "ADD_WAYPOINT" and has_route:
                print("Intent is ADD_WAYPOINT. Handling waypoint addition (streaming)...")
                
                # Extract the waypoint from the parameters
                waypoint_text = parameters.get("waypoint")
                if not waypoint_text:
                    print("No waypoint specified in ADD_WAYPOINT intent")
                    # Continue to normal streaming chat below
                else:
                    # Geocode the waypoint
                    waypoint_data = geocode_address_custom(waypoint_text)
                    if not waypoint_data:
                        print(f"Failed to geocode waypoint: {waypoint_text}")
                        # Continue to normal streaming chat below
                    else:
                        print(f"Successfully geocoded waypoint: {waypoint_data['display_name']}")
                        
                        # Get origin and destination for the response message
                        origin_name = chat_controller.route_state.get("origin", {}).get("display_name", "your origin")
                        destination_name = chat_controller.route_state.get("destination", {}).get("display_name", "your destination")
                        
                        # Create a response message
                        response_message = f"I've added {waypoint_data['display_name']} as a waypoint to your route from {origin_name} to {destination_name}. Check the map!"
                        
                        # Add to history
                        chat_controller.add_user_message(message)
                        chat_controller.add_assistant_message(response_message)
                        
                        # Return a special event that will trigger the UI update
                        # The frontend will handle adding the waypoint and regenerating the route
                        yield f"data: {json.dumps({'status': 'waypoint_added', 'message': response_message, 'requires_ui_update': True, 'waypoint': waypoint_data})}\n\n"
                        return # Stop the generator here
            
            # --- End of Intent Processing Logic ---

            # If we reach here, either a route existed or intent wasn't ROUTE_QUERY
            # Proceed with normal streaming chat
            print("Proceeding with normal chat streaming...")

            # Async function to collect and yield chunks from the LLM
            async def stream_llm_response():
                full_response = ""
                async for chunk in chat_controller.process_message_stream(message):
                    full_response += chunk
                    # Yield the chunk for SSE
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                # After all chunks, send completion event
                yield f"data: {json.dumps({'complete': True, 'requires_ui_update': False})}\n\n" # Always false here

            # Create an async generator from the helper function
            gen = stream_llm_response()

            # Process chunks from the generator using the loop
            while True:
                try:
                    chunk_event = loop.run_until_complete(gen.__anext__())
                    yield chunk_event
                except StopAsyncIteration:
                    break # Finished streaming
                except Exception as e:
                    print(f"Error processing chunk (streaming): {str(e)}")
                    yield f"data: {json.dumps({'error': f'Error processing chunk: {str(e)}'})}\n\n"
                    break

        except Exception as e:
            # Catch errors from intent classification or initial setup
            print(f"Error in streaming chat setup: {str(e)}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Ensure the loop is closed
            if loop and not loop.is_closed():
                loop.close()
    
    # Return a streaming response
    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

@app.route('/chat/history', methods=['GET'])
def get_chat_history():
    """Get the chat history"""
    try:
        # Get the conversation history - this is synchronous so no need for async handling
        history = chat_controller.get_conversation_history()
        
        # Return the history
        return jsonify({
            "history": history
        })
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_current_route', methods=['GET'])
def get_current_route():
    """Get the current route data for updating the UI"""
    try:
        # Check if there's an active route
        if not chat_controller.route_state.get("has_active_route", False):
            return jsonify({"error": "No active route"}), 404
        
        # Get the route data
        origin = chat_controller.route_state.get("origin", {})
        destination = chat_controller.route_state.get("destination", {})
        waypoints = chat_controller.route_state.get("waypoints", [])
        route_data = chat_controller.route_state.get("route_data", {})
        
        # Return the route data
        return jsonify({
            "origin": origin,
            "destination": destination,
            "waypoints": waypoints,
            "route_data": route_data
        })
    except Exception as e:
        print(f"Error getting current route: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat/reset', methods=['POST'])
def reset_chat():
    """Reset the chat conversation"""
    try:
        # Reset the conversation - this is synchronous so no need for async handling
        chat_controller.reset_conversation()
        
        # Return success
        return jsonify({
            "success": True,
            "message": "Conversation reset successfully"
        })
    except Exception as e:
        print(f"Error resetting chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_conversation_state', methods=['POST'])
def update_conversation_state():
    """Update the conversation state with route data"""
    data = request.json
    
    try:
        print("Updating conversation state with route data")
        
        # Update the route state
        chat_controller.update_route_state(
            data.get('origin', {}),
            data.get('destination', {}),
            data.get('waypoints', []),
            data.get('route_data', {})
        )
        
        # Return success
        return jsonify({
            "success": True,
            "message": "Conversation state updated successfully"
        })
    except Exception as e:
        print(f"Error updating conversation state: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_places_data', methods=['POST'])
def update_places_data():
    """Update the conversation state with places data"""
    data = request.json
    
    try:
        places_data = data.get('places', [])
        print(f"Updating conversation state with {len(places_data)} places")
        
        # Update the places data
        chat_controller.update_places_data(places_data)
        
        # Return success
        return jsonify({
            "success": True,
            "message": f"Places data updated successfully with {len(places_data)} places"
        })
    except Exception as e:
        print(f"Error updating places data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/update_features_data', methods=['POST'])
def update_features_data():
    """Update the conversation state with features data"""
    data = request.json
    
    try:
        features_data = data.get('features', [])
        print(f"Updating conversation state with {len(features_data)} features")
        
        # Update the features data
        chat_controller.update_features_data(features_data)
        
        # Return success
        return jsonify({
            "success": True,
            "message": f"Features data updated successfully with {len(features_data)} features"
        })
    except Exception as e:
        print(f"Error updating features data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the app with debug mode but disable auto-reloading to preserve global state
    app.run(debug=True, use_reloader=False)
