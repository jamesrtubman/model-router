#!/usr/bin/env python3
"""Provider-agnostic complexity scorer for model-router.

Pure heuristics — no LLM call, no provider knowledge. Given a prompt, return a
(tier, score, reasons) triple. The tier names (trivial / moderate / complex) are
mapped to concrete models per provider elsewhere (see providers.py).

This runs inside a synchronous UserPromptSubmit hook on Claude Code, Codex CLI, and
Gemini CLI, so it must stay fast and stdlib-only.
"""
import os
import re

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
# Everyday-engineering signals: a couple of these → moderate tier.
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
    """Apply env-var tier overrides. Returns (tier, forced)."""
    force = (os.environ.get("MODEL_ROUTER_FORCE") or "").strip().lower()
    if force in ORDER:
        return force, True
    floor = (os.environ.get("MODEL_ROUTER_FLOOR") or "").strip().lower()
    if floor in ORDER and ORDER.index(tier) < ORDER.index(floor):
        return floor, False
    return tier, False
