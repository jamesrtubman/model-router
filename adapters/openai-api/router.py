#!/usr/bin/env python3
"""model-router — OpenAI-compatible API adapter.

For tools that call an OpenAI-compatible endpoint directly (the OpenAI SDK, an app, a
local Ollama / LM Studio server) there is no hook surface. Instead, score the prompt and
pick the model id *before* you make the request.

Library use:

    from router import pick_model, classify
    model = pick_model("refactor the auth service and prove it is race-free")
    client.chat.completions.create(model=model, messages=[...])

CLI use (any language / CI can shell out):

    python3 router.py "what is a closure in python"
    # -> {"tier": "trivial", "model": "gpt-5-mini", "score": -3.0, "reasons": [...]}

Provider defaults to "openai"; override with MODEL_ROUTER_PROVIDER, and per-tier model
ids with MODEL_ROUTER_<PROVIDER>_<TIER> or by editing core/providers.json.
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)

os.environ.setdefault("MODEL_ROUTER_PROVIDER", "openai")

from core import scorer, providers  # noqa: E402


def classify(prompt: str):
    """Return {tier, model, display, score, reasons} for the active provider."""
    tier, sc, reasons = scorer.score(prompt)
    tier, _forced = scorer.apply_overrides(tier)
    provider = providers.get_provider()
    spec = provider["tiers"][tier]
    return {
        "tier": tier,
        "model": spec["model"],
        "display": spec["display"],
        "score": sc,
        "reasons": reasons,
    }


def pick_model(prompt: str) -> str:
    """Return just the model id to pass as the API `model` parameter."""
    return classify(prompt)["model"]


def main():
    prompt = " ".join(sys.argv[1:]).strip()
    if not prompt:
        print('usage: router.py "your prompt"', file=sys.stderr)
        sys.exit(2)
    print(json.dumps(classify(prompt)))


if __name__ == "__main__":
    main()
