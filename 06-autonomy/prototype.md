

# Prototype: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 1, the working agent demo

## What it does

_One paragraph: the agent in action, end to end._

## How you built it

- **Coding agent:** _which one you directed (Claude Code / Cursor / Codex)_
- **Model + bounds:** _model used, max iterations, cost cap, queue cap_
- **Repo / config:** _path to your build in `00-build/`_
- **Live link:** _[shareable URL, optional bonus]_

## Screenshots (required, collected M2 to M6)

Real screenshots of *your* Cortex running. These are the `00-build/CORTEX-ANATOMY.md` set and they are required, a link alone is not enough.

| # | Screenshot | What it shows | From |
|---|---|---|---|
| 1 | <img width="756" height="491" alt="Happy Path Claude Code UI - Start" src="https://github.com/user-attachments/assets/d71a04bb-07d7-4220-8c55-67247aa1e07d" /><img width="756" height="491" alt="Happy Path Claude UI - End" src="https://github.com/user-attachments/assets/b2ea8dfc-00a4-43b0-b067-8d8af63e4e43" />
 | happy-path run: a real drafted update + the HITL checkpoint (queued, not posted) | M2 |
| 2 | <img width="756" height="491" alt="M3_Step4_Jailbreak_Path_20Jul26" src="https://github.com/user-attachments/assets/008c408a-176a-4ea2-b81e-94d7cfbbe326" /> | the critic rejecting a bad draft (revise/block/escalate) | M3 |
| 3 | _[img: screenshot `python agent.py happy`]_ + _[img: screenshot `CORTEX_WITHHOLD_SOURCE=get_activity python agent.py happy`]_ | **Grounded run**: update cites PR #812/#815 + dates from `get_activity`, "39%" from `search_past_updates`, queues 5 stories, real update. **Withheld-source run**: `get_activity` returns empty (no error), Cortex tries 3 times to spin the silence into a reassuring "Green, on track, team preparing" narrative, the critic rejects all 3 attempts for exactly that ("Green... without evidence", a placeholder date, unsupported "no risks" claim), run correctly ends in `REVISION CAP hit` escalation instead of a false pass. Reproduce with the two commands at left. | M4 |
| 4 | _[img]_ | jailbreak refused + escalated | M5 |
| 5 | _[img]_ | an iteration/cost/queue bound halting a runaway | M5 |
| 6 | _[img]_ | end-to-end run | M6 |

## How to run it

_Minimal steps for someone to reproduce the demo (env vars, and the command or the coding-agent prompt you used)._
