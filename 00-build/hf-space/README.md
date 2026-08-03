---
title: Cortex Email Triage Agent
emoji: 📨
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 6.22.0
app_file: app.py
pinned: false
---

# Cortex Email Triage Agent — live demo

A bounded email-triage agent: reads one inbound email, classifies it into one
of six categories, drafts a reply (or refuses to draft at all when policy
requires escalation), and passes the draft through an independent critic
before a human ever sees it. There is no send tool anywhere in this codebase.

This folder is a self-contained copy of the agent (`triageagent.py`,
`triagetools.py`, `triageprompt.py`, `critic.py`, `prompts.py`, `fixtures/`)
plus a small Gradio wrapper (`app.py`) so it can run as a public, clickable
demo instead of only a local CLI script.

## Deploying this to Hugging Face Spaces

1. Go to <https://huggingface.co/new-space>, pick a name, choose **SDK:
   Gradio**, hardware **CPU basic** (free tier is enough). HF will write a
   current `sdk_version` into this file's frontmatter for you when the Space
   is created, if it differs from the one already here, use HF's, not this
   one (this was tested locally against Gradio 6.22.0).
2. Upload every file in this folder to the new Space (drag-and-drop via the
   web UI, or `git clone` the Space's repo and copy these files in, then
   `git add . && git commit && git push`).
3. In the Space's **Settings → Repository secrets**, add a secret named
   `OPENAI_API_KEY` with your real key. **Never** put it in a file you commit.
4. The Space builds automatically. Once it's live, the Space's URL is your
   shareable link — anyone who opens it can click a scenario and watch a real
   run.

## Before you make this public: read this

Every click on this Space makes a real OpenAI API call billed to whatever key
you put in the secret. A few things worth doing before sharing the link
widely:

- **Set a hard spend limit on the API key itself**, in your provider's
  dashboard. This is the backstop if every other bound somehow fails.
- The agent's own bounds (`CORTEX_COST_CAP_USD`, `CORTEX_DAILY_COST_CAP_USD`,
  `CORTEX_MAX_ITERATIONS`, `CORTEX_MAX_READ_CALLS`) are the safety net for any
  single run or single day, set them as Space secrets/variables the same way
  as the API key if you want different values than the code's defaults.
- The kill switch (`triageagent.py`'s `.cortex_halt` file check) works from
  inside the running container, but for a public Space the simplest real
  kill switch is the **Pause this Space** button in the Space's own settings,
  that stops all traffic immediately, no file needed.
- There's no free-text input by design (see `app.py`), only the fixed
  scenario list, so there's no surface for a visitor to feed the agent a
  novel prompt against your key.

## Local test before deploying

```bash
pip install -r requirements.txt gradio
cp .env.example .env   # if you have one; otherwise just export OPENAI_API_KEY
python app.py
```

Opens at `http://127.0.0.1:7860`.
