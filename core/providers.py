#!/usr/bin/env python3
"""Provider registry for model-router.

Loads the tier→model mapping per provider from providers.json, then applies
per-tier env-var overrides so users on different plans / model names can adjust
without editing files:

    MODEL_ROUTER_<PROVIDER>_<TIER> = <model-id>
    e.g.  MODEL_ROUTER_OPENAI_COMPLEX=o3   MODEL_ROUTER_GEMINI_TRIVIAL=gemini-flash-lite

The active provider is chosen with MODEL_ROUTER_PROVIDER (default "claude").
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_REGISTRY_PATH = os.path.join(_HERE, "providers.json")

DEFAULT_PROVIDER = "claude"


def _load_registry():
    with open(_REGISTRY_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def active_provider_name():
    """Provider id selected for this session (lowercased)."""
    name = (os.environ.get("MODEL_ROUTER_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    return name or DEFAULT_PROVIDER


def get_provider(name=None):
    """Return the provider config dict (with env overrides applied).

    Falls back to the default provider if `name` is unknown.
    """
    registry = _load_registry()
    name = (name or active_provider_name())
    cfg = registry.get(name) or registry[DEFAULT_PROVIDER]
    name = name if name in registry else DEFAULT_PROVIDER

    # Apply per-tier env overrides for the model id.
    for tier, spec in cfg["tiers"].items():
        env_key = f"MODEL_ROUTER_{name.upper()}_{tier.upper()}"
        override = (os.environ.get(env_key) or "").strip()
        if override:
            spec["model"] = override
    cfg["_name"] = name
    return cfg
