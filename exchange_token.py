"""Exchange a GitHub Actions OIDC token for a short-lived Zalor token.

This script is called by the composite action. It reads the OIDC token from
GitHub's token endpoint (via ACTIONS_ID_TOKEN_REQUEST_URL and
ACTIONS_ID_TOKEN_REQUEST_TOKEN env vars), then POSTs it to the Zalor
/auth/github/exchange endpoint and prints the resulting token to stdout.
"""

import json
import os
import sys
import urllib.error
import urllib.request

ZALOR_ENDPOINT = os.environ.get("ZALOR_ENDPOINT", "https://agents.zalor.ai")

# Step 1: Request a GitHub OIDC JWT scoped to Zalor
request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")

if not request_url or not request_token:
    print(
        "ERROR: ACTIONS_ID_TOKEN_REQUEST_URL / ACTIONS_ID_TOKEN_REQUEST_TOKEN not set.\n"
        "Make sure the job has `permissions: id-token: write`.",
        file=sys.stderr,
    )
    sys.exit(1)

oidc_url = request_url + ("&" if "?" in request_url else "?") + "audience=zalor.ai"
req = urllib.request.Request(oidc_url, headers={"Authorization": f"bearer {request_token}"})
try:
    with urllib.request.urlopen(req) as resp:
        oidc_token = json.loads(resp.read())["value"]
except urllib.error.HTTPError as exc:
    print(f"ERROR: Failed to fetch GitHub OIDC token: {exc}", file=sys.stderr)
    sys.exit(1)

# Step 2: Exchange with Zalor
exchange_url = f"{ZALOR_ENDPOINT.rstrip('/')}/api/auth/github/exchange"
req = urllib.request.Request(
    exchange_url,
    data=b"{}",
    headers={
        "Authorization": f"Bearer {oidc_token}",
        "Content-Type": "application/json",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(result["token"])
except urllib.error.HTTPError as exc:
    body = exc.read().decode(errors="replace")
    print(f"ERROR: Zalor token exchange failed ({exc.code}): {body}", file=sys.stderr)
    sys.exit(1)
