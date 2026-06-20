# model-router — OpenAI-compatible API adapter

For code that calls an OpenAI-compatible endpoint directly (OpenAI SDK, your own app, a
local **Ollama** / **LM Studio** server). There's no hook to intercept here — instead you
score the prompt and pick the model id *before* the request.

## Library

```python
from router import pick_model, classify

prompt = "design a distributed rate limiter and prove it is correct under concurrency"
model = pick_model(prompt)                 # -> "gpt-5-pro"
client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])

classify(prompt)
# {"tier": "complex", "model": "gpt-5-pro", "display": "GPT-5 Pro", "score": ..., "reasons": [...]}
```

## CLI (shell out from any language)

```bash
python3 adapters/openai-api/router.py "what is a closure in python"
# {"tier": "trivial", "model": "gpt-5-mini", "score": -3.0, "reasons": ["very short", "simple ask"]}
```

## Models

Defaults map the `openai` provider tiers. Point it at any OpenAI-compatible model family:

```bash
# local Ollama
MODEL_ROUTER_OPENAI_TRIVIAL=llama3.2:1b \
MODEL_ROUTER_OPENAI_MODERATE=llama3.1:8b \
MODEL_ROUTER_OPENAI_COMPLEX=llama3.1:70b \
python3 adapters/openai-api/router.py "refactor this and prove it correct"
```

Or set `MODEL_ROUTER_PROVIDER=gemini` to use the Gemini tier ids, or add your own block to
`core/providers.json`. Tier cutoffs / keywords live in `core/scorer.py`.
