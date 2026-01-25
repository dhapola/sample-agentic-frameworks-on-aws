(function() {
    'use strict';

    const defaultConfig = {
        apiUrl: 'http://localhost:3000/api',
        position: 'bottom-right',
        theme: 'default',
        title: 'API Twin',
        subtitle: 'We\'re here to help',
        placeholder: 'Type your message...',
        autoOpen: false,
        allowedOrigins: ['http://localhost:8000', 'http://127.0.0.1:8000'] // Configure allowed origins
    };

    const config = { ...defaultConfig, ...(window.ChatPluginConfig || {}) };
    
    // Validate origin for postMessage
    function isAllowedOrigin(origin) {
        // In development, allow localhost
        if (origin.startsWith('http://localhost:') || origin.startsWith('http://127.0.0.1:')) {
            return true;
        }
        // Check against configured allowed origins
        return config.allowedOrigins.includes(origin);
    }

    // Create FAB
    const fab = document.createElement('button');
    fab.id = 'chat-fab';
    fab.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
    `;
    fab.style.cssText = `
        position: fixed;
        ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
        ${config.position.includes('top') ? 'top: 20px;' : 'bottom: 20px;'}
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: #007bff;
        color: white;
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s, box-shadow 0.2s;
    `;

    fab.addEventListener('mouseenter', () => {
        fab.style.transform = 'scale(1.1)';
        fab.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)';
    });

    fab.addEventListener('mouseleave', () => {
        fab.style.transform = 'scale(1)';
        fab.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    });

    // Create iframe container
    const container = document.createElement('div');
    container.id = 'chat-widget-container';
    container.style.cssText = `
        position: fixed;
        ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
        ${config.position.includes('top') ? 'top: 20px;' : 'bottom: 90px;'}
        width: 380px;
        height: 600px;
        max-height: calc(100vh - 120px);
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        z-index: 999998;
        display: none;
        overflow: hidden;
    `;

    const iframe = document.createElement('iframe');
    iframe.id = 'chat-widget-iframe';
    iframe.style.cssText = `
        width: 100%;
        height: 100%;
        border: none;
        border-radius: 12px;
    `;

    container.appendChild(iframe);
    document.body.appendChild(fab);
    document.body.appendChild(container);
    
    // Initialize fullscreen state
    container.dataset.fullscreen = 'false';

    let isOpen = false;
    let isLoaded = false;

    fab.addEventListener('click', () => {
        if (!isLoaded) {
            // Add cache-busting parameter
            const timestamp = Date.now();
            iframe.src = `${window.location.origin}/widget.html?v=${timestamp}&config=${encodeURIComponent(JSON.stringify(config))}`;
            isLoaded = true;
        }

        isOpen = !isOpen;
        container.style.display = isOpen ? 'block' : 'none';
        fab.innerHTML = isOpen ? 
            '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>' :
            '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
    });

    // Message passing with origin validation
    window.addEventListener('message', (event) => {
        console.log('[Chat Plugin] Received message:', event.data, 'from origin:', event.origin);
        
        // Validate origin
        if (!isAllowedOrigin(event.origin)) {
            console.warn('[Chat Widget] Blocked message from untrusted origin:', event.origin);
            return;
        }
        
        // Validate message structure
        if (!event.data || typeof event.data !== 'object') {
            console.warn('[Chat Widget] Invalid message format');
            return;
        }
        
        // Handle specific message types
        if (event.data.type === 'CHAT_CLOSE') {
            console.log('[Chat Plugin] Closing chat');
            fab.click();
        } else if (event.data.type === 'CHAT_TOGGLE_FULLSCREEN') {
            console.log('[Chat Plugin] Toggling fullscreen');
            toggleFullscreen();
        }
    });

    function toggleFullscreen() {
        const isFullscreen = container.dataset.fullscreen === 'true';
        console.log('[Chat Plugin] toggleFullscreen called, current state:', isFullscreen);
        
        if (isFullscreen) {
            // Return to normal size
            console.log('[Chat Plugin] Switching to normal size');
            container.style.cssText = `
                position: fixed;
                ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'}
                ${config.position.includes('top') ? 'top: 20px;' : 'bottom: 90px;'}
                width: 380px;
                height: 600px;
                max-height: calc(100vh - 120px);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.2);
                z-index: 999998;
                display: block;
                overflow: hidden;
                transition: all 0.3s ease;
            `;
            container.dataset.fullscreen = 'false';
            fab.style.display = 'flex';
        } else {
            // Expand to fullscreen
            console.log('[Chat Plugin] Switching to fullscreen');
            container.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                width: 100vw;
                height: 100vh;
                max-height: 100vh;
                border-radius: 0;
                box-shadow: none;
                z-index: 999998;
                display: block;
                overflow: hidden;
                transition: all 0.3s ease;
            `;
            container.dataset.fullscreen = 'true';
            fab.style.display = 'none';
        }
        
        console.log('[Chat Plugin] New fullscreen state:', container.dataset.fullscreen);
    }

    if (config.autoOpen) {
        setTimeout(() => fab.click(), 1000);
    }
})();
