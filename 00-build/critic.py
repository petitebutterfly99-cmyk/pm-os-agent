"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

import json
import os

from prompts import CRITIC_SYSTEM as DEFAULT_CRITIC_SYSTEM

# Shared by both agent.py and triageagent.py; neither had a call timeout before,
# a hung critic call could stall a run indefinitely with nothing to catch it.
CALL_TIMEOUT_S = float(os.environ.get("CORTEX_CALL_TIMEOUT_S", "30"))


def review(client, model: str, proposed_output: str, source_data: str,
           critic_system: str = DEFAULT_CRITIC_SYSTEM) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons": [...]} for a proposed output.

    critic_system lets a caller (e.g. triageagent.py) supply its own rubric
    instead of the PM status-update one; defaults to the PM rubric so
    agent.py's existing call sites keep working unchanged."""
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
    verdict["_usage"] = {"prompt": usage.prompt_tokens, "completion": usage.completion_tokens}
    return verdict
