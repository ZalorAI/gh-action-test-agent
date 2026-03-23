"""Fetch eval scores for the current run and the baseline, then write a PR comment.

Usage:
    python report.py <api_key> <endpoint> <agent_name>

Reads zalor_run.json (written by run_test.py).
Writes zalor_report.md with the formatted PR comment body.

Polls /v1/agents/{agent_id}/runs/{run_id}/score until pending_count == 0
or until POLL_TIMEOUT_SECONDS is exceeded.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

POLL_TIMEOUT_SECONDS = int(os.environ.get("ZALOR_POLL_TIMEOUT", "120"))
POLL_INTERVAL_SECONDS = 10
ZALOR_LOGO_URL = "https://agents.zalor.ai/logo-sm.png"


def _get(url: str, api_key: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _pct(pass_count: int, total: int) -> str:
    if total == 0:
        return "—"
    return f"{round(pass_count / total * 100)}%"


def _score_line(score: dict) -> tuple[str, str, str]:
    """Return (pct_str, fraction_str, pending_str)."""
    total = score["simulation_count"]
    passed = score["pass_count"]
    pending = score["pending_count"]
    pct = _pct(passed, total)
    fraction = f"{passed}/{total}"
    pending_str = f" *(+{pending} pending)*" if pending else ""
    return pct, fraction, pending_str


def _delta_emoji(pr_pct: int | None, base_pct: int | None) -> str:
    if pr_pct is None or base_pct is None:
        return ""
    diff = pr_pct - base_pct
    if diff > 0:
        return f"✅ +{diff}%"
    if diff < 0:
        return f"⚠️ {diff}%"
    return "➡️ 0%"


def main() -> None:
    if len(sys.argv) < 4:
        print("Usage: report.py <api_key> <endpoint> <agent_name>", file=sys.stderr)
        sys.exit(1)

    api_key = sys.argv[1]
    endpoint = sys.argv[2].rstrip("/")
    agent_name = sys.argv[3]

    try:
        with open("zalor_run.json") as f:
            run_meta = json.load(f)
    except FileNotFoundError:
        print("ERROR: zalor_run.json not found — did run_test.py succeed?", file=sys.stderr)
        sys.exit(1)

    agent_id = run_meta["agent_id"]
    run_id = run_meta["run_id"]
    results_url = run_meta["results_url"]

    score_url = f"{endpoint}/v1/agents/{agent_id}/runs/{run_id}/score"
    baseline_url = f"{endpoint}/v1/agents/{agent_id}/baseline/score"

    # Poll until evals complete or timeout
    print(f"Waiting for eval scores (up to {POLL_TIMEOUT_SECONDS}s)...")
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    score = {}
    while True:
        try:
            score = _get(score_url, api_key)
        except urllib.error.HTTPError as exc:
            print(f"WARNING: Score fetch failed ({exc.code}), retrying...", file=sys.stderr)
            score = {}

        pending = score.get("pending_count", 1)
        if pending == 0:
            break
        if time.monotonic() >= deadline:
            print(
                f"WARNING: Timed out waiting for evals. "
                f"{pending} simulation(s) still pending — showing partial results.",
                file=sys.stderr,
            )
            break
        print(f"  {pending} eval(s) pending, checking again in {POLL_INTERVAL_SECONDS}s...")
        time.sleep(POLL_INTERVAL_SECONDS)

    # Fetch baseline (may not exist yet)
    baseline: dict = {}
    try:
        baseline = _get(baseline_url, api_key)
    except urllib.error.HTTPError:
        pass  # No baseline set yet

    # Build PR comment
    has_baseline = bool(baseline.get("run_id"))

    pr_pct_raw = None
    base_pct_raw = None
    if score.get("simulation_count"):
        pr_pct_raw = round(score["pass_count"] / score["simulation_count"] * 100)
    if has_baseline and baseline.get("simulation_count"):
        base_pct_raw = round(baseline["pass_count"] / baseline["simulation_count"] * 100)

    pr_pct, pr_fraction, pr_pending = _score_line(score) if score else ("—", "—", "")

    lines = [
        f'<img src="{ZALOR_LOGO_URL}" height="20" alt="Zalor"> &nbsp;**Zalor Agent Test — {agent_name}**',
        "",
        "| | Score | Pass/Total |",
        "|---|---|---|",
    ]

    if has_baseline:
        base_pct, base_fraction, _ = _score_line(baseline)
        delta = _delta_emoji(pr_pct_raw, base_pct_raw)
        lines += [
            f"| 🔀 This PR | **{pr_pct}**{pr_pending} | {pr_fraction} |",
            f"| 🌿 Baseline | {base_pct} | {base_fraction} |",
            f"| Δ | {delta} | |",
        ]
    else:
        lines += [
            f"| 🔀 This PR | **{pr_pct}**{pr_pending} | {pr_fraction} |",
            f"| 🌿 Baseline | *none set yet* | |",
        ]

    lines += [
        "",
        f"[View full results →]({results_url})",
    ]

    body = "\n".join(lines)

    with open("zalor_report.md", "w") as f:
        f.write(body)

    print(body)


if __name__ == "__main__":
    main()
