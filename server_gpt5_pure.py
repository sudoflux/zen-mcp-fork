#!/usr/bin/env python3
"""
Pure GPT-5 + Claude MCP Server

Tailored exclusively for GPT-5 API access with Claude Desktop.
No fallbacks, no compatibility - just optimized GPT-5 workflows.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config_gpt5 import __author__, __updated__, __version__, GPT5_CONFIG
from providers.base import ProviderType
from providers.openai_provider import OpenAIModelProvider
from providers.registry import ModelProviderRegistry
# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create MCP server instance
mcp_server = Server("gpt5-claude")

# Tool registry
AVAILABLE_TOOLS = {}

# ----------------------------------------------------------------------------
# GPT-5 Only Provider Setup
# ----------------------------------------------------------------------------

def setup_gpt5_provider():
    """Setup OpenAI provider configured for GPT-5 only."""
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key or openai_key == "your_openai_api_key_here":
        logger.error("OpenAI API key not configured")
        logger.error("Please set OPENAI_API_KEY in your .env file")
        sys.exit(1)
    
    try:
        # Register OpenAI provider
        ModelProviderRegistry.register_provider(ProviderType.OPENAI, OpenAIModelProvider)
        
        # Test GPT-5 access
        provider = ModelProviderRegistry.get_provider(ProviderType.OPENAI)
        if provider:
            # Quick test call to verify GPT-5 access
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-5",
                messages=[{"role": "user", "content": "Hello"}],
                max_completion_tokens=5
            )
            logger.info("✓ GPT-5 provider verified and ready")
            logger.info(f"✓ GPT-5 context: {GPT5_CONFIG['context_window']:,} tokens")
            logger.info(f"✓ GPT-5 output: {GPT5_CONFIG['output_limit']:,} tokens")
            logger.info(f"✓ Reasoning tokens: {GPT5_CONFIG['max_reasoning_tokens']:,}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to setup GPT-5 provider: {e}")
        logger.error("Ensure you have GPT-5 API access")
        sys.exit(1)

# ----------------------------------------------------------------------------
# Tool Registration
# ----------------------------------------------------------------------------

def register_gpt5_tools():
    """Register tools optimized for GPT-5 workflows."""
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
    
    # All tools configured for GPT-5
    tool_classes = [
        ChatTool,           # GPT-5 collaborative thinking
        ThinkDeepTool,      # Extended reasoning (12K tokens)
        DebugTool,          # Advanced debugging
        CodeReviewTool,     # Deep code review
        AnalyzeTool,        # Full codebase analysis
        RefactorTool,       # Intelligent refactoring
        PlannerTool,        # Complex project planning
        PrecommitTool,      # Pre-commit validation
        TestGenTool,        # Comprehensive test generation
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
            logger.debug(f"Registered GPT-5 tool: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to register {tool_class.__name__}: {e}")
    
    logger.info(f"✓ Registered {len(AVAILABLE_TOOLS)} GPT-5 optimized tools")

# ----------------------------------------------------------------------------
# MCP Server Implementation
# ----------------------------------------------------------------------------

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all GPT-5 optimized tools for Claude."""
    tools = []
    
    for name, tool in AVAILABLE_TOOLS.items():
        try:
            tools.append(Tool(
                name=name,
                description=f"[GPT-5] {tool.get_description()}",
                inputSchema=tool.get_input_schema()
            ))
        except Exception as e:
            logger.error(f"Error listing tool {name}: {e}")
    
    return tools

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list:
    """Execute a GPT-5 optimized tool."""
    if name not in AVAILABLE_TOOLS:
        logger.error(f"Tool not found: {name}")
        return [{
            "type": "text",
            "text": f"Error: Tool '{name}' not found. Available tools: {', '.join(AVAILABLE_TOOLS.keys())}"
        }]
    
    tool = AVAILABLE_TOOLS[name]
    
    try:
        # Force GPT-5 model if not specified
        if "model" not in arguments or arguments["model"] == "auto":
            arguments["model"] = "gpt-5"
        
        # Add GPT-5 specific optimizations
        if arguments["model"] == "gpt-5":
            # Add reasoning tokens for complex tasks
            if name in ["debug", "codereview", "analyze", "planner"]:
                if "thinking_mode" not in arguments:
                    arguments["thinking_mode"] = "high"
        
        logger.info(f"Executing GPT-5 tool: {name}")
        logger.debug(f"Model: {arguments.get('model', 'gpt-5')}")
        
        result = await tool.execute(arguments)
        
        logger.info(f"GPT-5 tool {name} completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error executing GPT-5 tool {name}: {e}", exc_info=True)
        return [{
            "type": "text",
            "text": f"Error executing {name}: {str(e)}"
        }]

# ----------------------------------------------------------------------------
# Server Lifecycle
# ----------------------------------------------------------------------------

async def startup():
    """Initialize GPT-5 server on startup."""
    logger.info("=" * 60)
    logger.info(f" GPT-5 + Claude MCP Server v{__version__}")
    logger.info(f" Optimized for GPT-5 API access")
    logger.info(f" Updated: {__updated__} | Author: {__author__}")
    logger.info("=" * 60)
    
    # Setup GPT-5 provider
    setup_gpt5_provider()
    
    # Register tools
    register_gpt5_tools()
    
    # Show GPT-5 configuration
    logger.info("")
    logger.info("GPT-5 Configuration:")
    logger.info(f"  • Context Window: {GPT5_CONFIG['context_window']:,} tokens")
    logger.info(f"  • Output Limit: {GPT5_CONFIG['output_limit']:,} tokens") 
    logger.info(f"  • Reasoning Tokens: {GPT5_CONFIG['max_reasoning_tokens']:,}")
    logger.info(f"  • Thinking Mode: {GPT5_CONFIG['default_thinking_mode']}")
    logger.info(f"  • File Strategy: {GPT5_CONFIG['file_strategy']}")
    logger.info("")
    logger.info("Ready for Claude Desktop connection")
    logger.info("=" * 60)

async def shutdown():
    """Cleanup on server shutdown."""
    logger.info("Shutting down GPT-5 MCP Server...")
    
    try:
        registry = ModelProviderRegistry()
        if hasattr(registry, "_initialized_providers"):
            for provider in list(registry._initialized_providers.values()):
                if hasattr(provider, "cleanup"):
                    await provider.cleanup()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    logger.info("GPT-5 server shutdown complete")

# ----------------------------------------------------------------------------
# Main Entry Point
# ----------------------------------------------------------------------------

@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool):
    """Run the GPT-5 + Claude MCP Server."""
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("\nGPT-5 server stopped by user")
    except Exception as e:
        logger.error(f"GPT-5 server error: {e}", exc_info=True)
        sys.exit(1)

async def serve():
    """Run the GPT-5 MCP server."""
    mcp_server._startup_handler = startup
    mcp_server._shutdown_handler = shutdown
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    main()