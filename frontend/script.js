// Replace with actual WhatsApp Number (include country code, no '+')
const WHATSAPP_NUMBER = "919997754141"; 

let activeProfile = null;
let chatHistory = [];

function selectPath(path) {
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById(`${path}-screen`).classList.add('active');
}

function goBack() {
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById('selection-screen').classList.add('active');
}

function submitAstrology(e) {
    e.preventDefault();
    
    // Store user profile details
    activeProfile = {
        name: document.getElementById('astro-name').value,
        mobile: document.getElementById('astro-mobile').value,
        email: document.getElementById('astro-email').value,
        dob: document.getElementById('astro-dob').value,
        time: document.getElementById('astro-time').value,
        place: document.getElementById('astro-place').value
    };

    // Transition to chat screen
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById('astrology-chat-screen').classList.add('active');
    
    // Set up profile title
    document.getElementById('chat-user-name').innerText = `Vedic Profile: ${activeProfile.name} (${activeProfile.place})`;

    // Initialize conversation
    chatHistory = [];
    const chatMessagesDiv = document.getElementById('chat-messages');
    chatMessagesDiv.innerHTML = '';

    const welcomeText = `Namaste ${activeProfile.name}! 🌟 I have cast your birth chart based on your details: DOB ${activeProfile.dob} at ${activeProfile.time} in ${activeProfile.place}. How may I guide you on your destiny today?`;
    appendChatMessage('ai', welcomeText);
}

function exitChat() {
    activeProfile = null;
    chatHistory = [];
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById('astrology-screen').classList.add('active');
}

function appendChatMessage(sender, text) {
    const chatMessagesDiv = document.getElementById('chat-messages');
    const msgElement = document.createElement('div');
    msgElement.className = `message ${sender}`;
    msgElement.innerText = text;
    chatMessagesDiv.appendChild(msgElement);
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
    
    // Keep track of history (formatted for Gemini)
    chatHistory.push({
        role: sender === 'user' ? 'user' : 'model',
        content: text
    });
}

async function sendChatMessage(e) {
    e.preventDefault();
    
    const inputElement = document.getElementById('chat-input');
    const userQuery = inputElement.value.trim();
    if (!userQuery) return;
    
    // Add user message to screen & history
    appendChatMessage('user', userQuery);
    inputElement.value = '';
    
    // Show typing indicator
    const typingIndicator = document.getElementById('typing-indicator');
    typingIndicator.style.display = 'flex';
    
    const chatMessagesDiv = document.getElementById('chat-messages');
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
    
    try {
        const response = await fetch('/astrology_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: activeProfile.name,
                dob: activeProfile.dob,
                time: activeProfile.time,
                place: activeProfile.place,
                query: userQuery,
                history: chatHistory.slice(0, -1) // pass history before adding current query
            })
        });
        
        const data = await response.json();
        
        // Hide typing indicator
        typingIndicator.style.display = 'none';
        
        if (response.ok) {
            appendChatMessage('ai', data.response);
        } else {
            appendChatMessage('ai', `⚠️ Celestial Connection Error: ${data.detail || 'Could not fetch reading.'}`);
        }
    } catch (error) {
        typingIndicator.style.display = 'none';
        appendChatMessage('ai', `⚠️ Error: Could not connect to the cosmic servers. Please try again.`);
    }
}

function submitPalmistry(e) {
    e.preventDefault();
    
    const name = document.getElementById('palm-name').value;
    const mobile = document.getElementById('palm-mobile').value;
    const email = document.getElementById('palm-email').value;
    const hand = document.getElementById('palm-hand').value;

    const message = `*New Palmistry Inquiry* ✋\n\n` +
                    `*Name:* ${name}\n` +
                    `*Mobile:* ${mobile}\n` +
                    `*Email:* ${email}\n` +
                    `*Handedness:* ${hand}\n\n` +
                    `I will be sending 4-5 images of my palms shortly. Please review them.`;

    redirectToWhatsApp(message);
}

function redirectToWhatsApp(text) {
    const encodedText = encodeURIComponent(text);
    const whatsappUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodedText}`;
    window.open(whatsappUrl, '_blank');
}
