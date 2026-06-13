#!/usr/bin/env python3
"""model-router: classify prompt complexity on UserPromptSubmit and route to a model tier.

Reads the UserPromptSubmit hook payload on stdin, scores the prompt with fast,
transparent heuristics (no LLM call — this runs synchronously and must be quick),
then emits:
  - systemMessage:    a one-line router banner shown to the user
  - additionalContext: an instruction telling the assistant to announce the chosen
                       model before acting and to route the work to the matching tier

The active session model cannot be hot-swapped by a hook (Claude Code exposes no
such field), so the actual model switch happens by delegating to the tier's worker
agent (agents/router-*.md), each pinned to a model via frontmatter.

Overrides (env vars):
  MODEL_ROUTER_FORCE = trivial|moderate|complex   force a tier, skip scoring
  MODEL_ROUTER_FLOOR = trivial|moderate|complex   never route below this tier
  MODEL_ROUTER_OFF   = 1                           disable routing for the session
"""
import json
import os
import re
import sys

# --- tier definitions ------------------------------------------------------
TIERS = {
    "trivial": {
        "model": "haiku",
        "display": "Haiku 4.5",
        "agent": "model-router:router-haiku",
    },
    "moderate": {
        "model": "sonnet",
        "display": "Sonnet 4.6",
        "agent": "model-router:router-sonnet",
    },
    "complex": {
        "model": "opus",
        "display": "Opus 4.8",
        "agent": "model-router:router-opus",
    },
}
ORDER = ["trivial", "moderate", "complex"]

# Keywords that pull a prompt toward the heavy tier.
COMPLEX_KW = [
    "architect", "architecture", "refactor", "redesign", "design a", "design an",
    "debug", "root cause", "race condition", "concurrency", "deadlock", "optimi",
    "performance", "scalab", "distributed", "migrat", "trade-off", "tradeoff",
    "algorithm", "prove", "security", "vulnerab", "threat model", "end-to-end",
    "from scratch", "build a", "build an", "implement", "rewrite", "plan ",
    "compare", "evaluate", "why does", "why is", "strategy", "multi-step",
]
# Everyday-engineering signals: a couple of these → moderate (Sonnet) tier.
MODERATE_KW = [
    "add a", "add an", "create a", "create an", "write a", "write an", "build ",
    "fix ", "fix it", "fixing", "bug", "debug", "broken", "not working", "fails",
    "failing", "intermittent", "flaky", "error", "crash", "why", "endpoint",
    "function", "method", "class ", "test", "tests", "parse", "update ", "feature",
    "handle", "support for", "integrate",
]
# Keywords that pull a prompt toward the light tier.
TRIVIAL_KW = [
    "what is", "what's", "define", "definition", "list all", "give me a list",
    "rename", "typo", "spelling", "fix the import", "capitalize", "lowercase",
    "uppercase", "yes or no", "tldr", "tl;dr", "one-liner", "single line",
]


def score(prompt: str):
    """Return (tier, score, reasons[]) from transparent heuristics."""
    p = prompt.lower()
    words = re.findall(r"\S+", prompt)
    n = len(words)
    s = 0.0
    reasons = []

    # Length: longer asks tend to be harder.
    if n > 250:
        s += 3; reasons.append("very long")
    elif n > 100:
        s += 2; reasons.append("long")
    elif n > 40:
        s += 1
    elif n <= 8:
        s -= 1; reasons.append("very short")

    # Code blocks → real engineering.
    fences = prompt.count("```")
    if fences >= 2:
        s += 2; reasons.append("code block")

    # Multi-part asks: numbered lists or chained steps.
    steps = len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*])\s+", prompt))
    if steps >= 3:
        s += 2; reasons.append(f"{steps} sub-tasks")
    elif steps == 2:
        s += 1
    chains = len(re.findall(r"(and then|after that|followed by|then design|, then |; then |next,|also,)", p))
    if chains:
        s += min(chains, 2); reasons.append("multi-step")

    # File / path references → touching a codebase.
    paths = len(re.findall(r"[\w./-]+\.(?:py|js|ts|tsx|jsx|go|rs|java|rb|c|cpp|h|json|yaml|yml|sh|md|sql)\b", p))
    if paths >= 2:
        s += 1; reasons.append("multiple files")

    # Keyword pulls. Distinct complex signals weigh heavily (1.5 each, capped).
    hits = sorted({k.strip() for k in COMPLEX_KW if k in p})
    if hits:
        s += min(len(hits) * 1.5, 4.5); reasons.append("complex: " + ", ".join(hits[:3]))
    # Everyday-engineering signals nudge toward moderate (1.0 each, capped at 2.0).
    mhits = sorted({k.strip() for k in MODERATE_KW if k in p})
    if mhits:
        s += min(len(mhits) * 1.0, 2.0); reasons.append("eng: " + ", ".join(mhits[:3]))
    tlow = [k.strip() for k in TRIVIAL_KW if k in p]
    if tlow:
        s -= 2; reasons.append("simple ask")

    # Map score → tier.
    if s >= 4:
        tier = "complex"
    elif s >= 1.5:
        tier = "moderate"
    else:
        tier = "trivial"

    if not reasons:
        reasons.append("short, single-step ask")
    return tier, round(s, 1), reasons


def apply_overrides(tier):
    force = (os.environ.get("MODEL_ROUTER_FORCE") or "").strip().lower()
    if force in TIERS:
        return force, True
    floor = (os.environ.get("MODEL_ROUTER_FLOOR") or "").strip().lower()
    if floor in TIERS and ORDER.index(tier) < ORDER.index(floor):
        return floor, False
    return tier, False


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

    tier, sc, reasons = score(prompt)
    tier, forced = apply_overrides(tier)
    t = TIERS[tier]
    reason_str = "; ".join(reasons) if not forced else "forced via MODEL_ROUTER_FORCE"

    banner = f"🧭 Router → {t['display']}  ({tier}, score {sc}) — {reason_str}"

    instruction = (
        "[model-router] A complexity classifier scored the user's prompt.\n"
        f"  tier: {tier} (score {sc})\n"
        f"  signals: {reason_str}\n"
        f"  recommended model: {t['display']} (alias `{t['model']}`)\n"
        f"  worker agent for this tier: {t['agent']}\n\n"
        "BEFORE any other output or tool call, your FIRST line must be exactly:\n"
        f"  {banner}\n\n"
        "Then handle the task using this routing policy:\n"
        f"  - complex  → delegate the work to the `{TIERS['complex']['agent']}` agent "
        "(runs on Opus) unless you are already on Opus, in which case proceed in-session.\n"
        f"  - moderate → proceed in-session if already on Sonnet or Opus; otherwise delegate "
        f"to `{TIERS['moderate']['agent']}`.\n"
        f"  - trivial  → you may delegate to `{TIERS['trivial']['agent']}` (runs on Haiku) to "
        "conserve budget, or answer directly if a switch adds more overhead than it saves.\n"
        "Delegation is how the model actually changes — a hook cannot switch the live session "
        "model. If you judge the classification wrong, say so in one line and route by your own "
        "judgment. Keep the banner regardless."
    )

    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": instruction,
        },
        "systemMessage": banner,
    }
    print(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
