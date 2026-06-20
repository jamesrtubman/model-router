#!/usr/bin/env python3
"""model-router shared hook entrypoint (provider-agnostic).

Used by every hook-based adapter (Claude Code, Codex CLI, Gemini CLI). Reads the
UserPromptSubmit payload on stdin, scores complexity, maps the tier to a model for the
active provider (MODEL_ROUTER_PROVIDER, default "claude"), and prints the hook JSON:
  - systemMessage:     a one-line router banner
  - additionalContext: an instruction telling the assistant to announce the chosen model
                       first, then route per the provider's delegation policy.

No tool can hot-swap the live model from a hook, so routing is by recommendation —
delegation to a model-pinned subagent (Claude) or a /model switch (Codex / Gemini).

Overrides (env vars):
  MODEL_ROUTER_PROVIDER = claude|openai|gemini    pick the model family (default claude)
  MODEL_ROUTER_FORCE    = trivial|moderate|complex force a tier, skip scoring
  MODEL_ROUTER_FLOOR    = trivial|moderate|complex never route below this tier
  MODEL_ROUTER_OFF      = 1                        disable routing for the session
  MODEL_ROUTER_<PROVIDER>_<TIER> = <model-id>      override a tier's model id
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import scorer, providers, emit  # noqa: E402


def detect_provider(data):
    """Infer the host tool from the environment when not set explicitly.

    The same `UserPromptSubmit` hook serves Claude Code, Codex CLI, and Gemini CLI.
    Each host exports a distinctive env var during hook execution, so one shared hook
    routes to the right model family with no per-tool config:

      - Codex   → CODEX_HOME / PLUGIN_DATA   (also sends `turn_id` in the payload)
      - Gemini  → GEMINI_SESSION_ID / GEMINI_CWD
      - Claude  → (default)

    An explicit MODEL_ROUTER_PROVIDER always wins. (GitHub Copilot CLI uses a separate
    sessionStart adapter — see adapters/copilot/ — because it ignores per-prompt hook
    output.)
    """
    env = os.environ
    if (env.get("MODEL_ROUTER_PROVIDER") or "").strip():
        return  # explicit wins
    if env.get("CODEX_HOME") or env.get("PLUGIN_DATA") or "turn_id" in data:
        env["MODEL_ROUTER_PROVIDER"] = "openai"
    elif env.get("GEMINI_SESSION_ID") or env.get("GEMINI_CWD"):
        env["MODEL_ROUTER_PROVIDER"] = "gemini"


def route(prompt):
    """Score `prompt` and return the hook output dict for the active provider."""
    tier, sc, reasons = scorer.score(prompt)
    tier, forced = scorer.apply_overrides(tier)
    provider = providers.get_provider()
    return emit.build_output(tier, sc, reasons, provider, forced=forced)


def main():
    if (os.environ.get("MODEL_ROUTER_OFF") or "").strip() == "1":
        sys.exit(0)
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        sys.exit(0)

    detect_provider(data)
    print(json.dumps(route(prompt)))
    sys.exit(0)


if __name__ == "__main__":
    main()
