#!/usr/bin/env python3
"""Plugin hook entry for model-router (shared by Claude Code and Codex CLI).

Both tools install this plugin and run this same hook via ${CLAUDE_PLUGIN_ROOT}.
It's a thin pass-through to the provider-agnostic entrypoint at the repo root
(`../route.py` + `core/`), which auto-detects the host (Claude vs Codex) from the
hook payload. An explicit MODEL_ROUTER_PROVIDER still wins.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

import route  # noqa: E402

if __name__ == "__main__":
    route.main()
