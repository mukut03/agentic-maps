/**
 * Main Application Module
 * Initializes all modules and handles application startup
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize all modules
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    try {
        // Initialize map
        if (window.MapModule) {
            window.MapModule.initMap();
        } else {
            console.error('Map module not loaded');
        }
        
        // Initialize form
        if (window.FormModule) {
            window.FormModule.initForm();
        } else {
            console.error('Form module not loaded');
        }
        
        // Initialize chat
        if (window.ChatModule) {
            window.ChatModule.initChat();
        } else {
            console.error('Chat module not loaded');
        }
        
        // Initialize sidebar
        if (window.SidebarModule) {
            window.SidebarModule.initSidebar();
        } else {
            console.error('Sidebar module not loaded');
        }
        
        console.log('Application initialized successfully');
    } catch (error) {
        console.error('Error initializing application:', error);
    }
}

// Export functions
window.AppModule = {
    initializeApp
};
