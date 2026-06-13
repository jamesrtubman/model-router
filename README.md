# model-router

A Claude Code plugin that scores each prompt's complexity and routes the work to the
right Claude model — **Haiku** for trivial asks, **Sonnet** for everyday work, **Opus**
for hard problems. It **announces the chosen model before acting**, so you always see
where your prompt landed and why.

```
🧭 Router → Opus 4.8  (complex, score 5.5) — multi-step; complex: concurrency, design a, distributed
```

## How it works

1. A `UserPromptSubmit` hook runs `hooks/route.py` on every prompt.
2. The script scores complexity with fast, transparent heuristics (length, code blocks,
   sub-task count, multi-step chaining, file references, and complexity/simplicity
   keywords). No LLM call — it runs synchronously and stays quick.
3. The score maps to a tier → model:
   | Tier | Model | Model ID | Typical work |
   |------|-------|----------|--------------|
   | `trivial` | Haiku 4.5 | `claude-haiku-4-5` | definitions, renames, lookups, one-line edits |
   | `moderate` | Sonnet 4.6 | `claude-sonnet-4-6` | features, focused multi-file edits, routine debugging |
   | `complex` | Opus 4.8 | `claude-opus-4-8` | architecture, hard debugging, concurrency/security, big refactors |

   Agents reference these by alias (`haiku` / `sonnet` / `opus`) so they track the
   current model in each family.
4. The hook injects an instruction making the assistant **print the router banner as its
   first line**, then route the task to that tier.

### Why routing happens via delegation

Claude Code exposes **no hook field that hot-swaps the live session model** — only
`SessionStart` sees a read-only `model` value. So the actual model change happens by
**delegating** the work to the matching worker agent, each pinned to a model in its
frontmatter:

- `agents/router-haiku.md`  → `model: haiku`
- `agents/router-sonnet.md` → `model: sonnet`
- `agents/router-opus.md`   → `model: opus`

The assistant announces the tier, then hands non-trivial work to the right agent so it
runs on the chosen model. If you're already on a model at or above the recommended tier,
it just proceeds in-session.

## Install

Local / development:

```bash
claude --plugin-dir /path/to/model-router
```

Then `/reload-plugins` after edits.

## Usage

Routing is automatic — every prompt gets a banner. To inspect how a prompt *would* be
classified without doing the work:

```
/model-router:route Refactor the auth service and prove the token refresh is race-free
```

## Examples

Real classifier output across the difficulty range:

| Prompt | Routed to |
|--------|-----------|
| `what is a closure in javascript?` | 🧭 Haiku 4.5 — `trivial, score -3.0` (very short; simple ask) |
| `rename the variable foo to bar in utils.py` | 🧭 Haiku 4.5 — `trivial, score -3.0` |
| `give me a list of HTTP status codes` | 🧭 Haiku 4.5 — `trivial` |
| `add a --verbose flag to cli.py that prints debug logs and update the README` | 🧭 Sonnet 4.6 — `moderate, score 1.5` |
| `write a function to parse a CSV into a list of dicts and add a unit test` | 🧭 Sonnet 4.6 — `moderate` |
| `find why the /login endpoint returns 500 intermittently and fix it` | 🧭 Sonnet 4.6 — `moderate` |
| `refactor the auth service to fix a race condition in token refresh, then design a migration plan for the distributed cache and prove it is safe under concurrency` | 🧭 Opus 4.8 — `complex, score 5.5` (multi-step; concurrency, design, distributed) |
| `design a distributed rate limiter and prove it is correct under concurrency` | 🧭 Opus 4.8 — `complex, score 4.5` |
| `architect a multi-tenant billing system: schema, isolation, and migration strategy` | 🧭 Opus 4.8 — `complex` |

What pushes a prompt **up**: length, fenced code, 3+ sub-tasks, multi-step chaining
(`then`, `after that`), multiple file references, and keywords like *architect,
refactor, race condition, concurrency, security, distributed, migrate, optimize, prove*.

What pulls it **down**: very short, plus keywords like *what is, define, rename, typo,
list all, yes or no*.

Inspect any prompt without running it:

```
/model-router:route architect a multi-tenant billing system with tenant isolation
```

## Tuning

Edit the keyword lists and thresholds in `hooks/route.py`:

- `COMPLEX_KW` / `TRIVIAL_KW` — signal words that pull a prompt up or down.
- Score → tier cutoffs in `score()` (`>= 4` complex, `>= 1.5` moderate, else trivial).

Per-session overrides (environment variables):

| Var | Effect |
|-----|--------|
| `MODEL_ROUTER_FORCE=trivial\|moderate\|complex` | force a tier, skip scoring |
| `MODEL_ROUTER_FLOOR=trivial\|moderate\|complex` | never route below this tier |
| `MODEL_ROUTER_OFF=1` | disable routing for the session |

## Layout

```
model-router/
├── .claude-plugin/plugin.json
├── hooks/
│   ├── hooks.json          # UserPromptSubmit → route.py
│   └── route.py            # complexity scorer + banner/instruction emitter
├── agents/
│   ├── router-haiku.md     # model: haiku
│   ├── router-sonnet.md    # model: sonnet
│   └── router-opus.md      # model: opus
└── skills/route/SKILL.md   # /model-router:route — inspect a classification
```
