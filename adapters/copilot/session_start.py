#!/usr/bin/env python3
"""GitHub Copilot CLI adapter — sessionStart hook.

Copilot ignores `userPromptSubmitted` hook output and only reads `additionalContext`
at `sessionStart`, with a bare `{"additionalContext": "..."}` schema (no
`hookSpecificOutput` wrapper). So model-router can't surface a per-prompt banner here —
instead it injects a standing routing rubric once, and the assistant self-classifies
each prompt against it. Provider is fixed to `copilot` (GPT tiers; override via
core/providers.json or MODEL_ROUTER_COPILOT_<TIER>).
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

from core import rubric  # noqa: E402


def main():
    try:
        json.load(sys.stdin)  # drain stdin if present; we don't need fields
    except Exception:
        pass
    print(json.dumps({"additionalContext": rubric.build_rubric("copilot")}))
    sys.exit(0)


if __name__ == "__main__":
    main()
