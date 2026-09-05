# Acceptance — step 1, foundation (crew#729)

From the decision record: "`pytest tests/test_no_deploy_hands.py` proves no merge, deploy or
cluster tool exists; a seeded issue produces a pull request and a plan comment; the trace is
returned by a Langfuse query printed in the run log."

| Row | Command or place | Green when |
|---|---|---|
| No hands | `pytest tests/test_no_deploy_hands.py` | passes in CI on `main` |
| Boots only when seen | `pytest tests/test_boot_refuses_dark.py`; the `image` job runs the container dark | exit 3, `REFUSED:` line |
| Seeded issue | the workload runs `agent-workforce <number>` against a ticket in any queued lane | a comment ending `Optimised:` and a pull request from `agent-workforce/<number>` exist on the board |
| Trace proved from the backend | the last line of the run log | `langfuse traces for session agent-workforce-<number>-<id>: N` with N > 0; exit 0 |

The seeded-issue and trace rows need the workload from step 3 (the founder deploys it). Until
then they are `Not done:` on the handoff, and this file says so.

## Deviations from the record, each one clause

- Identity is a lane on the estate's one GitHub App, not a second App (one platform, one
  identity layer; see the `idp` runbook `docs/runbooks/agent-workforce-identity.md`).
- Long-term memory is crewAI's own store on the workload's volume, not the cluster Postgres:
  crewAI 1.9.3 ships no Postgres store, and writing one would be new code for a problem the
  volume already solves.
