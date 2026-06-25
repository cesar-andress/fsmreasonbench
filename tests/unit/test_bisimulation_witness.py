"""Tests for bisimulation_witness certificate contract."""

from __future__ import annotations

from fsmreasonbench.certificates.separation import build_bisimulation_witness_certificate
from fsmreasonbench.experiments.constructible_equivalence_study import filter_equivalence_subset
from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item
from fsmreasonbench.verifier.separation import verify_bisimulation_witness_certificate


def test_gold_bisimulation_witness_passes() -> None:
    item = generate_separation_item(
        21,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    cert = build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
    result = verify_bisimulation_witness_certificate(item.fsm_a, item.fsm_b, cert)
    assert result.valid
    assert cert["certificate_type"] == "bisimulation_witness"
    assert "minimized_hash" not in str(cert["payload"])


def test_equivalence_witness_still_supported() -> None:
    from fsmreasonbench.certificates.separation import build_equivalence_witness_certificate

    item = generate_separation_item(
        21,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    cert = build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
    from fsmreasonbench.verifier.separation import verify_equivalence_witness_certificate

    result = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, cert)
    assert result.valid


def test_filter_equivalence_subset_from_cohort() -> None:
    from fsmreasonbench.cohort.expanded_n100 import EXPANDED_COHORT_ROOT, resolve_cohort_bundle
    from fsmreasonbench.dev.doc_consistency import find_repo_root
    from fsmreasonbench.evaluator.jsonl import load_items_jsonl

    repo = find_repo_root()
    _c2, f1_items, _c2id, _f1id = resolve_cohort_bundle(repo / EXPANDED_COHORT_ROOT)
    items = load_items_jsonl(f1_items)
    subset = filter_equivalence_subset(items)
    assert len(subset) == 51
    assert len(items) == 100
