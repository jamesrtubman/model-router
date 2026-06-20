# model-router — Gemini CLI adapter

Route Gemini prompts to a tier (Flash-Lite / Flash / Pro) by complexity, announcing the
choice before acting.

## How it works

Gemini CLI's hook system uses the same event taxonomy and JSON contract as Claude Code
(`UserPromptSubmit` → `{"hookSpecificOutput": {"additionalContext": ...}}`). The shared
`route.py` runs unchanged; `MODEL_ROUTER_PROVIDER=gemini` maps tiers to Gemini models.

Gemini cannot hot-swap the model from a hook, so the banner recommends a `/model` switch
(or starting with `gemini --model <id>`) when the session is below the recommended tier.

## Install

This folder **is** a Gemini extension. Install it by linking/copying it into your Gemini
extensions directory:

```bash
mkdir -p ~/.gemini/extensions
cp -r adapters/gemini ~/.gemini/extensions/model-router
```

Then edit `~/.gemini/extensions/model-router/hooks/hooks.json` and replace
`/ABSOLUTE/PATH/TO/model-router` with your clone path. Restart Gemini CLI.

## Tune

- Model ids: edit `core/providers.json` (`gemini` block) or set env overrides
  `MODEL_ROUTER_GEMINI_TRIVIAL` / `_MODERATE` / `_COMPLEX`.
- Tier cutoffs / keywords: `core/scorer.py`.
- Disable: `MODEL_ROUTER_OFF=1`. Force a tier: `MODEL_ROUTER_FORCE=complex`.

Confirm current Gemini model ids against the
[Gemini CLI docs](https://geminicli.com/docs/) — defaults here
(`gemini-flash-lite` / `gemini-flash` / `gemini-pro`) are placeholders.
