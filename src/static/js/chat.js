document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-query-input');
    const sendButton = document.getElementById('send-query-button');
    const loadingIndicator = document.getElementById('loading-indicator');

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function displayMessage(text, sender) {
        const messageContainer = document.createElement('div');
        messageContainer.classList.add('message', `${sender}-message`);

        const messageParagraph = document.createElement('p');
        
        // Basic Markdown-like formatting (strong, em, br)
        // More advanced Markdown would require a library
        let formattedText = text
            .replace(/&/g, "&amp;") // Escape HTML special characters first
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\*(.*?)\*/g, '<em>$1</em>')         // Italics
            .replace(/\n/g, '<br>');                       // Newlines
        
        messageParagraph.innerHTML = formattedText;
        messageContainer.appendChild(messageParagraph);
        
        chatWindow.appendChild(messageContainer);
        scrollToBottom();
    }

    function setLoading(isLoading) {
        if (isLoading) {
            loadingIndicator.style.display = 'block';
            userInput.disabled = true;
            sendButton.disabled = true;
        } else {
            loadingIndicator.style.display = 'none';
            userInput.disabled = false;
            sendButton.disabled = false;
            userInput.focus();
        }
    }

    async function sendMessage() {
        const query = userInput.value.trim();
        if (!query) return;

        displayMessage(query, 'user');
        userInput.value = ''; // Clear input field immediately
        setLoading(true);

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                // Ensure the backend expects 'query' as the key
                body: JSON.stringify({ query: query }), 
            });

            const data = await response.json(); // Try to parse JSON regardless of response.ok for error messages

            if (!response.ok) {
                let errorMessage = data.error || `Server error: ${response.status}`;
                 if (response.status === 401 && data.re_auth_required === true) {
                    errorMessage = `Authentication Error: ${data.error || 'Your session may have expired.'} <a href="/login">Please log in again.</a>`;
                    // Consider also automatically redirecting or providing a more prominent login button.
                } else if (response.status === 401) { // General 401 without specific re_auth_required flag
                     errorMessage = data.error || "Error: You are not authorized. Your session may have expired. Please try logging in again.";
                }
                displayMessage(errorMessage, 'bot error'); // Use a distinct class for bot errors
                console.error('Server error:', data);
            } else {
                // Backend expects 'ai_response' based on current web_app.py
                displayMessage(data.ai_response || "Sorry, I didn't get a valid response.", 'bot');
            }

        } catch (error) { // Catches network errors or if response.json() fails
            console.error('Chat request failed:', error);
            displayMessage('Sorry, I encountered a network problem or the server is not responding. Please try again.', 'bot error');
        } finally {
            setLoading(false);
        }
    }

    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault(); 
            sendMessage();
        }
    });

    userInput.focus(); // Focus on input field on page load
    scrollToBottom(); // Ensure initial message is visible if window is small
});
