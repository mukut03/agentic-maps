/**
 * Chat Module - Handles chat functionality
 */

/**
 * Initialize chat functionality
 */
function initChat() {
    console.log('🔄 Initializing Chat Module...');
    
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const chatResetBtn = document.getElementById('chat-reset-btn');
    
    console.log('📌 Chat elements found:', {
        chatInput: !!chatInput,
        chatSendBtn: !!chatSendBtn,
        chatMessages: !!chatMessages,
        chatResetBtn: !!chatResetBtn
    });
    
    // Send message on button click
    chatSendBtn.addEventListener('click', () => {
        console.log('🖱️ Chat send button clicked');
        sendMessage();
    });
    
    // Send message on Enter key (but allow Shift+Enter for new lines)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            console.log('⌨️ Enter key pressed in chat input');
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Reset conversation
    chatResetBtn.addEventListener('click', async () => {
        console.log('🔄 Reset conversation button clicked');
        try {
            console.log('📤 Sending reset conversation request to API...');
            const success = await window.ApiModule.resetChatConversation();
            
            if (success) {
                console.log('✅ Conversation reset successful');
                // Clear chat messages except for the initial greeting
                chatMessages.innerHTML = `
                    <div class="chat-message assistant">
                        Hello! I'm MapChat, your route planning assistant. How can I help you today? You can ask me to find routes, show places along a route, or tell you about natural features you'll encounter on your journey.
                    </div>
                `;
                
                // Clear any displayed route
                console.log('🗑️ Clearing map layers');
                window.MapModule.clearMapLayers();
            } else {
                console.error('❌ Failed to reset conversation');
            }
        } catch (error) {
            console.error('❌ Error resetting conversation:', error);
        }
    });
    
    // Load chat history
    console.log('📥 Loading chat history...');
    loadChatHistory();
    
    console.log('✅ Chat Module initialized successfully');
}

/**
 * Send a message
 */
async function sendMessage() {
    console.log('🔄 Starting sendMessage function');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const message = chatInput.value.trim();
    
    console.log('📝 User message:', message);
    
    if (!message) {
        console.log('⚠️ Empty message, not sending');
        return;
    }
    
    // Add user message to chat
    console.log('➕ Adding user message to chat UI');
    const userMessageElement = document.createElement('div');
    userMessageElement.className = 'chat-message user';
    userMessageElement.textContent = message;
    chatMessages.appendChild(userMessageElement);
    
    // Clear input
    console.log('🧹 Clearing input field');
    chatInput.value = '';
    
    // Scroll to bottom
    console.log('📜 Scrolling chat to bottom');
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        // Create a placeholder for the assistant's message
        console.log('➕ Adding assistant response placeholder to chat UI');
        const assistantMessageElement = document.createElement('div');
        assistantMessageElement.className = 'chat-message assistant';
        assistantMessageElement.textContent = ''; // Start empty
        chatMessages.appendChild(assistantMessageElement);
        
        // Add a blinking cursor to indicate typing
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        cursor.textContent = '▋';
        cursor.style.animation = 'blink 1s step-end infinite';
        assistantMessageElement.appendChild(cursor);
        
        // Scroll to bottom
        console.log('📜 Scrolling chat to bottom');
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Stream the message from the backend
        console.log('📤 Streaming message from backend API...');
        console.time('chatApiStreamResponse');
        
        // Use the streaming API
        window.ApiModule.streamChatMessage(
            message,
            // onChunk callback - called for each chunk of the response
            (chunk) => {
                // Remove the cursor if it exists
                if (cursor.parentNode === assistantMessageElement) {
                    assistantMessageElement.removeChild(cursor);
                }
                
                // Append the chunk to the message
                assistantMessageElement.textContent += chunk;
                
                // Re-add the cursor at the end
                assistantMessageElement.appendChild(cursor);
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            },
            // onComplete callback - called when streaming is complete
            (result) => { // Expect a single result object
                // Simplified diagnostic log:
                console.log('onComplete received responseText type:', typeof result.responseText);
                console.log('onComplete received requiresUpdate value:', result && result.requiresUpdate);
                
                console.timeEnd('chatApiStreamResponse');
                
                // Remove the cursor
                if (cursor.parentNode === assistantMessageElement) {
                    assistantMessageElement.removeChild(cursor);
                }
                
                // Set the final message from the object property
                assistantMessageElement.textContent = result && result.responseText || '';
                
                // Scroll to bottom one last time
                chatMessages.scrollTop = chatMessages.scrollHeight;
                
                // Check if we need to update the UI based on the flag in the result object
                if (result && result.requiresUpdate) { 
                    console.log('✅ UI update required, calling checkForRouteUpdate()');
                    checkForRouteUpdate();
                } else {
                    console.log('ℹ️ No UI update required by this response.');
                }
            },
            // onError callback - called if there's an error
            (error) => {
                console.error('❌ Error streaming message:', error);
                
                // Remove the cursor
                if (cursor.parentNode === assistantMessageElement) {
                    assistantMessageElement.removeChild(cursor);
                }
                
                // Set an error message
                assistantMessageElement.textContent = 'Sorry, there was an error processing your request. Please try again.';
                assistantMessageElement.classList.add('error');
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        );
    } catch (error) {
        console.error('❌ Error sending message:', error);
        
        // Add error message to chat
        console.log('➕ Adding error message to chat UI');
        const errorMessageElement = document.createElement('div');
        errorMessageElement.className = 'chat-message assistant error';
        errorMessageElement.textContent = 'Sorry, there was an error processing your request. Please try again.';
        chatMessages.appendChild(errorMessageElement);
        
        // Scroll to bottom
        console.log('📜 Scrolling chat to bottom');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

/**
 * Load chat history
 */
async function loadChatHistory() {
    console.log('🔄 Loading chat history...');
    const chatMessages = document.getElementById('chat-messages');
    
    try {
        console.log('📤 Requesting chat history from API...');
        console.time('loadChatHistory');
        const history = await window.ApiModule.loadChatHistory();
        console.timeEnd('loadChatHistory');
        
        console.log('📥 Received chat history:', history);
        
        // Clear chat messages
        console.log('🧹 Clearing existing chat messages');
        chatMessages.innerHTML = '';
        
        // Add messages to chat
        console.log('➕ Adding history messages to chat UI');
        history.forEach((message, index) => {
            console.log(`📝 Adding message ${index + 1}/${history.length} (${message.role})`);
            const messageElement = document.createElement('div');
            messageElement.className = `chat-message ${message.role}`;
            messageElement.textContent = message.content;
            chatMessages.appendChild(messageElement);
        });
        
        // If no messages, add initial greeting
        if (history.length === 0) {
            console.log('ℹ️ No history found, adding initial greeting');
            const greetingElement = document.createElement('div');
            greetingElement.className = 'chat-message assistant';
            greetingElement.textContent = "Hello! I'm MapChat, your route planning assistant. How can I help you today? You can ask me to find routes, show places along a route, or tell you about natural features you'll encounter on your journey.";
            chatMessages.appendChild(greetingElement);
        }
        
        // Scroll to bottom
        console.log('📜 Scrolling chat to bottom');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (error) {
        console.error('❌ Error loading chat history:', error);
        
        // Add initial greeting if loading fails
        console.log('➕ Adding fallback greeting due to error');
        chatMessages.innerHTML = `
            <div class="chat-message assistant">
                Hello! I'm MapChat, your route planning assistant. How can I help you today? You can ask me to find routes, show places along a route, or tell you about natural features you'll encounter on your journey.
            </div>
        `;
    }
    
    console.log('✅ Chat history loading complete');
}

/**
 * Check if we need to update the UI with route data
 */
async function checkForRouteUpdate() {
    // This function is now called explicitly when requiresUpdate is true
    console.log('🔄 Performing route update check...');
    
    try {
        // Get the current route data
        const routeData = await window.ApiModule.getCurrentRouteData();
        
        // If there's no route data, return
        if (!routeData) {
            console.log('ℹ️ No route data found, skipping UI update');
            return;
        }
        
        console.log('📥 Route data found, updating UI');
        
        // Update the form fields
        const originInput = document.getElementById('origin');
        const destinationInput = document.getElementById('destination');
        const waypointsContainer = document.getElementById('waypoints-container');
        
        if (originInput && routeData.origin) {
            originInput.value = routeData.origin.display_name || '';
            console.log('✅ Updated origin input:', originInput.value);
            
            // Update origin coordinates display if available
            const originCoordsElement = document.getElementById('origin-coords');
            if (originCoordsElement && routeData.origin.lat && routeData.origin.lng) {
                originCoordsElement.textContent = `Lat: ${routeData.origin.lat.toFixed(6)}, Lng: ${routeData.origin.lng.toFixed(6)}`;
            }
        }
        
        if (destinationInput && routeData.destination) {
            destinationInput.value = routeData.destination.display_name || '';
            console.log('✅ Updated destination input:', destinationInput.value);
            
            // Update destination coordinates display if available
            const destinationCoordsElement = document.getElementById('destination-coords');
            if (destinationCoordsElement && routeData.destination.lat && routeData.destination.lng) {
                destinationCoordsElement.textContent = `Lat: ${routeData.destination.lat.toFixed(6)}, Lng: ${routeData.destination.lng.toFixed(6)}`;
            }
        }
        
        // Clear existing waypoints
        if (waypointsContainer) {
            waypointsContainer.innerHTML = '';
            
            // Add waypoints
            if (routeData.waypoints && routeData.waypoints.length > 0) {
                routeData.waypoints.forEach(waypoint => {
                    const waypointDiv = document.createElement('div');
                    waypointDiv.className = 'waypoint';
                    waypointDiv.innerHTML = `
                        <input type="text" class="waypoint-input" placeholder="Enter waypoint address" value="${waypoint.display_name || ''}">
                        <button type="button" class="remove-waypoint">×</button>
                    `;
                    waypointsContainer.appendChild(waypointDiv);
                    
                    // Add event listener to remove button
                    const removeBtn = waypointDiv.querySelector('.remove-waypoint');
                    removeBtn.addEventListener('click', () => {
                        waypointDiv.remove();
                    });
                });
                
                console.log('✅ Added waypoints:', routeData.waypoints.length);
            }
        }

        // Check if we already have a valid route in memory
        const existingRoute = window.FormModule.getCurrentRoute();
        
        // If we have a valid route in memory, use it directly
        if (existingRoute && existingRoute.polyline_coords) {
            console.log('✅ Using existing route from memory');
            
            // Display the route on the map
            window.MapModule.displayRoute(existingRoute);
            
            // Update route info in the sidebar
            window.SidebarModule.updateRouteInfo(existingRoute.distance_text, existingRoute.duration_text);
            
            // Display sampled points if available
            if (existingRoute.sampled_points) {
                const count = existingRoute.sampled_points.length;
                window.SidebarModule.updateSampledInfo(count);
                
                // Add markers for sampled points
                existingRoute.sampled_points.forEach(point => {
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
            
            // Check if places or features are enabled and display them
            if (document.getElementById('show-places').checked) {
                // Get current places data
                const currentPlaces = window.FormModule.getCurrentPlaces();
                const placesRadiusKm = document.getElementById('places-radius').value;
                const forceRefreshPlaces = !currentPlaces || currentPlaces.radius !== placesRadiusKm;
                
                window.FormModule.getPlaces(existingRoute.polyline_coords, forceRefreshPlaces);
            }
            
            if (document.getElementById('show-features').checked) {
                // Get current features data
                const currentFeatures = window.FormModule.getCurrentFeatures();
                const featuresRadiusKm = document.getElementById('features-radius').value;
                const forceRefreshFeatures = !currentFeatures || currentFeatures.radius !== featuresRadiusKm;
                
                window.FormModule.getNaturalFeatures(existingRoute.polyline_coords, forceRefreshFeatures);
            }
            
            // Show results
            window.SidebarModule.showResults();
        } else {
            // If we don't have a valid route in memory, trigger the Generate Route button
            console.log('ℹ️ No valid route in memory, triggering Generate Route button');
            const generateRouteBtn = document.getElementById('generate-route');
            if (generateRouteBtn) {
                console.log('🖱️ Programmatically clicking the Generate Route button to update the map and sidebar');
                generateRouteBtn.click();
            } else {
                console.error('❌ Could not find Generate Route button (id="generate-route") to trigger route update');
            }
        }

        // Switch to the Info tab
        const infoToggle = document.getElementById('info-toggle');
        const chatToggle = document.getElementById('chat-toggle');
        const infoContent = document.getElementById('info-content');
        const chatContent = document.getElementById('chat-content');
        
        if (infoToggle && chatToggle && infoContent && chatContent) {
            infoToggle.click();
        }
        
    } catch (error) {
        console.error('❌ Error checking for route updates:', error);
    }
}

// Export functions
window.ChatModule = {
    initChat,
    sendMessage,
    loadChatHistory,
    checkForRouteUpdate
};
