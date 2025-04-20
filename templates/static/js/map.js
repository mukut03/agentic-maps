/**
 * Map Module - Handles map initialization and route display
 */

// Map layers
let map;
let routeLayer;
let markersLayer;
let placesLayer;
let featuresLayer;

/**
 * Initialize the map
 */
function initMap() {
    map = L.map('map').setView([37.7749, -122.4194], 5);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    routeLayer = L.layerGroup().addTo(map);
    markersLayer = L.layerGroup().addTo(map);
    placesLayer = L.layerGroup().addTo(map);
    featuresLayer = L.layerGroup().addTo(map);
}

/**
 * Display route on map
 * @param {Object} routeData - Route data from API
 */
function displayRoute(routeData) {
    if (!routeData.polyline_coords || !Array.isArray(routeData.polyline_coords) || routeData.polyline_coords.length === 0) {
        console.error('Invalid polyline coordinates:', routeData.polyline_coords);
        return;
    }
    
    const coords = routeData.polyline_coords.map(point => [point[0], point[1]]);
    
    // Add polyline for the route
    const routePolyline = L.polyline(coords, {
        color: '#3498db',
        weight: 5,
        opacity: 0.7
    }).addTo(routeLayer);
    
    // Add markers for origin and destination
    const originPoint = coords[0];
    const destinationPoint = coords[coords.length - 1];
    
    L.marker(originPoint).addTo(markersLayer)
        .bindPopup('Origin')
        .openPopup();
    
    L.marker(destinationPoint).addTo(markersLayer)
        .bindPopup('Destination');
    
    // Fit map to route bounds using the polyline's bounds
    if (coords.length > 0) {
        map.fitBounds(routePolyline.getBounds(), { padding: [50, 50] });
    }
}

/**
 * Clear all map layers
 */
function clearMapLayers() {
    routeLayer.clearLayers();
    markersLayer.clearLayers();
    placesLayer.clearLayers();
    featuresLayer.clearLayers();
}

/**
 * Display places on map
 * @param {Array} places - Places data from API
 */
function displayPlaces(places) {
    placesLayer.clearLayers();
    
    const placeColors = {
        'city': '#e74c3c',
        'town': '#f39c12',
        'village': '#f1c40f'
    };
    
    places.forEach(place => {
        const color = placeColors[place.type] || '#95a5a6';
        
        L.circleMarker([place.lat, place.lon], {
            radius: place.type === 'city' ? 8 : (place.type === 'town' ? 6 : 4),
            color: color,
            fillColor: color,
            fillOpacity: 0.8
        }).addTo(placesLayer)
            .bindPopup(`<strong>${place.name}</strong><br>${place.type}`);
    });
}

/**
 * Display natural features on map
 * @param {Array} features - Features data from API
 */
function displayFeatures(features) {
    featuresLayer.clearLayers();
    
    const featureColors = {
        'water': '#3498db',
        'river': '#3498db',
        'stream': '#74b9ff',
        'peak': '#9b59b6',
        'wood': '#27ae60',
        'beach': '#f1c40f',
        'cliff': '#95a5a6',
        'valley': '#95a5a6',
        'scrub': '#2ecc71',
        'wetland': '#1abc9c'
    };
    
    features.forEach(feature => {
        if (feature.lat && feature.lon) {
            const color = featureColors[feature.type] || '#95a5a6';
            
            L.circleMarker([feature.lat, feature.lon], {
                radius: 4,
                color: color,
                fillColor: color,
                fillOpacity: 0.8
            }).addTo(featuresLayer)
                .bindPopup(`<strong>${feature.name}</strong><br>${feature.type}`);
        }
    });
}

// Export functions
window.MapModule = {
    initMap,
    displayRoute,
    clearMapLayers,
    displayPlaces,
    displayFeatures,
    getMap: () => map,
    getRoutesLayer: () => routeLayer,
    getMarkersLayer: () => markersLayer,
    getPlacesLayer: () => placesLayer,
    getFeaturesLayer: () => featuresLayer
};
