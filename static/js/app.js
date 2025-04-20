/**
 * Main Application Module
 * Initializes all modules and handles application startup
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM fully loaded, initializing application...');
    // Initialize all modules
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('🔄 Starting application initialization');
    console.time('appInitialization');
    
    // Initialize global variables
    window.requiresRouteUpdate = false;
    console.log('🔄 Initialized global variables');
    
    try {
        // Initialize map
        console.log('🗺️ Initializing Map Module...');
        if (window.MapModule) {
            window.MapModule.initMap();
            console.log('✅ Map Module initialized successfully');
        } else {
            console.error('❌ Map module not loaded');
        }
        
        // Initialize form
        console.log('📝 Initializing Form Module...');
        if (window.FormModule) {
            window.FormModule.initForm();
            console.log('✅ Form Module initialized successfully');
        } else {
            console.error('❌ Form module not loaded');
        }
        
        // Initialize chat
        console.log('💬 Initializing Chat Module...');
        if (window.ChatModule) {
            window.ChatModule.initChat();
            console.log('✅ Chat Module initialized successfully');
        } else {
            console.error('❌ Chat module not loaded');
        }
        
        // Initialize sidebar
        console.log('📊 Initializing Sidebar Module...');
        if (window.SidebarModule) {
            window.SidebarModule.initSidebar();
            console.log('✅ Sidebar Module initialized successfully');
        } else {
            console.error('❌ Sidebar module not loaded');
        }
        
        console.timeEnd('appInitialization');
        console.log('🎉 Application initialized successfully');
        
        // Log available modules
        console.log('📚 Available modules:', {
            MapModule: !!window.MapModule,
            ApiModule: !!window.ApiModule,
            FormModule: !!window.FormModule,
            ChatModule: !!window.ChatModule,
            SidebarModule: !!window.SidebarModule
        });
    } catch (error) {
        console.error('❌ Error initializing application:', error);
        console.trace('Application initialization stack trace');
    }
}

// Export functions
window.AppModule = {
    initializeApp
};
