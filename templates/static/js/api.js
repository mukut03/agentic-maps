/**
 * API Module - Handles all API requests
 */

/**
 * Geocode an address
 * @param {string} address - Address to geocode
 * @param {string|null} displayElementId - Optional element ID to display result
 * @returns {Promise<Object|null>} - Geocoded coordinates or null on error
 */
async function geocodeAddress(address, displayElementId) {
    try {
        const response = await fetch('/geocode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ address })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (displayElementId) {
                document.getElementById(displayElementId).textContent = 
                    `Lat: ${data.lat.toFixed(6)}, Lng: ${data.lng.toFixed(6)}`;
            }
            return data;
        } else {
            console.error('Geocoding error:', data.error);
            if (displayElementId) {
                document.getElementById(displayElementId).textContent = 
                    `Error: ${data.error}`;
                document.getElementById(displayElementId).classList.add('error');
            }
            return null;
        }
    } catch (error) {
        console.error('Geocoding error:', error);
        if (displayElementId) {
            document.getElementById(displayElementId).textContent = 
                `Error: ${error.message}`;
            document.getElementById(displayElementId).classList.add('error');
        }
        return null;
    }
}

/**
 * Generate a route
 * @param {Object} requestData - Route request data
 * @returns {Promise<Object>} - Route data
 */
async function generateRouteRequest(requestData) {
    const response = await fetch('/route', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    
    const routeData = await response.json();
    
    if (!response.ok || routeData.error) {
        throw new Error(routeData.error || 'Failed to generate route');
    }
    
    return routeData;
}

/**
 * Get places along a route
 * @param {Array} polylineCoords - Route coordinates
 * @param {number} radiusKm - Search radius in kilometers
 * @returns {Promise<Array>} - Places data
 */
async function getPlacesRequest(polylineCoords, radiusKm) {
    const radiusM = radiusKm * 1000;
    
    const requestData = {
        polyline_coords: polylineCoords,
        radius_m: radiusM,
        method: "node"
    };
    
    const response = await fetch('/places', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get places');
    }
    
    const data = await response.json();
    return data.places;
}

/**
 * Get natural features along a route
 * @param {Array} polylineCoords - Route coordinates
 * @param {number} radiusKm - Search radius in kilometers
 * @returns {Promise<Array>} - Features data
 */
async function getFeaturesRequest(polylineCoords, radiusKm) {
    const radiusM = radiusKm * 1000;
    
    const requestData = {
        polyline_coords: polylineCoords,
        radius_m: radiusM,
        method: "way"
    };
    
    const response = await fetch('/natural_features', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to get natural features');
    }
    
    const data = await response.json();
    return data.features;
}

/**
 * Send a chat message
 * @param {string} message - Message to send
 * @returns {Promise<Object>} - Response data
 */
async function sendChatMessage(message) {
    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
    });
    
    if (!response.ok) {
        throw new Error('Failed to send message');
    }
    
    return await response.json();
}

/**
 * Reset chat conversation
 * @returns {Promise<boolean>} - Success status
 */
async function resetChatConversation() {
    const response = await fetch('/chat/reset', {
        method: 'POST'
    });
    
    return response.ok;
}

/**
 * Load chat history
 * @returns {Promise<Array>} - Chat history
 */
async function loadChatHistory() {
    const response = await fetch('/chat/history');
    
    if (!response.ok) {
        throw new Error('Failed to load chat history');
    }
    
    const data = await response.json();
    return data.history;
}

// Export functions
window.ApiModule = {
    geocodeAddress,
    generateRouteRequest,
    getPlacesRequest,
    getFeaturesRequest,
    sendChatMessage,
    resetChatConversation,
    loadChatHistory
};
