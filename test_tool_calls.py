import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Force UTF-8 output on Windows terminal to avoid display errors
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

async def main():
    # Load credentials from .env
    load_dotenv()
    
    token = os.getenv("SOLACE_API_TOKEN")
    base_url = os.getenv("SOLACE_API_BASE_URL", "https://api.solace.cloud")

    if not token or token == "your_token_here":
        print("[ERROR] SOLACE_API_TOKEN is not set in your .env file.")
        sys.exit(1)

    print("[OK] Token loaded successfully.")

    # Prepare environment variables for the MCP server
    env = {**os.environ, "SOLACE_API_TOKEN": token, "SOLACE_API_BASE_URL": base_url}

    # Configure the server parameters just like we did with subprocess in test_list_tools.py
    server_params = StdioServerParameters(
        command="uvx",
        args=[
            "--from", 
            "solace-event-portal-designer-mcp", 
            "solace-ep-designer-mcp"
        ],
        env=env
    )

    print("[...] Starting MCP server and calling getApplicationDomains...")

    try:
        # stdio_client handles spawning the process and managing the pipes
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                
                # Must initialize the session first
                await session.initialize()
                print("[OK] Connected to Solace MCP Server")

                # Call the specific tool
                result = await session.call_tool(
                    "getApplicationDomains",
                    {}
                )

                print("\n[OK] Tool executed successfully")
                print("\n========== SOLACE RESPONSE ==========")
                
                # The result contains a list of content objects
                for content in result.content:
                    if content.type == "text":
                        print(content.text)
                        
                print("=====================================")
                
    except Exception as e:
        print(f"[ERROR] MCP Communication failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())