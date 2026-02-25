document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    const welcomeMessage = document.getElementById('welcome-message');
    const pdfUpload = document.getElementById('pdf-upload');
    const uploadStatus = document.getElementById('upload-status');
    const uploadPercent = document.getElementById('upload-percent');
    const uploadBar = document.getElementById('upload-bar');
    const uploadFilename = document.getElementById('upload-filename');
    const modelSelect = document.getElementById('model-select');
    const toggleSidebar = document.getElementById('toggle-sidebar');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const filesList = document.getElementById('files-list');

    // Mobile Sidebar Toggle
    const toggleMenu = () => {
        sidebar.classList.toggle('-translate-x-full');
        sidebarOverlay.classList.toggle('hidden');
    };

    toggleSidebar.addEventListener('click', toggleMenu);
    sidebarOverlay.addEventListener('click', toggleMenu);

    // Toast Function
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `p-4 rounded-xl shadow-2xl transition-all duration-300 transform translate-y-10 opacity-0 ${type === 'success' ? 'bg-emerald-500/90' : 'bg-rose-500/90'
            } text-white flex items-center gap-3 glass`;

        toast.innerHTML = `
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span class="text-sm font-medium">${message}</span>
        `;

        const container = document.getElementById('toast-container');
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.remove('translate-y-10', 'opacity-0');
        }, 10);

        setTimeout(() => {
            toast.classList.add('translate-y-10', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // PDF Upload Logic
    pdfUpload.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        uploadStatus.classList.remove('hidden');
        uploadFilename.textContent = file.name;
        uploadPercent.textContent = '0%';
        uploadBar.style.width = '0%';

        const formData = new FormData();
        formData.append('file', file);

        try {
            // Simulated progress for UI feel
            let progress = 0;
            const interval = setInterval(() => {
                if (progress < 90) {
                    progress += Math.random() * 10;
                    uploadPercent.textContent = `${Math.floor(progress)}%`;
                    uploadBar.style.width = `${progress}%`;
                }
            }, 300);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            clearInterval(interval);

            if (response.ok) {
                uploadPercent.textContent = '100%';
                uploadBar.style.width = '100%';
                showToast('Handbook uploaded and indexed!');

                // Add to list
                const li = document.createElement('li');
                li.className = 'flex items-center gap-2 p-2 rounded-lg bg-white/5 text-xs text-slate-300';
                li.innerHTML = `<i class="fas fa-file-pdf text-indigo-400"></i> <span class="truncate">${file.name}</span>`;
                filesList.appendChild(li);

                setTimeout(() => {
                    uploadStatus.classList.add('hidden');
                }, 2000);
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error(error);
            showToast('Failed to process PDF', 'error');
            uploadStatus.classList.add('hidden');
        }
    });

    // Chat Logic
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        const model = modelSelect.value;

        if (!message) return;

        // Hide welcome message
        if (welcomeMessage) welcomeMessage.style.display = 'none';

        // Add user message
        addMessage(message, 'user');
        userInput.value = '';

        // Add bot message placeholder
        const botMessageId = 'bot-' + Date.now();
        const botMessageDiv = addMessage('', 'bot', botMessageId);
        const textElement = botMessageDiv.querySelector('.message-text');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, model })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                // Keep the last partial line in the buffer
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            if (data.text) {
                                fullText += data.text;
                                if (data.done) {
                                    textElement.innerHTML = formatMessage(fullText);
                                } else {
                                    textElement.textContent = fullText;
                                }
                                chatWindow.scrollTop = chatWindow.scrollHeight;
                            }
                        } catch (e) {
                            console.error('Error parsing stream chunk:', e);
                        }
                    }
                }
            }
        } catch (error) {
            console.error(error);
            showToast('Chat error occurred', 'error');
            textElement.textContent = 'Sorry, I encountered an error.';
        }
    });

    function addMessage(text, role, id = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-4 message-animate`;
        if (id) messageDiv.id = id;

        const innerHTML = `
            <div class="max-w-[85%] lg:max-w-[70%] rounded-2xl p-4 ${role === 'user' ? 'chat-bubble-user text-white' : 'chat-bubble-bot text-slate-800'
            }">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] ${role === 'user' ? 'bg-white/20' : 'bg-[#592a8a]/20'
            }">
                        <i class="fas ${role === 'user' ? 'fa-user' : 'fa-graduation-cap'} ${role === 'user' ? 'text-white' : 'text-[#592a8a]'}"></i>
                    </div>
                    <span class="text-[10px] font-bold uppercase tracking-widest ${role === 'user' ? 'text-white/70' : 'text-slate-500'}">
                        ${role === 'user' ? 'You' : 'ECU Assistant'}
                    </span>
                </div>
                <div class="message-text text-sm leading-relaxed whitespace-pre-wrap">${text}</div>
            </div>
        `;

        messageDiv.innerHTML = innerHTML;
        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return messageDiv;
    }

    function formatMessage(text) {
        // Simple citation formatter
        return text.replace(/\(Source: (.*?), Page (.*?)\)/g, '<span class="citation"><i class="fas fa-file-alt mr-1"></i> $1, Page $2</span>');
    }
});
