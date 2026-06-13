---
name: route
description: Show how model-router would classify a given prompt — its tier, score, signals, and chosen model — without doing the work. Use to inspect or tune routing. Trigger when the user asks how a prompt would be routed or invokes /model-router:route.
disable-model-invocation: true
---

# Inspect routing

The user wants to see how the model-router classifier scores a prompt: `$ARGUMENTS`

Run the classifier directly against that text and report the result. Use the plugin's
own scorer so the answer matches live routing:

```bash
python3 - "$ARGUMENTS" <<'PY'
import json, subprocess, sys, os
prompt = sys.argv[1] if len(sys.argv) > 1 else ""
root = os.environ.get("CLAUDE_PLUGIN_ROOT", ".")
script = os.path.join(root, "hooks", "route.py")
out = subprocess.run(["python3", script], input=json.dumps({"prompt": prompt}),
                     capture_output=True, text=True)
print(out.stdout or "(no output — empty prompt or routing disabled)")
PY
```

Then summarize for the user in plain language: the tier (trivial / moderate / complex),
the numeric score, the signals that drove it, and the model it would route to. Do **not**
perform the underlying task — this is inspection only.
