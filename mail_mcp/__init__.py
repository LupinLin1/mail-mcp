"""
Mail MCP Server - A simple MCP server for email operations
"""

__version__ = "2.1.0"
__author__ = "Mail MCP Team"

from .setup import MailMCPSetup
from .config_tool import MailMCPConfigTool

__all__ = ['MailMCPSetup', 'MailMCPConfigTool']
