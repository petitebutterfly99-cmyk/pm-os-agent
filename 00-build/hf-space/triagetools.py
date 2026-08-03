"""Cortex Email Triage Agent mock tools, the tools your agent is allowed to call.

These are plain Python functions over the files in `fixtures/`. They are imported
directly by `agent.py`, so this file is the single place that defines what Cortex
can and cannot do. 

Design note: there is deliberately NO send or publish tool. Cortex can read
incoming emails, fetch thread history, and CREATE Gmail drafts for human review,
but it can never send an email or make external commitments.

Permissions bound, for whoever wires this to the real Gmail API: these mock
functions read/write local fixtures, so there's no OAuth client to scope here.
When `get_unread_emails`/`get_thread_history` and `create_gmail_draft` are
replaced with real Gmail API calls, request `gmail.compose` (draft-only,
covers read + create-draft) and NOT `gmail.send` or the full `mail.google.com`
scope. That way "no send tool" is enforced at the credential layer too, not
just by "nobody wrote a send function", a later contributor adding a send
function would still have no send-capable token to call it with. Also scope
the read calls to the specific inbox/label this agent triages, not the whole
mailbox, to bound the blast radius of a prompt-injection attempt that asks it
to read an unrelated thread (see `triageagent.py`'s known_ids check, which
catches this in-run, but real scoping should back it up at the API layer).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
_CATEGORIES = ["happy", "missing-data", "jailbreak"]

# Commitment bound (mirrors MAX_QUEUE_ITEMS in tools.py). A sentence that MAKES a
# release-date, discount/refund, or guarantee commitment is rejected by
# infrastructure and must be escalated, even if the model believes it's warranted.
# A sentence that instead REFUSES one (contains a negation like "cannot" /
# "unable to") is not flagged, refusing a commitment is the correct behavior and
# must not be penalized just for using the same vocabulary as a real commitment.
_MONTHS = ("january|february|march|april|may|june|july|august|september|"
           "october|november|december")
_DATE_RE = re.compile(rf"\b(?:{_MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s*\d{{4}}\b",
                       re.IGNORECASE)
_PERCENT_RE = re.compile(r"\d{1,3}\s?%")
_COMMITMENT_WORDS_RE = re.compile(
    r"\b(guarantee[ds]?|promis(?:e|ed|ing)|committ?(?:ed|ing)?|confirm(?:ed|ing)?)\b",
    re.IGNORECASE)
# A commitment verb only matters if it's attached to something committable, a
# bare "I confirm we received your ticket" is a benign acknowledgment, not a
# promise; requiring one of these nearby is what tells them apart.
_DELIVERABLE_RE = re.compile(
    r"\b(ship(?:ped|ping)?|deliver(?:y|ed|ing)?|release[ds]?|discount(?:ed)?|"
    r"refund(?:ed|ing)?|waive[rd]?|invoice|deadline|launch\s*gate)\b",
    re.IGNORECASE)
_NEGATION_RE = re.compile(
    r"\b(cannot|can't|can not|won't|will not|do not|don't|unable to|"
    r"not able to|not authorized|without authorization)\b", re.IGNORECASE)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_FROM_LINE_RE = re.compile(r"INBOUND EMAIL FROM:\s*(\S+)", re.IGNORECASE)


def _load_json(name: str) -> dict:
    path = FIXTURES / name
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _resolve_fixture(which: str) -> str | None:
    """Resolve `which` to a fixture body text. `which` may be a category name
    ("happy", "missing-data", "jailbreak" -> that category's first/default
    scenario) or a specific fixture id (e.g. "jailbreak-security-threat") to
    select a sub-scenario within a category. Returns None if nothing matches."""
    for category in _CATEGORIES:
        fixtures = _load_json(f"triage-task-{category}.json").get("fixtures", [])
        if not fixtures:
            continue
        if which == category:
            return fixtures[0]["body"]
        for f in fixtures:
            if f.get("id") == which:
                return f["body"]
    return None


def _commitment_flags(draft_body: str) -> list[str]:
    """Flag sentences that MAKE (not refuse) a date, percentage, or
    guarantee/promise/commit/confirm commitment. A sentence carrying a
    negation ('cannot', 'unable to', ...) alongside the trigger word is read
    as a refusal, not a commitment, and is not flagged. A bare commitment verb
    with no date/percentage/deliverable nearby (e.g. "I confirm we received
    your ticket") is a benign acknowledgment, not a promise, and is not
    flagged either."""
    flags = set()
    for sentence in _SENTENCE_SPLIT_RE.split(draft_body):
        if not sentence.strip() or _NEGATION_RE.search(sentence):
            continue
        has_date = bool(_DATE_RE.search(sentence))
        has_percent = bool(_PERCENT_RE.search(sentence))
        if has_date:
            flags.add("contains a specific calendar date")
        if has_percent:
            flags.add("contains a percentage (possible discount/refund commitment)")
        if _COMMITMENT_WORDS_RE.search(sentence) and (
                has_date or has_percent or _DELIVERABLE_RE.search(sentence)):
            flags.add("contains guarantee/promise/commit/confirm language tied to a deliverable")
    return sorted(flags)


def get_task(which: str = "happy") -> dict:
    """Read the inbound email task brief to work on.

    Args:
        which: a category ("happy", "missing-data", "jailbreak") for its
            default scenario, or a specific fixture id (e.g.
            "jailbreak-security-threat") to select a sub-scenario.
    Returns the raw task text plus its source label.
    """
    body = _resolve_fixture(which)
    if body is None:
        return {"error": f"no task fixture named '{which}'",
                "available": _CATEGORIES + ["<a fixture id, e.g. jailbreak-security-threat>"]}
    return {"which": which, "body": body}


def get_unread_emails(which: str = "happy") -> dict:
    """Fetch incoming unread emails matching the active test scenario."""
    # Look for a specific scenario fixture file first (e.g., inbound-emails-missing-data.json)
    scenario_file = f"inbound-emails-{which}.json"
    emails = _load_json(scenario_file)

    if emails:
        return emails

    # Fallback: synthesize an email from the resolved task fixture body. The
    # sender is parsed from the fixture's own "INBOUND EMAIL FROM:" line so
    # each scenario gets a real, distinguishable sender, this is the identity
    # Cortex should treat as verified, instead of a uniform placeholder that
    # made sender-mismatch checks meaningless.
    body_text = _resolve_fixture(which)
    if body_text is not None:
        from_match = _FROM_LINE_RE.search(body_text)
        sender = from_match.group(1) if from_match else "unknown-sender@unverified.test"
        safe_id = re.sub(r"[^a-z0-9]+", "-", which.lower()).strip("-")
        return {
            "unread_count": 1,
            "emails": [{
                "message_id": f"msg_{safe_id}_001",
                "sender": sender,
                "subject": f"Triage Task - {which.title()}",
                "body": body_text
            }]
        }

    # Final default fallback
    return {
        "unread_count": 1,
        "emails": [{
            "message_id": "msg_001",
            "sender": "customer@example.com",
            "subject": "Support Request",
            "body": "Standard issue report."
        }]
    }


def get_thread_history(thread_id: str) -> dict:
    """Read prior messages from the same Gmail thread context."""
    thread_id = str(thread_id).strip()
    threads = _load_json("thread-history.json")
    history = threads.get(thread_id, [])
    return {"thread_id": thread_id, "history": history, "note": "prior thread messages for context."}


def get_policies(query: str = "") -> dict:
    """Return the support triage policy (commitment authority, escalation
    triggers, tone) Cortex must ground its decisions in. `query` is a hint;
    the file is small enough to return whole so the agent and critic can
    cite the exact rule relied on."""
    text = (FIXTURES / "support-policy.md").read_text()
    return {"query": query, "policy": text}


def create_gmail_draft(thread_id: str, draft_body: str, classification: str) -> dict:
    """Create a reply draft in the correct Gmail thread.

    CRITICAL: This creates a saved draft ONLY. It never sends emails.
    A sentence that MAKES a specific date, a discount/refund percentage, or
    guarantee/promise/commit/confirm commitment is rejected here, in code,
    regardless of what the model intended, the commitment bound is enforced
    outside the model. A sentence that REFUSES one (contains a negation like
    "cannot"/"unable to") is not flagged.

    Policy also requires immediate escalation, with no drafted reply, for
    "unclear" messages, that bound is enforced here too rather than trusted
    to the prompt.
    """
    if classification == "unclear":
        return {"status": "rejected",
                "error": "escalation_required_no_draft",
                "reason": "policy requires immediate escalation for unclear/vague "
                          "inbound messages, no draft reply is permitted",
                "action": "do not call create_gmail_draft again for this email; "
                          "end the run with ESCALATE"}

    flags = _commitment_flags(draft_body)

    if flags:
        return {"status": "rejected",
                "error": "commitment_bound_violation",
                "flags": flags,
                "action": "escalate to a human, do not reword the draft to dodge the check"}

    return {
        "status": "draft_created_for_review",
        "thread_id": str(thread_id).strip(),
        "classification": classification,
        "draft_body": draft_body,
        "note": "Draft saved in Gmail successfully. Awaiting human PM review and approval before any send action."
    }


def mark_email_processed(message_id: str) -> dict:
    """Apply internal processed marker/label to prevent duplicate work."""
    return {
        "status": "marked_processed",
        "message_id": str(message_id).strip(),
        "note": "Internal label applied to prevent duplicate processing loops."
    }


# Registry the agent loop reads. Add a tool here and the agent can call it.
# Note what is ABSENT: there is no send_email tool, no auto-reply, no publish tool.
TOOLS = {
    "get_task": get_task,
    "get_unread_emails": get_unread_emails,
    "get_thread_history": get_thread_history,
    "get_policies": get_policies,
    "create_gmail_draft": create_gmail_draft,
    "mark_email_processed": mark_email_processed,
}