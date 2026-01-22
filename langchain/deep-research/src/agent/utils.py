"""Utility functions and helpers for the Deep Research agent."""

import asyncio
import logging
import os
import warnings
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional

import aiohttp
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    MessageLikeRepresentation,
    filter_messages,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import (
    BaseTool,
    InjectedToolArg,
    StructuredTool,
    ToolException,
    tool,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.config import get_store
from mcp import McpError
from tavily import AsyncTavilyClient

from agent.configuration import Configuration, SearchAPI
from agent.prompts import summarize_webpage_prompt
from agent.state import ResearchComplete, Summary

##########################
# AWS Credentials Setup
##########################
def setup_bedrock_credentials():
    """Set up AWS credentials from BEDROCK_* environment variables if standard AWS_* vars are not set."""
    # Only set if standard AWS credentials are not already set
    if not os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("BEDROCK_AWS_ACCESS_KEY_ID"):
        os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("BEDROCK_AWS_ACCESS_KEY_ID")
    if not os.getenv("AWS_SECRET_ACCESS_KEY") and os.getenv("BEDROCK_AWS_SECRET_ACCESS_KEY"):
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("BEDROCK_AWS_SECRET_ACCESS_KEY")
    if not os.getenv("AWS_DEFAULT_REGION") and os.getenv("BEDROCK_AWS_REGION"):
        os.environ["AWS_DEFAULT_REGION"] = os.getenv("BEDROCK_AWS_REGION")
    # Also set AWS_REGION if not set
    if not os.getenv("AWS_REGION") and os.getenv("BEDROCK_AWS_REGION"):
        os.environ["AWS_REGION"] = os.getenv("BEDROCK_AWS_REGION")

##########################
# Tavily Search Tool Utils
##########################
TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)
@tool(description=TAVILY_SEARCH_DESCRIPTION)
async def tavily_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 2,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: RunnableConfig = None
) -> str:
    """Fetch and summarize search results from Tavily search API.

    Args:
        queries: List of search queries to execute
        max_results: Maximum number of results to return per query
        topic: Topic filter for search results (general, news, or finance)
        config: Runtime configuration for API keys and model settings

    Returns:
        Formatted string containing summarized search results
    """
    # Step 1: Execute search queries asynchronously
    search_results = await tavily_search_async(
        queries,
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
        config=config
    )
    
    # Step 2: Deduplicate results by URL to avoid processing the same content multiple times
    unique_results = {}
    for response in search_results:
        for result in response['results']:
            url = result['url']
            if url not in unique_results:
                unique_results[url] = {**result, "query": response['query']}
    
    # Step 3: Set up the summarization model with configuration
    configurable = Configuration.from_runnable_config(config)
    
    # Character limit to stay within model token limits (configurable)
    max_char_to_include = configurable.max_content_length
    
    # Initialize summarization model with retry logic
    summarization_model_config = build_model_config(
        configurable.summarization_model,
        configurable.summarization_model_max_tokens,
        config,
        tags=["langsmith:nostream"]
    )
    summarization_model = init_chat_model(
        **summarization_model_config
    ).with_structured_output(Summary).with_retry(
        stop_after_attempt=configurable.max_structured_output_retries
    )
    
    # Step 4: Create summarization tasks (skip empty content)
    async def noop():
        """No-op function for results without raw content."""
        return None
    
    summarization_tasks = [
        noop() if not result.get("raw_content") 
        else summarize_webpage(
            summarization_model, 
            result['raw_content'][:max_char_to_include]
        )
        for result in unique_results.values()
    ]
    
    # Step 5: Execute all summarization tasks in parallel
    summaries = await asyncio.gather(*summarization_tasks)
    
    # Step 6: Combine results with their summaries
    summarized_results = {
        url: {
            'title': result['title'], 
            'content': result['content'] if summary is None else summary
        }
        for url, result, summary in zip(
            unique_results.keys(), 
            unique_results.values(), 
            summaries
        )
    }
    
    # Step 7: Format the final output
    if not summarized_results:
        return "No valid search results found. Please try different search queries or use a different search API."
    
    formatted_output = "Search results: \n\n"
    for i, (url, result) in enumerate(summarized_results.items()):
        formatted_output += f"\n\n--- SOURCE {i+1}: {result['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result['content']}\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"
    
    return formatted_output

async def tavily_search_async(
    search_queries, 
    max_results: int = 2, 
    topic: Literal["general", "news", "finance"] = "general", 
    include_raw_content: bool = True, 
    config: RunnableConfig = None
):
    """Execute multiple Tavily search queries asynchronously.
    
    Args:
        search_queries: List of search query strings to execute
        max_results: Maximum number of results per query
        topic: Topic category for filtering results
        include_raw_content: Whether to include full webpage content
        config: Runtime configuration for API key access
        
    Returns:
        List of search result dictionaries from Tavily API
    """
    # Initialize the Tavily client with API key from config
    tavily_client = AsyncTavilyClient(api_key=get_tavily_api_key(config))
    
    # Create search tasks for parallel execution
    search_tasks = [
        tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic
        )
        for query in search_queries
    ]
    
    # Execute all search queries in parallel and return results
    search_results = await asyncio.gather(*search_tasks)
    return search_results

async def summarize_webpage(model: BaseChatModel, webpage_content: str) -> str:
    """Summarize webpage content using AI model with timeout protection.
    
    Args:
        model: The chat model configured for summarization
        webpage_content: Raw webpage content to be summarized
        
    Returns:
        Formatted summary with key excerpts, or original content if summarization fails
    """
    try:
        # Create prompt with current date context
        prompt_content = summarize_webpage_prompt.format(
            webpage_content=webpage_content, 
            date=get_today_str()
        )
        
        # Execute summarization with timeout to prevent hanging
        summary = await asyncio.wait_for(
            model.ainvoke([HumanMessage(content=prompt_content)]),
            timeout=60.0  # 60 second timeout for summarization
        )
        
        # Format the summary with structured sections
        formatted_summary = (
            f"<summary>\n{summary.summary}\n</summary>\n\n"
            f"<key_excerpts>\n{summary.key_excerpts}\n</key_excerpts>"
        )
        
        return formatted_summary
        
    except asyncio.TimeoutError:
        # Timeout during summarization - return original content
        logging.warning("Summarization timed out after 60 seconds, returning original content")
        return webpage_content
    except Exception as e:
        # Other errors during summarization - log and return original content
        logging.warning(f"Summarization failed with error: {str(e)}, returning original content")
        return webpage_content

##########################
# Reflection Tool Utils
##########################

@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"

##########################
# MCP Utils
##########################

async def get_mcp_access_token(
    supabase_token: str,
    base_mcp_url: str,
) -> Optional[Dict[str, Any]]:
    """Exchange Supabase token for MCP access token using OAuth token exchange.
    
    Args:
        supabase_token: Valid Supabase authentication token
        base_mcp_url: Base URL of the MCP server
        
    Returns:
        Token data dictionary if successful, None if failed
    """
    try:
        # Prepare OAuth token exchange request data
        form_data = {
            "client_id": "mcp_default",
            "subject_token": supabase_token,
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "resource": base_mcp_url.rstrip("/") + "/mcp",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }
        
        # Execute token exchange request
        async with aiohttp.ClientSession() as session:
            token_url = base_mcp_url.rstrip("/") + "/oauth/token"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            async with session.post(token_url, headers=headers, data=form_data) as response:
                if response.status == 200:
                    # Successfully obtained token
                    token_data = await response.json()
                    return token_data
                else:
                    # Log error details for debugging
                    response_text = await response.text()
                    logging.error(f"Token exchange failed: {response_text}")
                    
    except Exception as e:
        logging.error(f"Error during token exchange: {e}")
    
    return None

async def get_tokens(config: RunnableConfig):
    """Retrieve stored authentication tokens with expiration validation.
    
    Args:
        config: Runtime configuration containing thread and user identifiers
        
    Returns:
        Token dictionary if valid and not expired, None otherwise
    """
    store = get_store()
    
    # Extract required identifiers from config
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return None
        
    user_id = config.get("metadata", {}).get("owner")
    if not user_id:
        return None
    
    # Retrieve stored tokens
    tokens = await store.aget((user_id, "tokens"), "data")
    if not tokens:
        return None
    
    # Check token expiration
    expires_in = tokens.value.get("expires_in")  # seconds until expiration
    created_at = tokens.created_at  # datetime of token creation
    current_time = datetime.now(timezone.utc)
    expiration_time = created_at + timedelta(seconds=expires_in)
    
    if current_time > expiration_time:
        # Token expired, clean up and return None
        await store.adelete((user_id, "tokens"), "data")
        return None

    return tokens.value

async def set_tokens(config: RunnableConfig, tokens: dict[str, Any]):
    """Store authentication tokens in the configuration store.
    
    Args:
        config: Runtime configuration containing thread and user identifiers
        tokens: Token dictionary to store
    """
    store = get_store()
    
    # Extract required identifiers from config
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        return
        
    user_id = config.get("metadata", {}).get("owner")
    if not user_id:
        return
    
    # Store the tokens
    await store.aput((user_id, "tokens"), "data", tokens)

async def fetch_tokens(config: RunnableConfig) -> dict[str, Any]:
    """Fetch and refresh MCP tokens, obtaining new ones if needed.
    
    Args:
        config: Runtime configuration with authentication details
        
    Returns:
        Valid token dictionary, or None if unable to obtain tokens
    """
    # Try to get existing valid tokens first
    current_tokens = await get_tokens(config)
    if current_tokens:
        return current_tokens
    
    # Extract Supabase token for new token exchange
    supabase_token = config.get("configurable", {}).get("x-supabase-access-token")
    if not supabase_token:
        return None
    
    # Extract MCP configuration
    mcp_config = config.get("configurable", {}).get("mcp_config")
    if not mcp_config or not mcp_config.get("url"):
        return None
    
    # Exchange Supabase token for MCP tokens
    mcp_tokens = await get_mcp_access_token(supabase_token, mcp_config.get("url"))
    if not mcp_tokens:
        return None

    # Store the new tokens and return them
    await set_tokens(config, mcp_tokens)
    return mcp_tokens

def wrap_mcp_authenticate_tool(tool: StructuredTool) -> StructuredTool:
    """Wrap MCP tool with comprehensive authentication and error handling.
    
    Args:
        tool: The MCP structured tool to wrap
        
    Returns:
        Enhanced tool with authentication error handling
    """
    original_coroutine = tool.coroutine
    
    async def authentication_wrapper(**kwargs):
        """Enhanced coroutine with MCP error handling and user-friendly messages."""
        
        def _find_mcp_error_in_exception_chain(exc: BaseException) -> McpError | None:
            """Recursively search for MCP errors in exception chains."""
            if isinstance(exc, McpError):
                return exc
            
            # Handle ExceptionGroup (Python 3.11+) by checking attributes
            if hasattr(exc, 'exceptions'):
                for sub_exception in exc.exceptions:
                    if found_error := _find_mcp_error_in_exception_chain(sub_exception):
                        return found_error
            return None
        
        try:
            # Execute the original tool functionality
            return await original_coroutine(**kwargs)
            
        except BaseException as original_error:
            # Search for MCP-specific errors in the exception chain
            mcp_error = _find_mcp_error_in_exception_chain(original_error)
            if not mcp_error:
                # Not an MCP error, re-raise the original exception
                raise original_error
            
            # Handle MCP-specific error cases
            error_details = mcp_error.error
            error_code = getattr(error_details, "code", None)
            error_data = getattr(error_details, "data", None) or {}
            
            # Check for authentication/interaction required error
            if error_code == -32003:  # Interaction required error code
                message_payload = error_data.get("message", {})
                error_message = "Required interaction"
                
                # Extract user-friendly message if available
                if isinstance(message_payload, dict):
                    error_message = message_payload.get("text") or error_message
                
                # Append URL if provided for user reference
                if url := error_data.get("url"):
                    error_message = f"{error_message} {url}"
                
                raise ToolException(error_message) from original_error
            
            # For other MCP errors, re-raise the original
            raise original_error
    
    # Replace the tool's coroutine with our enhanced version
    tool.coroutine = authentication_wrapper
    return tool

async def load_mcp_tools(
    config: RunnableConfig,
    existing_tool_names: set[str],
) -> list[BaseTool]:
    """Load and configure MCP (Model Context Protocol) tools with authentication.
    
    Args:
        config: Runtime configuration containing MCP server details
        existing_tool_names: Set of tool names already in use to avoid conflicts
        
    Returns:
        List of configured MCP tools ready for use
    """
    configurable = Configuration.from_runnable_config(config)
    
    # Step 1: Handle authentication if required
    if configurable.mcp_config and configurable.mcp_config.auth_required:
        mcp_tokens = await fetch_tokens(config)
    else:
        mcp_tokens = None
    
    # Step 2: Validate configuration requirements
    config_valid = (
        configurable.mcp_config and 
        configurable.mcp_config.url and 
        configurable.mcp_config.tools and 
        (mcp_tokens or not configurable.mcp_config.auth_required)
    )
    
    if not config_valid:
        return []
    
    # Step 3: Set up MCP server connection
    server_url = configurable.mcp_config.url.rstrip("/") + "/mcp"
    
    # Configure authentication headers if tokens are available
    auth_headers = None
    if mcp_tokens:
        auth_headers = {"Authorization": f"Bearer {mcp_tokens['access_token']}"}
    
    mcp_server_config = {
        "server_1": {
            "url": server_url,
            "headers": auth_headers,
            "transport": "streamable_http"
        }
    }
    # TODO: When Multi-MCP Server support is merged in OAP, update this code
    
    # Step 4: Load tools from MCP server
    try:
        client = MultiServerMCPClient(mcp_server_config)
        available_mcp_tools = await client.get_tools()
    except Exception:
        # If MCP server connection fails, return empty list
        return []
    
    # Step 5: Filter and configure tools
    configured_tools = []
    for mcp_tool in available_mcp_tools:
        # Skip tools with conflicting names
        if mcp_tool.name in existing_tool_names:
            warnings.warn(
                f"MCP tool '{mcp_tool.name}' conflicts with existing tool name - skipping"
            )
            continue
        
        # Only include tools specified in configuration
        if mcp_tool.name not in set(configurable.mcp_config.tools):
            continue
        
        # Wrap tool with authentication handling and add to list
        enhanced_tool = wrap_mcp_authenticate_tool(mcp_tool)
        configured_tools.append(enhanced_tool)
    
    return configured_tools


##########################
# OpenSearch Search Tool (via MCP)
##########################

DUCKDUCKGO_SEARCH_DESCRIPTION = (
    "A web search tool that uses DuckDuckGo to find current information. "
    "Useful for when you need to answer questions about current events or find recent information."
)

GOOGLE_SEARCH_DESCRIPTION = (
    "A web search tool that uses Google Custom Search to find current information. "
    "Useful for when you need to answer questions about current events or find recent information. "
    "Requires GOOGLE_API_KEY and GOOGLE_ENGINE_ID environment variables."
)

def create_duckduckgo_search_wrapper(mcp_tool: BaseTool):
    """Create a wrapper tool for DuckDuckGo MCP tool with summarization.
    
    Args:
        mcp_tool: The DuckDuckGo MCP tool loaded from OpenSearch
        
    Returns:
        A tool function that wraps the MCP tool with summarization
    """
    @tool(description=DUCKDUCKGO_SEARCH_DESCRIPTION)
    async def duckduckgo_search(
        query: str,
        engine: Annotated[str, InjectedToolArg] = "duckduckgo",
        config: RunnableConfig = None
    ) -> str:
        """Fetch and summarize search results from DuckDuckGo via MCP.
        
        Args:
            query: Search query string
            engine: Search engine to use (default: "duckduckgo")
            config: Runtime configuration for API keys and model settings
            
        Returns:
            Formatted string containing summarized search results
        """
        # Execute the search via MCP tool (reuse the already-loaded tool)
        try:
            result = await asyncio.wait_for(
                mcp_tool.ainvoke({"query": query, "engine": engine}, config),
                timeout=45.0  # 45 second timeout
            )
        except asyncio.TimeoutError:
            return "Search request timed out after 45 seconds. Please try again with a more specific query."
        except McpError as e:
            # Handle MCP errors from OpenSearch plugin - these often indicate DuckDuckGo blocking or parsing issues
            error_msg = str(e)
            if "failed to fetch duckduckgo results" in error_msg.lower():
                return "DuckDuckGo search encountered an error. This may be due to rate limiting, CAPTCHA challenges, or DuckDuckGo blocking automated requests. Please try again with a different query or wait a moment."
            return f"DuckDuckGo search error: {error_msg}. Please try again with a different query."
        except Exception as e:
            error_str = str(e)
            if "closed file" in error_str.lower() or "connection" in error_str.lower():
                return f"Search request encountered a connection error. Please try again. Error: {error_str[:200]}"
            return f"Search error: {error_str}. Please try again."
        
        # Step 3: Parse and summarize results (reuse Tavily's logic)
        if isinstance(result, str):
            try:
                import json
                parsed_result = json.loads(result)
                if isinstance(parsed_result, dict) and "items" in parsed_result:
                    return await _summarize_opensearch_results(parsed_result, config)
            except (json.JSONDecodeError, KeyError):
                # If parsing fails, return original result
                pass
        
        return result if isinstance(result, str) else str(result)
    
    return duckduckgo_search


def create_google_search_wrapper(mcp_tool: BaseTool):
    """Create a wrapper tool for Google MCP tool with auto-injected credentials and summarization.
    
    Args:
        mcp_tool: The Google MCP tool loaded from OpenSearch
        
    Returns:
        A tool function that wraps the MCP tool with credential injection and summarization
    """
    @tool(description=GOOGLE_SEARCH_DESCRIPTION)
    async def google_search(
        query: str,
        engine: Annotated[str, InjectedToolArg] = "google",
        config: RunnableConfig = None
    ) -> str:
        """Fetch and summarize search results from Google via MCP.
        
        Args:
            query: Search query string
            engine: Search engine to use (default: "google")
            config: Runtime configuration for API keys and model settings
            
        Returns:
            Formatted string containing summarized search results
        """
        # Get Google credentials from environment variables
        api_key = os.getenv("GOOGLE_API_KEY")
        engine_id = os.getenv("GOOGLE_ENGINE_ID")
        
        if not api_key or not engine_id:
            return "Google search is not configured. Please set GOOGLE_API_KEY and GOOGLE_ENGINE_ID environment variables."
        
        # Execute the search via MCP tool with auto-injected credentials
        try:
            result = await asyncio.wait_for(
                mcp_tool.ainvoke({
                    "query": query,
                    "engine": engine,
                    "api_key": api_key,
                    "engine_id": engine_id
                }, config),
                timeout=45.0  # 45 second timeout
            )
        except asyncio.TimeoutError:
            return "Search request timed out after 45 seconds. Please try again with a more specific query."
        except McpError as e:
            # Handle MCP errors from OpenSearch plugin
            error_msg = str(e)
            if "failed to fetch" in error_msg.lower() or "400" in error_msg.lower():
                return "Google search encountered an error. This may be due to invalid API credentials, rate limiting, or API configuration issues. Please verify your Google API key and Engine ID are correct."
            return f"Google search error: {error_msg}. Please try again with a different query."
        except Exception as e:
            error_str = str(e)
            if "closed file" in error_str.lower() or "connection" in error_str.lower():
                return f"Search request encountered a connection error. Please try again. Error: {error_str[:200]}"
            return f"Search error: {error_str}. Please try again."
        
        # Parse and summarize results (reuse DuckDuckGo's logic)
        if isinstance(result, str):
            try:
                import json
                parsed_result = json.loads(result)
                if isinstance(parsed_result, dict) and "items" in parsed_result:
                    # Limit to top 2 results to save API costs
                    if isinstance(parsed_result["items"], list):
                        parsed_result["items"] = parsed_result["items"][:2]
                    return await _summarize_opensearch_results(parsed_result, config)
            except (json.JSONDecodeError, KeyError):
                # If parsing fails, return original result
                pass
        
        return result if isinstance(result, str) else str(result)
    
    return google_search


async def _load_mcp_tools(config: RunnableConfig) -> List[BaseTool]:
    """Load tools from MCP server.
    
    Args:
        config: Runtime configuration containing MCP server details
        
    Returns:
        List of available tools from MCP server
        
    Raises:
        ValueError: If MCP is configured but tools cannot be loaded
    """
    configurable = Configuration.from_runnable_config(config)
    
    # Check if MCP is configured
    if not configurable.mcp_config or not configurable.mcp_config.url:
        return []
    
    mcp_url = configurable.mcp_config.url
    
    # Set up MCP client connection - try both endpoint formats
    endpoints_to_try = [
        mcp_url.rstrip("/") + "/_plugins/_ml/mcp",  # OpenSearch ML Commons MCP endpoint
        mcp_url.rstrip("/") + "/mcp",  # Standard MCP endpoint
    ]
    
    # Always use authentication if credentials are provided
    auth_headers = None
    if configurable.mcp_config.username and configurable.mcp_config.password:
        import base64
        credentials = f"{configurable.mcp_config.username}:{configurable.mcp_config.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        auth_headers = {"Authorization": f"Basic {encoded_credentials}"}
    elif configurable.mcp_config.auth_required:
        raise ValueError("MCP auth_required=True but username/password not provided")
    
    last_error = None
    available_tools = None
    
    # Try each endpoint format
    for server_url in endpoints_to_try:
        try:
            mcp_server_config = {
                "opensearch": {
                    "transport": "streamable_http",
                    "url": server_url,
                }
            }
            
            # Add headers if authentication is configured
            if auth_headers:
                mcp_server_config["opensearch"]["headers"] = auth_headers
            
            # Load tools from MCP server
            client = MultiServerMCPClient(mcp_server_config)
            available_tools = await client.get_tools()
            
            break  # Success, exit loop
            
        except Exception as e:
            last_error = e
            continue
    
    if available_tools is None:
        raise ValueError(
            f"Failed to connect to MCP server at {mcp_url}. "
            f"Tried endpoints: {endpoints_to_try}. "
            f"Last error: {last_error}"
        )
    
    return available_tools


async def load_duckduckgo_from_mcp(config: RunnableConfig) -> Optional[List[BaseTool]]:
    """Load DuckDuckGo search tool from MCP server.
    
    Args:
        config: Runtime configuration containing MCP server details
        
    Returns:
        List containing DuckDuckGo tool if available from MCP server, None otherwise
        
    Raises:
        ValueError: If MCP is configured but tool cannot be loaded
    """
    available_tools = await _load_mcp_tools(config)
    if not available_tools:
        return None
    
    # Find DuckDuckGo tool - use exact name from OpenSearch config
    tool_name = 'DuckduckgoWebSearchTool'  # Exact name from OpenSearch registration
    duckduckgo_tool = next(
        (tool for tool in available_tools if tool.name == tool_name), 
        None
    )
    
    if not duckduckgo_tool:
        return None
    
    # Return the raw MCP tool (it will be used internally by duckduckgo_search wrapper)
    return [duckduckgo_tool]


async def load_google_from_mcp(config: RunnableConfig) -> Optional[List[BaseTool]]:
    """Load Google search tool from MCP server.
    
    Args:
        config: Runtime configuration containing MCP server details
        
    Returns:
        List containing Google tool if available from MCP server, None otherwise
    """
    available_tools = await _load_mcp_tools(config)
    if not available_tools:
        return None
    
    # Find Google tool
    google_tool = next(
        (tool for tool in available_tools if tool.name == "GoogleWebSearchTool"), 
        None
    )
    
    if not google_tool:
        return None
    
    return [google_tool]


async def _summarize_opensearch_results(result: dict, config: RunnableConfig) -> str:
    """Summarize OpenSearch WebSearchTool results using Tavily's summarization logic.
    
    Args:
        result: Parsed JSON result from OpenSearch WebSearchTool (supports DuckDuckGo, Google, etc.)
        config: Runtime configuration for summarization model
        
    Returns:
        Formatted string with summarized search results
    """
    configurable = Configuration.from_runnable_config(config)
    items = result.get("items", [])
    
    # Step 1: Extract and deduplicate results by URL (same as Tavily)
    unique_results = {}
    for item in items:
        if item and isinstance(item, dict) and item.get("url"):
            url = item["url"]
            if url not in unique_results:
                unique_results[url] = {
                    "url": url,
                    "title": item.get("title", ""),
                    "raw_content": item.get("content", "")  # Use same key name as Tavily
                }
    
    if not unique_results:
        return "No valid search results found. Please try different search queries."
    
    # Step 2: Set up summarization model (reuse Tavily's logic)
    max_char_to_include = configurable.max_content_length
    summarization_model_config = build_model_config(
        configurable.summarization_model,
        configurable.summarization_model_max_tokens,
        config,
        tags=["langsmith:nostream"]
    )
    summarization_model = init_chat_model(
        **summarization_model_config
    ).with_structured_output(Summary).with_retry(
        stop_after_attempt=configurable.max_structured_output_retries
    )
    
    # Step 3: Create summarization tasks (reuse Tavily's pattern)
    async def noop():
        """No-op function for results without raw content."""
        return None
    
    summarization_tasks = [
        noop() if not result.get("raw_content")
        else summarize_webpage(
            summarization_model,
            result["raw_content"][:max_char_to_include]
        )
        for result in unique_results.values()
    ]
    
    # Step 4: Execute all summarization tasks in parallel (reuse Tavily's pattern)
    summaries = await asyncio.gather(*summarization_tasks)
    
    # Step 5: Combine results with their summaries (reuse Tavily's pattern)
    summarized_results = {
        url: {
            "title": result["title"] or "Untitled",
            "content": result["raw_content"] if summary is None else summary
        }
        for url, result, summary in zip(
            unique_results.keys(),
            unique_results.values(),
            summaries
        )
    }
    
    # Step 6: Format the final output (reuse Tavily's formatting)
    if not summarized_results:
        return "No valid search results found. Please try different search queries or use a different search API."
    
    formatted_output = "Search results: \n\n"
    for i, (url, result_data) in enumerate(summarized_results.items()):
        formatted_output += f"\n\n--- SOURCE {i+1}: {result_data['title']} ---\n"
        formatted_output += f"URL: {url}\n\n"
        formatted_output += f"SUMMARY:\n{result_data['content']}\n\n"
        formatted_output += "\n\n" + "-" * 80 + "\n"
    
    return formatted_output

##########################
# Tool Utils
##########################

async def get_search_tool(search_api: SearchAPI):
    """Configure and return search tools based on the specified API provider.
    
    Args:
        search_api: The search API provider to use (Anthropic, OpenAI, Tavily, or None)
        
    Returns:
        List of configured search tool objects for the specified provider
    """
    if search_api == SearchAPI.ANTHROPIC:
        # Anthropic's native web search with usage limits
        return [{
            "type": "web_search_20250305", 
            "name": "web_search", 
            "max_uses": 5
        }]
        
    elif search_api == SearchAPI.OPENAI:
        # OpenAI's web search preview functionality
        return [{"type": "web_search_preview"}]
        
    elif search_api == SearchAPI.TAVILY:
        # Configure Tavily search tool with metadata
        search_tool = tavily_search
        search_tool.metadata = {
            **(search_tool.metadata or {}), 
            "type": "search", 
            "name": "web_search"
        }
        return [search_tool]
        
    elif search_api == SearchAPI.NONE:
        # No search functionality configured
        return []
        
    # Default fallback for unknown search API types
    return []
    
async def get_all_tools(config: RunnableConfig):
    """Assemble complete toolkit including research, search, and MCP tools.
    
    Args:
        config: Runtime configuration specifying search API and MCP settings
        
    Returns:
        List of all configured and available tools for research operations
    """
    # Start with core research tools
    tools = [tool(ResearchComplete), think_tool]
    
    # Add configured search tools
    configurable = Configuration.from_runnable_config(config)

    # Check if Google MCP tool is available
    google_mcp_tools = await load_google_from_mcp(config)
    if google_mcp_tools:
        # Create wrapper tool that handles credential injection and summarization
        google_mcp_tool = google_mcp_tools[0]
        google_wrapper = create_google_search_wrapper(google_mcp_tool)
        # Set the tool name to match what the LLM expects
        google_wrapper.name = "WebSearchTool"
        google_wrapper.metadata = {
            **(google_wrapper.metadata or {}),
            "type": "search"
        }
        tools.append(google_wrapper)

    search_api = SearchAPI(get_config_value(configurable.search_api))
    # search_tools = await get_search_tool(search_api)
    # tools.extend(search_tools)
    
    # Track existing tool names to prevent conflicts
    existing_tool_names = {
        tool.name if hasattr(tool, "name") else tool.get("name", "web_search") 
        for tool in tools
    }
    
    # Add MCP tools if configured
    mcp_tools = await load_mcp_tools(config, existing_tool_names)
    tools.extend(mcp_tools)
    
    return tools

def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    """Extract notes from tool call messages."""
    return [tool_msg.content for tool_msg in filter_messages(messages, include_types="tool")]

##########################
# Model Provider Native Websearch Utils
##########################

def anthropic_websearch_called(response):
    """Detect if Anthropic's native web search was used in the response.
    
    Args:
        response: The response object from Anthropic's API
        
    Returns:
        True if web search was called, False otherwise
    """
    try:
        # Navigate through the response metadata structure
        usage = response.response_metadata.get("usage")
        if not usage:
            return False
        
        # Check for server-side tool usage information
        server_tool_use = usage.get("server_tool_use")
        if not server_tool_use:
            return False
        
        # Look for web search request count
        web_search_requests = server_tool_use.get("web_search_requests")
        if web_search_requests is None:
            return False
        
        # Return True if any web search requests were made
        return web_search_requests > 0
        
    except (AttributeError, TypeError):
        # Handle cases where response structure is unexpected
        return False

def openai_websearch_called(response):
    """Detect if OpenAI's web search functionality was used in the response.
    
    Args:
        response: The response object from OpenAI's API
        
    Returns:
        True if web search was called, False otherwise
    """
    # Check for tool outputs in the response metadata
    tool_outputs = response.additional_kwargs.get("tool_outputs")
    if not tool_outputs:
        return False
    
    # Look for web search calls in the tool outputs
    for tool_output in tool_outputs:
        if tool_output.get("type") == "web_search_call":
            return True
    
    return False


##########################
# Token Limit Exceeded Utils
##########################

def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Determine if an exception indicates a token/context limit was exceeded.
    
    Args:
        exception: The exception to analyze
        model_name: Optional model name to optimize provider detection
        
    Returns:
        True if the exception indicates a token limit was exceeded, False otherwise
    """
    error_str = str(exception).lower()
    
    # Step 1: Determine provider from model name if available
    provider = None
    if model_name:
        model_str = str(model_name).lower()
        if model_str.startswith('openai:'):
            provider = 'openai'
        elif model_str.startswith('anthropic:'):
            provider = 'anthropic'
        elif model_str.startswith('gemini:') or model_str.startswith('google:'):
            provider = 'gemini'
    
    # Step 2: Check provider-specific token limit patterns
    if provider == 'openai':
        return _check_openai_token_limit(exception, error_str)
    elif provider == 'anthropic':
        return _check_anthropic_token_limit(exception, error_str)
    elif provider == 'gemini':
        return _check_gemini_token_limit(exception, error_str)
    
    # Step 3: If provider unknown, check all providers
    return (
        _check_openai_token_limit(exception, error_str) or
        _check_anthropic_token_limit(exception, error_str) or
        _check_gemini_token_limit(exception, error_str)
    )

def _check_openai_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates OpenAI token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')
    
    # Check if this is an OpenAI exception
    is_openai_exception = (
        'openai' in exception_type.lower() or 
        'openai' in module_name.lower()
    )
    
    # Check for typical OpenAI token limit error types
    is_request_error = class_name in ['BadRequestError', 'InvalidRequestError']
    
    if is_openai_exception and is_request_error:
        # Look for token-related keywords in error message
        token_keywords = ['token', 'context', 'length', 'maximum context', 'reduce']
        if any(keyword in error_str for keyword in token_keywords):
            return True
    
    # Check for specific OpenAI error codes
    if hasattr(exception, 'code') and hasattr(exception, 'type'):
        error_code = getattr(exception, 'code', '')
        error_type = getattr(exception, 'type', '')
        
        if (error_code == 'context_length_exceeded' or
            error_type == 'invalid_request_error'):
            return True
    
    return False

def _check_anthropic_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates Anthropic token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')
    
    # Check if this is an Anthropic exception
    is_anthropic_exception = (
        'anthropic' in exception_type.lower() or 
        'anthropic' in module_name.lower()
    )
    
    # Check for Anthropic-specific error patterns
    is_bad_request = class_name == 'BadRequestError'
    
    if is_anthropic_exception and is_bad_request:
        # Anthropic uses specific error messages for token limits
        if 'prompt is too long' in error_str:
            return True
    
    return False

def _check_gemini_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates Google/Gemini token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')
    
    # Check if this is a Google/Gemini exception
    is_google_exception = (
        'google' in exception_type.lower() or 
        'google' in module_name.lower()
    )
    
    # Check for Google-specific resource exhaustion errors
    is_resource_exhausted = class_name in [
        'ResourceExhausted', 
        'GoogleGenerativeAIFetchError'
    ]
    
    if is_google_exception and is_resource_exhausted:
        return True
    
    # Check for specific Google API resource exhaustion patterns
    if 'google.api_core.exceptions.resourceexhausted' in exception_type.lower():
        return True
    
    return False

# NOTE: This may be out of date or not applicable to your models. Please update this as needed.
MODEL_TOKEN_LIMITS = {
    "openai:gpt-4.1-mini": 1047576,
    "openai:gpt-4.1-nano": 1047576,
    "openai:gpt-4.1": 1047576,
    "openai:gpt-4o-mini": 128000,
    "openai:gpt-4o": 128000,
    "openai:o4-mini": 200000,
    "openai:o3-mini": 200000,
    "openai:o3": 200000,
    "openai:o3-pro": 200000,
    "openai:o1": 200000,
    "openai:o1-pro": 200000,
    "anthropic:claude-opus-4": 200000,
    "anthropic:claude-sonnet-4": 200000,
    "anthropic:claude-3-7-sonnet": 200000,
    "anthropic:claude-3-5-sonnet": 200000,
    "anthropic:claude-3-5-haiku": 200000,
    "google:gemini-1.5-pro": 2097152,
    "google:gemini-1.5-flash": 1048576,
    "google:gemini-pro": 32768,
    "cohere:command-r-plus": 128000,
    "cohere:command-r": 128000,
    "cohere:command-light": 4096,
    "cohere:command": 4096,
    "mistral:mistral-large": 32768,
    "mistral:mistral-medium": 32768,
    "mistral:mistral-small": 32768,
    "mistral:mistral-7b-instruct": 32768,
    "ollama:codellama": 16384,
    "ollama:llama2:70b": 4096,
    "ollama:llama2:13b": 4096,
    "ollama:llama2": 4096,
    "ollama:mistral": 32768,
    "bedrock:us.amazon.nova-premier-v1:0": 1000000,
    "bedrock:us.amazon.nova-pro-v1:0": 300000,
    "bedrock:us.amazon.nova-lite-v1:0": 300000,
    "bedrock:us.amazon.nova-micro-v1:0": 128000,
    "bedrock:us.anthropic.claude-3-7-sonnet-20250219-v1:0": 200000,
    "bedrock:us.anthropic.claude-sonnet-4-20250514-v1:0": 200000,
    "bedrock:us.anthropic.claude-opus-4-20250514-v1:0": 200000,
    "anthropic.claude-opus-4-1-20250805-v1:0": 200000,
}

def get_model_token_limit(model_string):
    """Look up the token limit for a specific model.
    
    Args:
        model_string: The model identifier string to look up
        
    Returns:
        Token limit as integer if found, None if model not in lookup table
    """
    # Search through known model token limits
    for model_key, token_limit in MODEL_TOKEN_LIMITS.items():
        if model_key in model_string:
            return token_limit
    
    # Model not found in lookup table
    return None

def remove_up_to_last_ai_message(messages: list[MessageLikeRepresentation]) -> list[MessageLikeRepresentation]:
    """Truncate message history by removing up to the last AI message.
    
    This is useful for handling token limit exceeded errors by removing recent context.
    
    Args:
        messages: List of message objects to truncate
        
    Returns:
        Truncated message list up to (but not including) the last AI message
    """
    # Search backwards through messages to find the last AI message
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            # Return everything up to (but not including) the last AI message
            return messages[:i]
    
    # No AI messages found, return original list
    return messages

##########################
# Misc Utils
##########################

def get_today_str() -> str:
    """Get current date formatted for display in prompts and outputs.
    
    Returns:
        Human-readable date string in format like 'Mon Jan 15, 2024'
    """
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day}, {now:%Y}"

def get_config_value(value):
    """Extract value from configuration, handling enums and None values."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    elif isinstance(value, dict):
        return value
    else:
        return value.value

def get_api_key_for_model(model_name: str, config: RunnableConfig):
    """Get API key for a specific model from environment or config.
    
    For Bedrock models, this sets up AWS credentials from BEDROCK_* env vars and returns None
    (Bedrock uses AWS credentials instead of API keys).
    """
    should_get_from_config = os.getenv("GET_API_KEYS_FROM_CONFIG", "false")
    model_name = model_name.lower()
    
    # Bedrock models don't use API keys, they use AWS credentials
    # Set up AWS credentials from BEDROCK_* env vars if this is a Bedrock model
    if model_name.startswith("bedrock:"):
        setup_bedrock_credentials()
        return None
    
    if should_get_from_config.lower() == "true":
        api_keys = config.get("configurable", {}).get("apiKeys", {})
        if not api_keys:
            return None
        if model_name.startswith("openai:"):
            return api_keys.get("OPENAI_API_KEY")
        elif model_name.startswith("anthropic:"):
            return api_keys.get("ANTHROPIC_API_KEY")
        elif model_name.startswith("google"):
            return api_keys.get("GOOGLE_API_KEY")
        return None
    else:
        if model_name.startswith("openai:"): 
            return os.getenv("OPENAI_API_KEY")
        elif model_name.startswith("anthropic:"):
            return os.getenv("ANTHROPIC_API_KEY")
        elif model_name.startswith("google"):
            return os.getenv("GOOGLE_API_KEY")
        return None

def build_model_config(model_name: str, max_tokens: int, config: RunnableConfig, tags: Optional[List[str]] = None):
    """Build a model configuration dictionary, excluding api_key for Bedrock models.
    
    Args:
        model_name: The model identifier
        max_tokens: Maximum tokens for the model
        config: Runtime configuration
        tags: Optional list of tags to include
        
    Returns:
        Dictionary with model configuration, excluding api_key for Bedrock models
    """
    api_key = get_api_key_for_model(model_name, config)
    model_config = {
        "model": model_name,
        "max_tokens": max_tokens,
    }
    
    # Only include api_key if it's not None (i.e., not a Bedrock model)
    if api_key is not None:
        model_config["api_key"] = api_key
    
    if tags:
        model_config["tags"] = tags
    
    return model_config

def get_tavily_api_key(config: RunnableConfig):
    """Get Tavily API key from environment or config."""
    should_get_from_config = os.getenv("GET_API_KEYS_FROM_CONFIG", "false")
    if should_get_from_config.lower() == "true":
        api_keys = config.get("configurable", {}).get("apiKeys", {})
        if not api_keys:
            return None
        return api_keys.get("TAVILY_API_KEY")
    else:
        return os.getenv("TAVILY_API_KEY")
