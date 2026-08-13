"""
"Development script to trigger Jira webhooks."
"Bypasses Windows terminal escaping issues for clean JSON delivery."
"""
import json
import urllib.request

url = "http://localhost:8000/api/v1/webhooks/jira"
payload = {
    "ticket_id": "SEC-9950",
    "user_email": "employee@company.com",
    "alert_type": "impossible_travel"
}

# Encode payload to bytes for the HTTP request
data = json.dumps(payload).encode("utf-8")
headers = {"Content-Type": "application/json"}

request = urllib.request.Request(url, data=data, headers=headers)

try:
    with urllib.request.urlopen(request) as response:
        print(f"Success! Status Code: {response.getcode()}")
        print(f"Response Body: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as error:
    print(f"Failed! Status Code: {error.code}")
    print(f"Error Body: {error.read().decode('utf-8')}")