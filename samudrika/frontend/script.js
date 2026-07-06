document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const scanBtn = document.getElementById('scanBtn');
    const scanBtnText = document.getElementById('scanBtnText');
    const spinner = document.getElementById('spinner');
    const imageInput = document.getElementById('imageInput');
    
    const registerView = document.getElementById('registerView');
    const regName = document.getElementById('regName');
    const regEmail = document.getElementById('regEmail');
    const regPhone = document.getElementById('regPhone');
    const submitRegBtn = document.getElementById('submitRegBtn');

    const mainView = document.getElementById('mainView');
    const resultsView = document.getElementById('resultsView');
    const readingContent = document.getElementById('readingContent');
    const resetBtn = document.getElementById('resetBtn');
    const logoTitle = document.getElementById('logoTitle');

    // Chat and Payment Elements
    const chatOptionBtn = document.getElementById('chatOptionBtn');
    const chatView = document.getElementById('chatView');
    const chatWindow = document.getElementById('chatWindow');
    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendChatBtn');

    const sessionStatusBar = document.getElementById('sessionStatusBar');
    const statusBarTimer = document.getElementById('statusBarTimer');
    const statusBarLabel = document.getElementById('statusBarLabel');

    const paymentModal = document.getElementById('paymentModal');
    const pack51Btn = document.getElementById('pack51Btn');
    const pack21Btn = document.getElementById('pack21Btn');
    const confirmPayBtn = document.getElementById('confirmPayBtn');
    const cancelPayBtn = document.getElementById('cancelPayBtn');

    // App State
    let timerInterval = null;
    let timeRemaining = 0; // seconds
    let selectedPack = 51; // 51 or 21
    let chatHistory = [];
    let isFreeTrialUsed = false;
    let sessionId = localStorage.getItem('samudrika_session_id') || null;

    // Check session on load
    if (sessionId) {
        registerView.classList.add('hidden');
        registerView.classList.remove('flex');
        mainView.classList.remove('hidden');
        mainView.classList.add('flex');
    } else {
        registerView.classList.remove('hidden');
        registerView.classList.add('flex');
        mainView.classList.add('hidden');
        mainView.classList.remove('flex');
    }

    // Handle Profile Registration Submit
    submitRegBtn.addEventListener('click', async () => {
        const name = regName.value.trim();
        const email = regEmail.value.trim();
        const phone = regPhone.value.trim();

        if (!name || !email || !phone) {
            alert('Please fill in all details to proceed.');
            return;
        }

        // Basic Email regex validation
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            alert('Please enter a valid email address.');
            return;
        }

        submitRegBtn.disabled = true;
        submitRegBtn.innerText = 'Creating Profile...';

        try {
            const response = await fetch('/start_session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, phone })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to start session.');
            }

            const data = await response.json();
            sessionId = data.session_id;
            localStorage.setItem('samudrika_session_id', sessionId);

            // Shift Views
            registerView.classList.add('hidden');
            registerView.classList.remove('flex');
            mainView.classList.remove('hidden');
            mainView.classList.add('flex');

        } catch (error) {
            alert('Cosmic registration failed: ' + error.message);
        } finally {
            submitRegBtn.disabled = false;
            submitRegBtn.innerText = 'Start Cosmic Journey';
        }
    });

    // Trigger file picker when Scan button is clicked
    scanBtn.addEventListener('click', () => {
        imageInput.click();
    });

    // Handle file selection and API call for Palm Scan
    imageInput.addEventListener('change', async (e) => {
        if (!e.target.files.length) return;
        
        const file = e.target.files[0];
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file.');
            return;
        }

        // Show loading state
        scanBtnText.style.opacity = '0';
        spinner.style.display = 'block';
        scanBtn.disabled = true;

        const formData = new FormData();
        formData.append('image_file', file);
        if (sessionId) {
            formData.append('session_id', sessionId);
        }

        try {
            const response = await fetch('/process_palm', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to process image');
            }

            const data = await response.json();
            
            // Switch views
            mainView.classList.add('hidden');
            mainView.classList.remove('flex');
            
            resultsView.classList.remove('hidden');
            resultsView.classList.add('flex');
            
            // Format and display reading
            readingContent.innerHTML = data.reading.replace(/\n/g, '<br><br>');
            
        } catch (error) {
            alert('Cosmic Connection Failed: ' + error.message);
        } finally {
            // Restore button state
            scanBtnText.style.opacity = '1';
            spinner.style.display = 'none';
            scanBtn.disabled = false;
            // Clear input so same file can be selected again if needed
            imageInput.value = '';
        }
    });

    // Reset back to main view
    const resetApp = () => {
        clearInterval(timerInterval);
        sessionStatusBar.classList.add('hidden');
        chatView.classList.add('hidden');
        chatView.classList.remove('flex');
        resultsView.classList.add('hidden');
        resultsView.classList.remove('flex');
        
        mainView.classList.remove('hidden');
        mainView.classList.add('flex');
        
        readingContent.innerHTML = '';
        chatWindow.innerHTML = `
            <div class="chat-msg system bg-yellow-600/10 border border-yellow-600/20 rounded-xl p-3 text-xs text-yellow-500 text-center">
                🔮 Sage Samudra is listening. Ask him about your lines, career, love, or health.
            </div>
        `;
        chatHistory = [];
        timeRemaining = 0;
    };

    resetBtn.addEventListener('click', resetApp);
    logoTitle.addEventListener('click', resetApp);

    // ==========================================
    // Chat & Payment Logic
    // ==========================================

    // Start 1 minute free trial
    chatOptionBtn.addEventListener('click', () => {
        resultsView.classList.add('hidden');
        resultsView.classList.remove('flex');
        chatView.classList.remove('hidden');
        chatView.classList.add('flex');
        
        sessionStatusBar.classList.remove('hidden');
        
        // Start 1 minute (60s) free trial
        appendSystemMessage("🎁 Free trial activated! You have 1 minute to ask Sage Samudra anything.");
        startCountdown(60);
    });

    // Package Selector in Payment Modal
    pack51Btn.addEventListener('click', () => selectPack(51));
    pack21Btn.addEventListener('click', () => selectPack(21));

    const selectPack = (pack) => {
        selectedPack = pack;
        if (pack === 51) {
            pack51Btn.classList.add('bg-yellow-500/20', 'border-yellow-500');
            pack51Btn.classList.remove('bg-transparent', 'border-yellow-600/30');
            pack21Btn.classList.remove('bg-yellow-500/20', 'border-yellow-500');
            pack21Btn.classList.add('bg-transparent', 'border-yellow-600/30');
            confirmPayBtn.innerText = 'Simulate Success (₹51)';
        } else {
            pack21Btn.classList.add('bg-yellow-500/20', 'border-yellow-500');
            pack21Btn.classList.remove('bg-transparent', 'border-yellow-600/30');
            pack51Btn.classList.remove('bg-yellow-500/20', 'border-yellow-500');
            pack51Btn.classList.add('bg-transparent', 'border-yellow-600/30');
            confirmPayBtn.innerText = 'Simulate Success (₹21)';
        }
    };

    // Close Modal
    cancelPayBtn.addEventListener('click', () => {
        paymentModal.classList.add('hidden');
    });

    // Confirm Mock Payment
    confirmPayBtn.addEventListener('click', () => {
        paymentModal.classList.add('hidden');
        chatInput.disabled = false;
        chatInput.placeholder = "Ask Sage Samudra...";
        sendChatBtn.disabled = false;
        
        const secondsToAdd = selectedPack === 51 ? 300 : 120;
        const minutes = selectedPack === 51 ? 5 : 2;
        
        appendSystemMessage(`💸 Payment of ₹${selectedPack} Successful! Added ${minutes} minutes to your session.`);
        startCountdown(timeRemaining + secondsToAdd);
    });

    // Countdown Timer logic
    const startCountdown = (seconds) => {
        clearInterval(timerInterval);
        timeRemaining = seconds;
        updateTimerDisplay();

        timerInterval = setInterval(() => {
            timeRemaining--;
            updateTimerDisplay();

            if (timeRemaining <= 0) {
                clearInterval(timerInterval);
                lockChatSession();
            }
        }, 1000);
    };

    const updateTimerDisplay = () => {
        const mins = Math.floor(timeRemaining / 60);
        const secs = timeRemaining % 60;
        const timeString = `⏳ ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        statusBarTimer.innerText = timeString;

        if (timeRemaining < 60) {
            statusBarTimer.classList.add('timer-low');
        } else {
            statusBarTimer.classList.remove('timer-low');
        }
    };

    const lockChatSession = () => {
        chatInput.disabled = true;
        chatInput.placeholder = "Session expired. Refill time to ask...";
        sendChatBtn.disabled = true;
        
        appendSystemMessage("⚠️ Your chat session has expired. Please select a package below to continue chatting.");
        
        // Show payment modal
        paymentModal.classList.remove('hidden');
    };

    // Helper to append message to Chat Window
    const appendUserMessage = (text) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-msg user';
        msgDiv.innerText = text;
        chatWindow.appendChild(msgDiv);
        scrollToBottom();
    };

    const appendAstroMessage = (text) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-msg astro';
        msgDiv.innerText = text;
        chatWindow.appendChild(msgDiv);
        scrollToBottom();
    };

    function appendSystemMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-msg system bg-yellow-600/10 border border-yellow-600/20 rounded-xl p-3 text-xs text-yellow-500 text-center w-full';
        msgDiv.innerText = text;
        chatWindow.appendChild(msgDiv);
        scrollToBottom();
    }

    const scrollToBottom = () => {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    };

    // Chat API Interaction
    const handleSendChat = async () => {
        const query = chatInput.value.trim();
        if (!query) return;

        appendUserMessage(query);
        chatInput.value = '';

        // Show typing indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'chat-msg astro italic text-gray-500';
        typingIndicator.innerText = 'Sage is reading the cosmos...';
        chatWindow.appendChild(typingIndicator);
        scrollToBottom();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: query
                })
            });

            // Remove typing indicator
            chatWindow.removeChild(typingIndicator);

            if (!response.ok) {
                throw new Error('Cosmic line is busy.');
            }

            const data = await response.json();
            appendAstroMessage(data.response);

            // Record to history
            chatHistory.push({ role: 'user', text: query });
            chatHistory.push({ role: 'model', text: data.response });

        } catch (error) {
            chatWindow.removeChild(typingIndicator);
            appendSystemMessage('❌ Failed to connect: ' + error.message);
        }
    };

    sendChatBtn.addEventListener('click', handleSendChat);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleSendChat();
    });
});

