# agent-workforce

A brand-new platform crew on [crewAI](https://docs.crewai.com) 1.9.3. It takes one board ticket
to a green pull request and stops. The founder merges and deploys. It has no merge, deploy,
workflow-dispatch, secret, admin or cluster hand, and `tests/test_no_deploy_hands.py` proves that
on every push.

Decision record: `crew/docs/plans/2026-09-01-brand-new-agent-workforce-on-crewai.md` (crew#729).

## What it is

| Element | Choice |
|---|---|
| Runtime | crewAI 1.9.3, Python 3.11, one container, runs as a cluster workload |
| Brain | any model, only through the estate router (`LITELLM_BASE_URL`); the alias picks the lane, the router picks the vendor |
| Identity | an installation token for the `agent-workforce` lane of the estate's one GitHub App: read, write on `agent-workforce/*` branches, open pull requests, comment, read Actions logs |
| Laws | crewAI Knowledge over the law and standards files, embedded through the router |
| Memory | crewAI long-term memory on the workload's volume (`AGENT_WORKFORCE_STORAGE_DIR`) |
| Traces | OpenTelemetry to the estate collector and to Langfuse; the run ends by querying Langfuse and printing the count |
| Verifier | a separate agent on a separate model lane grades the builder's pull request; also a task guardrail |
| Kill switches | suspend the App installation; the `agents_enabled` toggle (crew#767); the replica count in git |

## Roles

manager (hierarchical process) · planner · builder · verifier · watcher.

## Running it

The crew is a workload; nobody runs it by hand. Its manifest sets every value in
`src/agent_workforce/estate.py` and starts it with one argument, the board issue number:

    agent-workforce 812

A missing value ends the run at once with `REFUSED: <what is missing>` and exit code 3.

## Proving it

    pytest tests/test_no_deploy_hands.py        # no merge, deploy or cluster hand exists
    pytest tests/test_boot_refuses_dark.py      # refuses to boot without router, traces, laws or credential
    pytest tests/test_config_no_literals.py     # no host, path, account or key literal in any shipped file

The acceptance for step 1 of the decision record is in `docs/ACCEPTANCE.md`.
