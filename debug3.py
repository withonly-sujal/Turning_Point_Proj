import asyncio
import json
import os
from dotenv import load_dotenv
load_dotenv()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

env = {
    **os.environ,
    "SOLACE_API_TOKEN": os.getenv("SOLACE_API_TOKEN", ""),
    "SOLACE_API_BASE_URL": os.getenv("SOLACE_API_BASE_URL", "https://api.solace.cloud"),
}
params = StdioServerParameters(
    command="uvx",
    args=["-q", "--from", "solace-event-portal-designer-mcp", "solace-ep-designer-mcp"],
    env=env,
)

async def test():
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            result = await s.list_tools()
            for t in result.tools:
                if t.name == "getApplicationVersions":
                    print(json.dumps(t.input_schema, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
