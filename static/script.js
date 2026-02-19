const chatWindow = document.getElementById('chatWindow');
const userInput = document.getElementById('userInput');

// Auto focus
userInput.focus();

// Enter key to send
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});

function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;

    // Add user message
    addMessage(text, 'user');
    userInput.value = '';

    // Send to backend
    sendMessage(text);
}

function sendMessage(text, isPayload = false) {
    // Show typing indicator (optional simplified version: just wait)
    // If it's a button click (payload), we still want to show what they "said"
    // unless we handled it in options logic. Assuming text is what we send.

    if (!isPayload) {
        // If it came from a button, it might have been added already
    }

    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: text })
    })
        .then(res => res.json())
        .then(data => {
            // Add bot response
            addMessage(data.text, 'bot');

            // Add Options if any
            if (data.options && data.options.length > 0) {
                addOptions(data.options);
            }
        })
        .catch(err => {
            addMessage("Sorry, I'm having trouble connecting to the server.", 'bot');
        });
}

function addMessage(html, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}-message`;
    div.innerHTML = `<div class="bubble">${html}</div>`;

    // Remove previous options to clean up UI (optional, but good for focus)
    const prevOptions = document.querySelector('.options-container:last-child');
    if (prevOptions) prevOptions.remove();

    chatWindow.appendChild(div);
    scrollToBottom();
}

function addOptions(options) {
    const div = document.createElement('div');
    div.className = 'options-container user-message'; // Right aligned partially, or just simplified
    div.style.justifyContent = 'flex-start'; // Actually bot's suggestions usually left or center
    div.className = 'options-container';
    div.style.paddingLeft = '20px'; // Align with bot text

    options.forEach(opt => {
        if (typeof opt === 'string') {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.textContent = opt;
            btn.onclick = () => {
                addMessage(opt, 'user');
                sendMessage(opt);
            };
            div.appendChild(btn);
        } else {
            // Object with action
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.textContent = opt.label;

            if (opt.action === 'link') {
                btn.onclick = () => window.open(opt.url, '_blank');
            } else if (opt.action === 'post') {
                btn.onclick = () => {
                    // Don't show the ugly payload "dept:CT", show the label "Computer Engineering"
                    addMessage(opt.label, 'user');
                    sendMessage(opt.value, true);
                };
            }
            div.appendChild(btn);
        }
    });

    chatWindow.appendChild(div);
    scrollToBottom();
}

function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
}
