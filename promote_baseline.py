"""Promote the current run as the baseline for its agent.

Usage:
    python promote_baseline.py <api_key> <endpoint>

Reads zalor_run.json (written by run_test.py).
"""

import json
import sys
import urllib.error
import urllib.request


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: promote_baseline.py <api_key> <endpoint>", file=sys.stderr)
        sys.exit(1)

    api_key = sys.argv[1]
    endpoint = sys.argv[2].rstrip("/")

    try:
        with open("zalor_run.json") as f:
            run_meta = json.load(f)
    except FileNotFoundError:
        print("ERROR: zalor_run.json not found - did run_test.py succeed?", file=sys.stderr)
        sys.exit(1)

    agent_id = run_meta["agent_id"]
    run_id = run_meta["run_id"]

    url = f"{endpoint}/api/v1/agents/{agent_id}/runs/{run_id}/baseline"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"✅ Run {run_id} promoted as baseline for agent {agent_id}")
            return result
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"ERROR: Baseline promotion failed ({exc.code}): {body}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
