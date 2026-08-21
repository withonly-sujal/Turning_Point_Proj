import asyncio
import json
from EventFlow_AI import mcp_client as mcp

async def test():
    async with mcp.managed_session() as s:
        print("--- SEARCH ---")
        res1 = await mcp._search_entity(s, 'application', 'FraudDetectionService')
        print(json.dumps(res1, indent=2))
        
        # We need to see what ID it returns. Let's assume 'ccc0kyv6wi8' based on previous logs
        # or grab it dynamically if found
        app_id = 'ccc0kyv6wi8'
        if res1.get('result'):
            for app in res1['result']:
                if app.get('name') == 'FraudDetectionService':
                    app_id = app.get('id')
                    print(f"Found ID: {app_id}")
                    break
                    
        print("\n--- PRODUCED EVENTS ---")
        res2 = await mcp._get_relationships(s, app_id, 'produced_events')
        print(json.dumps(res2, indent=2))
        
        print("\n--- CONSUMED EVENTS ---")
        res3 = await mcp._get_relationships(s, app_id, 'consumed_events')
        print(json.dumps(res3, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
