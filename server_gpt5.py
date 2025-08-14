#!/usr/bin/env python3
"""
Zen MCP Server - GPT-5 + Claude Edition

A streamlined MCP server that provides GPT-5 capabilities to Claude Desktop.
This version focuses exclusively on OpenAI integration for GPT-5 access.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

import click
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import __author__, __updated__, __version__
from providers.base import ProviderType
from providers.openai_provider import OpenAIModelProvider
from providers.registry import ModelProviderRegistry
from utils.file_utils import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging(__name__)

# ----------------------------------------------------------------------------
# Server Configuration
# ----------------------------------------------------------------------------

# Create MCP server instance
mcp_server = Server("zen-mcp-gpt5")

# Tool registry
AVAILABLE_TOOLS = {}

# ----------------------------------------------------------------------------
# Provider Setup (OpenAI Only)
# ----------------------------------------------------------------------------

def setup_openai_provider():
    """Setup OpenAI provider for GPT-5 access."""
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key or openai_key == "your_openai_api_key_here":
        logger.warning("OpenAI API key not configured")
        logger.warning("Please set OPENAI_API_KEY in your .env file")
        return False
    
    try:
        # Register OpenAI provider
        ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
        logger.info("✓ OpenAI provider registered (GPT-5 ready)")
        
        # Verify GPT-5 availability
        provider = ModelProviderRegistry.get_provider(ProviderType.OPENAI)
        if provider:
            models = provider.get_supported_models()
            gpt5_models = [m for m in models if "gpt-5" in m.lower()]
            if gpt5_models:
                logger.info(f"✓ GPT-5 models available: {', '.join(gpt5_models)}")
            else:
                logger.warning("GPT-5 models not found - using GPT-4 models")
        
        return True
    except Exception as e:
        logger.error(f"Failed to setup OpenAI provider: {e}")
        return False

# ----------------------------------------------------------------------------
# Tool Registration
# ----------------------------------------------------------------------------

def register_core_tools():
    """Register essential tools for GPT-5 workflows."""
    from tools import (
        AnalyzeTool,
        ChatTool,
        CodeReviewTool,
        ConsensusTool,
        DebugTool,
        DocgenTool,
        PlannerTool,
        PrecommitTool,
        RefactorTool,
        SecauditTool,
        TestGenTool,
        ThinkDeepTool,
        TracerTool,
    )
    
    # Core tools for GPT-5 workflows
    tool_classes = [
        ChatTool,           # General collaborative thinking
        ThinkDeepTool,      # Extended reasoning with GPT-5
        DebugTool,          # Debugging with reasoning
        CodeReviewTool,     # Code review workflows
        AnalyzeTool,        # Code analysis
        RefactorTool,       # Refactoring with GPT-5
        PlannerTool,        # Planning complex tasks
        PrecommitTool,      # Pre-commit validation
        TestGenTool,        # Test generation
        SecauditTool,       # Security audits
        DocgenTool,         # Documentation generation
        TracerTool,         # Code tracing
        ConsensusTool,      # Multi-perspective analysis
    ]
    
    for tool_class in tool_classes:
        try:
            tool = tool_class()
            tool_name = tool.get_name()
            AVAILABLE_TOOLS[tool_name] = tool
            logger.debug(f"Registered tool: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to register {tool_class.__name__}: {e}")
    
    logger.info(f"✓ Registered {len(AVAILABLE_TOOLS)} tools")

# ----------------------------------------------------------------------------
# MCP Server Setup
# ----------------------------------------------------------------------------

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools for Claude."""
    tools = []
    
    for name, tool in AVAILABLE_TOOLS.items():
        try:
            tools.append(Tool(
                name=name,
                description=tool.get_description(),
                inputSchema=tool.get_input_schema()
            ))
        except Exception as e:
            logger.error(f"Error listing tool {name}: {e}")
    
    return tools

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list:
    """Execute a tool with the given arguments."""
    if name not in AVAILABLE_TOOLS:
        logger.error(f"Tool not found: {name}")
        return [{
            "type": "text",
            "text": f"Error: Tool '{name}' not found. Available tools: {', '.join(AVAILABLE_TOOLS.keys())}"
        }]
    
    tool = AVAILABLE_TOOLS[name]
    
    try:
        # Log tool execution
        logger.info(f"Executing tool: {name}")
        logger.debug(f"Arguments: {arguments}")
        
        # Execute tool
        result = await tool.execute(arguments)
        
        logger.info(f"Tool {name} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [{
            "type": "text",
            "text": f"Error executing {name}: {str(e)}"
        }]

# ----------------------------------------------------------------------------
# Startup and Shutdown
# ----------------------------------------------------------------------------

async def startup():
    """Initialize server on startup."""
    logger.info("=" * 60)
    logger.info(f" Zen MCP Server - GPT-5 Edition v{__version__}")
    logger.info(f" Updated: {__updated__} | Author: {__author__}")
    logger.info("=" * 60)
    
    # Setup OpenAI provider
    if not setup_openai_provider():
        logger.error("Failed to setup OpenAI provider")
        logger.error("Server will run with limited functionality")
    
    # Register tools
    register_core_tools()
    
    # Show configuration
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  • Default Model: {os.getenv('DEFAULT_MODEL', 'gpt-5')}")
    logger.info(f"  • GPT-5 Enabled: {os.getenv('ENABLE_GPT5', 'true')}")
    logger.info(f"  • Thinking Mode: {os.getenv('GPT5_DEFAULT_THINKING_MODE', 'medium')}")
    logger.info(f"  • Max Reasoning: {os.getenv('GPT5_MAX_REASONING_TOKENS', '12000')} tokens")
    logger.info("")
    logger.info("Server ready for Claude Desktop connection")
    logger.info("=" * 60)

async def shutdown():
    """Cleanup on server shutdown."""
    logger.info("Shutting down Zen MCP Server...")
    
    # Cleanup providers
    try:
        registry = ModelProviderRegistry()
        if hasattr(registry, "_initialized_providers"):
            for provider in list(registry._initialized_providers.values()):
                if hasattr(provider, "cleanup"):
                    await provider.cleanup()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    logger.info("Server shutdown complete")

# ----------------------------------------------------------------------------
# Main Entry Point
# ----------------------------------------------------------------------------

@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool):
    """Run the Zen MCP Server for GPT-5 integration."""
    
    # Set log level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run server
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

async def serve():
    """Run the MCP server."""
    # Setup handlers
    mcp_server._startup_handler = startup
    mcp_server._shutdown_handler = shutdown
    
    # Run with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    main()