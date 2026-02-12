// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');

// AI responses for demonstration
const aiResponses = [
    "That's an interesting question! Let me think about that...",
    "I understand what you're asking. Based on my knowledge, I would say...",
    "Great point! Here's what I think about that topic...",
    "Thanks for sharing that with me. Here's my perspective...",
    "I appreciate your question. Let me provide some insights...",
    "That's a thoughtful inquiry. From my analysis...",
    "Interesting! I'd be happy to help you with that...",
    "I see what you mean. Let me explain this in more detail...",
    "Good question! Here's what you should know...",
    "Thank you for asking. I can definitely help with that..."
];

// Add a message to the chat
function addMessage(text, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}`;
    avatar.textContent = isUser ? 'You' : 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const textP = document.createElement('p');
    textP.textContent = text;
    
    contentDiv.appendChild(textP);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Add typing indicator
function addTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar bot-avatar';
    avatar.textContent = 'AI';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    
    contentDiv.appendChild(typingDiv);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Remove typing indicator
function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Get AI response (simulated)
function getAIResponse(userMessage) {
    // Simple keyword-based responses
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
        return "Hello! It's great to chat with you. How can I assist you today?";
    } else if (lowerMessage.includes('how are you')) {
        return "I'm doing well, thank you for asking! I'm here and ready to help. How are you doing?";
    } else if (lowerMessage.includes('your name') || lowerMessage.includes('who are you')) {
        return "I'm an AI assistant created to help answer your questions and have conversations. You can call me AI!";
    } else if (lowerMessage.includes('help')) {
        return "I'm here to help! You can ask me questions, have a conversation, or just chat. What would you like to know?";
    } else if (lowerMessage.includes('thank')) {
        return "You're welcome! I'm always happy to help. Is there anything else you'd like to know?";
    } else if (lowerMessage.includes('bye') || lowerMessage.includes('goodbye')) {
        return "Goodbye! It was nice chatting with you. Feel free to come back anytime!";
    } else if (lowerMessage.includes('weather')) {
        return "I don't have access to real-time weather data, but I'd recommend checking a weather service for the most accurate information!";
    } else if (lowerMessage.includes('time')) {
        return `The current time is ${new Date().toLocaleTimeString()}. Is there anything else I can help you with?`;
    } else {
        // Random response for other messages
        return aiResponses[Math.floor(Math.random() * aiResponses.length)];
    }
}

// Handle sending a message
async function sendMessage() {
    const text = messageInput.value.trim();
    
    if (!text) return;
    
    // Add user message
    addMessage(text, true);
    
    // Clear input
    messageInput.value = '';
    
    // Disable input while processing
    messageInput.disabled = true;
    sendButton.disabled = true;
    
    // Show typing indicator
    addTypingIndicator();
    
    // Simulate AI processing time (1-2 seconds)
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000));
    
    // Remove typing indicator
    removeTypingIndicator();
    
    // Add AI response
    const response = getAIResponse(text);
    addMessage(response, false);
    
    // Re-enable input
    messageInput.disabled = false;
    sendButton.disabled = false;
    messageInput.focus();
}

// Event listeners
sendButton.addEventListener('click', sendMessage);

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Focus input on load
messageInput.focus();
