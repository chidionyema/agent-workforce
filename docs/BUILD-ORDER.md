# Build order — the agent workforce, checkpoints 1 to 6

This is the executable brief for the build lane. Every checkpoint has its own ticket on
`chidionyema/crew` with the full specification; this file says **what order they go in, what is
true for all of them, and how each one is accepted**. Read this file, then read the ticket, then
build. Do not start a checkpoint whose predecessor is not merged.

Parent ticket: `chidionyema/crew#850`.

## The order, and why it is this order

| # | Ticket | Builds | Depends on |
|---|---|---|---|
| 1 | crew#854 | CrewAI 1.9.3 → 1.15.20 | nothing |
| 2 | crew#856 | the run becomes a `Flow` with persisted state | crew#854 |
| 3 | crew#851 | estate MCP tools replace the hand-written client | crew#854 |
| 4 | crew#852 | the authority boundary becomes an enforced tool hook | crew#854 |
| 5 | crew#853 | one scoped memory per department | crew#854 |
| 6 | crew#855 | departments become data, not Python | crew#856, crew#853 |

**The upgrade is first and it is not negotiable.** `pyproject.toml` pins `crewai==1.9.3`. Every
other checkpoint uses a surface that does not exist in 1.9.3: `@persist` and `CheckpointConfig`
(CP1), `MCPServerAdapter` with `streamable-http` (CP2), `@on(InterceptionPoint.PRE_TOOL_CALL)`
and `HookAborted` (CP3), and the unified `Memory` class (CP4). Starting anywhere else means
writing code against an API the installed library does not have.

**Checkpoints 3, 4 and 5 in the table are independent of each other.** Once the upgrade is
merged they may be built in any order, or at the same time on separate branches. Checkpoint 6 is
last because it turns what the earlier ones built into data.

## What is true for every checkpoint

- **One branch, one pull request, one checkpoint.** Branch name `cp<N>/<short-slug>`, for example
  `cp1/crewai-1-15-20`. The pull request body names its crew ticket in the first line.
- **Turn auto-merge on when you open it.** `gh pr merge --auto --squash --delete-branch`.
- **Ubuntu CI is the only verification road.** This work cannot be run on the founder's Mac: it
  is Intel x86_64 and `crewai`'s `lancedb` dependency publishes no macOS x86_64 wheel. Do not
  spend time making it install locally, and do not report a local failure as a defect.
- **`.github/workflows/ci.yml` must stay green**, including `pytest tests/test_queue.py
  tests/test_crew_wires.py`. A checkpoint that needs a test changed changes the test in the same
  pull request and says why in the body.
- **Never hand-roll what the library does.** No state file, lock file, resume script, retry
  loop, memory store or tool registry written by hand. If CrewAI does it, use CrewAI's. If it
  does not, say so in the pull request body and name the version you checked.
- **No credential, key or token literal in any file**, and no path naming a home directory, a
  checkout or a machine. Configuration arrives as an environment variable with a default that
  works in CI.
- **The queue labels are the board's real lanes.** `lane:platform`, `lane:agents`,
  `lane:observability`, `lane:security`, `lane:process`, `lane:dr`. `tests/test_queue.py` pins
  this; the workload idled for its whole first deployment because it queued on a label that had
  never existed. Do not add a label to that list without adding it to the board first.
- **One storage directory.** `AGENT_WORKFORCE_STORAGE_DIR` (`/var/lib/agent-workforce` in the
  cluster) is where flow state, checkpoints and memory all live. A second directory, a second
  database or a second store is the stitching this estate deletes.

## How a checkpoint is accepted

A checkpoint is accepted when all four hold:

1. The pull request is merged into `main`.
2. The repository's ubuntu CI run on the merge commit is green.
3. The test the ticket names under **Definition of done** exists and passes in that run.
4. A comment on the crew ticket carries the merge commit and the run URL.

Nothing here is accepted on a description, a screenshot or a local run.

## Where the deployed copy lives

The image is `ghcr.io/chidionyema/agent-workforce:main`, published by
`.github/workflows/image.yml` on every push to `main`. The cluster runs it from
`chidionyema/idp` at `platform/agent-workforce/`, reconciled by Flux. A checkpoint that changes
the workload's shape — a new environment variable, a new volume, a new secret key — needs a
matching pull request against `chidionyema/idp` in the same session, or the merged code never
reaches the cluster.
