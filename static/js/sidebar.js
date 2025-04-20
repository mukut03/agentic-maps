/**
 * Sidebar Module - Handles sidebar toggle functionality and tab switching
 */

/**
 * Initialize sidebar functionality
 */
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mapContainer = document.getElementById('map-container');
    const sidebarToggleHandle = document.getElementById('sidebar-toggle-handle');
    const infoToggle = document.getElementById('info-toggle');
    const chatToggle = document.getElementById('chat-toggle');
    const infoContent = document.getElementById('info-content');
    const chatContent = document.getElementById('chat-content');
    
    // Toggle sidebar visibility
    sidebarToggleHandle.addEventListener('click', () => {
        sidebar.classList.toggle('hidden');
        mapContainer.classList.toggle('expanded');
        
        // Update toggle handle icon
        if (sidebar.classList.contains('hidden')) {
            sidebarToggleHandle.innerHTML = '<span>▶</span>';
        } else {
            sidebarToggleHandle.innerHTML = '<span>◀</span>';
        }
        
        // Trigger a resize event to update the map
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 300);
    });
    
    // Toggle between info and chat modes
    infoToggle.addEventListener('click', () => {
        infoToggle.classList.add('active');
        chatToggle.classList.remove('active');
        infoContent.classList.add('active');
        chatContent.classList.remove('active');
    });
    
    chatToggle.addEventListener('click', () => {
        chatToggle.classList.add('active');
        infoToggle.classList.remove('active');
        chatContent.classList.add('active');
        infoContent.classList.remove('active');
    });
    
    // Initialize result tabs
    initResultTabs();
}

/**
 * Initialize result tabs
 */
function initResultTabs() {
    const tabs = document.querySelectorAll('.tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab
            tab.classList.add('active');
            
            // Show corresponding content
            const tabId = tab.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

/**
 * Switch to info tab
 */
function switchToInfoTab() {
    document.getElementById('info-toggle').click();
}

/**
 * Switch to chat tab
 */
function switchToChatTab() {
    document.getElementById('chat-toggle').click();
}

/**
 * Show loading indicator
 */
function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

/**
 * Show results
 */
function showResults() {
    document.getElementById('results').style.display = 'block';
}

/**
 * Update route info
 * @param {string} distance - Distance text
 * @param {string} duration - Duration text
 */
function updateRouteInfo(distance, duration) {
    document.getElementById('distance').textContent = `Distance: ${distance}`;
    document.getElementById('duration').textContent = `Duration: ${duration}`;
}

/**
 * Update sampled points info
 * @param {number|null} count - Number of sampled points or null to clear
 */
function updateSampledInfo(count) {
    const sampledInfo = document.getElementById('sampled-info');
    if (count) {
        sampledInfo.textContent = `Route sampled to ${count} points`;
    } else {
        sampledInfo.textContent = '';
    }
}

/**
 * Update places list
 * @param {Array} places - Places data
 */
function updatePlacesList(places) {
    const placesList = document.getElementById('places-list');
    placesList.innerHTML = '';
    
    if (places.length === 0) {
        placesList.innerHTML = '<p>No places found along this route.</p>';
        return;
    }
    
    // Group places by type
    const placesByType = {
        'city': [],
        'town': [],
        'village': []
    };
    
    places.forEach(place => {
        if (placesByType[place.type]) {
            placesByType[place.type].push(place);
        }
    });
    
    // Add places to list by type
    for (const [type, typeList] of Object.entries(placesByType)) {
        if (typeList.length > 0) {
            const typeHeading = document.createElement('h4');
            typeHeading.textContent = `${type.charAt(0).toUpperCase() + type.slice(1)}s (${typeList.length})`;
            placesList.appendChild(typeHeading);
            
            typeList.forEach(place => {
                const placeItem = document.createElement('div');
                placeItem.className = 'feature-item';
                placeItem.textContent = place.name;
                placeItem.addEventListener('click', () => {
                    const map = window.MapModule.getMap();
                    map.setView([place.lat, place.lon], 12);
                    
                    // Find and open the popup for this place
                    window.MapModule.getPlacesLayer().eachLayer(layer => {
                        const latlng = layer.getLatLng();
                        if (latlng.lat === place.lat && latlng.lng === place.lon) {
                            layer.openPopup();
                        }
                    });
                });
                placesList.appendChild(placeItem);
            });
        }
    }
}

/**
 * Update features list
 * @param {Array} features - Features data
 */
function updateFeaturesList(features) {
    const featuresList = document.getElementById('features-list');
    featuresList.innerHTML = '';
    
    if (features.length === 0) {
        featuresList.innerHTML = '<p>No natural features found along this route.</p>';
        return;
    }
    
    // Group features by type
    const featuresByType = {};
    
    features.forEach(feature => {
        if (!featuresByType[feature.type]) {
            featuresByType[feature.type] = [];
        }
        featuresByType[feature.type].push(feature);
    });
    
    // Add features to list by type
    for (const [type, typeList] of Object.entries(featuresByType)) {
        if (typeList.length > 0) {
            const typeHeading = document.createElement('h4');
            typeHeading.textContent = `${type.charAt(0).toUpperCase() + type.slice(1)}s (${typeList.length})`;
            featuresList.appendChild(typeHeading);
            
            typeList.forEach(feature => {
                if (feature.name !== 'unnamed') {
                    const featureItem = document.createElement('div');
                    featureItem.className = 'feature-item';
                    featureItem.textContent = feature.name;
                    featureItem.addEventListener('click', () => {
                        const map = window.MapModule.getMap();
                        map.setView([feature.lat, feature.lon], 13);
                        
                        // Find and open the popup for this feature
                        window.MapModule.getFeaturesLayer().eachLayer(layer => {
                            const latlng = layer.getLatLng();
                            if (latlng.lat === feature.lat && latlng.lng === feature.lon) {
                                layer.openPopup();
                            }
                        });
                    });
                    featuresList.appendChild(featureItem);
                }
            });
        }
    }
}

// Export functions
window.SidebarModule = {
    initSidebar,
    switchToInfoTab,
    switchToChatTab,
    showLoading,
    hideLoading,
    showResults,
    updateRouteInfo,
    updateSampledInfo,
    updatePlacesList,
    updateFeaturesList
};
