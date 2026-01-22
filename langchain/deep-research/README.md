# 🔬 Open Deep Research

<img width="1388" height="298" alt="full_diagram" src="https://github.com/user-attachments/assets/12a2371b-8be2-4219-9b48-90503eb43c69" />

Deep research has broken out as one of the most popular agent applications.

<img width="817" height="666" alt="Screenshot 2025-07-13 at 11 21 12 PM" src="https://github.com/user-attachments/assets/052f2ed3-c664-4a4f-8ec2-074349dcaa3f" />

### 🚀 Quickstart

1. Clone the repository and activate a virtual environment:
```bash
git clone https://github.com/xuro-langchain/aws-deep-research
cd aws-deep-research
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
uv sync
# or
uv pip install -r pyproject.toml
```

3. Set up your `.env` file to customize the environment variables (for model selection, search tools, and other configuration settings):
```bash
cp .env.example .env
```

4. Launch agent with the LangGraph server locally:

```bash
# Install dependencies and start the LangGraph server
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
```

This will open the LangGraph Studio UI in your browser.

```
- 🚀 API: http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs: http://127.0.0.1:2024/docs
```

Ask a question in the `messages` input field and click `Submit`. Select different configuration in the "Manage Assistants" tab.


### ⚙️ Configurations

#### LLM :brain:

Open Deep Research supports a wide range of LLM providers via the [init_chat_model() API](https://python.langchain.com/docs/how_to/chat_models_universal_init/). It uses LLMs for a few different tasks. See the below model fields in the [configuration.py](https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/configuration.py) file for more details. This can be accessed via the LangGraph Studio UI. 

> Note: The below configuration is for the final, optimized agent. For the multiagent and parallel iterations of the agent, the specific subtasks are different. However, all versions use gpt-4.1.mini by default.

- **Summarization** (default: `openai:gpt-4.1-mini`): Summarizes search API results
- **Research** (default: `openai:gpt-4.1`): Power the search agent
- **Compression** (default: `openai:gpt-4.1`): Compresses research findings
- **Final Report Model** (default: `openai:gpt-4.1`): Write the final report

> Note: the selected model will need to support [structured outputs](https://python.langchain.com/docs/integrations/chat/) and [tool calling](https://python.langchain.com/docs/how_to/tool_calling/).

> Note: For OpenRouter: Follow [this guide](https://github.com/langchain-ai/open_deep_research/issues/75#issuecomment-2811472408) and for local models via Ollama  see [setup instructions](https://github.com/langchain-ai/open_deep_research/issues/65#issuecomment-2743586318).

#### Search API :mag:

Open Deep Research supports a wide range of search tools. By default it uses the [Tavily](https://www.tavily.com/) search API. Has full MCP compatibility and work native web search for Anthropic and OpenAI. See the `search_api` and `mcp_config` fields in the [configuration.py](https://github.com/langchain-ai/open_deep_research/blob/main/src/open_deep_research/configuration.py) file for more details. This can be accessed via the LangGraph Studio UI.

#### OpenSearch MCP Server :database:

This project supports using OpenSearch as an MCP (Model Context Protocol) server to provide web search capabilities via DuckDuckGo. To set up OpenSearch:

1. **Start OpenSearch with Docker Compose:**

   Create a `docker-compose.yml` file:
   ```yaml
   services:
     opensearch-node1:
       image: opensearchproject/opensearch:latest
       container_name: opensearch-node1
       environment:
         - cluster.name=opensearch-cluster
         - node.name=opensearch-node1
         - discovery.type=single-node
         - bootstrap.memory_lock=true
         - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
         - DISABLE_SECURITY_PLUGIN=true
       ulimits:
         memlock:
           soft: -1
           hard: -1
         nofile:
           soft: 65536
           hard: 65536
       volumes:
         - opensearch-data1:/usr/share/opensearch/data
       ports:
         - 9200:9200
       networks:
         - opensearch-net

   volumes:
     opensearch-data1:

   networks:
     opensearch-net:
   ```

2. **Start OpenSearch:**
   ```bash
   docker-compose up -d
   ```

3. **Enable the MCP Server:**
   ```bash
   curl -X PUT "http://localhost:9200/_cluster/settings" \
     -H 'Content-Type: application/json' \
     -d '{"persistent": {"plugins.ml_commons.mcp_server_enabled": "true"}}'
   ```

4. **Register the DuckDuckGo Tool:**
   ```bash
   curl -X POST "http://localhost:9200/_plugins/_ml/mcp/tools/_register" \
     -H 'Content-Type: application/json' \
     -d '{
       "tools": [
         {
           "type": "WebSearchTool",
           "name": "DuckduckgoWebSearchTool",
           "attributes": {
             "input_schema": {
               "type": "object",
               "properties": {
                 "engine": {
                   "type": "string",
                   "description": "The search engine that will be used by the tool."
                 },
                 "query": {
                   "type": "string",
                   "description": "The search query parameter that will be used by the engine to perform the search."
                 },
                 "next_page": {
                   "type": "string",
                   "description": "The search results next page link. If this is provided, the WebSearchTool will fetch the next page results using this link and crawl the links on the page."
                 }
               },
               "required": ["engine", "query"]
             },
             "strict": false
           }
         }
       ]
     }'
   ```

5. **Configure Environment Variables:**

   Add to your `.env` file:
   ```bash
   MCP_URL=http://localhost:9200
   # Optional: if security plugin is enabled
   # MCP_USERNAME=admin
   # MCP_PASSWORD=your_password
   ```

   **Note:** When `DISABLE_SECURITY_PLUGIN=true` is set in docker-compose, authentication is not required. The default configuration uses `http://localhost:9200` with `auth_required=False`.

6. **Verify Setup:**

   The agent will automatically connect to the MCP server and use the `DuckduckgoWebSearchTool` when `search_api` is set to use MCP tools.

**Important Notes:**
- The `DISABLE_SECURITY_PLUGIN=true` setting enables HTTP instead of HTTPS, which is suitable for local development only
- For production, remove `DISABLE_SECURITY_PLUGIN` and use HTTPS with proper authentication
- MCP server settings and tool registrations persist in OpenSearch volumes
- If you delete volumes, you'll need to re-enable the MCP server and re-register tools 


## Samples

Research Trace:
- Basic Question https://smith.langchain.com/public/a6d3fb4a-66ec-4683-a747-9bfbfe1a3464/r

Evaluation:
https://smith.langchain.com/public/c5e7a6ad-fdba-478c-88e6-3a388459ce8b/d


