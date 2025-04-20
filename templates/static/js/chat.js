/**
 * Chat Module - Handles chat functionality
 */

/**
 * Initialize chat functionality
 */
function initChat() {
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const chatResetBtn = document.getElementById('chat-reset-btn');
    
    // Send message on button click
    chatSendBtn.addEventListener('click', () => {
        sendMessage();
    });
    
    // Send message on Enter key (but allow Shift+Enter for new lines)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Reset conversation
    chatResetBtn.addEventListener('click', async () => {
        try {
            const success = await window.ApiModule.resetChatConversation();
            
            if (success) {
                // Clear chat messages except for the initial greeting
                chatMessages.innerHTML = `
                    <div class="chat-message assistant">
                        Hello! I'm MapChat, your route planning assistant. How can I help you today? You can ask me to find routes, show places along a route, or tell you about natural features you'll encounter on your journey.
                    </div>
                `;
                
                // Clear any displayed route
                window.MapModule.clearMapLayers();
            } else {
                console.error('Failed to reset conversation');
            }
        } catch (error) {
            console.error('Error resetting conversation:', error);
        }
    });
    
    // Load chat history
    loadChatHistory();
}

/**
 * Send a message
 */
async function sendMessage() {
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    const userMessageElement = document.createElement('div');
    userMessageElement.className = 'chat-message user';
    userMessageElement.textContent = message;
    chatMessages.appendChild(userMessageElement);
    
    // Clear input
    chatInput.value = '';
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        // Send message to backend
        const data = await window.ApiModule.sendChatMessage(message);
        
        // Add assistant message to chat
        const assistantMessageElement = document.createElement('div');
        assistantMessageElement.className = 'chat-message assistant';
        assistantMessageElement.textContent = data.message;
        chatMessages.appendChild(assistantMessageElement);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // If UI update is required, switch to info mode and update the UI
        if (data.requires_ui_update) {
            // Switch to info mode
            window.SidebarModule.switchToInfoTab();
        }
    } catch (error) {
        console.error('Error sending message:', error);
        
        // Add error message to chat
        const errorMessageElement = document.createElement('div');
        errorMessageElement.className = 'chat-message assistant';
        errorMessageElement.textContent = 'Sorry, there was an error processing your request. Please try again.';
        chatMessages.appendChild(errorMessageElement);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

/**
 * Load chat history
 */
async function loadChatHistory() {
    const chatMessages = document.getElementById('chat-messages');
    
    try {
        const history = await window.ApiModule.loadChatHistory();
        
        // Clear chat messages
        chatMessages.innerHTML = '';
        
        // Add messages to chat
        history.forEach(message => {
            const messageElement = document.createElement('div');
            messageElement.className = `chat-message ${message.role}`;
            messageElement.textContent = message.content;
            chatMessages.appendChild(messageElement);
        });
        
        // If no messages, add initial greeting
        if (history.length === 0) {
            const greetingElement = document.createElement('div');
            greetingElement.className = 'chat-message assistant';
            greetingElement.textContent = "Hello! I'm MapChat, your route planning assistant. How can I help you today? You can ask me to find routes, show places along a route, or tell you about natural features you'll encounter on your journey.";
            chatMessages.appendChild(greetingElement);
        }
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (error) {
        console.error('Error loading chat history:', error);
        
        // Add initial greeting if loading fails
        chatMessages.innerHTML = `
            <div class="chat-message assistant">
                Hello! I'm MapChat, your route planning assistant. How can I help you today? You can ask me to find routes, show places along a route, or tell you about natural features you'll encounter on your journey.
            </div>
        `;
    }
}

// Export functions
window.ChatModule = {
    initChat,
    sendMessage,
    loadChatHistory
};
