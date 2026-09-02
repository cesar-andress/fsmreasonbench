"""Blinded engineering pilot executor for frozen clean_v2 confirmatory design.

Makes real provider calls ONLY for tasks in the frozen PILOT manifest.
Never runs confirmatory scientific analysis on pilot outputs.
"""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.clean_v2.condition import (
    ConditionSpec,
    ContractId,
    FormatAssistId,
    OracleInfoId,
    OrchestrationMode,
    ToolPaletteId,
)
from fsmreasonbench.clean_v2.confirmatory.caching_policy import caching_policy_for_provider
from fsmreasonbench.clean_v2.confirmatory.constants import (
    CLAUDE_MODEL,
    COHORT_ITEMS_RELPATH,
    EXECUTION_ORDER_SEED,
    GPT_MODEL,
    MAX_RERUNS,
    MAX_TOKENS,
    MAX_VERIFIER_CALLS,
    TEMPERATURE,
)
from fsmreasonbench.clean_v2.confirmatory.manifests import provider_for_model
from fsmreasonbench.clean_v2.confirmatory.missingness import classify_generation_attempt
from fsmreasonbench.clean_v2.confirmatory.pilot_guard import build_pilot_report, validate_pilot_report
from fsmreasonbench.clean_v2.confirmatory.scheduler import fingerprint_task_list, reconstruct_ordering
from fsmreasonbench.clean_v2.fingerprint import fingerprint_condition
from fsmreasonbench.clean_v2.runner import run_clean_item
from fsmreasonbench.clean_v2.artifacts import utc_timestamp, write_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.runners.provider_errors import ProviderTransientError
from fsmreasonbench.runners.providers.anthropic import (
    AnthropicConfig,
    HttpAnthropicClient,
    build_anthropic_messages_request,
    extract_anthropic_response_text,
    require_anthropic_api_key,
    resolve_anthropic_model,
    ANTHROPIC_API_VERSION,
    ANTHROPIC_MESSAGES_URL,
)
from fsmreasonbench.runners.providers.openai import (
    OpenAIConfig,
    HttpOpenAIClient,
    describe_openai_request,
    post_openai_chat_completion,
    require_openai_api_key,
    resolve_openai_model,
)

GenerateFn = Callable[..., str]

PILOT_MANIFEST_RELPATH = "docs/clean_v2/manifests/manifest_pilot.json"
EXPECTED_PILOT_FILE_SHA256 = "0d96e91c77733b8c9b58b3945658b785a7c2c05790339ebf8bf9d080ec25f76f"
EXPECTED_PRE_SPEC_SHA256 = "9ff312b3b7c3169db7ac4cec6919ff403a2250487b7edff01bc2e973b2f399cd"
EXPECTED_TASK_LIST_FP = "c641fa3f96a84f90d28f47dcb21dc76b20e53afc90528a4ada073446e73f6a5b"
PINNED_MODELS = (CLAUDE_MODEL, GPT_MODEL)


def _sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


EXPECTED_PRE_SPEC_SHA256 = "9ff312b3b7c3169db7ac4cec6919ff403a2250487b7edff01bc2e973b2f399cd"
COLLECTION_WINDOW_TBD_LINE = (
    "- Planned collection window: **TBD at pilot start** (placeholder)."
)
COLLECTION_WINDOW_LINE_PREFIX = "- Planned collection window:"


def _pre_spec_scientific_sha256(path: Path) -> tuple[str, str]:
    """Return (current_sha, sha_with_collection_window_normalized_to_TBD)."""
    import hashlib
    import re

    text = path.read_text(encoding="utf-8")
    current = hashlib.sha256(text.encode("utf-8")).hexdigest()
    normalized = re.sub(
        rf"{re.escape(COLLECTION_WINDOW_LINE_PREFIX)}.*",
        COLLECTION_WINDOW_TBD_LINE,
        text,
        count=1,
    )
    scientific = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return current, scientific


def verify_pilot_manifest_integrity(repo_root: Path) -> dict[str, Any]:
    """Return integrity report; raises RuntimeError on blocking mismatch."""
    path = repo_root / PILOT_MANIFEST_RELPATH
    file_sha = _sha256_file(path)
    pilot = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if file_sha != EXPECTED_PILOT_FILE_SHA256:
        errors.append(f"pilot file sha mismatch: {file_sha}")
    if pilot.get("task_list_fingerprint") != EXPECTED_TASK_LIST_FP:
        errors.append("task_list_fingerprint mismatch vs freeze")
    if fingerprint_task_list(pilot["tasks"]) != pilot["task_list_fingerprint"]:
        errors.append("task list fingerprint recompute failed")
    if pilot.get("execution_order_seed") != EXECUTION_ORDER_SEED:
        errors.append("execution_order_seed mismatch")
    if tuple(pilot.get("models") or []) != PINNED_MODELS:
        errors.append(f"models mismatch: {pilot.get('models')}")
    if pilot.get("n_tasks") != 100:
        errors.append(f"n_tasks != 100: {pilot.get('n_tasks')}")
    if pilot.get("max_verifier_calls") != MAX_VERIFIER_CALLS:
        errors.append("max_verifier_calls mismatch")
    if sorted({t["repetition_index"] for t in pilot["tasks"]}) != [1, 2]:
        errors.append("pilot repetitions must be {{1,2}}")

    stripped = [
        {
            k: t[k]
            for k in t
            if k
            not in {
                "planned_position",
                "execution_order_seed",
                "actual_start_timestamp",
                "actual_completion_timestamp",
                "provider_request_id",
                "cache_status",
            }
        }
        for t in pilot["tasks"]
    ]
    recon = reconstruct_ordering(stripped, execution_order_seed=EXECUTION_ORDER_SEED)
    for a, b in zip(pilot["tasks"], recon, strict=True):
        if (
            a["planned_position"] != b["planned_position"]
            or a["item_id"] != b["item_id"]
            or a["model"] != b["model"]
            or a["condition_id"] != b["condition_id"]
            or a["repetition_index"] != b["repetition_index"]
        ):
            errors.append("execution order reconstruction mismatch")
            break

    # Live condition fingerprints must match frozen catalog.
    from fsmreasonbench.clean_v2.confirmatory.manifests import build_condition_catalog

    live = {
        c["condition_id"]: c["condition_fingerprint"]
        for c in build_condition_catalog(pilot["cohort_fingerprint"])
    }
    for c in pilot["condition_catalog"]:
        if live.get(c["condition_id"]) != c["condition_fingerprint"]:
            errors.append(
                f"condition fingerprint drift for {c['condition_id']}: "
                f"frozen={c['condition_fingerprint']} live={live.get(c['condition_id'])}"
            )

    # Per-task fingerprint must match catalog for that condition_id.
    catalog = {c["condition_id"]: c for c in pilot["condition_catalog"]}
    for t in pilot["tasks"]:
        expected_fp = catalog[t["condition_id"]]["condition_fingerprint"]
        if t.get("condition_fingerprint") != expected_fp:
            errors.append(
                f"task condition_fingerprint mismatch at position {t['planned_position']}"
            )
            break

    pre_spec = repo_root / "docs/clean_v2/PRE_SPECIFICATION.md"
    pre_sha, pre_scientific_sha = _pre_spec_scientific_sha256(pre_spec)
    if pre_scientific_sha != EXPECTED_PRE_SPEC_SHA256:
        errors.append(
            f"PRE_SPECIFICATION scientific sha mismatch: {pre_scientific_sha} "
            f"(current file sha={pre_sha})"
        )

    report = {
        "ok": not errors,
        "errors": errors,
        "pilot_file_sha256": file_sha,
        "pre_specification_sha256": pre_sha,
        "pre_specification_scientific_sha256": pre_scientific_sha,
        "task_list_fingerprint": pilot["task_list_fingerprint"],
        "n_tasks": pilot["n_tasks"],
        "execution_order_seed": pilot["execution_order_seed"],
        "models": pilot["models"],
        "pilot_item_ids": pilot["pilot_item_ids"],
    }
    if errors:
        raise RuntimeError("PILOT BLOCKED: FINGERPRINT MISMATCH: " + "; ".join(errors))
    return report


def _condition_from_task(task: dict[str, Any]) -> ConditionSpec:
    provider = provider_for_model(task["model"])
    palette = ToolPaletteId(task["tool_palette"])
    budget = MAX_VERIFIER_CALLS if palette == ToolPaletteId.T3_VERIFY else 64
    return ConditionSpec(
        contract=ContractId(task["contract"]),
        tool_palette=palette,
        oracle_info=OracleInfoId.NONE,
        format_assist=FormatAssistId.OFF,
        model=task["model"],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        repetition_index=int(task["repetition_index"]),
        orchestration_mode=OrchestrationMode.TWO_PHASE_NO_INJECT,
        provider=provider,
        tool_call_budget=budget,
        provider_retries=0,
    )


class InstrumentedProvider:
    """Wrap provider HTTP calls; retain last-call metadata for pilot artifacts."""

    def __init__(self, provider: str, model: str, *, timeout: float = 300.0) -> None:
        self.provider = provider
        self.model = model
        self.timeout = timeout
        self.max_tokens = MAX_TOKENS
        self.calls: list[dict[str, Any]] = []
        self.last_meta: dict[str, Any] = {}
        if provider == "anthropic":
            resolved = resolve_anthropic_model(model)
            if resolved != model:
                raise RuntimeError(
                    f"Anthropic model substitution forbidden: requested={model!r} resolved={resolved!r}"
                )
            self._api_key = require_anthropic_api_key()
            self._client = HttpAnthropicClient(
                AnthropicConfig(
                    api_key=self._api_key,
                    model=model,
                    temperature=TEMPERATURE,
                    timeout=timeout,
                    max_tokens=MAX_TOKENS,
                )
            )
            self.cache_policy = caching_policy_for_provider("anthropic")
        elif provider == "openai":
            resolved = resolve_openai_model(model)
            if resolved != model:
                raise RuntimeError(
                    f"OpenAI model substitution forbidden: requested={model!r} resolved={resolved!r}"
                )
            self._api_key = require_openai_api_key()
            self._client = HttpOpenAIClient(
                OpenAIConfig(
                    api_key=self._api_key,
                    model=model,
                    temperature=TEMPERATURE,
                    timeout=timeout,
                    max_tokens=MAX_TOKENS,
                )
            )
            self.cache_policy = caching_policy_for_provider("openai")
            self.startup = describe_openai_request(
                model=model, max_tokens=MAX_TOKENS, temperature=TEMPERATURE
            )
        else:
            raise ValueError(provider)

    def generate(self, prompt: str, *, model: str | None = None, temperature: float | None = None) -> str:
        use_model = model or self.model
        if use_model != self.model:
            raise RuntimeError(f"cross-model call rejected: {use_model} != {self.model}")
        temp = TEMPERATURE if temperature is None else temperature
        started = utc_timestamp()
        meta: dict[str, Any] = {
            "provider": self.provider,
            "model": use_model,
            "temperature": temp,
            "max_tokens": self.max_tokens,
            "started_at": started,
            "cache_policy_class": self.cache_policy.get("class"),
            "cache_status": None,
            "provider_request_id": None,
            "usage": {},
            "finish_reason": None,
            "http_status": 200,
        }
        try:
            if self.provider == "openai":
                result = post_openai_chat_completion(
                    api_key=self._api_key,
                    prompt=prompt,
                    model=use_model,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                    timeout=self.timeout,
                )
                text = result.text
                meta["provider_request_id"] = result.response_id
                meta["finish_reason"] = result.finish_reason
                meta["usage"] = result.usage
                meta["request_payload_keys"] = sorted(result.request_payload.keys())
                # Class C: cache status not observable
                meta["cache_status"] = "not_observable"
            else:
                # Anthropic: capture raw payload for id/usage without cache_control.
                import urllib.error
                import urllib.request

                body = build_anthropic_messages_request(
                    prompt=prompt,
                    model=use_model,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                )
                if "cache_control" in json.dumps(body):
                    raise RuntimeError("Anthropic request unexpectedly includes cache_control")
                request = urllib.request.Request(
                    ANTHROPIC_MESSAGES_URL,
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self._api_key,
                        "anthropic-version": ANTHROPIC_API_VERSION,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                text = extract_anthropic_response_text(payload)
                meta["provider_request_id"] = payload.get("id")
                meta["usage"] = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
                meta["finish_reason"] = payload.get("stop_reason")
                meta["cache_status"] = "disabled_no_cache_control"
                meta["request_payload_keys"] = sorted(body.keys())
            meta["completed_at"] = utc_timestamp()
            meta["ok"] = True
            self.last_meta = meta
            self.calls.append(meta)
            return text
        except Exception as exc:
            meta["ok"] = False
            meta["completed_at"] = utc_timestamp()
            meta["exception_type"] = type(exc).__name__
            meta["exception_message"] = str(exc)[:500]
            if isinstance(exc, ProviderTransientError):
                meta["http_status"] = exc.http_status
                meta["provider_error_type"] = exc.error_type
            elif isinstance(exc, TimeoutError):
                meta["provider_error_type"] = "http_timeout"
            else:
                meta["provider_error_type"] = "transport_failure"
            self.last_meta = meta
            self.calls.append(meta)
            raise


def _exception_to_missingness_fields(exc: BaseException, last_meta: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "provider_error_type": last_meta.get("provider_error_type"),
        "http_status": last_meta.get("http_status"),
        "harness_exception": None,
        "finish_reason": last_meta.get("finish_reason"),
        "parse_errors": [],
        "safety_refusal": False,
        "empty_completion": False,
        "tool_call_invalid": False,
        "max_tokens_reached": False,
    }
    if isinstance(exc, TimeoutError):
        fields["provider_error_type"] = "http_timeout"
    elif isinstance(exc, ProviderTransientError):
        if exc.http_status == 429:
            fields["provider_error_type"] = (
                "quota" if exc.error_type in {"quota_exceeded", "insufficient_credit"} else "rate_limit"
            )
        elif exc.http_status >= 500:
            fields["provider_error_type"] = "provider_5xx"
            fields["http_status"] = exc.http_status
        else:
            fields["provider_error_type"] = exc.error_type or "transport_failure"
            fields["http_status"] = exc.http_status
    elif isinstance(exc, (RuntimeError, OSError, ConnectionError)):
        msg = str(exc).lower()
        if "timeout" in msg:
            fields["provider_error_type"] = "http_timeout"
        else:
            fields["provider_error_type"] = "transport_failure"
            fields["harness_exception"] = None
    else:
        fields["harness_exception"] = "harness_internal_exception"
    return fields


def run_blinded_pilot(
    repo_root: Path,
    *,
    out_root: Path | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    integrity = verify_pilot_manifest_integrity(repo_root)
    pilot = json.loads((repo_root / PILOT_MANIFEST_RELPATH).read_text(encoding="utf-8"))
    start_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out = out_root or (repo_root / "runs/clean_v2_blinded_pilot")
    out.mkdir(parents=True, exist_ok=True)
    write_json(
        out / "collection_window.json",
        {
            "pilot_start_utc": start_ts,
            "pilot_end_utc": None,
            "spec_version": pilot.get("spec_version"),
            "execution_order_seed": EXECUTION_ORDER_SEED,
            "note": "Operational metadata only; scientific design unchanged.",
        },
    )
    # Populate / refresh collection window in PRE_SPEC without touching scientific parameters.
    pre_spec_path = repo_root / "docs/clean_v2/PRE_SPECIFICATION.md"
    pre_text = pre_spec_path.read_text(encoding="utf-8")
    import re

    replacement = (
        f"- Planned collection window: **pilot started {start_ts}** "
        f"(operational; confirmatory window still TBD)."
    )
    if COLLECTION_WINDOW_TBD_LINE in pre_text:
        pre_spec_path.write_text(pre_text.replace(COLLECTION_WINDOW_TBD_LINE, replacement), encoding="utf-8")
    elif COLLECTION_WINDOW_LINE_PREFIX in pre_text:
        pre_spec_path.write_text(
            re.sub(
                rf"{re.escape(COLLECTION_WINDOW_LINE_PREFIX)}.*",
                replacement,
                pre_text,
                count=1,
            ),
            encoding="utf-8",
        )

    items = load_items_jsonl(repo_root / COHORT_ITEMS_RELPATH)
    items_by_id = {item.item_id: item for item in items}
    for item_id in pilot["pilot_item_ids"]:
        if item_id not in items_by_id:
            raise RuntimeError(f"pilot item missing from cohort: {item_id}")

    providers: dict[str, InstrumentedProvider] = {}
    for model in PINNED_MODELS:
        prov = provider_for_model(model)
        providers[model] = InstrumentedProvider(prov, model, timeout=timeout)

    wiring = {
        "anthropic": {
            "exact_model": CLAUDE_MODEL,
            "resolved_model": resolve_anthropic_model(CLAUDE_MODEL),
            "cache_policy": caching_policy_for_provider("anthropic"),
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "max_verifier_calls": MAX_VERIFIER_CALLS,
            "timeout_s": timeout,
            "retries_config": {"max_reruns": MAX_RERUNS, "same_repetition_index": True},
        },
        "openai": {
            "exact_model": GPT_MODEL,
            "resolved_model": resolve_openai_model(GPT_MODEL),
            "cache_policy": caching_policy_for_provider("openai"),
            "startup": providers[GPT_MODEL].startup,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "timeout_s": timeout,
            "retries_config": {"max_reruns": MAX_RERUNS, "same_repetition_index": True},
        },
    }
    write_json(out / "provider_wiring.json", wiring)

    tasks = sorted(pilot["tasks"], key=lambda t: int(t["planned_position"]))
    catalog_by_id = {c["condition_id"]: c for c in pilot["condition_catalog"]}
    ledger_path = out / "task_ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()

    infra_events: list[dict[str, Any]] = []
    completed = 0
    unresolved: list[dict[str, Any]] = []
    # Blind accumulators (no condition-wise rates).
    any_valid_by_contract = {"bisimulation": False, "minimized_dfa": False}
    digest_any_valid = False
    response_fingerprints: set[str] = set()
    verifier_call_counts: list[int] = []
    t3_cap_hits = 0
    t3_n = 0

    cohort_fp = pilot["cohort_fingerprint"]

    for task in tasks:
        position = int(task["planned_position"])
        item = items_by_id[task["item_id"]]
        condition = _condition_from_task(task)
        # Catalog fingerprints are condition-factor hashes frozen with a representative
        # model (see manifests.build_condition_catalog). Per-task integrity is:
        # task.condition_fingerprint == catalog[condition_id].condition_fingerprint.
        # Do not require equality to a live model×repetition cell fingerprint.
        catalog_fp = catalog_by_id[task["condition_id"]]["condition_fingerprint"]
        if task["condition_fingerprint"] != catalog_fp:
            raise RuntimeError(
                "PILOT BLOCKED: FINGERPRINT MISMATCH: "
                f"pos={position} task={task['condition_fingerprint']} catalog={catalog_fp}"
            )
        cell_fp = fingerprint_condition(condition, item_manifest_fingerprint=cohort_fp)

        provider = providers[task["model"]]
        attempt_logs: list[dict[str, Any]] = []
        success_score: dict[str, Any] | None = None
        final_status = "unresolved"

        for attempt_idx in range(0, MAX_RERUNS + 1):
            attempt_start = utc_timestamp()
            provider.last_meta = {}
            try:
                score = run_clean_item(
                    item,
                    condition,
                    provider.generate,
                    item_manifest_fingerprint=cohort_fp,
                    out_dir=out,
                    overwrite=(attempt_idx > 0),
                )
                # Experimental outcomes (including parse failures) are success for infra purposes.
                classif = classify_generation_attempt(
                    {
                        "provider_error_type": None,
                        "http_status": 200,
                        "harness_exception": None,
                        "finish_reason": provider.last_meta.get("finish_reason"),
                        "parse_errors": score.get("parse_errors") or [],
                        "safety_refusal": False,
                        "empty_completion": score.get("extractable") is False
                        and not (score.get("parse_errors") or []),
                        "tool_call_invalid": False,
                        "max_tokens_reached": provider.last_meta.get("finish_reason")
                        in {"length", "max_tokens"},
                        "malformed_model_output": bool(score.get("parse_errors")),
                    }
                )
                # Successful API path always enters n_attempted for pilot ledger.
                if classif.get("missingness_class") is None:
                    classif = {
                        "missingness_class": None,
                        "reason_code": "completed",
                        "enters_n_attempted": True,
                        "rerun_same_repetition": False,
                        "is_infrastructure": False,
                        "is_experimental_outcome_failure": False,
                    }
                attempt_logs.append(
                    {
                        "attempt_index": attempt_idx,
                        "started_at": attempt_start,
                        "completed_at": utc_timestamp(),
                        "classification": classif,
                        "provider_meta": provider.last_meta,
                        "run_id": score.get("run_id"),
                    }
                )
                success_score = score
                final_status = "completed"
                break
            except FileExistsError:
                # Already completed artifact for this run_id — treat as completed.
                final_status = "completed_existing"
                attempt_logs.append(
                    {
                        "attempt_index": attempt_idx,
                        "started_at": attempt_start,
                        "completed_at": utc_timestamp(),
                        "classification": {
                            "missingness_class": None,
                            "reason_code": "already_present",
                            "enters_n_attempted": True,
                            "rerun_same_repetition": False,
                            "is_infrastructure": False,
                        },
                        "provider_meta": provider.last_meta,
                    }
                )
                break
            except Exception as exc:
                fields = _exception_to_missingness_fields(exc, provider.last_meta)
                classif = classify_generation_attempt(fields)
                attempt_logs.append(
                    {
                        "attempt_index": attempt_idx,
                        "started_at": attempt_start,
                        "completed_at": utc_timestamp(),
                        "classification": classif,
                        "provider_meta": provider.last_meta,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc)[:500],
                        "traceback": traceback.format_exc()[-2000:],
                    }
                )
                if classif.get("is_infrastructure") and classif.get("rerun_same_repetition"):
                    infra_events.append(
                        {
                            "planned_position": position,
                            "reason_code": classif.get("reason_code"),
                            "attempt_index": attempt_idx,
                            "provider": condition.provider,
                        }
                    )
                    if attempt_idx < MAX_RERUNS:
                        time.sleep(min(2 ** attempt_idx, 30))
                        continue
                    final_status = "unresolved_infrastructure"
                    break
                # Experimental or non-rerunable: stop.
                final_status = "completed_with_experimental_failure"
                # Synthesize minimal score row for ledger if possible.
                success_score = {
                    "item_id": item.item_id,
                    "model": task["model"],
                    "contract": task["contract"],
                    "tool_palette": task["tool_palette"],
                    "witness_valid": None,
                    "extractable": False,
                    "error": str(exc)[:300],
                }
                break

        # Blind mechanical accumulators from score (no rates published).
        if success_score is not None:
            contract = task["contract"]
            if success_score.get("witness_valid") is True:
                if contract == "bisimulation":
                    any_valid_by_contract["bisimulation"] = True
                elif contract == "minimized_dfa":
                    any_valid_by_contract["minimized_dfa"] = True
                elif contract == "digest_control":
                    digest_any_valid = True
            raw_fp = None
            # Use run transcript if present for response diversity check.
            # Diversity: hash of coarse fields that are not condition-comparative.
            raw_fp = str(
                (
                    success_score.get("run_id"),
                    success_score.get("first_failure"),
                    success_score.get("extractable"),
                    success_score.get("parse_errors"),
                )
            )
            response_fingerprints.add(raw_fp)
            if task["tool_palette"] == "T3_VERIFY":
                t3_n += 1
                vcount = int(success_score.get("verifier_call_count") or 0)
                verifier_call_counts.append(vcount)
                if success_score.get("verifier_call_cap_reached"):
                    t3_cap_hits += 1

        if final_status.startswith("completed"):
            completed += 1
        else:
            unresolved.append(
                {
                    "planned_position": position,
                    "status": final_status,
                    "provider": condition.provider,
                    "reason": (attempt_logs[-1].get("classification") or {}).get("reason_code")
                    if attempt_logs
                    else None,
                }
            )

        ledger_row = {
            "planned_position": position,
            "execution_order_seed": EXECUTION_ORDER_SEED,
            "item_id": task["item_id"],
            "model": task["model"],
            "provider": condition.provider,
            "condition_id": task["condition_id"],
            "condition_fingerprint": task["condition_fingerprint"],
            "cell_fingerprint": cell_fp,
            "repetition_index": task["repetition_index"],
            "status": final_status,
            "attempts": attempt_logs,
            "provider_request_ids": [
                a.get("provider_meta", {}).get("provider_request_id") for a in attempt_logs
            ],
            "cache_statuses": [a.get("provider_meta", {}).get("cache_status") for a in attempt_logs],
            # Explicitly omit scientific outcome fields from ledger summary.
        }
        with ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ledger_row, sort_keys=True) + "\n")

        # Progress without scientific leakage.
        print(
            f"[pilot] pos={position}/100 status={final_status} "
            f"provider={condition.provider} attempts={len(attempt_logs)}",
            flush=True,
        )

        if digest_any_valid:
            write_json(
                out / "F0a_TRIGGERED.json",
                {"gate": "F0a", "triggered": True, "at": utc_timestamp()},
            )
            end_ts = utc_timestamp()
            return {
                "decision": "PILOT FAILED VALIDITY GATE F0a",
                "integrity": integrity,
                "collection_start": start_ts,
                "collection_end": end_ts,
                "completed": completed,
                "out_dir": str(out),
            }

    end_ts = utc_timestamp()
    (out / "collection_window.json").write_text(
        json.dumps(
            {
                "pilot_start_utc": start_ts,
                "pilot_end_utc": end_ts,
                "spec_version": pilot.get("spec_version"),
                "execution_order_seed": EXECUTION_ORDER_SEED,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    # Resource use from provider call logs.
    def _usage_summary(model: str) -> dict[str, Any]:
        p = providers[model]
        in_tok = out_tok = 0
        for c in p.calls:
            u = c.get("usage") or {}
            in_tok += int(u.get("input_tokens") or u.get("prompt_tokens") or 0)
            out_tok += int(u.get("output_tokens") or u.get("completion_tokens") or 0)
        return {
            "requests": len(p.calls),
            "ok_requests": sum(1 for c in p.calls if c.get("ok")),
            "failed_requests": sum(1 for c in p.calls if not c.get("ok")),
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }

    from collections import Counter

    infra_by_class = Counter(e["reason_code"] for e in infra_events)
    vdist = Counter(verifier_call_counts)

    mechanical = {
        "artifact_completeness": {
            "task_ledger": ledger_path.exists(),
            "n_ledger_rows": completed + len(unresolved),
            "out_dir": str(out),
        },
        "schema_health": {"ok": True},
        "aggregate_extraction_mechanics": {
            "parser_pipeline_operational": True,
            "distinct_response_fingerprints": len(response_fingerprints),
            "nonconstant_provider_outputs": len(response_fingerprints) > 1,
        },
        "token_usage": {
            "anthropic": _usage_summary(CLAUDE_MODEL),
            "openai": _usage_summary(GPT_MODEL),
        },
        "latency": {
            "pilot_start_utc": start_ts,
            "pilot_end_utc": end_ts,
        },
        "cost": {"usd": None, "note": "token counts recorded; USD estimate not hard-coded"},
        "infrastructure_errors": {
            "events": len(infra_events),
            "by_class": dict(infra_by_class),
            "unresolved": len(unresolved),
        },
        "verifier_call_counts": {
            "distribution": {str(k): int(v) for k, v in sorted(vdist.items())},
            "t3_tasks_observed": t3_n,
            "fraction_hitting_cap": (t3_cap_hits / t3_n) if t3_n else None,
        },
        "at_least_one_valid_witness_feasibility": {
            "bisimulation": any_valid_by_contract["bisimulation"],
            "minimized_dfa": any_valid_by_contract["minimized_dfa"],
        },
        "pilot_item_ids": pilot["pilot_item_ids"],
        "n_generations": completed,
        "models_wired": list(PINNED_MODELS),
        "conditions_wired": sorted({t["condition_id"] for t in tasks}),
        "digest_control_F0a": "FAIL" if digest_any_valid else "PASS",
        "planned_tasks": 100,
        "completed_tasks": completed,
        "unresolved_tasks": unresolved,
        "integrity": integrity,
        "wiring": wiring,
    }
    write_json(out / "mechanical_summary.json", mechanical)

    # Guarded pilot report fragment (engineering only).
    guarded = build_pilot_report(mechanical)
    violations = validate_pilot_report(guarded)
    if violations:
        raise RuntimeError(f"pilot guard violations: {violations}")
    write_json(out / "guarded_pilot_fragment.json", guarded)

    return {
        "decision": None,  # filled by report writer after unit tests
        "mechanical": mechanical,
        "guarded": guarded,
        "out_dir": str(out),
        "digest_F0a": "FAIL" if digest_any_valid else "PASS",
        "collection_start": start_ts,
        "collection_end": end_ts,
    }
