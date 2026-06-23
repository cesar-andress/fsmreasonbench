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

Gemini can return **HTTP 429** (quota/rate limit) or **503 UNAVAILABLE** under high demand. These are retried per item with exponential backoff and optional **Retry-After** honoring before skipping the item.

Provider failures are scored with `failure_stage=provider_error` and **`infrastructure_failure=true`** — they are **not** model extraction failures. Per-cell summaries expose `provider_error_count`, `provider_quota_error_count` (429 quota/rate-limit), and `model_extractability_rate` (extractable / items that received model output).

Use provider throttling on cheap Gemini smokes:

| Flag | Default | Purpose |
|------|---------|---------|
| `--provider-sleep-between-items SECONDS` | `0` | Pause between items to avoid burst rate limits |
| `--provider-retries N` | `0` (or `--ollama-retries`) | Per-item retries after transient HTTP or Ollama timeout |
| `--provider-backoff-base SECONDS` | `5` | Base delay for exponential backoff (alias: `--provider-retry-backoff`) |
| `--provider-max-retry-delay SECONDS` | `120` | Cap per-retry sleep (prevents hour-long backoff) |
| `--skip-item-on-timeout` | on | Record `infrastructure_failure=true` and continue cell |

**Quota exhausted (`429 quota_exceeded`):** not retried during a run — the item is skipped immediately with a stderr warning. Retries apply only to transient rate limits and 503 unavailable errors.

**Recommended low-cost Gemini smoke:** `--max-items 10 --provider-sleep-between-items 10 --provider-retries 3 --provider-backoff-base 15 --provider-max-retry-delay 120`

Missing API keys and non-retryable HTTP errors (4xx except 429) still fail immediately.

## Gemini JSON output contract

For `provider=gemini`, R0 prompts append a strict JSON contract (single object, no markdown fences, `certificate` must be an object). The Gemini API request sets `generationConfig.responseMimeType` to `application/json` so responses are JSON-shaped. The runner still applies harmless extraction (fence stripping, first balanced object, JSON-object certificate strings) before the unchanged family parser runs.

Use **`--provider-retries 2`** (or higher) on Gemini smokes; most v1 non-extractable items were transient **503** failures, not parse errors.

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
  --provider-sleep-between-items 10 \
  --provider-retries 5 \
  --provider-backoff-base 15 \
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
