# model-router — GitHub Copilot CLI adapter

Route Copilot work to the right GPT tier by complexity.

## How it works (and the honest limitation)

Copilot CLI's hook system differs from Claude Code / Codex / Gemini in one decisive way:
**it ignores `userPromptSubmitted` hook output** and only reads `additionalContext` once, at
**`sessionStart`**, with a bare `{"additionalContext": "..."}` schema.

So model-router can't print a deterministic per-prompt banner here. Instead, at session start it
injects a **routing rubric** — the same complexity signals and tier→model table the scorer uses —
and the assistant self-classifies each prompt against it, announces the tier, and recommends a
`/model` switch when below it. (`hooks/copilot-hooks.json` + `adapters/copilot/session_start.py`.)

Tiers map to **GPT-5 mini / GPT-5 / GPT-5 Pro** (override in `core/providers.json` `copilot` block
or via `MODEL_ROUTER_COPILOT_<TIER>`).

## Install

```
copilot plugin marketplace add jamesrtubman/model-router
copilot plugin install model-router@model-router
```

Then start Copilot and trust the plugin's `sessionStart` hook when prompted. Restart the session so
the rubric is injected.

Requires `python3` on PATH (the hook is a small stdlib script).

## Why not per-prompt like the others?

If Copilot later surfaces `userPromptSubmitted` output, model-router can route per-prompt there too
— the shared scorer already supports it. Until then, session-start rubric injection is the most it
can do on Copilot.
