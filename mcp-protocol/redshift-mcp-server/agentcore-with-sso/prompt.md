we want to build an mcp server using python and FastMCP for executing queries on redshift database. redshift database is configured for federated authentication using aws identity center in aws mumbai region. 

we plan to host this on Bedrock Agentcore runtime. Flow will be as below:

MCP client -> MCP server running in AgentCore Runtime -> Redshift database


Users of this MCP server is expected to have aws cli installed on the laptops running mcp client. For authentication, user will run `aws login` on their laptop and then key in their credentials on AWS SSO console.

Once user is authenticated, AgentCore runtime to use the auth tokens to authenticate with redshift.

Rules:
- We do not want to store any credentials on the MCP client.
- MCP server should run with standard MCP clients like kiro, claude code, claude desktop etc.
- do not create a custom mcp client
- first we will finalize the design then generate code


Task: Validate above authentication process against AgentCore documentation and suggest if any changes required. ask me questions for any clarification

