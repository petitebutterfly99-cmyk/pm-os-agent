# Build Insights: Cortex Email Triage Agent

> Module 6 · ★ Deliverable 4, what you learned building it

## Friction

The critic silently ran the wrong rubric. `critic.py`'s `review()` had a default parameter pointing at the PM agent's status-update rubric, so the triage agent was validating email drafts against checks like "does this reference the correct project" for several runs with no error, no warning. It only surfaced when I specifically compared how the two variants enforce commitment dates and asked what was actually different between them.

A fix in one variant didn't propagate to its sibling. The repeat-call loop (a tool called seven times in a row with an identical error) got fixed in the triage agent early on, then showed up again, unpatched, in the PM agent during an unrelated M4 probe. Same underlying bug, same codebase family, and nothing forced the second instance to get caught until I happened to be testing something else entirely.

## Learning

A bound written in a prompt is not a bound. Every prompt-only rule tested this session, no-repeat-calls, escalate-for-unclear, no-commitment-language, eventually broke under a hard case, and the fix was always the same shape: move it into code.

Shared infrastructure between sibling agents doesn't guarantee shared rigor. `critic.py` is common to both agents; the dedup-guard fix wasn't, until it was deliberately backported. Nothing keeps two variants built from the same scaffold equally hardened over time.

Comparing two variants side by side surfaces gaps that auditing either one alone wouldn't. The missing "commitment level" row in the triage agent's line-map, and the un-backported dedup guard in the PM agent, were both found by asking what's different here, not by reviewing either agent in isolation.

## Aha moment

The line map is a design input, not documentation. The missing "commitment level" row in `triage-agent-line-map.md` wasn't a paperwork gap, it's why the commitment-boundary code guard didn't exist yet either. Adding the row back is what triggered building the actual enforcement. Score the full line map before writing any tool code next time, not after.

## What you'd do differently

Score the complete line map, every above/below-the-line row, for a new agent before writing any tool code, not after discovering a gap by comparison.

Make shared functions like `critic.py`'s `review()` take required parameters instead of silent defaults. A shared function with a silent default is exactly what let the wiring bug hide; a required parameter turns it into an immediate error instead of a silent wrong-rubric. Done: `critic_system` no longer has a default, a missing rubric now raises `TypeError` instead of quietly falling back to the wrong one.

Set up an explicit backport check for sibling agents sharing infrastructure, instead of finding divergence by accident.
