# GPT frontier campaign (Claude-parity protocol)

> **TOSEM freeze:** Primary evidence is the frozen run tree `runs/frontier_gpt_tools_n100_v1/`.
> Reviewers should use `./scripts/reproduce_tosem_tables.sh` (read-only export). Modes
> `smoke`/`full`/`r1`/`r2` below require API keys and are **not part of reproduction**.

## API endpoint

OpenAI integration uses **Chat Completions**:

`POST https://api.openai.com/v1/chat/completions`

It is **not** the Responses API. Models such as **gpt-5** reject `max_tokens` on Chat
Completions and require **`max_completion_tokens`** instead; the provider selects the
correct field automatically from the resolved model id.

**gpt-5** (and o-series reasoning models) also reject custom **`temperature`** on Chat
Completions — only the server default (`1`) applies. The provider **omits** the field for
those models and prints a startup warning when the manifest requests another value (e.g.
`0.2`). For **T=0.2 Claude-parity** runs, set:

```bash
export OPENAI_MODEL=gpt-4.1
```

## Required workflow

```bash
export OPENAI_API_KEY=...
# optional override: export OPENAI_MODEL=gpt-4.1

cd fsmreasonbench

# 1) REQUIRED — one-request smoke test
./scripts/run_frontier_gpt_campaign.sh smoke

# 2) Only after smoke succeeds
./scripts/run_frontier_gpt_campaign.sh r1
./scripts/run_frontier_gpt_campaign.sh r2
# or: ./scripts/run_frontier_gpt_campaign.sh full

./scripts/run_frontier_gpt_campaign.sh report
./scripts/run_frontier_gpt_campaign.sh export
```

Do **not** launch n=100 cells until smoke succeeds.

## Model resolution and metadata

| Manifest `model` | Resolved id | Recorded in scores / combined_summary |
|------------------|-------------|---------------------------------------|
| `gpt` (alias) | `OPENAI_MODEL` or `gpt-5` | **resolved id only** |
| `gpt-4.1` | `gpt-4.1` | `gpt-4.1` |

Run directories use the resolved model slug, e.g. `runs/.../gpt-5/F1/temp_0.2/R1/`.
Earlier failed runs under `gpt/` should be discarded or rerun with `--force`.

Startup validation (printed once before the first scored item):

- provider, api_kind, endpoint
- resolved_model (+ model_arg if alias)
- output_limit_param
- full request_parameters JSON

## Smoke test output

`./scripts/run_frontier_gpt_campaign.sh smoke` reports:

- endpoint
- resolved model
- request payload
- response id
- token usage
- finish reason
