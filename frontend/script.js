// Replace with actual WhatsApp Number (include country code, no '+')
const WHATSAPP_NUMBER = "919997754141"; 

let activeProfile = null;
let chatHistory = [];
let activeDocumentId = null;
let documentChatHistory = [];

function selectPath(path) {
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById(`${path}-screen`).classList.add('active');
    
    if (path === 'docchat') {
        loadDocumentList();
    }
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

// ==========================================
// Document Chat Client Logic
// ==========================================
async function submitDocumentUpload(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('docchat-file');
    const uploadBtn = document.getElementById('docchat-upload-btn');
    if (!fileInput.files.length) return;
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    uploadBtn.innerText = "Ingesting PDF...";
    uploadBtn.disabled = true;
    
    try {
        const response = await fetch('/upload_document', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        uploadBtn.innerText = "Upload and Start Chatting ➔";
        uploadBtn.disabled = false;
        
        if (response.ok) {
            activeDocumentId = data.document_id;
            
            // Transition to chat screen
            document.querySelectorAll('.screen').forEach(el => {
                el.classList.remove('active');
            });
            document.getElementById('docchat-chat-screen').classList.add('active');
            
            // Set header title
            document.getElementById('docchat-file-name').innerText = `Document: ${data.filename}`;
            
            // Reset chat
            documentChatHistory = [];
            const messagesDiv = document.getElementById('docchat-messages');
            messagesDiv.innerHTML = '';
            
            appendDocumentChatMessage('ai', `Document uploaded successfully! 📄 I have analyzed your PDF "${data.filename}". Ask me any questions about its content!`);
        } else {
            alert(`Upload Failed: ${data.detail || 'Error processing PDF'}`);
        }
    } catch (error) {
        uploadBtn.innerText = "Upload and Start Chatting ➔";
        uploadBtn.disabled = false;
        alert(`Error connecting to server: ${error.message}`);
    }
}

function exitDocumentChat() {
    activeDocumentId = null;
    documentChatHistory = [];
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById('docchat-screen').classList.add('active');
    loadDocumentList();
}

function appendDocumentChatMessage(sender, text) {
    const messagesDiv = document.getElementById('docchat-messages');
    const msgElement = document.createElement('div');
    msgElement.className = `message ${sender}`;
    msgElement.innerText = text;
    messagesDiv.appendChild(msgElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    documentChatHistory.push({
        role: sender === 'user' ? 'user' : 'model',
        content: text
    });
}

async function sendDocumentChatMessage(e) {
    e.preventDefault();
    
    const inputElement = document.getElementById('docchat-input');
    const queryText = inputElement.value.trim();
    if (!queryText || !activeDocumentId) return;
    
    appendDocumentChatMessage('user', queryText);
    inputElement.value = '';
    
    const typingIndicator = document.getElementById('docchat-typing-indicator');
    typingIndicator.style.display = 'flex';
    
    const messagesDiv = document.getElementById('docchat-messages');
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    try {
        const response = await fetch('/document_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_ids: [activeDocumentId],
                query: queryText,
                history: documentChatHistory.slice(0, -1)
            })
        });
        
        const data = await response.json();
        
        typingIndicator.style.display = 'none';
        
        if (response.ok) {
            appendDocumentChatMessage('ai', data.response);
        } else {
            appendDocumentChatMessage('ai', `⚠️ Error: ${data.detail || 'Could not fetch response.'}`);
        }
    } catch (error) {
        typingIndicator.style.display = 'none';
        appendDocumentChatMessage('ai', `⚠️ Error: Connection failed.`);
    }
}

// ==========================================
// Document List History Helpers
// ==========================================
async function loadDocumentList() {
    const listContainer = document.getElementById('doc-list-container');
    if (!listContainer) return;
    
    try {
        const response = await fetch('/list_documents');
        const docs = await response.json();
        
        listContainer.innerHTML = '';
        if (docs.length === 0) {
            listContainer.innerHTML = '<p class="empty-list-msg" style="color: #7f8c8d; font-size: 0.95rem; font-style: italic;">No documents uploaded yet.</p>';
            return;
        }
        
        docs.forEach(doc => {
            const item = document.createElement('div');
            item.className = 'doc-item';
            item.innerHTML = `
                <div class="doc-details">
                    <span class="doc-name">${doc.filename}</span>
                    <span class="doc-date">Uploaded: ${doc.uploaded_at}</span>
                </div>
                <button class="doc-chat-btn" onclick="startChatWithDoc('${doc.id}', '${doc.filename}')">Chat ➔</button>
            `;
            listContainer.appendChild(item);
        });
    } catch (error) {
        listContainer.innerHTML = '<p class="empty-list-msg" style="color: #c0392b; font-size: 0.95rem;">Failed to load previous uploads.</p>';
    }
}

function startChatWithDoc(docId, filename) {
    activeDocumentId = docId;
    
    // Transition to chat screen
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById('docchat-chat-screen').classList.add('active');
    
    // Set header title
    document.getElementById('docchat-file-name').innerText = `Document: ${filename}`;
    
    // Reset chat
    documentChatHistory = [];
    const messagesDiv = document.getElementById('docchat-messages');
    messagesDiv.innerHTML = '';
    
    appendDocumentChatMessage('ai', `Opened session for "${filename}". Ask me any questions about its content!`);
}
