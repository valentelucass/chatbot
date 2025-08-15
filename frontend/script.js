document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const longModeToggle = document.getElementById('long-mode');
    // Seleciona automaticamente o endpoint correto (local vs produção)
    const isLocal = (location.hostname === 'localhost' || location.hostname === '127.0.0.1');
    const apiEndpointStream = isLocal ? 'http://127.0.0.1:8000/api/chat_stream' : '/api/chat_stream';
    const apiEndpointNonStream = isLocal ? 'http://127.0.0.1:8000/api/chat' : '/api/chat';

    // Histórico local da conversa para manter contexto
    const history = [];

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Impede o recarregamento da página

        const userMessage = userInput.value.trim();
        if (!userMessage) return;

        // Adiciona a mensagem do usuário ao chat
        addMessageToChat('user', userMessage);
        history.push({ role: 'user', content: userMessage });
        
        // Limpa o campo de input e desabilita o formulário
        userInput.value = '';
        toggleForm(false);

        // Mostra o spinner de carregamento
        const loadingSpinner = addLoadingSpinner();

        try {
            const response = await fetch(apiEndpointStream, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMessage,
                    history,
                    mode: (longModeToggle && longModeToggle.checked) ? 'long' : 'short',
                }),
            });

            // Se a chamada stream não for suportada, faz fallback automático
            if (!response.ok || !response.body) {
                const nonStreamResp = await fetch(apiEndpointNonStream, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: userMessage,
                        history,
                        mode: (longModeToggle && longModeToggle.checked) ? 'long' : 'short',
                    }),
                });
                if (!nonStreamResp.ok) throw new Error(`Erro na API (fallback): ${nonStreamResp.status} ${nonStreamResp.statusText}`);
                const data = await nonStreamResp.json();
                const finalMessage = data.response || '';
                const botElement = document.createElement('div');
                botElement.classList.add('message', 'bot-message');
                chatBox.replaceChild(botElement, loadingSpinner);
                renderBotHtmlInto(botElement, finalMessage);
                history.push({ role: 'assistant', content: finalMessage });
                return; // encerra cedo pois já respondeu
            }

            // Prepara um elemento vazio para stream
            const botElement = document.createElement('div');
            botElement.classList.add('message', 'bot-message');
            botElement.textContent = '';
            chatBox.replaceChild(botElement, loadingSpinner);

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let done = false;
            let buffer = '';
            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                if (value) {
                    const chunk = decoder.decode(value, { stream: !done });
                    buffer += chunk;
                    // Mostra texto bruto durante o streaming (sem markdown) para melhor UX
                    botElement.textContent = buffer;
                    scrollToBottom();
                }
            }

            // Final do stream: renderiza markdown e aplica colapsável + highlight
            const finalMessage = buffer;
            renderBotHtmlInto(botElement, finalMessage);
            history.push({ role: 'assistant', content: finalMessage });

        } catch (error) {
            console.error('Falha ao se comunicar com o chatbot:', error);
            // Remove o spinner e mostra uma mensagem de erro
            if (loadingSpinner && loadingSpinner.parentElement === chatBox) {
                chatBox.removeChild(loadingSpinner);
            }
            addMessageToChat('bot', 'Desculpe, não consegui me conectar. Tente novamente mais tarde.');
        } finally {
            // Reabilita o formulário
            toggleForm(true);
        }
    });

    /**
     * Adiciona uma mensagem à caixa de chat.
     * @param {('user'|'bot')} sender - Quem enviou a mensagem.
     * @param {string} message - O conteúdo da mensagem.
     */
    function addMessageToChat(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        
        if (sender === 'bot') {
            renderBotHtmlInto(messageElement, message);
        } else {
            const paragraph = document.createElement('p');
            paragraph.textContent = message;
            messageElement.appendChild(paragraph);
        }
        
        chatBox.appendChild(messageElement);
        scrollToBottom();
    }
    
    /**
     * Adiciona um spinner de carregamento visual.
     * @returns {HTMLElement} O elemento do spinner.
     */
    function addLoadingSpinner() {
        const spinnerElement = document.createElement('div');
        spinnerElement.classList.add('message', 'bot-message', 'loading-spinner');
        spinnerElement.innerHTML = `
            <span></span>
            <span></span>
            <span></span>
        `;
        chatBox.appendChild(spinnerElement);
        scrollToBottom();
        return spinnerElement;
    }
    
    /**
     * Habilita ou desabilita o formulário de input.
     * @param {boolean} isEnabled - True para habilitar, false para desabilitar.
     */
    function toggleForm(isEnabled) {
        userInput.disabled = !isEnabled;
        chatForm.querySelector('button').disabled = !isEnabled;
        if (isEnabled) {
            userInput.focus();
        }
    }

    /**
     * Rola a caixa de chat para a mensagem mais recente.
     */
    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    /**
     * Renderiza Markdown básico com segurança: escapa HTML, depois aplica conversões simples.
     * Suporte: **bold**, *itálico*, `código`, blocos ``` ``` , listas, e quebras de linha.
     */
    function renderMarkdownSafe(text) {
        const escaped = escapeHtml(text);
        // Blocos de código com linguagem: ```lang\n...```
        let html = escaped.replace(/```([a-zA-Z0-9#+\-.]*)\n([\s\S]*?)```/g, (_, lang, code) => {
            const cls = lang ? ` class="language-${lang.toLowerCase()}"` : '';
            return `<pre><code${cls}>${code}</code></pre>`;
        });
        // Inline code `code`
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold **text**
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Italic *text*
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        // Listas simples - item
        html = html.replace(/^(?:-\s.+)$/gm, match => `<li>${match.replace(/^-([\s])*/, '')}</li>`);
        html = html.replace(/(<li>.*<\/li>)(\n?)(?!<li>)/g, '<ul>$1</ul>');
        // Quebras de linha
        html = html.replace(/\n/g, '<br>');
        return html;
    }

    function renderBotHtmlInto(element, message) {
        // Não envolver HTML de bot em <p> para evitar truncamento de blocos (ul, pre, etc.)
        const html = renderMarkdownSafe(message || '');
        const isLong = message && message.length > 800;
        if (isLong) {
            element.classList.add('collapsible');
            const content = document.createElement('div');
            content.className = 'collapsible-content collapsed';
            content.innerHTML = html;

            const fade = document.createElement('div');
            fade.className = 'fade-gradient';

            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'expand-btn';
            btn.textContent = 'Mostrar mais';
            btn.addEventListener('click', () => {
                const collapsed = content.classList.toggle('collapsed');
                btn.textContent = collapsed ? 'Mostrar mais' : 'Mostrar menos';
                fade.style.display = collapsed ? '' : 'none';
                scrollToBottom();
            });

            element.innerHTML = '';
            element.appendChild(content);
            element.appendChild(fade);
            element.appendChild(btn);
            if (window.Prism) Prism.highlightAllUnder(element);
        } else {
            element.innerHTML = html;
            if (window.Prism) Prism.highlightAllUnder(element);
        }
        scrollToBottom();
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});