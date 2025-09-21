"""
MCP Server entry point for mail_mcp package
"""

from .main import MailMCPServer
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create global MCP server instance
mcp = MailMCPServer()

# Setup services and register tools
try:
    mcp.setup_services()
    mcp.register_tools()
    logger.info("Mail MCP Server initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Mail MCP Server: {e}")
    raise

# Export the mcp instance for FastMCP compatibility
__all__ = ['mcp']

# Run server if executed directly
async def run_server(host="localhost", port=8000):
    """Run the MCP server"""
    await mcp.mcp.run(host=host, port=port)

async def run_stdio():
    """Run the MCP server in stdio mode"""
    await mcp.mcp.run(transport="stdio")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stdio":
        asyncio.run(run_stdio())
    else:
        asyncio.run(run_server())