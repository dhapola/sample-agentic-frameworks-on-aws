export class ChatAPI {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
    }

    async createConversation() {
        const response = await fetch(`${this.apiUrl}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        return await response.json();
    }

    async getConversation(conversationId) {
        const response = await fetch(`${this.apiUrl}/conversations/${conversationId}`);
        return await response.json();
    }

    async *streamChat(message, conversationId = null) {
        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, conversation_id: conversationId })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        yield line.slice(6);
                    } else if (line.startsWith('event: done')) {
                        const dataLine = lines[lines.indexOf(line) + 1];
                        if (dataLine && dataLine.startsWith('data: ')) {
                            return dataLine.slice(6);
                        }
                    } else if (line.startsWith('event: error')) {
                        const dataLine = lines[lines.indexOf(line) + 1];
                        const errorMsg = dataLine && dataLine.startsWith('data: ') ? dataLine.slice(6) : 'Unknown error';
                        throw new Error(errorMsg);
                    }
                }
            }
        } catch (error) {
            console.error('Stream chat error:', error);
            throw error;
        }
    }
}
