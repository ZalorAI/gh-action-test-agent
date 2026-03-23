"""Load an agent entrypoint, run test_agent, and write run metadata to zalor_run.json.

Usage:
    python run_test.py <agent_name> <entrypoint> <api_key> [dataset]

entrypoint uses uvicorn-style module:function syntax, e.g.:
    myapp.agent:run_agent
    demo.agent_normal:run_agent

Writes zalor_run.json with {"agent_id", "run_id", "results_url"} on success.
"""

import contextlib
import importlib
import io
import json
import re
import sys


def main() -> None:
    if len(sys.argv) < 4:
        print("Usage: run_test.py <agent_name> <entrypoint> <api_key> [dataset]", file=sys.stderr)
        sys.exit(1)

    agent_name = sys.argv[1]
    entrypoint = sys.argv[2]
    api_key = sys.argv[3]
    dataset = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None

    if ":" not in entrypoint:
        print(
            f"ERROR: entrypoint '{entrypoint}' must be in 'module:function' format.",
            file=sys.stderr,
        )
        sys.exit(1)

    module_path, func_name = entrypoint.rsplit(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        print(f"ERROR: Could not import '{module_path}': {exc}", file=sys.stderr)
        sys.exit(1)

    run_agent = getattr(module, func_name, None)
    if run_agent is None:
        print(f"ERROR: '{module_path}' has no attribute '{func_name}'", file=sys.stderr)
        sys.exit(1)

    from zalor.agents import test_agent

    # Capture stdout so we can parse the results URL while still printing to the log
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        test_agent(
            agent_name=agent_name,
            api_key=api_key,
            run_agent=run_agent,
            dataset=dataset,
        )
    output = buf.getvalue()
    sys.stdout.write(output)

    # Parse "View results: https://agents.zalor.ai/agents/{agent_id}/runs/{run_id}"
    match = re.search(r"/agents/([^/\s]+)/runs/([^/\s]+)", output)
    if not match:
        print("ERROR: Could not parse results URL from test_agent output.", file=sys.stderr)
        sys.exit(1)

    agent_id, run_id = match.group(1), match.group(2)
    results_url = match.group(0)
    # Reconstruct full URL from the output line
    url_match = re.search(r"https?://\S+/agents/[^/\s]+/runs/[^/\s]+", output)
    results_url = url_match.group(0) if url_match else results_url

    with open("zalor_run.json", "w") as f:
        json.dump({"agent_id": agent_id, "run_id": run_id, "results_url": results_url}, f)


if __name__ == "__main__":
    main()
