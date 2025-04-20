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
    console.log('🔄 Geocoding address:', address);
    try {
        console.time('geocodeRequest');
        const response = await fetch('/geocode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ address })
        });
        console.timeEnd('geocodeRequest');
        
        const data = await response.json();
        console.log('📥 Geocode response:', data);
        
        if (response.ok) {
            if (displayElementId) {
                document.getElementById(displayElementId).textContent = 
                    `Lat: ${data.lat.toFixed(6)}, Lng: ${data.lng.toFixed(6)}`;
                console.log('✅ Geocode result displayed in element:', displayElementId);
            }
            return data;
        } else {
            console.error('❌ Geocoding error:', data.error);
            if (displayElementId) {
                document.getElementById(displayElementId).textContent = 
                    `Error: ${data.error}`;
                document.getElementById(displayElementId).classList.add('error');
                console.log('⚠️ Geocode error displayed in element:', displayElementId);
            }
            return null;
        }
    } catch (error) {
        console.error('❌ Geocoding exception:', error);
        if (displayElementId) {
            document.getElementById(displayElementId).textContent = 
                `Error: ${error.message}`;
            document.getElementById(displayElementId).classList.add('error');
            console.log('⚠️ Geocode exception displayed in element:', displayElementId);
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
    console.log('🔄 Generating route with data:', requestData);
    console.time('routeRequest');
    const response = await fetch('/route', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    console.timeEnd('routeRequest');
    
    const routeData = await response.json();
    console.log('📥 Route response received:', {
        success: response.ok,
        hasError: !!routeData.error,
        dataKeys: Object.keys(routeData)
    });
    
    if (!response.ok || routeData.error) {
        console.error('❌ Route generation error:', routeData.error || 'Unknown error');
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
    console.log('🔄 Getting places along route:', {
        coordinateCount: polylineCoords.length,
        radiusKm: radiusKm
    });
    
    const radiusM = radiusKm * 1000;
    
    const requestData = {
        polyline_coords: polylineCoords,
        radius_m: radiusM,
        method: "node"
    };
    
    console.time('placesRequest');
    const response = await fetch('/places', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    console.timeEnd('placesRequest');
    
    if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Places request error:', errorData.error || 'Unknown error');
        throw new Error(errorData.error || 'Failed to get places');
    }
    
    const data = await response.json();
    console.log('📥 Places response received:', {
        placeCount: data.places ? data.places.length : 0
    });
    
    return data.places;
}

/**
 * Get natural features along a route
 * @param {Array} polylineCoords - Route coordinates
 * @param {number} radiusKm - Search radius in kilometers
 * @returns {Promise<Array>} - Features data
 */
async function getFeaturesRequest(polylineCoords, radiusKm) {
    console.log('🔄 Getting natural features along route:', {
        coordinateCount: polylineCoords.length,
        radiusKm: radiusKm
    });
    
    const radiusM = radiusKm * 1000;
    
    const requestData = {
        polyline_coords: polylineCoords,
        radius_m: radiusM,
        method: "way"
    };
    
    console.time('featuresRequest');
    const response = await fetch('/natural_features', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    console.timeEnd('featuresRequest');
    
    if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ Features request error:', errorData.error || 'Unknown error');
        throw new Error(errorData.error || 'Failed to get natural features');
    }
    
    const data = await response.json();
    console.log('📥 Features response received:', {
        featureCount: data.features ? data.features.length : 0
    });
    
    return data.features;
}

/**
 * Send a chat message
 * @param {string} message - Message to send
 * @returns {Promise<Object>} - Response data
 */
async function sendChatMessage(message) {
    console.log('🔄 Sending chat message to LLM:', message);
    
    console.time('chatRequest');
    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
    });
    console.timeEnd('chatRequest');
    
    if (!response.ok) {
        console.error('❌ Chat request failed with status:', response.status);
        throw new Error('Failed to send message');
    }
    
    const data = await response.json();
    console.log('📥 Chat response received:', {
        messageLength: data.message ? data.message.length : 0,
        requiresUiUpdate: !!data.requires_ui_update
    });
    
    if (data.requires_ui_update) {
        console.log('ℹ️ Chat response requires UI update');
    }
    
    return data;
}

/**
 * Stream a chat message
 * 
 * IMPORTANT: All user chat messages (typed in the chat input) MUST always be sent to /chat/stream
 * via this function, so that the backend can perform intent classification and robustly choose
 * between route, places, features, or context-based answers. Do NOT use direct endpoints for chat
 * input, only for manual form submissions.
 * 
 * @param {string} message - Message to send
 * @param {function} onChunk - Callback for each chunk of the response
 * @param {function} onComplete - Callback when streaming is complete
 * @param {function} onError - Callback for errors
 */
function streamChatMessage(message, onChunk, onComplete, onError) {
    console.log('🔄 Streaming chat message to LLM:', message);
    
    console.time('chatStreamRequest');
    
    // First, send a POST request to initiate the streaming response
    fetch('/chat/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
    }).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Create a new ReadableStream from the response body
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        // Initialize variables
        let fullResponse = '';
        let requiresUpdate = false; // Flag to store if UI update is needed
        
        // Function to process the stream
        function processStream() {
            // Read from the stream
            reader.read().then(({ done, value }) => {
                // If the stream is done, call the onComplete callback
                if (done) {
                    console.log('📥 Chat stream complete:', {
                        messageLength: fullResponse.length,
                        requiresUpdate: requiresUpdate
                    });
                    
                    // Attach the flag to the response string object
                    if (typeof fullResponse === 'string') {
                        fullResponse = new String(fullResponse); // Ensure it's an object
                    }
                    // Call the onComplete callback with an object containing text and flag
                    if (onComplete && typeof onComplete === 'function') {
                        onComplete({ responseText: fullResponse, requiresUpdate: requiresUpdate }); 
                    }
                    
                    console.timeEnd('chatStreamRequest');
                    return;
                }
                
                // Decode the chunk and add it to the buffer
                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                
                // Process any complete SSE messages in the buffer
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || ''; // Keep the last incomplete line in the buffer
                
                // Process each complete SSE message
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            // --- Handle different event types ---
                            
                            // 1. Route Generated Event
                            if (data.status === 'route_generated') {
                                console.log('✅ Received route_generated event:', data);
                                fullResponse = data.message || ''; // Use the message from the event
                                requiresUpdate = data.requires_ui_update || false;
                                
                                // Call onComplete immediately with an object
                                if (onComplete && typeof onComplete === 'function') {
                                    onComplete({ responseText: fullResponse, requiresUpdate: requiresUpdate });
                                }
                                reader.cancel(); // Stop reading the stream
                                console.timeEnd('chatStreamRequest');
                                return; 
                            }
                            
                            // 2. Places Requested Event
                            if (data.status === 'places_requested') {
                                console.log('✅ Received places_requested event:', data);
                                fullResponse = data.message || ''; // Use the message from the event
                                requiresUpdate = data.requires_ui_update || false;
                                
                                // Check the "show places" checkbox
                                if (data.show_places) {
                                    console.log('🔄 Checking "show places" checkbox');
                                    const showPlacesCheckbox = document.getElementById('show-places');
                                    if (showPlacesCheckbox && !showPlacesCheckbox.checked) {
                                        showPlacesCheckbox.checked = true;
                                        // Trigger the change event to show the options
                                        const changeEvent = new Event('change', { bubbles: true });
                                        showPlacesCheckbox.dispatchEvent(changeEvent);
                                    }
                                    
                                    // Get the current route and places data
                                    const currentRoute = window.FormModule.getCurrentRoute();
                                    const currentPlaces = window.FormModule.getCurrentPlaces();
                                    
                                    if (currentRoute && currentRoute.polyline_coords) {
                                        console.log('✅ Using existing route for places request');
                                        // Directly call getPlaces with the existing polyline
                                        // Check if we need to force refresh (e.g., if radius changed)
                                        const placesRadiusKm = document.getElementById('places-radius').value;
                                        const forceRefresh = !currentPlaces || currentPlaces.radius !== placesRadiusKm;
                                        
                                        window.FormModule.getPlaces(currentRoute.polyline_coords, forceRefresh);
                                    } else {
                                        // Only click generate route if we don't have a route
                                        console.log('🖱️ Clicking generate route button to create route and get places');
                                        const generateRouteBtn = document.getElementById('generate-route');
                                        if (generateRouteBtn) {
                                            generateRouteBtn.click();
                                        }
                                    }
                                }
                                
                                // Call onComplete immediately with an object
                                if (onComplete && typeof onComplete === 'function') {
                                    onComplete({ responseText: fullResponse, requiresUpdate: requiresUpdate });
                                }
                                reader.cancel(); // Stop reading the stream
                                console.timeEnd('chatStreamRequest');
                                return; 
                            }
                            
                            // 3. Features Requested Event
                            if (data.status === 'features_requested') {
                                console.log('✅ Received features_requested event:', data);
                                fullResponse = data.message || ''; // Use the message from the event
                                requiresUpdate = data.requires_ui_update || false;
                                
                                // Check the "show features" checkbox
                                if (data.show_features) {
                                    console.log('🔄 Checking "show features" checkbox');
                                    const showFeaturesCheckbox = document.getElementById('show-features');
                                    if (showFeaturesCheckbox && !showFeaturesCheckbox.checked) {
                                        showFeaturesCheckbox.checked = true;
                                        // Trigger the change event to show the options
                                        const changeEvent = new Event('change', { bubbles: true });
                                        showFeaturesCheckbox.dispatchEvent(changeEvent);
                                    }
                                    
                                    // Get the current route and features data
                                    const currentRoute = window.FormModule.getCurrentRoute();
                                    const currentFeatures = window.FormModule.getCurrentFeatures();
                                    
                                    if (currentRoute && currentRoute.polyline_coords) {
                                        console.log('✅ Using existing route for features request');
                                        // Directly call getNaturalFeatures with the existing polyline
                                        // Check if we need to force refresh (e.g., if radius changed)
                                        const featuresRadiusKm = document.getElementById('features-radius').value;
                                        const forceRefresh = !currentFeatures || currentFeatures.radius !== featuresRadiusKm;
                                        
                                        window.FormModule.getNaturalFeatures(currentRoute.polyline_coords, forceRefresh);
                                    } else {
                                        // Only click generate route if we don't have a route
                                        console.log('🖱️ Clicking generate route button to create route and get features');
                                        const generateRouteBtn = document.getElementById('generate-route');
                                        if (generateRouteBtn) {
                                            generateRouteBtn.click();
                                        }
                                    }
                                }
                                
                                // Call onComplete immediately with an object
                                if (onComplete && typeof onComplete === 'function') {
                                    onComplete({ responseText: fullResponse, requiresUpdate: requiresUpdate });
                                }
                                reader.cancel(); // Stop reading the stream
                                console.timeEnd('chatStreamRequest');
                                return; 
                            }
                            
                            // 4. Waypoint Added Event
                            if (data.status === 'waypoint_added') {
                                console.log('✅ Received waypoint_added event:', data);
                                fullResponse = data.message || ''; // Use the message from the event
                                requiresUpdate = data.requires_ui_update || false;
                                
                                // Add the waypoint to the form
                                if (data.waypoint) {
                                    console.log('🔄 Adding waypoint to form:', data.waypoint);
                                    
                                    // Get the waypoints container
                                    const waypointsContainer = document.getElementById('waypoints-container');
                                    if (waypointsContainer) {
                                        // Create a new waypoint div
                                        const waypointDiv = document.createElement('div');
                                        waypointDiv.className = 'waypoint';
                                        waypointDiv.innerHTML = `
                                            <input type="text" class="waypoint-input" placeholder="Enter waypoint address" value="${data.waypoint.display_name || ''}">
                                            <button type="button" class="remove-waypoint">×</button>
                                        `;
                                        waypointsContainer.appendChild(waypointDiv);
                                        
                                        // Add event listener to remove button
                                        const removeBtn = waypointDiv.querySelector('.remove-waypoint');
                                        removeBtn.addEventListener('click', () => {
                                            waypointDiv.remove();
                                        });
                                        
                                        console.log('✅ Waypoint added to form successfully');
                                        
                                        // Click the generate route button to update the route
                                        console.log('🖱️ Clicking generate route button to update route with new waypoint');
                                        const generateRouteBtn = document.getElementById('generate-route');
                                        if (generateRouteBtn) {
                                            generateRouteBtn.click();
                                        }
                                    } else {
                                        console.error('❌ Could not find waypoints container');
                                    }
                                }
                                
                                // Call onComplete immediately with an object
                                if (onComplete && typeof onComplete === 'function') {
                                    onComplete({ responseText: fullResponse, requiresUpdate: requiresUpdate });
                                }
                                reader.cancel(); // Stop reading the stream
                                console.timeEnd('chatStreamRequest');
                                return; 
                            }
                            
                            // 2. Chunk Event
                            if (data.chunk) {
                                fullResponse += data.chunk;
                                if (onChunk && typeof onChunk === 'function') {
                                    onChunk(data.chunk);
                                }
                            }
                            
                            // 3. Completion Event (for normal LLM streaming)
                            if (data.complete) {
                                console.log('📥 Received completion event:', data);
                                requiresUpdate = data.requires_ui_update || false; // Capture flag
                                // Don't call onComplete here, wait for 'done'
                            }
                            
                            // 4. Error Event
                            if (data.error) {
                                console.error('❌ Error in chat stream data:', data.error);
                                if (onError && typeof onError === 'function') {
                                    onError(data.error);
                                }
                                reader.cancel(); // Stop reading the stream
                                console.timeEnd('chatStreamRequest');
                                return;
                            }
                            
                        } catch (error) {
                            console.error('❌ Error parsing SSE data:', error, line);
                            // Optionally call onError or just log
                        }
                    }
                }
                
                // Continue reading from the stream
                processStream();
            }).catch(error => {
                console.error('❌ Error reading from stream:', error);
                
                // Call the onError callback with the error
                if (onError && typeof onError === 'function') {
                    onError(error.message);
                }
                
                console.timeEnd('chatStreamRequest');
            });
        }
        
        // Start processing the stream
        processStream();
        
        // Return a function to manually close the stream if needed
        return {
            close: () => {
                reader.cancel();
                console.timeEnd('chatStreamRequest');
                console.log('🛑 Chat stream manually closed');
            }
        };
    }).catch(error => {
        console.error('❌ Error initiating chat stream:', error);
        
        // Call the onError callback with the error
        if (onError && typeof onError === 'function') {
            onError(error.message);
        }
        
        console.timeEnd('chatStreamRequest');
    });
    
    // Return a dummy close function in case the fetch fails
    return {
        close: () => {
            console.timeEnd('chatStreamRequest');
            console.log('🛑 Chat stream manually closed (dummy)');
        }
    };
}

/**
 * Reset chat conversation
 * @returns {Promise<boolean>} - Success status
 */
async function resetChatConversation() {
    console.log('🔄 Resetting chat conversation');
    
    console.time('resetChatRequest');
    const response = await fetch('/chat/reset', {
        method: 'POST'
    });
    console.timeEnd('resetChatRequest');
    
    const data = await response.json();
    console.log('📥 Reset chat response:', data);
    
    return response.ok;
}

/**
 * Get current route data
 * @returns {Promise<Object|null>} - Current route data or null if no active route
 */
async function getCurrentRouteData() {
    console.log('🔄 Getting current route data');
    
    console.time('getCurrentRouteRequest');
    try {
        const response = await fetch('/get_current_route');
        console.timeEnd('getCurrentRouteRequest');
        
        if (!response.ok) {
            if (response.status === 404) {
                console.log('ℹ️ No active route found');
                return null;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📥 Current route data received:', {
            hasOrigin: !!data.origin,
            hasDestination: !!data.destination,
            waypointCount: data.waypoints ? data.waypoints.length : 0,
            hasRouteData: !!data.route_data
        });
        
        return data;
    } catch (error) {
        console.error('❌ Error getting current route data:', error);
        return null;
    }
}

/**
 * Load chat history
 * @returns {Promise<Array>} - Chat history
 */
async function loadChatHistory() {
    console.log('🔄 Loading chat history');
    
    console.time('chatHistoryRequest');
    const response = await fetch('/chat/history');
    console.timeEnd('chatHistoryRequest');
    
    if (!response.ok) {
        console.error('❌ Failed to load chat history with status:', response.status);
        throw new Error('Failed to load chat history');
    }
    
    const data = await response.json();
    console.log('📥 Chat history received:', {
        messageCount: data.history ? data.history.length : 0
    });
    
    return data.history;
}

/**
 * Update conversation state with route data
 * @param {Object} routeData - Route data
 * @param {Object} origin - Origin location data
 * @param {Object} destination - Destination location data
 * @param {Array} waypoints - Waypoint location data
 * @returns {Promise<boolean>} - Success status
 */
async function updateConversationState(routeData, origin, destination, waypoints) {
    console.log('🔄 Updating conversation state with route data');
    
    console.time('updateConversationStateRequest');
    const response = await fetch('/update_conversation_state', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            origin: origin,
            destination: destination,
            waypoints: waypoints,
            route_data: routeData
        })
    });
    console.timeEnd('updateConversationStateRequest');
    
    const data = await response.json();
    console.log('📥 Update conversation state response:', data);
    
    return response.ok;
}

/**
 * Get the latest route polyline and data
 * @returns {Promise<Object|null>} - Route data or null on error
 */
async function getRouteData() {
    console.log('🔄 Fetching latest route data from /get_route');
    try {
        const response = await fetch('/get_route');
        if (!response.ok) {
            console.error('❌ Failed to fetch route data with status:', response.status);
            return null;
        }
        const data = await response.json();
        console.log('📥 /get_route response:', data);
        return data;
    } catch (error) {
        console.error('❌ Error fetching route data:', error);
        return null;
    }
}

// Export functions
window.ApiModule = {
    geocodeAddress,
    generateRouteRequest,
    getPlacesRequest,
    getFeaturesRequest,
    sendChatMessage,
    streamChatMessage,
    resetChatConversation,
    getCurrentRouteData,
    getRouteData,
    loadChatHistory,
    updateConversationState
};
