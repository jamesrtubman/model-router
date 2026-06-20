#!/usr/bin/env python3
"""Build a standing routing-rubric instruction for hosts that can't surface
per-prompt hook output.

GitHub Copilot CLI ignores `userPromptSubmitted` hook output and only reads
`additionalContext` once, at `sessionStart`. So instead of the deterministic
per-prompt banner the other tools get, Copilot is given a *rubric*: the same signal
keywords and tier→model table the scorer uses, with an instruction to self-classify
each prompt, announce the tier, and recommend a model switch when below it.
"""
from core import scorer, providers


def _kw(words, n=10):
    return ", ".join(sorted({w.strip() for w in words})[:n])


def build_rubric(provider_name="copilot"):
    """Return the session-start routing instruction string for `provider_name`."""
    provider = providers.get_provider(provider_name)
    tiers = provider["tiers"]
    label = provider.get("label", provider_name)
    hint = provider.get("switch_hint", "/model <id>")

    return (
        f"[model-router] Route every task to the right {label} model by complexity, and "
        "announce the choice before acting.\n\n"
        "For EACH user prompt, before doing the work:\n"
        "1. Judge its complexity using these signals —\n"
        f"   • complex (hard): {_kw(scorer.COMPLEX_KW)} … plus length, fenced code, 3+ "
        "sub-tasks, multi-step chaining, multiple file references.\n"
        f"   • trivial (easy): {_kw(scorer.TRIVIAL_KW)} … plus very short, single-step asks.\n"
        "   • everything else is moderate.\n"
        "2. Make your FIRST line a banner of exactly this form:\n"
        f"     🧭 Router → {tiers['complex']['display']}  (complex) — <one-line reason>\n"
        "   (substitute the tier you picked and its model below).\n"
        "3. Map the tier to a model:\n"
        f"     • trivial  → {tiers['trivial']['display']}  ({tiers['trivial']['model']})\n"
        f"     • moderate → {tiers['moderate']['display']}  ({tiers['moderate']['model']})\n"
        f"     • complex  → {tiers['complex']['display']}  ({tiers['complex']['model']})\n"
        f"4. If the session is below the recommended model, recommend switching: {hint} "
        "(replace <id> with the model above). If already at or above it, just proceed.\n\n"
        "Keep the banner on every task. This tool can't switch the live model from a hook, so "
        "the switch is the user's `/model` command. If you judge the tier wrong, say so in one "
        "line and route by your own judgment."
    )
