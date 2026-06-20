#!/usr/bin/env python3
"""Build the hook banner + additionalContext instruction for a routed prompt.

The hook output schema is identical across Claude Code, Codex CLI, and Gemini CLI:

    {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                            "additionalContext": "..."},
     "systemMessage": "..."}

None of these tools can hot-swap the live model from a hook, so routing is by
recommendation. Two delegation styles:
  - "subagent": Claude Code delegates work to a model-pinned worker agent (the actual
                model change). Behavior is preserved verbatim from the original plugin.
  - "switch":   Codex / Gemini have no model-pinned subagents, so the assistant announces
                the tier and recommends switching with the provider's model command.
"""


def banner(tier, sc, reason_str, tier_spec):
    return f"🧭 Router → {tier_spec['display']}  ({tier}, score {sc}) — {reason_str}"


def _subagent_instruction(tier, sc, reason_str, provider, b):
    tiers = provider["tiers"]
    return (
        "[model-router] A complexity classifier scored the user's prompt.\n"
        f"  tier: {tier} (score {sc})\n"
        f"  signals: {reason_str}\n"
        f"  recommended model: {tiers[tier]['display']} (alias `{tiers[tier]['model']}`)\n"
        f"  worker agent for this tier: {tiers[tier]['agent']}\n\n"
        "BEFORE any other output or tool call, your FIRST line must be exactly:\n"
        f"  {b}\n\n"
        "Then handle the task using this routing policy:\n"
        f"  - complex  → delegate the work to the `{tiers['complex']['agent']}` agent "
        "(runs on Opus) unless you are already on Opus, in which case proceed in-session.\n"
        f"  - moderate → proceed in-session if already on Sonnet or Opus; otherwise delegate "
        f"to `{tiers['moderate']['agent']}`.\n"
        f"  - trivial  → you may delegate to `{tiers['trivial']['agent']}` (runs on Haiku) to "
        "conserve budget, or answer directly if a switch adds more overhead than it saves.\n"
        "Delegation is how the model actually changes — a hook cannot switch the live session "
        "model. If you judge the classification wrong, say so in one line and route by your own "
        "judgment. Keep the banner regardless."
    )


def _switch_instruction(tier, sc, reason_str, provider, b):
    tiers = provider["tiers"]
    label = provider.get("label", "this tool")
    hint = provider.get("switch_hint", "/model <id>").replace("<id>", tiers[tier]["model"])
    return (
        f"[model-router] A complexity classifier scored the user's prompt for {label}.\n"
        f"  tier: {tier} (score {sc})\n"
        f"  signals: {reason_str}\n"
        f"  recommended model: {tiers[tier]['display']} (`{tiers[tier]['model']}`)\n\n"
        "BEFORE any other output or tool call, your FIRST line must be exactly:\n"
        f"  {b}\n\n"
        "Then apply this routing policy:\n"
        f"  - If the session is already on {tiers[tier]['display']} (or stronger), proceed.\n"
        f"  - Otherwise recommend the user switch model before continuing the hard parts:\n"
        f"      {hint}\n"
        "A hook cannot switch the live model on this tool, and there are no model-pinned "
        "subagents — so the model change is the user's `/model` switch (or a new session "
        "started with the recommended model). If you judge the classification wrong, say so "
        "in one line and route by your own judgment. Keep the banner regardless."
    )


def build_output(tier, sc, reasons, provider, forced=False):
    """Return the hook JSON dict for the routed prompt."""
    reason_str = "; ".join(reasons) if not forced else "forced via MODEL_ROUTER_FORCE"
    tier_spec = provider["tiers"][tier]
    b = banner(tier, sc, reason_str, tier_spec)

    if provider.get("delegation") == "subagent":
        instruction = _subagent_instruction(tier, sc, reason_str, provider, b)
    else:
        instruction = _switch_instruction(tier, sc, reason_str, provider, b)

    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": instruction,
        },
        "systemMessage": b,
    }
