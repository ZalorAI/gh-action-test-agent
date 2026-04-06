# Zalor Agent Test - GitHub Action

Automatically test your AI agent on every pull request. Get a score, compare it to your baseline, and see a comment directly in your PR - with zero secrets required.

## How it works

1. A PR triggers the action
2. Your agent is run against a dataset on the Zalor platform
3. Results are compared to the current baseline (the last merged run)
4. A comment is posted on the PR showing the score delta
5. When the PR merges, that run becomes the new baseline

```
PR opened / updated
      |
      v
Exchange GitHub OIDC token -> Zalor token   (no secrets needed)
      |
      v
Load your agent (module:function) -> run against dataset
      |
      v
Poll for evaluation scores
      |
      v
Post PR comment with score vs. baseline
      |
      v  (on merge to baseline_branch)
Promote run as new baseline
```

## Setup

### 1. Add the workflow file

Create `.github/workflows/zalor-test.yml` in your repo:

```yaml
name: Zalor Agent Test

on:
  pull_request:
    types: [opened, synchronize, reopened, closed]

permissions:
  id-token: write     # required - lets the action get an OIDC token
  contents: read
  pull-requests: write  # required - lets the action post PR comments

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: zalor-ai/zalor-agent-test@main
        with:
          agent_name: my-agent          # name shown in the Zalor dashboard
          entrypoint: myapp.agent:run   # module:function pointing to your agent
          dataset: my-dataset           # optional - omit to let Zalor generate inputs
```

### 2. Make sure your agent is importable

The action sets `PYTHONPATH` to the root of your repo. Your entrypoint must be a Python callable in `module:function` format:

```
myapp.agent:run
^^^^^^^^^^^^^  ^^^
  module path  function name
```

For example, if your agent lives at `myapp/agent.py` with a `run` function:

```python
# myapp/agent.py

def run(input: str) -> str:
    # your agent logic here
    return response
```

Then your entrypoint is `myapp.agent:run`.

### 3. Install your dependencies (optional)

If your agent has dependencies, add a `requirements.txt` to the root of your repo. The action installs it automatically before running your agent.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `agent_name` | Yes | - | Name used to identify your agent in the Zalor dashboard |
| `entrypoint` | Yes | - | Agent callable in `module:function` format |
| `dataset` | No | `""` | Dataset to test against; Zalor generates inputs if omitted |
| `baseline_branch` | No | `main` | Branch whose runs are promoted to baseline on merge |

## PR comment

Every PR gets an automatically updated comment showing how your agent is performing:

| | Score | Pass/Total |
|---|---|---|
| This PR | **87.5%** | 7/8 |
| Baseline | 75.0% | 6/8 |
| Delta | +12.5% | |

## Authentication

This action uses **GitHub OIDC** - no API keys or secrets need to be stored in your repo. The action requests a short-lived token from GitHub and exchanges it for a temporary Zalor token at runtime. This requires `permissions: id-token: write` in your workflow (shown in the example above).

## Files in this repo

| File | What it does |
|---|---|
| `action.yml` | Action definition and step orchestration |
| `exchange_token.py` | Exchanges GitHub OIDC JWT for a Zalor API token |
| `run_test.py` | Loads your agent dynamically and runs it via the Zalor SDK |
| `report.py` | Polls for eval scores, compares to baseline, writes the PR comment body |
| `promote_baseline.py` | Marks the merged run as the new baseline |
