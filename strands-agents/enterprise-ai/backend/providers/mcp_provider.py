from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from utils.utility import Utility
from mcp import stdio_client, StdioServerParameters
from config import Config

MCP_JSON_FILE   = 'mcp.json'



class MCPProvider:
    # convert this class to a singleton class 
    _instance = None
    
    

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MCPProvider, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.mcp_servers = {}
            self.util = Utility()
            self.config = Config()
            

    
    def load_mcp_servers(self):
        
        mcp_json = Utility().load_mcp_json(MCP_JSON_FILE)
        mcp_servers = mcp_json.get("mcpServers", {})
        
        for server_name, server_config in mcp_servers.items():
            client = MCPClient(lambda: stdio_client(
                                StdioServerParameters(
                                    command = server_config.get("command"),
                                    args = server_config.get("args", []),
                                    env = server_config.get("env", {}))))

            client.start()
            mcp_tools = client.list_tools_sync()
            self.mcp_servers[server_name]= {
                    "mcp_client_object": client,
                    "mcp_tools": mcp_tools
                    }
            
        return True
            
    
    def get_tools(self):
        
        mcp_tools = []

        # todo - is there a better way to get list of buit-in tools?
        mcp_tools.append({
                "type": "Built-in Tools", 
                "tools": ["generate_sql_statement", "generate_response"]
                })

        self.util.log_data(self.mcp_servers)
        for mcp_server, server_config in self.mcp_servers.items():
            tool_names = []
            for t in server_config.get('mcp_tools'):
                tool_names.append(t.tool_name)
            mcp_tools.append({"type": f'{mcp_server} (MCP)', "tools": tool_names})

        return mcp_tools
    

    def get_tools_for_mcp_server(self, mcp_server_name: str):
        for mcp_server, server_config in self.mcp_servers.items():
            if (mcp_server == mcp_server_name):
                return server_config.get('mcp_tools')
        return None
    
    def get_mcp_servers(self):
        return self.mcp_servers    
        


