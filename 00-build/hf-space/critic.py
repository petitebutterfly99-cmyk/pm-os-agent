"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

import json
import os

# Shared by both agent.py and triageagent.py; neither had a call timeout before,
# a hung critic call could stall a run indefinitely with nothing to catch it.
CALL_TIMEOUT_S = float(os.environ.get("CORTEX_CALL_TIMEOUT_S", "30"))


def review(client, model: str, proposed_output: str, source_data: str,
           critic_system: str) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons": [...]} for a proposed output.

    critic_system is required, no default, on purpose: a silent default here
    once let triageagent.py validate email drafts against the PM agent's
    status-update rubric for several runs with no error at all. Every caller
    must now say explicitly which rubric it means."""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": critic_system},
            {"role": "user", "content":
                f"SOURCE DATA Cortex used:\n{source_data}\n\n"
                f"CORTEX PROPOSED OUTPUT:\n{proposed_output}"},
        ],
        response_format={"type": "json_object"},
        timeout=CALL_TIMEOUT_S,
    )
    usage = resp.usage
    try:
        verdict = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        verdict = {"verdict": "fail", "reasons": ["critic returned unparseable output"]}

    checks = verdict.get("checks")
    if isinstance(checks, list):
        # Structured rubric (triageagent.py's TRIAGE_CRITIC_SYSTEM): derive the
        # verdict from each check's own pass/fail instead of trusting a separate
        # top-level "verdict" field the model could get out of sync with its own
        # per-check reasoning, observed live: reasons read as all 7 checks passing
        # while the model's top-level field still said "fail".
        failed = [c for c in checks if not c.get("pass", True)]
        verdict["verdict"] = "fail" if failed else "pass"
        verdict["reasons"] = [f"{c.get('name', 'check')}: {c.get('reason', '')}" for c in failed]

    verdict["_usage"] = {"prompt": usage.prompt_tokens, "completion": usage.completion_tokens}
    return verdict
