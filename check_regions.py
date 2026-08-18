import os
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("SOLACE_API_TOKEN")

if not token or token == "your_token_here":
    print("Token not found in .env")
    exit(1)

regions = {
    "US": "https://api.solace.cloud",
    "AU": "https://api.solacecloud.com.au",
    "EU": "https://api.solacecloud.eu",
    "SG": "https://api.solacecloud.sg"
}

print("Checking all Solace Cloud regions for your Application Domains...\n")

found_data = False

for name, base_url in regions.items():
    url = f"{base_url}/api/v2/architecture/applicationDomains"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8')).get("data", [])
                print(f"[{name}] {base_url} -> Returned {len(data)} domains")
                if len(data) > 0:
                    print(f"    Domain names: {[d.get('name') for d in data]}")
                    found_data = True
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"[{name}] {base_url} -> 401 Unauthorized (Token invalid for this region)")
        else:
            print(f"[{name}] {base_url} -> Error {e.code}")
    except Exception as e:
        print(f"[{name}] Error connecting: {e}")

if not found_data:
    print("\nCould not find the domains in any standard region.")
    print("Please double check that the API token you generated belongs to the same Solace account shown in your screenshot.")
