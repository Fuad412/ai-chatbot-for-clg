(function () {
    'use strict';

    var STORAGE_KEY = 'majlis_chat_sessions_v1';

    var chatWindow = document.getElementById('chatWindow');
    var userInput = document.getElementById('userInput');
    var sendBtn = document.getElementById('sendBtn');
    var clearChatBtn = document.getElementById('clearChatBtn');
    var newChatBtn = document.getElementById('newChatBtn');
    var historyList = document.getElementById('historyList');
    var historyEmpty = document.getElementById('historyEmpty');
    var sidebar = document.getElementById('sidebar');
    var sidebarBackdrop = document.getElementById('sidebarBackdrop');
    var menuToggle = document.getElementById('menuToggle');

    var state = {
        sessions: Object.create(null),
        order: [],
        currentId: null
    };

    function uuid() {
        return 's' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
    }

    function loadFromStorage() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return;
            var parsed = JSON.parse(raw);
            if (parsed.sessions) state.sessions = parsed.sessions;
            if (parsed.order && Array.isArray(parsed.order)) state.order = parsed.order;
            if (parsed.currentId && state.sessions[parsed.currentId]) state.currentId = parsed.currentId;
        } catch (e) {}
    }

    function saveToStorage() {
        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({
                    sessions: state.sessions,
                    order: state.order,
                    currentId: state.currentId
                })
            );
        } catch (e) {}
    }

    function stripHtml(html) {
        var tmp = document.createElement('div');
        tmp.innerHTML = html;
        var t = tmp.textContent || tmp.innerText || '';
        return t.replace(/\s+/g, ' ').trim();
    }

    function touchSession(id) {
        var s = state.sessions[id];
        if (!s) return;
        s.updated = Date.now();
        state.order = [id].concat(state.order.filter(function (x) {
            return x !== id;
        }));
    }

    function ensureSession() {
        if (state.currentId && state.sessions[state.currentId]) return;
        var id = uuid();
        state.sessions[id] = {
            id: id,
            title: 'New chat',
            messages: [],
            updated: Date.now()
        };
        state.order = [id].concat(state.order);
        state.currentId = id;
    }

    function welcomeHtml() {
        return (
            '<div class="message bot-message">' +
            '<div class="bubble">Hello! I\'m the Majlis AI Assistant. Ask me about Syllabus, Fees, or Facilities!</div>' +
            '</div>' +
            '<div class="options-container" id="initialOptions">' +
            '<button type="button" class="option-btn" data-send="Syllabus">Syllabus</button>' +
            '<button type="button" class="option-btn" data-send="Fee Payment">Fee Payment</button>' +
            '<button type="button" class="option-btn" data-send="Admissions">Admissions</button>' +
            '<button type="button" class="option-btn" data-send="Hostel">Hostel</button>' +
            '</div>'
        );
    }

    function bindInitialOptions() {
        var root = chatWindow.querySelector('#initialOptions');
        if (!root) return;
        root.querySelectorAll('.option-btn[data-send]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var text = btn.getAttribute('data-send') || '';
                if (!text) return;
                addMessage(text, 'user');
                sendToApi(text);
            });
        });
    }

    function renderWelcome() {
        chatWindow.innerHTML = welcomeHtml();
        bindInitialOptions();
        scrollToBottom();
    }

    function appendBubble(role, html, persist) {
        var div = document.createElement('div');
        div.className = 'message ' + (role === 'user' ? 'user-message' : 'bot-message');
        div.innerHTML = '<div class="bubble">' + html + '</div>';
        chatWindow.appendChild(div);

        if (persist) {
            ensureSession();
            var s = state.sessions[state.currentId];
            s.messages.push({ role: role, html: html });
            if (s.title === 'New chat' && role === 'user') {
                var t = stripHtml(html);
                s.title = t.length > 48 ? t.slice(0, 45) + '…' : t || 'Chat';
            }
            touchSession(state.currentId);
            saveToStorage();
            renderHistoryList();
        }
        scrollToBottom();
    }

    function renderSession() {
        ensureSession();
        var s = state.sessions[state.currentId];
        chatWindow.innerHTML = '';
        if (!s.messages.length) {
            renderWelcome();
            return;
        }
        s.messages.forEach(function (m) {
            appendBubble(m.role, m.html, false);
        });
        scrollToBottom();
    }

    function removePreviousOptions() {
        var nodes = chatWindow.querySelectorAll('.options-container');
        nodes.forEach(function (n) {
            n.remove();
        });
    }

    function addMessage(html, sender) {
        removePreviousOptions();
        var role = sender === 'user' ? 'user' : 'bot';
        appendBubble(role, html, true);
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function renderHistoryList() {
        if (!historyList || !historyEmpty) return;
        historyList.innerHTML = '';
        var ids = state.order.filter(function (id) {
            return state.sessions[id];
        });
        if (!ids.length) {
            historyEmpty.classList.remove('is-hidden');
            return;
        }
        historyEmpty.classList.add('is-hidden');

        ids.forEach(function (id) {
            var s = state.sessions[id];
            var li = document.createElement('li');
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = s.title || 'Chat';
            if (id === state.currentId) btn.classList.add('is-active');
            btn.addEventListener('click', function () {
                if (state.currentId === id) {
                    closeSidebar();
                    return;
                }
                state.currentId = id;
                saveToStorage();
                renderSession();
                renderHistoryList();
                closeSidebar();
            });
            li.appendChild(btn);
            historyList.appendChild(li);
        });
    }

    function createNewChat() {
        var id = uuid();
        state.sessions[id] = {
            id: id,
            title: 'New chat',
            messages: [],
            updated: Date.now()
        };
        state.order = [id].concat(state.order.filter(function (x) {
            return x !== id;
        }));
        state.currentId = id;
        saveToStorage();
        renderWelcome();
        renderHistoryList();
        userInput.focus();
    }

    function clearCurrentChat() {
        ensureSession();
        var s = state.sessions[state.currentId];
        s.messages = [];
        s.title = 'New chat';
        s.updated = Date.now();
        touchSession(state.currentId);
        saveToStorage();
        renderWelcome();
        renderHistoryList();
        userInput.focus();
    }

    function handleSend() {
        var text = userInput.value.trim();
        if (!text) return;
        userInput.value = '';
        addMessage(text, 'user');
        sendToApi(text);
    }

    function sendToApi(text) {
        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        })
            .then(function (res) {
                return res.json();
            })
            .then(function (data) {
                addMessage(data.text, 'bot');
                if (data.options && data.options.length) {
                    addOptions(data.options);
                }
            })
            .catch(function () {
                addMessage("Sorry, I'm having trouble connecting to the server.", 'bot');
            });
    }

    function addOptions(options) {
        var div = document.createElement('div');
        div.className = 'options-container';

        options.forEach(function (opt) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'option-btn';

            if (typeof opt === 'string') {
                btn.textContent = opt;
                btn.addEventListener('click', function () {
                    addMessage(opt, 'user');
                    sendToApi(opt);
                });
            } else {
                btn.textContent = opt.label;
                if (opt.action === 'link') {
                    btn.addEventListener('click', function () {
                        window.open(opt.url, '_blank');
                    });
                } else if (opt.action === 'post') {
                    btn.addEventListener('click', function () {
                        addMessage(opt.label, 'user');
                        sendToApi(opt.value);
                    });
                }
            }
            div.appendChild(btn);
        });

        chatWindow.appendChild(div);
        scrollToBottom();
    }

    function openSidebar() {
        sidebar.classList.add('is-open');
        sidebarBackdrop.classList.add('is-visible');
        sidebarBackdrop.setAttribute('aria-hidden', 'false');
    }

    function closeSidebar() {
        sidebar.classList.remove('is-open');
        sidebarBackdrop.classList.remove('is-visible');
        sidebarBackdrop.setAttribute('aria-hidden', 'true');
    }

    function init() {
        loadFromStorage();
        ensureSession();
        touchSession(state.currentId);
        saveToStorage();

        var cur = state.sessions[state.currentId];
        if (cur && cur.messages.length) {
            renderSession();
        } else {
            renderWelcome();
        }
        renderHistoryList();

        userInput.focus();

        sendBtn.addEventListener('click', handleSend);
        userInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') handleSend();
        });

        clearChatBtn.addEventListener('click', clearCurrentChat);
        newChatBtn.addEventListener('click', function () {
            createNewChat();
            closeSidebar();
        });

        menuToggle.addEventListener('click', openSidebar);
        sidebarBackdrop.addEventListener('click', closeSidebar);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
