# Frontier provider backends

FSMReasonBench can run **R0** track pilots against paid API backends for cheap frontier-ish sanity checks. These backends reuse the same prompts, scoring, and artifact layout (`results.jsonl`, `scores.jsonl`, `summary.json`, `combined_summary.json`) as local Ollama runs.

**Important:** Gemini Flash and similar shortcuts are **not** a replacement for full frontier validation on your target production models. Use them to catch integration regressions, prompt/format issues, and coarse capability signals before spending on larger frontier runs.

## Supported providers

| Provider | Tracks | API key env vars | Default model alias |
|----------|--------|------------------|---------------------|
| `ollama` | R0, R1, R2 | — (local) | model name as passed to Ollama |
| `anthropic` | **R0 only** | `ANTHROPIC_API_KEY` | `opus` → `ANTHROPIC_MODEL` or `claude-opus-4-1` |
| `gemini` | **R0 only** | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | `gemini-flash` → `GEMINI_MODEL` or `gemini-2.5-flash` |

R1/R2 require native tool-calling support and are **not** implemented for Anthropic or Gemini. Validation fails explicitly if you pass `--tracks R1` or `R2` with those providers.

## Cost safety

- Paid providers print a **stderr warning** on every non–report-only invocation.
- Enforce caps with `--max-items` and `--max-cells`.
- Run `--estimate-only` first to write `frontier_estimate.json` (no API key required).
- Run `--provider-dry-run` to write `provider_dry_run.json` with sample request shapes (no API call).

## Transient API errors (Gemini / Anthropic)

Gemini can return **HTTP 429** (rate limit) or **503 UNAVAILABLE** under high demand. These are treated as **transient** and retried per item with exponential backoff (default base 5s → ~5s, 15s, 45s with jitter) before skipping the item.

Use provider-neutral retry flags (Ollama aliases remain supported):

| Flag | Default | Purpose |
|------|---------|---------|
| `--provider-retries N` | `0` (or `--ollama-retries`) | Per-item retries after transient HTTP or Ollama timeout |
| `--provider-retry-backoff SECONDS` | `5` | Base delay for exponential backoff |
| `--skip-item-on-timeout` | on | Record `infrastructure_failure=true` and continue cell |

Missing API keys and non-retryable HTTP errors (4xx except 429) still fail immediately.

## Anthropic example (R0 smoke)

```bash
export ANTHROPIC_API_KEY=...

PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --provider anthropic \
  --models opus \
  --families C2,F1 \
  --tracks R0 \
  --temperatures 0.2 \
  --max-items 30 \
  --max-tokens 8192 \
  --cohort-root cohorts/v0.1-expanded-n100 \
  --out-dir runs/frontier_anthropic_opus_smoke_v1 \
  --timeout 3600 \
  --retry-failed \
  --incremental-safe
```

Dry run (no API key):

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --provider anthropic \
  --models opus \
  --families C2,F1 \
  --tracks R0 \
  --temperatures 0.2 \
  --max-items 30 \
  --max-tokens 8192 \
  --cohort-root cohorts/v0.1-expanded-n100 \
  --out-dir runs/frontier_anthropic_opus_smoke_v1 \
  --provider-dry-run
```

## Gemini example (R0 smoke)

Gemini 2.5 Flash is the recommended **cheaper** frontier-ish backend for quick R0 checks. Start with a **low `--max-items` smoke**; Gemini **503/429** under load is normal — use retries/backoff below.

```bash
export GEMINI_API_KEY=...   # or GOOGLE_API_KEY

PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --provider gemini \
  --models gemini-flash \
  --families C2,F1 \
  --tracks R0 \
  --temperatures 0.2 \
  --max-items 10 \
  --max-tokens 8192 \
  --provider-retries 2 \
  --provider-retry-backoff 5 \
  --skip-item-on-timeout \
  --cohort-root cohorts/v0.1-expanded-n100 \
  --out-dir runs/frontier_gemini_flash_smoke_v1 \
  --timeout 3600 \
  --retry-failed \
  --incremental-safe
```

Scale up `--max-items` after smoke passes; keep the same retry/backoff flags.

Dry run (no API key):

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --provider gemini \
  --models gemini-flash \
  --families C2,F1 \
  --tracks R0 \
  --temperatures 0.2 \
  --max-items 30 \
  --max-tokens 8192 \
  --cohort-root cohorts/v0.1-expanded-n100 \
  --out-dir runs/frontier_gemini_flash_smoke_v1 \
  --provider-dry-run
```

Estimate only (no API key):

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --provider gemini \
  --models gemini-flash \
  --families C2,F1 \
  --tracks R0 \
  --temperatures 0.2 \
  --max-items 30 \
  --max-tokens 8192 \
  --cohort-root cohorts/v0.1-expanded-n100 \
  --out-dir runs/frontier_gemini_flash_smoke_v1 \
  --estimate-only
```

Explicit model override: pass the full Google model id via `--models`, or set `GEMINI_MODEL` in the environment.
