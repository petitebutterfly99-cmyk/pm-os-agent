"""Gradio demo for Cortex Email Triage Agent. Wraps triageagent.run() so each
click makes a real, bounded OpenAI call and shows the full trace.

Deliberately no free-text input: only the fixed fixture set below is
selectable, so a public visitor can watch the agent handle the scenarios it
was built for (including a live jailbreak refusal), never a novel prompt
against your API key.
"""
from __future__ import annotations

import contextlib
import io

import gradio as gr

import triageagent

FIXTURES = [
    "happy",
    "happy-enhancement",
    "happy-unrelated",
    "missing-data",
    "missing-context",
    "jailbreak",
    "jailbreak-security-threat",
]

FIXTURE_LABELS = {
    "happy": "Happy path — bug report",
    "happy-enhancement": "Happy path — enhancement request",
    "happy-unrelated": "Happy path — unrelated / newsletter",
    "missing-data": "Missing data — vague “it's broken” report",
    "missing-context": "Missing context — ambiguous error report",
    "jailbreak": "Jailbreak — commitment-trap injection",
    "jailbreak-security-threat": "Jailbreak — legal-threat / extortion",
}


def run_fixture(which: str) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            triageagent.run(which)
        except Exception as exc:  # surface config/API errors in the UI, not a blank page
            print(f"\nERROR: {exc}")
    return buf.getvalue()


with gr.Blocks(title="Cortex Email Triage Agent") as demo:
    gr.Markdown(
        "# Cortex Email Triage Agent\n"
        "A bounded triage agent: reads one inbound email, classifies it, drafts a "
        "reply or refuses to draft at all when policy requires escalation, and "
        "never sends anything, there's no send tool anywhere in the codebase. "
        "Pick a scenario below, each click makes a real, cost- and iteration-capped "
        "OpenAI call and shows the full trace, including the independent critic's "
        "verdict."
    )
    choice = gr.Radio(
        choices=[(FIXTURE_LABELS[f], f) for f in FIXTURES],
        value="happy",
        label="Scenario",
    )
    run_btn = gr.Button("Run", variant="primary")
    output = gr.Textbox(label="Trace", lines=30, max_lines=60)
    run_btn.click(fn=run_fixture, inputs=choice, outputs=output)

if __name__ == "__main__":
    demo.launch()
