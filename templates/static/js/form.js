/**
 * Form Module - Handles form functionality for route generation
 */

// Current route data
let currentRoute = null;

/**
 * Initialize form functionality
 */
function initForm() {
    const form = document.getElementById('route-form');
    const addWaypointBtn = document.getElementById('add-waypoint');
    const waypointsContainer = document.getElementById('waypoints-container');
    const sampleRouteCheckbox = document.getElementById('sample-route');
    const samplingOptions = document.getElementById('sampling-options');
    const sampleMethod = document.getElementById('sample-method');
    const intervalGroup = document.getElementById('interval-group');
    const nthGroup = document.getElementById('nth-group');
    const showPlacesCheckbox = document.getElementById('show-places');
    const placesOptions = document.getElementById('places-options');
    const placesRadiusSlider = document.getElementById('places-radius');
    const placesRadiusValue = document.getElementById('places-radius-value');
    const showFeaturesCheckbox = document.getElementById('show-features');
    const featuresOptions = document.getElementById('features-options');
    const featuresRadiusSlider = document.getElementById('features-radius');
    const featuresRadiusValue = document.getElementById('features-radius-value');
    
    // Add waypoint button
    addWaypointBtn.addEventListener('click', () => {
        const waypointDiv = document.createElement('div');
        waypointDiv.className = 'waypoint';
        waypointDiv.innerHTML = `
            <input type="text" class="waypoint-input" placeholder="Enter waypoint address">
            <button type="button" class="remove-waypoint">×</button>
        `;
        waypointsContainer.appendChild(waypointDiv);
        
        // Add event listener to remove button
        const removeBtn = waypointDiv.querySelector('.remove-waypoint');
        removeBtn.addEventListener('click', () => {
            waypointDiv.remove();
        });
        
        // Add event listener to geocode waypoint
        const waypointInput = waypointDiv.querySelector('.waypoint-input');
        waypointInput.addEventListener('blur', () => {
            if (waypointInput.value.trim()) {
                window.ApiModule.geocodeAddress(waypointInput.value, null);
            }
        });
    });
    
    // Sample route checkbox
    sampleRouteCheckbox.addEventListener('change', () => {
        samplingOptions.style.display = sampleRouteCheckbox.checked ? 'block' : 'none';
    });
    
    // Sample method change
    sampleMethod.addEventListener('change', () => {
        if (sampleMethod.value === 'interval') {
            intervalGroup.style.display = 'block';
            nthGroup.style.display = 'none';
        } else {
            intervalGroup.style.display = 'none';
            nthGroup.style.display = 'block';
        }
    });
    
    // Show places checkbox
    showPlacesCheckbox.addEventListener('change', () => {
        placesOptions.style.display = showPlacesCheckbox.checked ? 'block' : 'none';
    });
    
    // Places radius slider
    placesRadiusSlider.addEventListener('input', () => {
        placesRadiusValue.textContent = `${placesRadiusSlider.value} km`;
    });
    
    // Show features checkbox
    showFeaturesCheckbox.addEventListener('change', () => {
        featuresOptions.style.display = showFeaturesCheckbox.checked ? 'block' : 'none';
    });
    
    // Features radius slider
    featuresRadiusSlider.addEventListener('input', () => {
        featuresRadiusValue.textContent = `${featuresRadiusSlider.value} km`;
    });
    
    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await generateRoute();
    });
    
    // Geocode on blur
    document.getElementById('origin').addEventListener('blur', function() {
        if (this.value.trim()) {
            window.ApiModule.geocodeAddress(this.value, 'origin-coords');
        }
    });
    
    document.getElementById('destination').addEventListener('blur', function() {
        if (this.value.trim()) {
            window.ApiModule.geocodeAddress(this.value, 'destination-coords');
        }
    });
}

/**
 * Generate a route
 */
async function generateRoute() {
    const originInput = document.getElementById('origin').value;
    const destinationInput = document.getElementById('destination').value;
    const waypointInputs = Array.from(document.querySelectorAll('.waypoint-input')).map(input => input.value).filter(val => val.trim());
    
    // Show loading
    window.SidebarModule.showLoading();
    
    // Clear previous layers
    window.MapModule.clearMapLayers();
    
    try {
        // Geocode origin and destination
        const origin = await window.ApiModule.geocodeAddress(originInput);
        const destination = await window.ApiModule.geocodeAddress(destinationInput);
        
        if (!origin || !destination) {
            throw new Error('Failed to geocode origin or destination');
        }
        
        // Geocode waypoints
        const waypoints = [];
        for (const waypointInput of waypointInputs) {
            const waypoint = await window.ApiModule.geocodeAddress(waypointInput);
            if (waypoint) {
                waypoints.push(waypoint);
            }
        }
        
        // Prepare request data
        const requestData = {
            origin: { lat: origin.lat, lng: origin.lng },
            destination: { lat: destination.lat, lng: destination.lng },
            waypoints: waypoints.map(wp => ({ lat: wp.lat, lng: wp.lng }))
        };
        
        // Add sampling options if enabled
        if (document.getElementById('sample-route').checked) {
            requestData.sample = true;
            requestData.sample_method = document.getElementById('sample-method').value;
            
            if (requestData.sample_method === 'interval') {
                requestData.interval_km = document.getElementById('interval-km').value;
            } else {
                requestData.every_nth = document.getElementById('every-nth').value;
            }
        }
        
        // Get route
        const routeData = await window.ApiModule.generateRouteRequest(requestData);
        
        // Store current route
        currentRoute = routeData;
        
        // Check if we have the required data to display the route
        if (!routeData.polyline_coords || !Array.isArray(routeData.polyline_coords)) {
            throw new Error('Invalid route data: missing polyline coordinates');
        }
        
        // Display route on map
        window.MapModule.displayRoute(routeData);
        
        // Display route info
        window.SidebarModule.updateRouteInfo(routeData.distance_text, routeData.duration_text);
        
        // Display sampled points info if available
        if (routeData.sampled_points) {
            const count = routeData.sampled_points.length;
            window.SidebarModule.updateSampledInfo(count);
            
            // Add markers for sampled points
            routeData.sampled_points.forEach(point => {
                L.circleMarker([point[0], point[1]], {
                    radius: 5,
                    color: '#e67e22',
                    fillColor: '#e67e22',
                    fillOpacity: 0.8
                }).addTo(window.MapModule.getMarkersLayer());
            });
        } else {
            window.SidebarModule.updateSampledInfo(null);
        }
        
        // Get places if enabled
        if (document.getElementById('show-places').checked) {
            await getPlaces(routeData.polyline_coords);
        }
        
        // Get natural features if enabled
        if (document.getElementById('show-features').checked) {
            await getNaturalFeatures(routeData.polyline_coords);
        }
        
        // Show results
        window.SidebarModule.showResults();
        
    } catch (error) {
        console.error('Error generating route:', error);
        alert(`Error: ${error.message}`);
    } finally {
        // Hide loading
        window.SidebarModule.hideLoading();
    }
}

/**
 * Get places along the route
 * @param {Array} polylineCoords - Route coordinates
 */
async function getPlaces(polylineCoords) {
    try {
        console.log(`Getting places along route with ${polylineCoords.length} coordinates`);
        
        // Get the selected radius from the slider
        const placesRadiusKm = document.getElementById('places-radius').value;
        
        // Get places
        const places = await window.ApiModule.getPlacesRequest(polylineCoords, placesRadiusKm);
        
        // Display places on map
        window.MapModule.displayPlaces(places);
        
        // Update places list
        window.SidebarModule.updatePlacesList(places);
        
    } catch (error) {
        console.error('Error getting places:', error);
        document.getElementById('places-list').innerHTML = `<p>Error loading places: ${error.message}</p>`;
    }
}

/**
 * Get natural features along the route
 * @param {Array} polylineCoords - Route coordinates
 */
async function getNaturalFeatures(polylineCoords) {
    try {
        console.log(`Getting natural features along route with ${polylineCoords.length} coordinates`);
        
        // Get the selected radius from the slider
        const featuresRadiusKm = document.getElementById('features-radius').value;
        
        // Get features
        const features = await window.ApiModule.getFeaturesRequest(polylineCoords, featuresRadiusKm);
        
        // Display features on map
        window.MapModule.displayFeatures(features);
        
        // Update features list
        window.SidebarModule.updateFeaturesList(features);
        
    } catch (error) {
        console.error('Error getting natural features:', error);
        document.getElementById('features-list').innerHTML = `<p>Error loading natural features: ${error.message}</p>`;
    }
}

/**
 * Get current route
 * @returns {Object|null} - Current route data
 */
function getCurrentRoute() {
    return currentRoute;
}

// Export functions
window.FormModule = {
    initForm,
    generateRoute,
    getPlaces,
    getNaturalFeatures,
    getCurrentRoute
};
