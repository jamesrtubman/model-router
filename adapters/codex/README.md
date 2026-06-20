# model-router — Codex CLI adapter

Route Codex prompts to a GPT tier (mini / standard / pro) by complexity, announcing the
choice before acting.

## How it works

Codex's `UserPromptSubmit` hook shares the exact JSON contract Claude Code uses — stdin
`{prompt, ...}`, stdout `{"hookSpecificOutput": {"additionalContext": ...}}`. So the
shared `route.py` runs unchanged; `MODEL_ROUTER_PROVIDER=openai` maps tiers to GPT models.

Codex (like Claude Code) **cannot hot-swap the model from a hook**, and has no
model-pinned subagents — so the banner recommends a `/model` switch (or a one-off
`codex -c model='"..."'`) when the session is below the recommended tier.

## Install

### Marketplace (recommended)

```
codex plugin marketplace add jamesrtubman/model-router
codex
```

Then open `/plugins`, select the model-router marketplace, and install **model-router**. Open
`/hooks`, review and **trust** its lifecycle hook, and start a new thread. This same install also
covers the Codex desktop app — restart the app after installing and it picks up the plugin.

The plugin ships a `.codex-plugin/plugin.json` pointing at the shared `hooks/hooks.json`; the hook
auto-detects Codex from the prompt payload and sets the provider to `openai` — no env needed.

### Manual

1. Clone this repo somewhere stable.
2. Merge `config.toml` from this folder into `~/.codex/config.toml`, replacing
   `/ABSOLUTE/PATH/TO/model-router` with your clone path.
3. Start Codex and run `/hooks` to review and **trust** the new hook.

## Tune

- Model ids: edit `core/providers.json` (`openai` block) or set env overrides:
  `MODEL_ROUTER_OPENAI_TRIVIAL`, `_MODERATE`, `_COMPLEX` (e.g. `=o3`).
- Tier cutoffs / keywords: `core/scorer.py`.
- Disable for a session: `MODEL_ROUTER_OFF=1`. Force a tier: `MODEL_ROUTER_FORCE=complex`.

Confirm current GPT model ids against the [Codex config reference](https://developers.openai.com/codex/config-reference)
— the defaults shipped here (`gpt-5-mini` / `gpt-5` / `gpt-5-pro`) are placeholders.
