import { ChatAPI } from './api/chat-api.js';

class ChatWidget {
    constructor() {
        this.config = this.parseConfig();
        this.api = new ChatAPI(this.config.apiUrl);
        this.conversationId = this.loadConversationId();
        this.isStreaming = false;
        this.marked = null;
        this.DOMPurify = null;
        
        // Load marked.js and DOMPurify dynamically
        this.loadDependencies();
        
        this.initElements();
        this.initEventListeners();
        this.applyConfig();
        this.loadHistory();
    }
    
    async loadDependencies() {
        try {
            // Load DOMPurify for XSS protection
            const purifyModule = await import('https://cdn.jsdelivr.net/npm/dompurify@3.0.8/dist/purify.es.mjs');
            this.DOMPurify = purifyModule.default;
            console.log('✅ DOMPurify loaded successfully');
        } catch (error) {
            console.error('❌ Failed to load DOMPurify:', error);
        }
        
        try {
            // Load marked.js for markdown parsing
            const markedModule = await import('https://cdn.jsdelivr.net/npm/marked@11.1.1/lib/marked.esm.js');
            this.marked = markedModule.marked;
            this.marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false
            });
            console.log('✅ Marked.js loaded successfully');
        } catch (error) {
            console.warn('⚠️ Failed to load marked.js, using fallback markdown parser:', error);
        }
    }

    parseConfig() {
        const params = new URLSearchParams(window.location.search);
        const configStr = params.get('config');
        const defaultConfig = {
            apiUrl: 'http://localhost:3000/api',
            title: 'API Twin',
            subtitle: 'We\'re here to help',
            placeholder: 'Type your message...'
        };
        
        try {
            const parsedConfig = configStr ? JSON.parse(decodeURIComponent(configStr)) : {};
            return { ...defaultConfig, ...parsedConfig };
        } catch (error) {
            console.error('Failed to parse config:', error);
            return defaultConfig;
        }
    }

    initElements() {
        this.messagesContainer = document.getElementById('chat-messages');
        this.input = document.getElementById('chat-input');
        this.sendBtn = document.getElementById('send-btn');
        this.expandBtn = document.getElementById('expand-btn');
        this.closeBtn = document.getElementById('close-btn');
        this.title = document.getElementById('chat-title');
        this.subtitle = document.getElementById('chat-subtitle');
        
        // Initialize expand button state
        this.expandBtn.dataset.fullscreen = 'false';
    }

    initEventListeners() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.expandBtn.addEventListener('click', () => this.toggleFullscreen());
        this.closeBtn.addEventListener('click', () => {
            window.parent.postMessage({ type: 'CHAT_CLOSE' }, '*');
        });
        this.input.addEventListener('input', () => this.autoResize());
    }

    applyConfig() {
        if (this.config.title) this.title.textContent = this.config.title;
        if (this.config.subtitle) this.subtitle.textContent = this.config.subtitle;
        if (this.config.placeholder) this.input.placeholder = this.config.placeholder;
    }

    autoResize() {
        this.input.style.height = 'auto';
        this.input.style.height = Math.min(this.input.scrollHeight, 120) + 'px';
    }

    toggleFullscreen() {
        console.log('[Widget] Sending CHAT_TOGGLE_FULLSCREEN message');
        console.log('[Widget] Current fullscreen state:', this.expandBtn.dataset.fullscreen);
        
        // Send message to parent with proper origin
        window.parent.postMessage({ type: 'CHAT_TOGGLE_FULLSCREEN' }, '*');
        
        // Update button icon - toggle the state
        const isCurrentlyFullscreen = this.expandBtn.dataset.fullscreen === 'true';
        
        if (isCurrentlyFullscreen) {
            // Currently fullscreen, switching to normal - show expand icon
            this.expandBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <polyline points="9 21 3 21 3 15"></polyline>
                    <line x1="21" y1="3" x2="14" y2="10"></line>
                    <line x1="3" y1="21" x2="10" y2="14"></line>
                </svg>
            `;
            this.expandBtn.setAttribute('aria-label', 'Expand chat');
            this.expandBtn.setAttribute('title', 'Expand');
            this.expandBtn.dataset.fullscreen = 'false';
        } else {
            // Currently normal, switching to fullscreen - show minimize icon
            this.expandBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="4 14 10 14 10 20"></polyline>
                    <polyline points="20 10 14 10 14 4"></polyline>
                    <line x1="14" y1="10" x2="21" y2="3"></line>
                    <line x1="3" y1="21" x2="10" y2="14"></line>
                </svg>
            `;
            this.expandBtn.setAttribute('aria-label', 'Minimize chat');
            this.expandBtn.setAttribute('title', 'Minimize');
            this.expandBtn.dataset.fullscreen = 'true';
        }
        
        console.log('[Widget] New fullscreen state:', this.expandBtn.dataset.fullscreen);
    }

    loadConversationId() {
        return sessionStorage.getItem('chat_conversation_id');
    }

    saveConversationId(id) {
        this.conversationId = id;
        sessionStorage.setItem('chat_conversation_id', id);
    }

    async loadHistory() {
        if (!this.conversationId) return;

        try {
            const messages = await this.api.getConversation(this.conversationId);
            messages.forEach(msg => {
                this.addMessage(msg.content, msg.role);
            });
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }

    addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (role === 'assistant') {
            contentDiv.innerHTML = this.formatMarkdown(content);
        } else {
            contentDiv.textContent = content;
        }
        
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        return contentDiv;
    }

    formatMarkdown(text) {
        // Use marked.js if available
        if (this.marked) {
            try {
                const rawHtml = this.marked.parse(text);
                // Sanitize with DOMPurify if available
                if (this.DOMPurify) {
                    return this.DOMPurify.sanitize(rawHtml, {
                        ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr'],
                        ALLOWED_ATTR: ['href', 'target', 'rel'],
                        ALLOW_DATA_ATTR: false,
                        ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i
                    });
                }
                return rawHtml;
            } catch (error) {
                console.error('❌ Markdown parsing error:', error);
            }
        }
        
        // Fallback: Simple but safe markdown parser
        return this.fallbackMarkdown(text);
    }
    
    fallbackMarkdown(text) {
        // Escape HTML to prevent XSS
        const escapeHtml = (str) => {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        };
        
        let html = escapeHtml(text);
        
        // Process code blocks (preserve escaped HTML inside)
        const codeBlocks = [];
        html = html.replace(/```[\w]*\n([\s\S]*?)```/g, (match, code) => {
            const placeholder = `___CODE_BLOCK_${codeBlocks.length}___`;
            codeBlocks.push('<pre><code>' + code.trim() + '</code></pre>');
            return placeholder;
        });
        
        // Process inline code
        const inlineCodes = [];
        html = html.replace(/`([^`]+)`/g, (match, code) => {
            const placeholder = `___INLINE_CODE_${inlineCodes.length}___`;
            inlineCodes.push('<code>' + code + '</code>');
            return placeholder;
        });
        
        // Headers
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        
        // Bold
        html = html.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
        
        // Italic
        html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
        
        // Links - sanitize URLs
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
            // Only allow http, https, mailto
            if (/^(https?:|mailto:)/i.test(url)) {
                return `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`;
            }
            return text; // Strip invalid links
        });
        
        // Lists
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        html = html.replace(/(<li>[\s\S]+?<\/li>)/g, '<ul>$1</ul>');
        
        // Paragraphs
        html = html.split('\n\n').map(para => {
            para = para.trim();
            if (!para) return '';
            if (para.match(/^<(h[1-6]|pre|ul|ol|blockquote|div)/)) {
                return para;
            }
            para = para.replace(/\n/g, '<br>');
            return '<p>' + para + '</p>';
        }).join('\n');
        
        // Restore code blocks
        codeBlocks.forEach((code, i) => {
            html = html.replace(`___CODE_BLOCK_${i}___`, code);
        });
        
        // Restore inline codes
        inlineCodes.forEach((code, i) => {
            html = html.replace(`___INLINE_CODE_${i}___`, code);
        });
        
        return html;
    }

    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message assistant';
        indicator.id = 'typing-indicator';
        
        const content = document.createElement('div');
        content.className = 'message-content typing-indicator';
        content.innerHTML = '<span></span><span></span><span></span>';
        
        indicator.appendChild(content);
        this.messagesContainer.appendChild(indicator);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    }

    async sendMessage() {
        const message = this.input.value.trim();
        if (!message || this.isStreaming) return;

        this.addMessage(message, 'user');
        this.input.value = '';
        this.autoResize();
        
        this.isStreaming = true;
        this.sendBtn.disabled = true;
        this.showTypingIndicator();

        try {
            let fullResponse = '';
            const responseDiv = document.createElement('div');
            responseDiv.className = 'message assistant';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            responseDiv.appendChild(contentDiv);

            this.removeTypingIndicator();
            this.messagesContainer.appendChild(responseDiv);

            const stream = this.api.streamChat(message, this.conversationId);
            
            for await (const chunk of stream) {
                if (typeof chunk === 'string' && chunk.length > 0) {
                    if (chunk.match(/^[a-f0-9-]{36}$/)) {
                        // This is the conversation ID
                        this.saveConversationId(chunk);
                    } else {
                        fullResponse += chunk;
                        // Show raw text during streaming to avoid partial markdown parsing
                        contentDiv.textContent = fullResponse;
                        this.scrollToBottom();
                    }
                }
            }
            
            // Debug: Log the raw response before parsing
            console.log('=== RAW RESPONSE ===');
            console.log('Length:', fullResponse.length);
            console.log('First 500 chars:', fullResponse.substring(0, 500));
            console.log('Has newlines:', fullResponse.includes('\n'));
            console.log('Newline count:', (fullResponse.match(/\n/g) || []).length);
            console.log('Raw text (escaped):', JSON.stringify(fullResponse.substring(0, 200)));
            
            // Parse markdown only when streaming is complete
            contentDiv.innerHTML = this.formatMarkdown(fullResponse);
            this.scrollToBottom();
        } catch (error) {
            console.error('Chat error:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                conversationId: this.conversationId,
                apiUrl: this.api.apiUrl
            });
            this.removeTypingIndicator();
            this.addMessage(`Error: ${error.message}. Please check the console for details.`, 'assistant');
        } finally {
            this.isStreaming = false;
            this.sendBtn.disabled = false;
            this.input.focus();
        }
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// Initialize widget
new ChatWidget();
