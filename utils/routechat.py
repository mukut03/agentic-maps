import os
import requests
import json
from datetime import datetime, timedelta
from google.maps import routing_v2
from google.maps.routing_v2.types import (
    ComputeRoutesRequest,
    Waypoint,
    Location,
    RouteTravelMode,
    RoutingPreference,
    PolylineQuality,
    RouteModifiers
)
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.json_format import MessageToJson
import polyline
from geopy.distance import geodesic
import folium

## TODO: Sort places_along_the_route. 

# ------------------------------
# Helper: Create Waypoint from coordinates
# ------------------------------
def create_waypoint(lat, lng):
    """
    Creates a Google Maps Waypoint object from latitude and longitude.

    Args:
        lat (float): Latitude of the location.
        lng (float): Longitude of the location.

    Returns:
        Waypoint: A Google Maps Waypoint object.
    """
    return Waypoint(location=Location(lat_lng={"latitude": lat, "longitude": lng}))

# ------------------------------
# Helper: Plot lat/long on map
# ------------------------------
def points_on_map(sampled_points):
    # Initialize a map centered around the first sampled point
    m = folium.Map(location=sampled_points[0], zoom_start=10)

    # Add markers for each sampled point
    for lat, lon in sampled_points:
        folium.Marker([lat, lon]).add_to(m)

    # Save the map to an HTML file
    m.save('sampled_points_map.html')
    print("Map HTML saved. ")

# ------------------------------
# Step 1: Fetch Route from Google Maps Routes API
# ------------------------------
def get_google_route(origin: tuple, destination: tuple, waypoints: list = []) -> dict:
    """
    Fetches a driving route using Google Maps Routes API.

    Args:
        origin (tuple): (latitude, longitude) of the starting point.
        destination (tuple): (latitude, longitude) of the destination.
        waypoints (list): Optional list of (latitude, longitude) tuples as intermediate stops.

    Returns:
        dict: A dictionary containing route information including polyline, steps, duration, and distance.
    """
    client = routing_v2.RoutesClient()

    origin_wp = create_waypoint(*origin)
    destination_wp = create_waypoint(*destination)
    intermediate_wps = [create_waypoint(*wp) for wp in waypoints]

    departure_time = Timestamp()
    departure_time.FromDatetime(datetime.utcnow() + timedelta(minutes=5))

    request = ComputeRoutesRequest(
        origin=origin_wp,
        destination=destination_wp,
        intermediates=intermediate_wps,
        travel_mode=RouteTravelMode.DRIVE,
        routing_preference=RoutingPreference.TRAFFIC_AWARE,
        polyline_quality=PolylineQuality.HIGH_QUALITY,
        departure_time=departure_time,
        route_modifiers=RouteModifiers(avoid_tolls=False)
    )

    field_mask = 'routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline'
    metadata = [('x-goog-fieldmask', field_mask)]
    response = client.compute_routes(request=request, metadata=metadata)
    
    if not response.routes:
        return {"error": "No route found."}

    route = response.routes[0]
    encoded_polyline = route.polyline.encoded_polyline
    decoded_coords = polyline.decode(encoded_polyline)

    # Format distance and duration (human readable)
    distance_km = route.distance_meters / 1000
    duration_minutes = route.duration.seconds / 60

    return {
        "polyline": encoded_polyline,
        "polyline_coords": decoded_coords,
        "distance_text": f"{distance_km:.1f} km",
        "duration_text": f"{duration_minutes:.0f} minutes"
    }


# ------------------------------
# Step 2: Sample Lat/Lng Points from Encoded Polyline
# ------------------------------
def sample_polyline(encoded_polyline: str, method: str = "interval", interval_km: float = 5.0, every_nth: int = 10) -> list:
    """
    Decodes an encoded polyline and samples points either by distance or by index.

    Args:
        encoded_polyline (str): The encoded polyline string from Google Maps.
        method (str): Sampling method: "interval" for distance-based or "nth" for index-based.
        interval_km (float): Distance interval in kilometers between samples (if method is "interval").
        every_nth (int): Take every nth point (if method is "nth").

    Returns:
        list: A list of sampled (latitude, longitude) tuples.
    """
    points = polyline.decode(encoded_polyline)

    if method == "nth":
        return points[::every_nth]

    elif method == "interval":
        if not points:
            return []

        sampled = [points[0]]
        last_point = points[0]

        for point in points[1:]:
            if geodesic(last_point, point).km >= interval_km:
                sampled.append(point)
                last_point = point

        if sampled[-1] != points[-1]:
            sampled.append(points[-1])

        return sampled

    else:
        raise ValueError("Unsupported sampling method. Use 'interval' or 'nth'.")


# ------------------------------
# Step 3: Query Cities/Towns along the Route using Overpass API
# ------------------------------
def get_overpass_places(sampled_points: list, radius_m: int = 1000) -> list:
    """
    Queries Overpass API to find nearby cities, towns, and villages around sampled lat/lng points.

    Args:
        sampled_points (list): A list of (latitude, longitude) tuples sampled along the route.
        radius_m (int): Search radius in meters around each point.

    Returns:
        list: A list of dictionaries containing place information (name, type, lat, lon).
    """
    # Start constructing the Overpass QL query
    query = "[out:json][timeout:25];\n"
    query += "(\n"
    for lat, lon in sampled_points:
        query += f"  node(around:{radius_m},{lat},{lon})[\"place\"~\"city|town|village\"];\n"
    query += ");\n"
    query += "out center;"

    # Send the query using a POST request
    response = requests.post("http://overpass-api.de/api/interpreter", data={"data": query})
    if response.status_code != 200:
        raise Exception(f"Overpass API error: {response.status_code} - {response.text}")

    elements = response.json().get("elements", [])
    seen = set()
    places = []

    for elem in elements:
        name = elem.get("tags", {}).get("name")
        place_type = elem.get("tags", {}).get("place")
        lat = elem.get("lat")
        lon = elem.get("lon")

        if name and (name, place_type) not in seen:
            places.append({
                "name": name,
                "type": place_type,
                "lat": lat,
                "lon": lon
            })
            seen.add((name, place_type))

    return places

import requests

import time
import random

def get_places_along_polyline(polyline_coords: list, radius_m: int = 2000, method: str = "node") -> list:
    """
    Queries Overpass API for places (city/town/village) along a polyline using optimized Overpass QL.
    Includes retry logic, multiple endpoints, and proper headers to handle API restrictions.

    Args:
        polyline_coords (list): List of (lat, lon) tuples representing the full polyline route.
        radius_m (int): Radius in meters for searching places along the polyline.
        method (str): 'node' for per-point buffer or 'way' for polyline query.

    Returns:
        list: List of place dicts with name, type, lat, lon.
    """
    print(f"get_places_along_polyline called with {len(polyline_coords)} coordinates")
    print(f"First few coordinates: {polyline_coords[:3]}")
    print(f"Coordinate type: {type(polyline_coords[0]) if polyline_coords else 'N/A'}")
    print(f"Using radius: {radius_m}m and method: {method}")
    
    if not polyline_coords:
        print("No coordinates provided, returning empty list")
        return []

    # Sample down the coordinates if there are too many to avoid overloading the Overpass API
    if len(polyline_coords) > 100:
        print(f"Too many coordinates ({len(polyline_coords)}), sampling down")
        # Sample every 10th point
        polyline_coords = polyline_coords[::10]
        print(f"Sampled down to {len(polyline_coords)} coordinates")

    def format_polyline_for_overpass(coords):
        return " ".join([f"{lat} {lon}" for lat, lon in coords])

    # Define multiple Overpass API endpoints to try
    overpass_endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
    ]
    
    # Define proper headers with user agent
    headers = {
        "User-Agent": "MapChat/1.0 (https://github.com/yourusername/mapchat; contact@example.com)",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    if method == "way":
        print("Using 'way' method for Overpass query with optimized QL")
        poly_string = format_polyline_for_overpass(polyline_coords)
        
        # More efficient query using Overpass QL features
        query = f"""
        [out:json][timeout:90];
        // Define the route as a set
        way(poly:"{poly_string}")->.route;
        
        // Find places within the specified radius of the route
        // Using a single query instead of multiple queries
        node["place"~"city|town|village"](around.route:{radius_m})->.places;
        
        // Output the results
        .places out center;
        """
    elif method == "node":
        print("Using 'node' method for Overpass query with optimized QL")
        
        # Create a more efficient query using Overpass QL union operations
        # Instead of querying each point separately, we'll create a union of areas
        
        # Select a reasonable number of points to avoid query size limits
        if len(polyline_coords) > 20:
            step = max(1, len(polyline_coords) // 20)
            sample_points = polyline_coords[::step][:20]
            print(f"Using {len(sample_points)} sample points for the query")
        else:
            sample_points = polyline_coords
        
        # Build a more efficient query using union
        query = """
        [out:json][timeout:90];
        (
        """
        
        # Add each point's area to the union
        for lat, lon in sample_points:
            query += f'  node["place"~"city|town|village"](around:{radius_m},{lat},{lon});\n'
        
        query += """
        );
        // Remove duplicates
        out center;
        """
    else:
        raise ValueError("Method must be 'way' or 'node'.")

    # Implement retry logic with exponential backoff
    max_retries = 3
    retry_delay = 2  # Initial delay in seconds
    
    # Try each endpoint with retries
    for endpoint in overpass_endpoints:
        retries = 0
        while retries < max_retries:
            try:
                print(f"Sending Overpass API request to {endpoint} (attempt {retries + 1}/{max_retries})")
                print(f"Query length: {len(query)} characters")
                
                # Add a small random delay to avoid hitting rate limits
                if retries > 0:
                    jitter = random.uniform(0, 1)
                    current_delay = retry_delay * (2 ** retries) + jitter
                    print(f"Waiting {current_delay:.2f} seconds before retry...")
                    time.sleep(current_delay)
                
                # Make the request with proper headers
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    headers=headers,
                    timeout=30  # Add a timeout to avoid hanging requests
                )
                
                print(f"Overpass API response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Success! Parse the response and return places
                    response_json = response.json()
                    elements = response_json.get("elements", [])
                    print(f"Received {len(elements)} elements from Overpass API")
                    
                    seen = set()
                    places = []

                    for elem in elements:
                        tags = elem.get("tags", {})
                        name = tags.get("name")
                        place_type = tags.get("place")
                        lat = elem.get("lat")
                        lon = elem.get("lon")

                        if name and (name, place_type) not in seen:
                            places.append({
                                "name": name,
                                "type": place_type,
                                "lat": lat,
                                "lon": lon
                            })
                            seen.add((name, place_type))

                    print(f"Found {len(places)} unique places")
                    if places:
                        print(f"First few places: {places[:3]}")
                    else:
                        print("No places found")
                    
                    return places
                
                elif response.status_code == 429 or response.status_code == 503:
                    # Rate limited or service unavailable, retry with backoff
                    print(f"Rate limited or service unavailable (status {response.status_code}), will retry...")
                    retries += 1
                    continue
                
                elif response.status_code == 403:
                    # Forbidden - try a different endpoint
                    print(f"Forbidden (status 403) from endpoint {endpoint}, trying next endpoint...")
                    break
                
                else:
                    # Other error, try a different endpoint
                    print(f"Error from endpoint {endpoint}: {response.status_code} - {response.text}")
                    break
                
            except requests.exceptions.RequestException as e:
                # Network error, retry or try next endpoint
                print(f"Request exception when calling {endpoint}: {str(e)}")
                retries += 1
                if retries >= max_retries:
                    print(f"Max retries reached for endpoint {endpoint}, trying next endpoint...")
                    break
    
    # If we've tried all endpoints and still failed, try a simplified fallback approach
    print("All Overpass API endpoints failed, using simplified fallback approach")
    
    # Use a very simple query with minimal features
    try:
        # Select just a few points to minimize query complexity
        sample_points = polyline_coords[::len(polyline_coords)//5 if len(polyline_coords) > 5 else 1][:5]
        
        # Build a very simple query
        simple_query = "[out:json][timeout:60];\n("
        for lat, lon in sample_points:
            simple_query += f'  node["place"~"city|town|village"](around:{radius_m},{lat},{lon});\n'
        simple_query += ");\nout center;"
        
        print(f"Trying simplified query with {len(sample_points)} points")
        
        # Try each endpoint one more time with the simplified query
        for endpoint in overpass_endpoints:
            try:
                response = requests.post(
                    endpoint,
                    data={"data": simple_query},
                    headers=headers,
                    timeout=20
                )
                
                if response.status_code == 200:
                    response_json = response.json()
                    elements = response_json.get("elements", [])
                    
                    seen = set()
                    places = []
                    
                    for elem in elements:
                        tags = elem.get("tags", {})
                        name = tags.get("name")
                        place_type = tags.get("place")
                        lat = elem.get("lat")
                        lon = elem.get("lon")
                        
                        if name and (name, place_type) not in seen:
                            places.append({
                                "name": name,
                                "type": place_type,
                                "lat": lat,
                                "lon": lon
                            })
                            seen.add((name, place_type))
                    
                    print(f"Fallback approach found {len(places)} places")
                    return places
            except:
                continue
    except Exception as e:
        print(f"Fallback approach also failed: {str(e)}")
    
    # If all else fails, return an empty list rather than raising an exception
    print("All approaches failed, returning empty places list")
    return []

import requests


def get_natural_features_along_polyline(polyline_coords: list, radius_m: int = 2000, method: str = "way") -> list:
    """
    Queries Overpass API for natural features (e.g., rivers, lakes, mountains, forests) along a polyline.
    Uses a simplified approach to ensure reliable results.

    Args:
        polyline_coords (list): List of (lat, lon) tuples representing the route.
        radius_m (int): Search radius around the polyline or points.
        method (str): "way" or "node" - how to build the Overpass query.

    Returns:
        list: List of natural features with name (if available), type, lat, lon.
    """
    print(f"get_natural_features_along_polyline called with {len(polyline_coords)} coordinates")
    print(f"First few coordinates: {polyline_coords[:3]}")
    print(f"Coordinate type: {type(polyline_coords[0]) if polyline_coords else 'N/A'}")
    print(f"Using radius: {radius_m}m and method: {method}")
    
    if not polyline_coords:
        print("No coordinates provided, returning empty list")
        return []

    # Sample down the coordinates if there are too many to avoid overloading the Overpass API
    if len(polyline_coords) > 100:
        print(f"Too many coordinates ({len(polyline_coords)}), sampling down")
        # Sample every 10th point
        polyline_coords = polyline_coords[::10]
        print(f"Sampled down to {len(polyline_coords)} coordinates")

    # Further sample down to a reasonable number of points for the query
    if len(polyline_coords) > 20:
        step = max(1, len(polyline_coords) // 20)
        sample_points = polyline_coords[::step][:20]
        print(f"Using {len(sample_points)} sample points for the natural features query")
    else:
        sample_points = polyline_coords

    # Use a simpler approach that's more reliable
    # Instead of trying to use complex Overpass QL features, we'll use a more direct approach
    # that's less likely to cause issues with the Overpass API
    
    # Build a query that searches for natural features around each sample point
    query = "[out:json][timeout:120];\n"
    query += "(\n"
    
    # Add queries for each sample point
    for lat, lon in sample_points:
        # Natural features
        query += f'  node(around:{radius_m},{lat},{lon})["natural"]["name"];\n'
        query += f'  way(around:{radius_m},{lat},{lon})["natural"]["name"];\n'
        
        # Waterways
        query += f'  node(around:{radius_m},{lat},{lon})["waterway"]["name"];\n'
        query += f'  way(around:{radius_m},{lat},{lon})["waterway"]["name"];\n'
    
    query += ");\n"
    query += "out center;"

    print(f"Sending Overpass API request with query length: {len(query)} characters")
    response = requests.post("http://overpass-api.de/api/interpreter", data={"data": query})
    print(f"Overpass API response status: {response.status_code}")
    
    if response.status_code != 200:
        error_msg = f"Overpass API error: {response.status_code} - {response.text}"
        print(error_msg)
        raise Exception(error_msg)

    response_json = response.json()
    elements = response_json.get("elements", [])
    print(f"Received {len(elements)} elements from Overpass API")
    
    seen = set()
    features = []

    for elem in elements:
        tags = elem.get("tags", {})
        name = tags.get("name")
        nat_type = tags.get("natural") or tags.get("waterway")
        lat = elem.get("lat") or elem.get("center", {}).get("lat")
        lon = elem.get("lon") or elem.get("center", {}).get("lon")

        if nat_type and (name or (lat and lon)) and (name, nat_type) not in seen:
            features.append({
                "name": name or "unnamed",
                "type": nat_type,
                "lat": lat,
                "lon": lon
            })
            seen.add((name, nat_type))

    print(f"Found {len(features)} unique natural features")
    if features:
        print(f"First few features: {features[:3]}")
    else:
        print("No natural features found")
    
    return features


import folium
import json

def render_route_map(polyline_coords, places_json="places_along_route.json", features_json="natural_features_along_route.json", output_file="route_map.html"):
    """
    Renders an interactive HTML map with the route, cities/towns, and natural features.

    Args:
        polyline_coords (list): List of (lat, lon) tuples representing the route.
        places_json (str): Path to JSON file with cities/towns/villages.
        features_json (str): Path to JSON file with natural features.
        output_file (str): Output HTML file path.
    """

    # Define color mapping for different place and feature types
    place_colors = {
        "city": "red",
        "town": "orange",
        "village": "yellow"
    }
    natural_colors = {
        "river": "blue",
        "stream": "lightblue",
        "lake": "blue",
        "water": "blue",
        "peak": "purple",
        "wood": "green",
        "beach": "beige",
        "cliff": "gray",
        "valley": "gray",
        "scrub": "green",
        "wetland": "teal",
    }

    # Center map on the first point
    m = folium.Map(location=polyline_coords[0], zoom_start=7)

    # Add the route as a polyline
    folium.PolyLine(locations=polyline_coords, color="black", weight=4, opacity=0.8).add_to(m)

    # Load and add place markers
    with open(places_json, "r") as f:
        places = json.load(f)

    for place in places:
        color = place_colors.get(place["type"], "gray")
        folium.CircleMarker(
            location=(place["lat"], place["lon"]),
            radius=6,
            color=color,
            fill=True,
            fill_opacity=0.9,
            popup=f"{place['name']} ({place['type']})"
        ).add_to(m)

    # Load and add natural feature markers
    with open(features_json, "r") as f:
        features = json.load(f)

    for feature in features:
        color = natural_colors.get(feature["type"], "gray")
        folium.CircleMarker(
            location=(feature["lat"], feature["lon"]),
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=f"{feature['name']} ({feature['type']})"
        ).add_to(m)

    # Save map to file
    m.save(output_file)
    print(f"Map saved to {output_file}")



# ------------------------------
# Example usage and save to file
# ------------------------------
def main():
    """
    Main function to demonstrate fetching a Google Maps route,
    sampling points from the polyline, and saving the result to a file.
    """
    origin = (37.7749, -122.4194)       # San Francisco, CA
    destination = (34.0522, -118.2437)  # Los Angeles, CA
    #waypoints = [(36.1627, -86.7816)]   # Nashville, TN (example only)
    waypoints = []
    route_data = get_google_route(origin, destination, waypoints)
    encoded_polyline = route_data['routes'][0]['polyline']['encodedPolyline']

    # Sample points using 5 km interval
    sampled_points = sample_polyline(encoded_polyline, method="interval", interval_km=25.0)

    output_file_path = 'sampled_points.json'
    with open(output_file_path, 'w') as f:
        json.dump(sampled_points, f, indent=2)

    print(f"Sampled points saved to {output_file_path}")
    
    polyline_coords = polyline.decode(encoded_polyline)
    
    polyline_output_path = 'polyline_route.json'
    with open(polyline_output_path, 'w') as f:
        json.dump(polyline_coords, f, indent=2)

    print(f"Polyline saved to {polyline_output_path}")
    
    # Fetch nearby cities/towns using Overpass and sampled_points
    #places_along_route = get_overpass_places(sampled_points, radius_m=10000)
    
    #Fetch nearby cities/towns using Overpass and polyline
    places_along_route = get_places_along_polyline(sampled_points, method="node", radius_m = 10000)

    places_output_path = 'places_along_route.json'
    with open(places_output_path, 'w') as f:
        json.dump(places_along_route, f, indent=2)

    print(f"Places along route saved to {places_output_path}")
    
    # Query natural features along the route
    features = get_natural_features_along_polyline(sampled_points, method="node", radius_m=2000)

    # Save to a JSON file
    with open("natural_features_along_route.json", "w") as f:
        json.dump(features, f, indent=2)

    print("Natural features saved to natural_features_along_route.json")

    
    points_on_map(sampled_points)
    
    #render_route_map(polyline_coords)
    print("Route Map HTML")

if __name__ == "__main__":
    main()
