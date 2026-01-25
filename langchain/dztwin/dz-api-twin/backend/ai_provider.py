from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Dict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from config import Settings

# Import providers conditionally to avoid missing dependency errors
try:
    from langchain_aws import ChatBedrock
except ImportError:
    ChatBedrock = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None


class BaseAIProvider(ABC):
    @abstractmethod
    async def stream_response(self, messages: List[Dict], context: Optional[str] = None) -> AsyncGenerator[str, None]:
        pass
    
    def _convert_messages(self, messages: List[Dict], context: Optional[str] = None):
        """Convert messages to LangChain format with optional RAG context"""
        lc_messages = []
        if context:
            system_prompt = """You are a helpful AI assistant with access to documentation. 

IMPORTANT: Use the following documentation context to answer the user's question. The context contains relevant information from official documentation. Always prioritize information from this context over your general knowledge.

If the context contains relevant information:
- Base your answer primarily on the context provided
- Include specific details, code examples, and steps from the context
- ALWAYS include source links at the end of your response in a "Sources" section

If the context doesn't contain relevant information:
- Clearly state that the information isn't in the provided documentation
- You may provide general knowledge but indicate it's not from the official docs

DOCUMENTATION CONTEXT:
{context}

Now, answer the user's question based on this context.

OUTPUT FORMAT:
- Use proper markdown formatting with blank lines between sections
- For headings, always add a blank line after: # Heading\\n\\n
- For lists, put each item on a new line with proper spacing
- For paragraphs, separate them with blank lines
- ALWAYS end with a "## Sources" section listing the documentation URLs
- Example format:
  # Welcome
  
  I'm here to help with:
  
  - Item 1
  - Item 2
  - Item 3
  
  ## Sources
  - [Documentation Title](https://example.com/docs)
  
  Let me know how I can assist!"""
            lc_messages.append(SystemMessage(content=system_prompt.format(context=context)))
        else:
            # Default system message when no RAG context
            system_prompt = """You are a helpful AI assistant.

OUTPUT FORMAT:
- Use proper markdown formatting with blank lines between sections
- For headings, always add a blank line after the heading
- For lists, put each item on a new line
- For paragraphs, separate them with blank lines
- Example:
  # Welcome
  
  I'm here to help with:
  
  - Item 1
  - Item 2
  - Item 3
  
  How can I assist you?"""
            lc_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))


        print(f'\n\n{lc_messages}\n\n')
        
        return lc_messages


class BedrockProvider(BaseAIProvider):
    def __init__(self, config: Settings):
        if ChatBedrock is None:
            raise ValueError(
                "langchain-aws is not installed. Install it with: pip install langchain-aws"
            )
        try:
            self.llm = ChatBedrock(
                model_id=config.BEDROCK_MODEL_ID,
                region_name=config.AWS_REGION,
                streaming=True
            )
        except Exception as e:
            raise ValueError(
                f"Failed to initialize Bedrock provider: {str(e)}\n"
                f"Please ensure:\n"
                f"1. AWS credentials are configured (run 'aws configure')\n"
                f"2. Install botocore[crt]: pip install 'botocore[crt]'\n"
                f"3. You have access to Bedrock in region {config.AWS_REGION}"
            )
    
    async def stream_response(self, messages: List[Dict], context: Optional[str] = None) -> AsyncGenerator[str, None]:
        lc_messages = self._convert_messages(messages, context)
        async for chunk in self.llm.astream(lc_messages):
            if chunk.content:
                yield chunk.content


class OpenAIProvider(BaseAIProvider):
    def __init__(self, config: Settings):
        if ChatOpenAI is None:
            raise ValueError(
                "langchain-openai is not installed. Install it with: pip install langchain-openai"
            )
        self.llm = ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            streaming=True
        )
    
    async def stream_response(self, messages: List[Dict], context: Optional[str] = None) -> AsyncGenerator[str, None]:
        lc_messages = self._convert_messages(messages, context)
        async for chunk in self.llm.astream(lc_messages):
            if chunk.content:
                yield chunk.content


class AnthropicProvider(BaseAIProvider):
    def __init__(self, config: Settings):
        if ChatAnthropic is None:
            raise ValueError(
                "langchain-anthropic is not installed. Install it with: pip install langchain-anthropic"
            )
        self.llm = ChatAnthropic(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.ANTHROPIC_MODEL,
            streaming=True
        )
    
    async def stream_response(self, messages: List[Dict], context: Optional[str] = None) -> AsyncGenerator[str, None]:
        lc_messages = self._convert_messages(messages, context)
        async for chunk in self.llm.astream(lc_messages):
            if chunk.content:
                yield chunk.content


class GeminiProvider(BaseAIProvider):
    def __init__(self, config: Settings):
        if ChatGoogleGenerativeAI is None:
            raise ValueError(
                "langchain-google-genai is not installed. Install it with: pip install langchain-google-genai"
            )
        self.llm = ChatGoogleGenerativeAI(
            google_api_key=config.GOOGLE_API_KEY,
            model=config.GEMINI_MODEL,
            streaming=True
        )
    
    async def stream_response(self, messages: List[Dict], context: Optional[str] = None) -> AsyncGenerator[str, None]:
        lc_messages = self._convert_messages(messages, context)
        async for chunk in self.llm.astream(lc_messages):
            if chunk.content:
                yield chunk.content


def create_provider(config: Settings) -> BaseAIProvider:
    provider_map = {
        "bedrock": BedrockProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider
    }
    
    provider_class = provider_map.get(config.AI_PROVIDER.lower())
    if not provider_class:
        raise ValueError(f"Unknown AI provider: {config.AI_PROVIDER}")
    
    try:
        return provider_class(config)
    except Exception as e:
        raise ValueError(
            f"Failed to initialize {config.AI_PROVIDER} provider: {str(e)}\n"
            f"Check your .env configuration and credentials."
        )
