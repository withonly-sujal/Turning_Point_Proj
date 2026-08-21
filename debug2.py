import asyncio
import json
from EventFlow_AI import mcp_client as mcp

async def test():
    async with mcp.managed_session() as s:
        versions = await mcp._call_mcp(s, 'getApplicationVersions', {'applicationId': 'ccc0kyv6wi8'})
        print(json.dumps(versions, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
