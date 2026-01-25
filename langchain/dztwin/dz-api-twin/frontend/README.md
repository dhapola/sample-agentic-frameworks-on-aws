# Chat Widget Frontend

Vanilla JavaScript embeddable chat widget with iframe isolation and streaming support.

## Features

- **Script tag injection** - One-line integration
- **Lazy loading** - Widget loads only when FAB is clicked
- **Iframe isolation** - Zero CSS/JS conflicts with host page
- **Floating Action Button (FAB)** - Customizable position and styling
- **Streaming responses** - Real-time token-by-token display
- **Session persistence** - Conversations persist across page reloads
- **Resizable & fullscreen** - Flexible UI modes
- **Markdown support** - Rich text formatting with marked.js
- **Source attribution** - Automatic citation with clickable documentation links
- **Event-driven** - postMessage API for extensibility
- **Customizable themes** - 10+ presets with CSS variables
- **Responsive design** - Mobile and desktop optimized

## Quick Setup

```bash
npm install
npm run dev
```

Server starts on http://localhost:8000

## Integration

### Basic Integration

Add to any website:

```html
<script>
  window.ChatPluginConfig = {
    apiUrl: 'http://localhost:3000/api'
  };
</script>
<script src="http://localhost:8000/chat-plugin.js"></script>
```

### Full Configuration

```html
<script>
  window.ChatPluginConfig = {
    // Required
    apiUrl: 'http://localhost:3000/api',
    
    // Optional
    position: 'bottom-right',              // bottom-right, bottom-left, top-right, top-left
    theme: 'default',                      // Theme name (see themes below)
    title: 'API Twin',                 // Header title
    subtitle: 'We\'re here to help',       // Header subtitle
    placeholder: 'Type your message...',   // Input placeholder
    autoOpen: false,                       // Auto-open on page load
    
    // Advanced
    fabSize: 60,                           // FAB button size in pixels
    widgetWidth: 380,                      // Widget width in pixels
    widgetHeight: 600,                     // Widget height in pixels
    maxHeight: 'calc(100vh - 120px)',     // Max height CSS value
    borderRadius: 12,                      // Border radius in pixels
    zIndex: 999998                         // Z-index for positioning
  };
</script>
<script src="http://localhost:8000/chat-plugin.js"></script>
```

## Configuration Options

### Required

- `apiUrl` (string) - Backend API URL

### Optional

- `position` (string) - FAB position
  - `'bottom-right'` (default)
  - `'bottom-left'`
  - `'top-right'`
  - `'top-left'`

- `theme` (string) - Theme name (default: `'default'`)
  - See [Themes](#themes) section

- `title` (string) - Chat header title (default: `'Chat Support'`)

- `subtitle` (string) - Chat header subtitle (default: `'We're here to help'`)

- `placeholder` (string) - Input placeholder (default: `'Type your message...'`)

- `autoOpen` (boolean) - Auto-open chat on page load (default: `false`)

## Themes

### Available Themes

1. **default** - Blue theme
2. **dark** - Dark mode
3. **light** - Light mode
4. **purple** - Purple accent
5. **green** - Green accent
6. **red** - Red accent
7. **orange** - Orange accent
8. **pink** - Pink accent
9. **teal** - Teal accent
10. **indigo** - Indigo accent

### Custom Theme

Create `customer_config.css` with CSS variables:

```css
:root {
  --chat-primary-color: #007bff;
  --chat-secondary-color: #6c757d;
  --chat-background-color: #ffffff;
  --chat-text-color: #333333;
  --chat-border-color: #e0e0e0;
  --chat-user-message-bg: #007bff;
  --chat-user-message-text: #ffffff;
  --chat-bot-message-bg: #f1f3f5;
  --chat-bot-message-text: #333333;
  --chat-input-bg: #ffffff;
  --chat-input-border: #e0e0e0;
  --chat-header-bg: #007bff;
  --chat-header-text: #ffffff;
  --chat-fab-bg: #007bff;
  --chat-fab-text: #ffffff;
  --chat-fab-shadow: rgba(0, 0, 0, 0.15);
}
```

Load custom theme:
```html
<link rel="stylesheet" href="customer_config.css">
<script>
  window.ChatPluginConfig = {
    apiUrl: 'http://localhost:3000/api',
    theme: 'custom'
  };
</script>
<script src="chat-plugin.js"></script>
```

## File Structure

```
frontend/
├── chat-plugin.js          # Entry point, FAB, iframe management
├── widget.html             # Chat UI (loaded in iframe)
├── widget.css              # Widget styles
├── widget.js               # Widget logic, event handling
├── customer_config.css     # Theme customization
├── resize-handles.css      # Resize functionality
├── api/
│   └── chat-api.js         # API client with SSE support
├── example.html            # Demo page
├── package.json            # NPM config
└── README.md               # This file
```

### Component Breakdown

#### `chat-plugin.js`
Entry point that creates:
- Floating Action Button (FAB)
- Iframe container
- Parent-child communication via postMessage
- Lazy loading logic

**Key Features:**
- Creates FAB with hover effects
- Manages iframe lifecycle
- Handles fullscreen toggle
- Implements lazy loading

#### `widget.html`
Chat UI loaded inside iframe:
- Header with title and controls
- Message container with scrolling
- Input area with send button
- Loading states

#### `widget.js`
Widget logic and event handling:
- Message rendering (user/bot)
- Streaming response handling
- Session persistence (localStorage)
- Markdown rendering
- Event listeners

**Key Features:**
- Real-time streaming display
- Auto-scroll to latest message
- Session restoration
- Error handling

#### `widget.css`
Widget styles:
- Responsive layout
- Message bubbles
- Animations
- Theme variables

#### `api/chat-api.js`
API client with SSE support:
- Conversation management
- Message sending
- Streaming response handling
- Error handling

**Key Features:**
- Server-Sent Events (SSE)
- Automatic conversation creation
- Retry logic
- Error handling

## API Client Usage

The `ChatAPI` class handles all backend communication:

```javascript
import { ChatAPI } from './api/chat-api.js';

const api = new ChatAPI('http://localhost:3000/api');

// Create conversation
const conversation = await api.createConversation();

// Send message with streaming
await api.sendMessage(
  'Hello!',
  conversation.conversation_id,
  (chunk) => {
    // Handle each chunk
    console.log(chunk);
  },
  (conversationId) => {
    // Handle completion
    console.log('Done:', conversationId);
  },
  (error) => {
    // Handle error
    console.error(error);
  }
);

// Get conversation history
const messages = await api.getConversation(conversation.conversation_id);
```

## Development

### Start Dev Server

```bash
npm run dev
```

Serves files on http://localhost:8000 with live reload.

### Build for Production

```bash
npm run build
```

Creates minified files:
- `chat-plugin.min.js`
- `widget.min.js`

### Testing

Open http://localhost:8000/example.html in browser.

Test features:
- Send messages
- Streaming responses
- Session persistence (reload page)
- Fullscreen mode
- Resize widget
- Theme switching

## Production Deployment

### 1. Build Minified Files

```bash
npm run build
```

### 2. Update Integration

Use minified version:
```html
<script src="https://your-cdn.com/chat-plugin.min.js"></script>
```

### 3. Configure API URL

Point to production backend:
```javascript
window.ChatPluginConfig = {
  apiUrl: 'https://api.yourdomain.com/api'
};
```

### 4. CDN Deployment

Upload to CDN:
- `chat-plugin.min.js`
- `widget.min.js`
- `widget.html`
- `widget.css`
- `customer_config.css` (if using custom theme)

### 5. Cache Headers

Set appropriate cache headers:
```
Cache-Control: public, max-age=31536000, immutable
```

## Advanced Features

### Event System

Listen to widget events:

```javascript
window.addEventListener('message', (event) => {
  if (event.data.type === 'CHAT_MESSAGE_SENT') {
    console.log('User sent:', event.data.message);
  }
  
  if (event.data.type === 'CHAT_MESSAGE_RECEIVED') {
    console.log('Bot replied:', event.data.message);
  }
  
  if (event.data.type === 'CHAT_OPENED') {
    console.log('Chat opened');
  }
  
  if (event.data.type === 'CHAT_CLOSED') {
    console.log('Chat closed');
  }
});
```

### Programmatic Control

Control widget from parent page:

```javascript
// Open chat
window.postMessage({ type: 'CHAT_OPEN' }, '*');

// Close chat
window.postMessage({ type: 'CHAT_CLOSE' }, '*');

// Toggle fullscreen
window.postMessage({ type: 'CHAT_TOGGLE_FULLSCREEN' }, '*');

// Send message programmatically
window.postMessage({ 
  type: 'CHAT_SEND_MESSAGE', 
  message: 'Hello from parent!' 
}, '*');
```

### Custom Styling

Override styles with higher specificity:

```css
#chat-widget-container iframe {
  border: 2px solid #007bff !important;
}

#chat-fab {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}
```

## Session Persistence

Conversations are stored in `localStorage`:

```javascript
// Key format
localStorage.getItem('chat_conversation_id');
localStorage.getItem('chat_messages');

// Clear session
localStorage.removeItem('chat_conversation_id');
localStorage.removeItem('chat_messages');
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Required Features:**
- ES6 modules
- Fetch API
- Server-Sent Events (SSE)
- localStorage
- postMessage API

## Troubleshooting

### Widget not loading
- Check console for errors
- Verify `apiUrl` is correct
- Check CORS settings on backend

### Streaming not working
- Verify backend supports SSE
- Check network tab for event-stream
- Ensure browser supports SSE

### Session not persisting
- Check localStorage is enabled
- Verify domain matches
- Check browser privacy settings

### Styling conflicts
- Iframe should prevent conflicts
- Check z-index values
- Verify CSS isolation

## Dependencies

- `marked` (v12.0.0) - Markdown rendering
- `terser` (dev) - JavaScript minification

## Performance

- **Lazy loading** - Widget loads only when clicked (~50KB initial)
- **Iframe isolation** - No impact on host page performance
- **Streaming** - Progressive rendering of responses
- **Minification** - Production builds are optimized

## Security

- **Iframe sandbox** - Isolated execution context
- **CORS** - Backend validates origins
- **XSS protection** - Markdown sanitization
- **No eval()** - No dynamic code execution

## License

MIT
